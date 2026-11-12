'use client';

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import PasswordField from '@/components/PasswordField';
import api, { getApiError } from '@/lib/api';
import { grantWorkplacePhone, restoreWorkplacePhones, sendChallengeToGrantedPhones } from '@/lib/workplace-bluetooth';

type Challenge = { id: string; approval_code: string | null; expires_at: string; phone: boolean; approved_node_ids: string[]; approved_node_count: number };
type TrustStatus = {
  username: string; level: 'password' | 'remote' | 'office'; phone_enrolled: boolean;
  office_trust_enabled: boolean; nodes: { id: string; label: string }[];
  challenge: Challenge | null;
};
type ContactDone = { id: string; at: number; granted: number };

function announceAuthChange() { window.dispatchEvent(new Event('ucm-auth-change')); }

export default function Login() {
  const router = useRouter();
  const [phase, setPhase] = useState<'checking' | 'credentials' | 'approval'>('checking');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState<TrustStatus | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [pairing, setPairing] = useState('Checking selected trusted nodes…');
  const [bluetoothMessage, setBluetoothMessage] = useState('');
  const [contactDone, setContactDone] = useState<ContactDone | null>(null);
  const contactStarted = useRef('');
  const navigating = useRef(false);
  const autoAdvance = useRef(false);

  const refreshStatus = useCallback(async () => {
    try {
      const result = await api.get<TrustStatus>('/api/trust/status');
      setStatus(result.data);
      announceAuthChange();
      return result.data;
    } catch (failure) {
      setError(getApiError(failure, 'Could not check your approval. Try signing in again.'));
      return null;
    }
  }, []);

  const startRequest = useCallback(async () => {
    setBusy('request'); setError(''); setContactDone(null); setBluetoothMessage('');
    try {
      await api.post('/api/trust/start', {});
      autoAdvance.current = true;
      navigating.current = false;
      contactStarted.current = '';
      await refreshStatus();
    } catch (failure) { setError(getApiError(failure, 'Could not start phone approval.')); }
    finally { setBusy(''); }
  }, [refreshStatus]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const profile = await api.get('/api/me');
        if (!active) return;
        if (profile.data.data?.password_change_required) { router.replace('/services/security'); return; }
        const trust = await api.get<TrustStatus>('/api/trust/status');
        if (!active) return;
        autoAdvance.current = trust.data.level === 'password';
        setUsername(trust.data.username); setStatus(trust.data); setPhase('approval');
        if (trust.data.level === 'password' && trust.data.phone_enrolled && !trust.data.challenge) void startRequest();
      } catch { if (active) setPhase('credentials'); }
    })();
    return () => { active = false; };
  }, [router, startRequest]);

  useEffect(() => {
    if (phase !== 'approval') return;
    const timer = window.setInterval(() => { void refreshStatus(); }, 3000);
    return () => window.clearInterval(timer);
  }, [phase, refreshStatus]);

  useEffect(() => {
    if (!status?.office_trust_enabled) return;
    void restoreWorkplacePhones(status.username).then(result => {
      setPairing(result.supported
        ? `${result.count} trusted ${result.count === 1 ? 'node' : 'nodes'} previously selected in this browser.`
        : 'This browser cannot restore Bluetooth access. Choose nearby nodes in desktop Chrome or Edge.');
    }).catch(() => setPairing('Bluetooth is unavailable in this browser. Remote access still works.'));
  }, [status?.office_trust_enabled, status?.username]);

  const contact = useCallback(async (challengeId: string, account: string) => {
    setBluetoothMessage('Checking nearby trusted nodes…');
    try {
      const result = await sendChallengeToGrantedPhones(challengeId, account, setBluetoothMessage);
      const summary = result.granted === 0
        ? 'No selected trusted nodes found. Remote access will open after the phone approval.'
        : `${result.reached} of ${result.granted} Bluetooth requests sent. ${result.failures.join(' | ') || 'Waiting for signed node reports.'}`;
      setBluetoothMessage(summary);
      setContactDone({ id: challengeId, at: Date.now(), granted: result.granted });
      await refreshStatus();
    } catch (failure) {
      setBluetoothMessage(failure instanceof Error ? failure.message : 'Bluetooth check did not complete. Remote access remains available.');
      setContactDone({ id: challengeId, at: Date.now(), granted: 0 });
    }
  }, [refreshStatus]);

  useEffect(() => {
    const challenge = status?.challenge;
    if (phase !== 'approval' || !autoAdvance.current || !challenge?.phone || !status || contactStarted.current === challenge.id ||
        status.level === 'office') return;
    contactStarted.current = challenge.id;
    if (status.office_trust_enabled) void contact(challenge.id, status.username);
    else setContactDone({ id: challenge.id, at: Date.now(), granted: 0 });
  }, [phase, status, contact]);

  useEffect(() => {
    if (phase !== 'approval' || !status || navigating.current || !autoAdvance.current) return;
    if (status.level === 'office') {
      navigating.current = true; announceAuthChange(); router.replace('/services/confidential'); return;
    }
    if (status.level === 'remote' && contactDone &&
        (status.challenge?.id === contactDone.id || !status.challenge) &&
        Date.now() - contactDone.at >= (contactDone.granted ? 12000 : 2500)) {
      navigating.current = true; announceAuthChange(); router.replace('/services');
    }
  }, [phase, status, contactDone, router]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setBusy('login');
    try {
      const response = await api.post('/api/login', { username, password });
      if (!response.data.success) { setError(response.data.message); return; }
      setPassword(''); announceAuthChange();
      if (response.data.data?.password_change_required) { router.replace('/services/security'); return; }
      autoAdvance.current = true;
      const trust = await refreshStatus();
      if (!trust) return;
      setPhase('approval');
      if (trust.phone_enrolled) await startRequest();
    } catch (failure) { setError(getApiError(failure, 'Cannot reach UCM. Check that the server is running.')); }
    finally { setBusy(''); }
  }

  async function chooseNode() {
    if (!status) return;
    setBusy('bluetooth'); setError('');
    try {
      const count = await grantWorkplacePhone(status.username);
      setPairing(`${count} trusted ${count === 1 ? 'node' : 'nodes'} selected in this browser.`);
      if (status.challenge?.phone) {
        setContactDone(null);
        await contact(status.challenge.id, status.username);
      }
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Could not select this node.'); }
    finally { setBusy(''); }
  }

  async function switchAccount() {
    setBusy('logout'); setError('');
    try {
      await api.post('/api/logout', {});
      autoAdvance.current = false;
      navigating.current = false;
      contactStarted.current = '';
      setContactDone(null); setStatus(null); setUsername(''); setPassword('');
      setBluetoothMessage(''); setPhase('credentials'); announceAuthChange();
    } catch (failure) { setError(getApiError(failure, 'Could not sign out. Try again.')); }
    finally { setBusy(''); }
  }

  const phoneApproved = Boolean(status?.challenge?.phone || status?.level === 'remote' || status?.level === 'office');
  const officeApproved = status?.level === 'office';
  const levels = [
    { name: 'Password', detail: 'Credentials accepted', done: phase === 'approval' },
    { name: 'Remote', detail: 'Main phone approved', done: phoneApproved },
    { name: 'Office', detail: 'Two distinct trusted nodes signed', done: officeApproved },
  ];

  return <main className="login-workspace">
    <section className="login-context">
      <h1>Access, verified in stages.</h1>
      <p>Sign in with your password, approve on your phone, and use trusted workplace nodes for confidential access.</p>
      <div className="access-ledger" aria-label="Access checks">
        {levels.map(level => <div className="access-ledger-row" key={level.name}>
          <span className={'access-ledger-mark' + (level.done ? ' is-done' : '')} aria-hidden="true" />
          <span><strong>{level.name}</strong><small>{level.detail}</small></span>
          <span className="access-ledger-state">{level.done ? 'Complete' : 'Waiting'}</span>
        </div>)}
      </div>
      <p className="login-context-note">Your phone approval enables remote access. Two enrolled nodes can authorize confidential resources and administrator monitoring.</p>
    </section>

    <section className="login-work" aria-live="polite">
      {phase === 'checking' && <><h2>Checking your session</h2><p className="muted">One moment…</p></>}
      {phase === 'credentials' && <>
        <h2>Enter your account details</h2>
        <p className="muted">Your password starts the request.</p>
        <form className="form-stack" onSubmit={submit}>
          <label className="field" htmlFor="username">Username
            <input id="username" autoComplete="username" value={username} maxLength={64}
              onChange={event => setUsername(event.target.value)} required placeholder="Your username" />
          </label>
          <PasswordField id="password" label="Password" value={password} onChange={setPassword} />
          {error && <p className="notice error" role="alert">{error}</p>}
          <button className="btn full" disabled={!!busy}>{busy === 'login' ? 'Checking password…' : 'Continue securely'}</button>
        </form>
        <div className="login-work-footer"><span>New to UCM? <Link href="/register">Create an account</Link></span><span>Forgot your password? Use the UCM Android app.</span></div>
      </>}
      {phase === 'approval' && <>
        <h2>{status?.level === 'office' ? 'Office access is active' : status?.level === 'remote' ? 'Remote access is active' : status?.phone_enrolled ? 'Approve on your main phone' : 'Set up your main phone'}</h2>
        <p className="muted">Signed in as <strong>{status?.username ?? username}</strong>.</p>
        {error && <p className="notice error" role="alert">{error}</p>}
        {!status?.phone_enrolled ? <div className="approval-instruction"><p>Open the UCM Android app, choose <strong>Enroll</strong>, and enroll this account with your current password. Return here to start main-phone approval. Account pages remain locked until that approval.</p><button className="btn secondary small" onClick={() => void (async () => { const updated = await refreshStatus(); if (updated?.phone_enrolled) await startRequest(); })()}>I have enrolled my phone</button></div> : <>
          {status?.challenge && !phoneApproved ? <div className="approval-code"><span>Request code</span><code>{status.challenge.approval_code ?? status.challenge.id}</code><p>Enter this in the app’s <strong>Approve</strong> screen, then use your biometric.</p><small>Expires {new Date(status.challenge.expires_at).toLocaleTimeString()}.</small></div> :
            phoneApproved ? <div className="approval-instruction success"><strong>{officeApproved ? 'Office access is ready' : 'Main phone approved'}</strong><p>{officeApproved ? 'Confidential data is available while this approval remains active.' : 'Remote access is ready. Two trusted node signatures are needed for office access.'}</p></div> :
              <div className="approval-instruction"><p>The previous code expired. Start another request.</p></div>}
          <button className="btn secondary small" disabled={!!busy} onClick={() => void startRequest()}>Get a new code</button>
          {status?.office_trust_enabled && <div className="login-bluetooth">
            <h3>Trusted nodes</h3><p>{pairing}</p>
            <div className="login-bluetooth-actions"><button className="btn secondary small" disabled={!!busy} onClick={() => void chooseNode()}>Choose a nearby node</button></div>
            <div className="login-node-states"><span>Distinct node signatures <strong>{officeApproved ? 'Office grant active' : `${status.challenge?.approved_node_count ?? 0} of 2 required`}</strong></span></div>
            {bluetoothMessage && <p className="login-bluetooth-status" role="status">{bluetoothMessage}</p>}
          </div>}
          {phoneApproved && <button className="text-link login-continue" onClick={() => router.replace(officeApproved ? '/services/confidential' : '/services')}>{officeApproved ? 'Continue to confidential access' : 'Continue with remote access'}</button>}
        </>}
        <button className="text-link login-continue" disabled={!!busy} onClick={() => void switchAccount()}>Sign out and use another account</button>
      </>}
    </section>
  </main>;
}
