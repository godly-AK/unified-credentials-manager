'use client';

import { useCallback, useEffect, useState } from 'react';
import api, { getApiError } from '@/lib/api';
import { grantWorkplacePhone, sendChallengeToGrantedPhones } from '@/lib/workplace-bluetooth';

type Node = { id: string; slot: 'A' | 'B'; label: string };
type Challenge = { id: string; expires_at: string; phone: boolean; node_a: boolean; node_b: boolean };
type Status = { level: 'password' | 'remote' | 'office'; phone_enrolled: boolean; office_trust_enabled: boolean; nodes: Node[]; challenge: Challenge | null };

export default function PipelinePage() {
  const [status, setStatus] = useState<Status>();
  const [remote, setRemote] = useState('');
  const [office, setOffice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [bluetoothMessage, setBluetoothMessage] = useState('');
  const [slot, setSlot] = useState<'A' | 'B'>('A');
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
      setOffice(officeResult.status === 'fulfilled' ? officeResult.value.data.content : 'Locked until both workplace nodes approve.');
      setError('');
    } catch (failure) { setError(getApiError(failure, 'Could not load the login pipeline.')); }
  }, []);
  useEffect(() => {
    void refresh();
    const poll = window.setInterval(() => { void refresh(); }, 5000);
    return () => window.clearInterval(poll);
  }, [refresh]);

  async function start() {
    setBusy('start'); setError('');
    try {
      const response = await api.post('/api/trust/start', {});
      await refresh();
      if (status?.office_trust_enabled) {
        const result = await sendChallengeToGrantedPhones(response.data.challenge_id);
        setBluetoothMessage(`${result.reached} of ${result.granted} previously permitted workplace phones reached. Their signed reports go directly to UCM.`);
      }
    }
    catch (failure) { setError(getApiError(failure, 'Could not start approval.')); }
    finally { setBusy(''); }
  }

  async function grant() {
    setBusy('bluetooth'); setError('');
    try {
      const count = await grantWorkplacePhone();
      setBluetoothMessage(`${count} device permissions saved in this browser. Repeat for the other workplace phone.`);
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Could not connect to the workplace phone.'); }
    finally { setBusy(''); }
  }

  async function contact() {
    if (!status?.challenge) return;
    setBusy('bluetooth'); setError('');
    try {
      const result = await sendChallengeToGrantedPhones(status.challenge.id);
      setBluetoothMessage(`${result.reached} of ${result.granted} previously permitted workplace phones reached. Their signed reports go directly to UCM.`);
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Could not contact workplace phones.'); }
    finally { setBusy(''); }
  }

  async function createTicket() {
    setBusy('enroll'); setError('');
    try {
      const response = await api.post('/api/trust/nodes/ticket', { slot, label, current_password: password });
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
    { title: '3 · Workplace node A', complete: !!status?.challenge?.node_a, description: 'A registered workplace key signs this request.' },
    { title: '4 · Workplace node B', complete: !!status?.challenge?.node_b, description: 'A second, distinct workplace key signs this request.' },
  ];

  return <main>
    <div className="heading-row"><div><h1>Login pipeline</h1><p className="muted">See exactly which approvals have opened each level of access.</p></div>
      <button className="btn secondary small" onClick={refresh}>Refresh status</button></div>
    {error && <p className="notice error" role="alert" style={{ marginBottom: 20 }}>{error}</p>}
    <section className="panel pipeline-intro">
      <div><p className="eyebrow">CURRENT ACCESS</p><h2>{status?.level === 'office' ? 'Office access' : status?.level === 'remote' ? 'Remote access' : 'Account setup only'}</h2>
        <p className="muted">Password → main phone → workplace node A + node B</p></div>
      <button className="btn" onClick={start} disabled={!!busy || !status?.phone_enrolled}>Start fresh approval</button>
    </section>
    {!status?.phone_enrolled && <p className="notice" style={{ marginTop: 18 }}>Enroll your main phone in the Android app before requesting an approval.</p>}
    {status && !status.office_trust_enabled && <p className="notice" style={{ marginTop: 18 }}>Office access is disabled until the Bluetooth witness flow has been tested with the computer and both workplace phones. Signed node responses alone do not prove local presence.</p>}
    {status?.office_trust_enabled && <section className="panel" style={{ marginTop: 18 }}><h2>Computer Bluetooth check</h2>
      <p className="muted">Grant each workplace phone once. Later login requests reconnect to previously permitted phones.</p>
      <div className="panel-actions"><button className="btn secondary" onClick={grant} disabled={!!busy}>Grant a workplace phone</button>
        <button className="btn secondary" onClick={contact} disabled={!!busy || !status.challenge}>Contact both phones now</button></div>
      {bluetoothMessage && <p className="notice" role="status" style={{ marginTop: 15 }}>{bluetoothMessage}</p>}
    </section>}
    <div className="pipeline-grid">
      <section className="panel"><h2>Approval steps</h2><div className="pipeline-steps">
        {checks.map(check => <div className="pipeline-step" key={check.title}><span className={'step-dot' + (check.complete ? ' done' : '')}>{check.complete ? '✓' : '·'}</span>
          <div><h3>{check.title}</h3><p className="muted">{check.description}</p></div><span className={'badge' + (check.complete ? '' : ' pending')}>{check.complete ? 'Complete' : 'Waiting'}</span></div>)}
      </div>
      {status?.challenge && <div className="challenge-box"><p className="eyebrow">ACTIVE REQUEST</p><p>Enter this request ID in the main-phone app:</p>
        <code>{status.challenge.id}</code><p className="hint">Expires {new Date(status.challenge.expires_at).toLocaleTimeString()}. A new request replaces the previous one.</p></div>}
      </section>
      <section className="panel"><h2>What you can access</h2><div className="data-tiers">
        <div><span className={'badge' + (status?.level === 'password' ? ' pending' : '')}>Remote</span><p>{remote || 'Checking…'}</p></div>
        <div><span className={'badge' + (status?.level === 'office' ? '' : ' pending')}>Office</span><p>{office || 'Checking…'}</p></div>
      </div><p className="security-info">The API enforces these levels. A hidden page or changed browser text cannot open protected data.</p></section>
    </div>
    <section className="panel" style={{ marginTop: 24 }}><h2>Workplace nodes</h2><p className="muted">Register two different device keys. Revoking a node removes office access.</p>
      <div className="node-list">{status?.nodes.map(node => <div key={node.id}><span><strong>{node.slot} · {node.label}</strong><small>{node.id}</small></span>
        <button className="btn secondary small" onClick={() => revoke(node.id)} disabled={!!busy}>Revoke</button></div>)}</div>
      <div className="node-form"><label className="field">Slot<select value={slot} onChange={event => setSlot(event.target.value as 'A' | 'B')}><option value="A">A</option><option value="B">B</option></select></label>
        <label className="field">Node label<input value={label} onChange={event => setLabel(event.target.value)} placeholder="Office desk A" /></label></div>
      <label className="field" style={{ marginTop: 16 }}>Current password<input type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" /></label>
      <button className="btn secondary" onClick={createTicket} disabled={!!busy || !label || !password} style={{ marginTop: 16 }}>Create enrollment code</button>
      {ticket && <div className="challenge-box" role="status"><p className="eyebrow">ONE-TIME ENROLLMENT CODE</p><code>{ticket}</code>
        <p className="hint">Enter this on workplace phone {slot} within five minutes. Then refresh the node list.</p></div>}
      <p className="security-info">Each node signs a fresh request after a nearby Bluetooth connection. Test that behavior on your three phones before enabling office access. Bluetooth signal strength is not an exact location measurement.</p>
    </section>
  </main>;
}
