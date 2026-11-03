'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import api, { getApiError } from '@/lib/api';
import { grantWorkplacePhone, restoreWorkplacePhones, sendChallengeToGrantedPhones } from '@/lib/workplace-bluetooth';

type Node = { id: string; label: string };
type Challenge = { id: string; approval_code: string | null; expires_at: string; phone: boolean; approved_node_count: number };
type Status = { username: string; level: 'password' | 'remote' | 'office'; phone_enrolled: boolean; office_trust_enabled: boolean; nodes: Node[]; challenge: Challenge | null };
type BluetoothResult = { reached: number; granted: number; failures: string[] };

function bluetoothSummary(result: BluetoothResult): string {
  if (result.granted === 0) return 'No saved trusted nodes are available in this browser. Choose nearby nodes once, then retry.';
  const count = `${result.reached} of ${result.granted} Bluetooth requests sent`;
  return result.failures.length ? `${count}. ${result.failures.join(' | ')}` : `${count}. Check the node approvals below; their signed reports go directly to UCM.`;
}

export default function PipelinePage() {
  const [status, setStatus] = useState<Status>();
  const [remote, setRemote] = useState('');
  const [office, setOffice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [bluetoothMessage, setBluetoothMessage] = useState('');
  const [pairingMessage, setPairingMessage] = useState('Checking saved Bluetooth permissions…');
  const autoStarted = useRef(false);
  const autoContacted = useRef('');
  const [label, setLabel] = useState('');
  const [ticket, setTicket] = useState('');
  const [password, setPassword] = useState('');

  const refresh = useCallback(async () => {
    try {
      const result = await api.get('/api/trust/status');
      setStatus(result.data);
      const [remoteResult, officeResult] = await Promise.allSettled([
        api.get('/api/data/remote'), api.get('/api/data/office'),
      ]);
      setRemote(remoteResult.status === 'fulfilled' ? remoteResult.value.data.content : 'Locked until main-phone approval.');
      setOffice(officeResult.status === 'fulfilled' ? officeResult.value.data.content : 'Locked until two distinct trusted nodes approve.');
      setError('');
    } catch (failure) { setError(getApiError(failure, 'Could not load the login pipeline.')); }
  }, []);
  useEffect(() => {
    void refresh();
    const poll = window.setInterval(() => { void refresh(); }, 5000);
    return () => window.clearInterval(poll);
  }, [refresh]);

  const start = useCallback(async () => {
    setBusy('start'); setError('');
    try {
      await api.post('/api/trust/start', {});
      await refresh();
      setBluetoothMessage('Waiting for main-phone approval. The website will then contact selected trusted nodes.');
    }
    catch (failure) { setError(getApiError(failure, 'Could not start approval.')); }
    finally { setBusy(''); }
  }, [refresh]);

  useEffect(() => {
    if (!status || autoStarted.current) return;
    if (status.challenge) { autoStarted.current = true; return; }
    if (status.phone_enrolled && status.level === 'password') {
      autoStarted.current = true;
      void start();
    }
  }, [status, start]);

  useEffect(() => {
    if (!status?.office_trust_enabled || !status.username) return;
    void restoreWorkplacePhones(status.username).then(result => {
      setPairingMessage(result.supported
        ? `${result.count} previously selected trusted nodes restored for this account.`
        : 'This browser cannot restore Bluetooth permissions after a reload. Choose the nodes in this tab, or use a supported desktop browser.');
    }).catch(() => setPairingMessage('Bluetooth is unavailable here. Use desktop Chrome or Edge.'));
  }, [status?.office_trust_enabled, status?.username]);

  useEffect(() => {
    const challenge = status?.challenge;
    if (!status?.office_trust_enabled || !challenge?.phone ||
        challenge.approved_node_count >= 2 || autoContacted.current === challenge.id) return;
    autoContacted.current = challenge.id;
    setBluetoothMessage('Main phone approved. Contacting previously selected trusted nodes…');
    void sendChallengeToGrantedPhones(challenge.id, status.username, setBluetoothMessage).then(result => {
      setBluetoothMessage(bluetoothSummary(result));
      void refresh();
    }).catch(failure => setBluetoothMessage(failure instanceof Error ? failure.message : 'Could not contact trusted nodes.'));
  }, [status?.challenge, status?.office_trust_enabled, status?.username, refresh]);

  async function grant() {
    setBusy('bluetooth'); setError('');
    try {
      if (!status) return;
      const count = await grantWorkplacePhone(status.username);
      setPairingMessage(`${count} trusted nodes selected for this account.`);
      if (count >= 2 && status.challenge?.phone) {
        setBluetoothMessage('At least two nodes selected. Contacting them now…');
        const result = await sendChallengeToGrantedPhones(status.challenge.id, status.username, setBluetoothMessage);
        setBluetoothMessage(bluetoothSummary(result));
        await refresh();
      }
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Could not connect to the workplace phone.'); }
    finally { setBusy(''); }
  }

  async function contact() {
    if (!status?.challenge) return;
    setBusy('bluetooth'); setError('');
    try {
      const result = await sendChallengeToGrantedPhones(status.challenge.id, status.username, setBluetoothMessage);
      setBluetoothMessage(bluetoothSummary(result));
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Could not contact workplace phones.'); }
    finally { setBusy(''); }
  }

  async function createTicket() {
    setBusy('enroll'); setError('');
    try {
      const response = await api.post('/api/trust/nodes/ticket', { label, current_password: password });
      setTicket(response.data.ticket); setPassword('');
    } catch (failure) { setError(getApiError(failure, 'Could not create an enrollment code.')); }
    finally { setBusy(''); }
  }

  async function revoke(id: string) {
    if (!password) { setError('Enter your current password to revoke a node.'); return; }
    setBusy(id); setError('');
    try { await api.delete('/api/trust/nodes/' + id, { data: { current_password: password } }); setPassword(''); await refresh(); }
    catch (failure) { setError(getApiError(failure, 'Could not revoke node.')); }
    finally { setBusy(''); }
  }

  const checks = [
    { title: '1 · Password', complete: !!status, description: 'Your password opened the account setup session.' },
    { title: '2 · Main phone', complete: status?.level !== 'password' && !!status, description: 'Biometric approval unlocks remote work data.' },
    { title: '3 · Trusted nodes', complete: (status?.challenge?.approved_node_count ?? 0) >= 2, description: `${status?.challenge?.approved_node_count ?? 0} of 2 distinct registered keys signed this request.` },
  ];
  const flowMessage = !status ? 'Checking your account…' : !status.phone_enrolled
    ? 'Enroll the main phone to enable signed approval.' : status.level === 'office'
      ? 'Office access is open. The main phone and two trusted nodes signed this request.'
      : !status.challenge ? 'The approval request is being prepared, or the previous one expired.'
        : !status.challenge.phone ? 'Enter the 8-digit request code on your main phone and approve with your biometric.'
          : status.challenge.approved_node_count === 1 ? 'Remote access is open. One trusted node signed; waiting for another.'
            : status.level === 'remote' ? 'Remote access is open. Checking nearby trusted nodes for office access.'
            : 'The main phone approved. Waiting for signed workplace node reports.';

  return <main>
    <div className="heading-row"><div><h1>Login pipeline</h1><p className="muted">See exactly which approvals have opened each level of access.</p></div>
      <button className="btn secondary small" onClick={refresh}>Refresh status</button></div>
    {error && <p className="notice error" role="alert" style={{ marginBottom: 20 }}>{error}</p>}
    <section className="panel pipeline-intro">
      <div><p className="eyebrow">CURRENT ACCESS</p><h2>{status?.level === 'office' ? 'Office access' : status?.level === 'remote' ? 'Remote access' : 'Account setup only'}</h2>
        <p className="muted">Password → main phone → any two distinct trusted nodes</p></div>
      <button className="btn" onClick={start} disabled={!!busy || !status?.phone_enrolled}>Start fresh approval</button>
    </section>
    <section className="panel" style={{ marginTop: 18 }} aria-live="polite"><p className="eyebrow">LIVE LOGIN PROGRESS</p><h2>{flowMessage}</h2>
      {bluetoothMessage && <p className="muted" style={{ marginTop: 10 }}>{bluetoothMessage}</p>}</section>
    {!status?.phone_enrolled && <p className="notice" style={{ marginTop: 18 }}>Enroll your main phone in the Android app before requesting an approval.</p>}
    {status && !status.office_trust_enabled && <p className="notice" style={{ marginTop: 18 }}>Office access is disabled until the Bluetooth witness flow has been tested with the computer and two trusted nodes. Signed node responses alone do not prove local presence.</p>}
    {status?.office_trust_enabled && <section className="panel" style={{ marginTop: 18 }}><h2>Computer Bluetooth check</h2>
      <p className="muted">Choose each trusted node once in this browser. Future requests contact selected devices automatically after main-phone approval.</p>
      <p className="hint" role="status">{pairingMessage}</p>
      <div className="panel-actions"><button className="btn secondary" onClick={grant} disabled={!!busy}>Choose a nearby node</button>
        <button className="btn secondary" onClick={contact} disabled={!!busy || !status.challenge}>Contact selected nodes now</button></div>
      {bluetoothMessage && <p className="notice" role="status" style={{ marginTop: 15 }}>{bluetoothMessage}</p>}
    </section>}
    <div className="pipeline-grid">
      <section className="panel"><h2>Approval steps</h2><div className="pipeline-steps">
        {checks.map(check => <div className="pipeline-step" key={check.title}><span className={'step-dot' + (check.complete ? ' done' : '')} aria-hidden="true" />
          <div><h3>{check.title}</h3><p className="muted">{check.description}</p></div><span className={'badge' + (check.complete ? '' : ' pending')}>{check.complete ? 'Complete' : 'Waiting'}</span></div>)}
      </div>
      {status?.challenge && <div className="challenge-box"><p className="eyebrow">ACTIVE REQUEST</p><p>Enter this request code in the main-phone app:</p>
        <code className="request-code">{status.challenge.approval_code ?? status.challenge.id}</code><p className="hint">Expires {new Date(status.challenge.expires_at).toLocaleTimeString()}. A new request replaces the previous one.</p></div>}
      </section>
      <section className="panel"><h2>What you can access</h2><div className="data-tiers">
        <div><span className={'badge' + (status?.level === 'password' ? ' pending' : '')}>Remote</span><p>{remote || 'Checking…'}</p></div>
        <div><span className={'badge' + (status?.level === 'office' ? '' : ' pending')}>Office</span><p>{office || 'Checking…'}</p></div>
      </div><p className="security-info">The API enforces these levels. A hidden page or changed browser text cannot open protected data.</p></section>
    </div>
    <section className="panel" style={{ marginTop: 24 }}><h2>Trusted nodes</h2><p className="muted">Register at least two different device keys. Any two may approve office access. Revoking a node removes active office access.</p>
      <div className="node-list">{status?.nodes.map(node => <div key={node.id}><span><strong>{node.label}</strong><small>{node.id}</small></span>
        <button className="btn secondary small" onClick={() => revoke(node.id)} disabled={!!busy}>Revoke</button></div>)}</div>
      <div className="node-form"><label className="field">Node label<input value={label} onChange={event => setLabel(event.target.value)} placeholder="Reception phone" /></label></div>
      <label className="field" style={{ marginTop: 16 }}>Current password<input type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" /></label>
      <button className="btn secondary" onClick={createTicket} disabled={!!busy || !label || !password} style={{ marginTop: 16 }}>Create enrollment code</button>
      {ticket && <div className="challenge-box" role="status"><p className="eyebrow">ONE-TIME ENROLLMENT CODE</p><code>{ticket}</code>
        <p className="hint">Enter this on a trusted node within five minutes. Then refresh the node list.</p></div>}
      <p className="security-info">Each node signs a fresh request after a nearby Bluetooth connection. Test that behavior on your three phones before enabling office access. Bluetooth signal strength is not an exact location measurement.</p>
    </section>
  </main>;
}
