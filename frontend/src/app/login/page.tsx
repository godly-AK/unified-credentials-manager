'use client';

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import PasswordField from '@/components/PasswordField';
import api, { getApiError } from '@/lib/api';
import { grantWorkplacePhone, restoreWorkplacePhones, sendChallengeToGrantedPhones } from '@/lib/workplace-bluetooth';

type Challenge = { id: string; approval_code: string | null; expires_at: string; phone: boolean; node_a: boolean; node_b: boolean };
type TrustStatus = {
  username: string; level: 'password' | 'remote' | 'office'; phone_enrolled: boolean;
  office_trust_enabled: boolean; nodes: { id: string; slot: 'A' | 'B'; label: string }[];
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
  const [pairing, setPairing] = useState('Checking saved workplace tablets…');
  const [bluetoothMessage, setBluetoothMessage] = useState('');
  const [contactDone, setContactDone] = useState<ContactDone | null>(null);
  const contactStarted = useRef('');
  const navigating = useRef(false);

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
        if (trust.data.level === 'office') { router.replace('/services/confidential'); return; }
        if (trust.data.level === 'remote') { router.replace('/services'); return; }
        setUsername(trust.data.username); setStatus(trust.data); setPhase('approval');
        if (trust.data.phone_enrolled && !trust.data.challenge) void startRequest();
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
        ? `${result.count} of 2 workplace tablets previously selected in this browser.`
        : 'This browser cannot restore Bluetooth access. Choose each tablet below in desktop Chrome or Edge.');
    }).catch(() => setPairing('Bluetooth is unavailable in this browser. Remote access still works.'));
  }, [status?.office_trust_enabled, status?.username]);

  const contact = useCallback(async (challengeId: string, account: string) => {
    setBluetoothMessage('Checking the nearby workplace tablets…');
    try {
      const result = await sendChallengeToGrantedPhones(challengeId, account, setBluetoothMessage);
      const summary = result.granted === 0
        ? 'No permitted tablets found. Remote access will open after the phone approval.'
        : `${result.reached} of ${result.granted} Bluetooth requests sent. ${result.failures.join(' | ') || 'Waiting for signed tablet reports.'}`;
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
    if (phase !== 'approval' || !challenge?.phone || !status || contactStarted.current === challenge.id ||
        status.level === 'office') return;
    contactStarted.current = challenge.id;
    if (status.office_trust_enabled) void contact(challenge.id, status.username);
    else setContactDone({ id: challenge.id, at: Date.now(), granted: 0 });
  }, [phase, status, contact]);

  useEffect(() => {
    if (phase !== 'approval' || !status || navigating.current) return;
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
      const trust = await refreshStatus();
      if (!trust) return;
      setPhase('approval');
      if (trust.phone_enrolled) await startRequest();
    } catch (failure) { setError(getApiError(failure, 'Cannot reach UCM. Check that the server is running.')); }
    finally { setBusy(''); }
  }

  async function chooseTablet(slot: 'A' | 'B') {
    if (!status) return;
    setBusy('bluetooth'); setError('');
    try {
      const count = await grantWorkplacePhone(slot, status.username);
      setPairing(`${count} of 2 workplace tablets selected in this browser.`);
      if (status.challenge?.phone) {
        setContactDone(null);
        await contact(status.challenge.id, status.username);
      }
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Could not select this tablet.'); }
    finally { setBusy(''); }
  }

  const phoneApproved = Boolean(status?.challenge?.phone);
  const officeApproved = status?.level === 'office';
  const levels = [
    { name: 'Account', detail: 'Password accepted', done: phase === 'approval' },
    { name: 'Remote', detail: 'Main phone approved', done: phoneApproved },
    { name: 'Office', detail: 'Both workplace tablets signed', done: officeApproved },
  ];

  return <main className="login-workspace">
    <section className="login-context">
      <h1>Sign in to UCM</h1>
      <p>One sign-in. Access grows as your devices approve it.</p>
      <div className="access-ledger" aria-label="Access checks">
        {levels.map(level => <div className="access-ledger-row" key={level.name}>
          <span className={'access-ledger-mark' + (level.done ? ' is-done' : '')} aria-hidden="true" />
          <span><strong>{level.name}</strong><small>{level.detail}</small></span>
          <span className="access-ledger-state">{level.done ? 'Open' : 'Waiting'}</span>
        </div>)}
      </div>
      <p className="login-context-note">Workplace tablets are checked after your main phone approves. If they are unavailable, you can continue with remote access.</p>
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
        <h2>{status?.phone_enrolled ? 'Approve on your main phone' : 'Set up your main phone'}</h2>
        <p className="muted">Signed in as <strong>{status?.username ?? username}</strong>.</p>
        {error && <p className="notice error" role="alert">{error}</p>}
        {!status?.phone_enrolled ? <div className="approval-instruction"><p>Enroll this account in the UCM Android app to enable remote and office access.</p><Link href="/services" className="btn">Open your account</Link></div> : <>
          {status?.challenge && !phoneApproved ? <div className="approval-code"><span>Request code</span><code>{status.challenge.approval_code ?? status.challenge.id}</code><p>Enter this in the app’s <strong>Approve</strong> screen, then use your biometric.</p><small>Expires {new Date(status.challenge.expires_at).toLocaleTimeString()}.</small></div> :
            phoneApproved ? <div className="approval-instruction success"><strong>Main phone approved</strong><p>Remote access is ready. Checking workplace tablets for office access…</p></div> :
              <div className="approval-instruction"><p>The previous code expired. Start another request.</p></div>}
          <button className="btn secondary small" disabled={!!busy} onClick={() => void startRequest()}>Get a new code</button>
          {status?.office_trust_enabled && <div className="login-bluetooth">
            <h3>Workplace tablets</h3><p>{pairing}</p>
            <div className="login-bluetooth-actions"><button className="btn secondary small" disabled={!!busy} onClick={() => void chooseTablet('A')}>Choose tablet A</button><button className="btn secondary small" disabled={!!busy} onClick={() => void chooseTablet('B')}>Choose tablet B</button></div>
            <div className="login-node-states"><span>Node A <strong>{status.challenge?.node_a ? 'Approved' : 'Waiting'}</strong></span><span>Node B <strong>{status.challenge?.node_b ? 'Approved' : 'Waiting'}</strong></span></div>
            {bluetoothMessage && <p className="login-bluetooth-status" role="status">{bluetoothMessage}</p>}
          </div>}
          {phoneApproved && <button className="text-link login-continue" onClick={() => router.replace('/services')}>Continue with remote access</button>}
        </>}
      </>}
    </section>
  </main>;
}
