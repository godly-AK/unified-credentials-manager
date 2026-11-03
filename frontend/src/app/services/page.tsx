'use client';
import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import api, { getApiError } from '@/lib/api';

type Profile = { username: string; email: string; device_enrolled: boolean; device_fingerprint?: string; is_monitoring_admin: boolean };
type Session = { id: string; current: boolean; client_type: string; ip_address?: string; created_at: string };

export default function AccountPage() {
  const [profile, setProfile] = useState<Profile>();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState('');
  const [password, setPassword] = useState('');
  const router = useRouter();
  const load = useCallback(async () => {
    try {
      const [me, active] = await Promise.all([api.get('/api/me'), api.get('/api/sessions')]);
      setProfile(me.data.data); setSessions(active.data.data.sessions);
    } catch (failure) { setError(getApiError(failure, 'Could not load your account. Refresh to try again.')); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function signOut(id?: string) {
    setBusy(id ?? 'logout'); setError('');
    try {
      if (!id) { await api.post('/api/logout', {}); window.dispatchEvent(new Event('ucm-auth-change')); router.replace('/login'); }
      else { await api.delete('/api/sessions/' + id); setMessage('That session has been signed out.'); await load(); }
    } catch (failure) { setError(getApiError(failure, 'Could not sign out. Try again.')); }
    finally { setBusy(''); }
  }
  async function removeDevice() {
    if (!profile || !password) return;
    setBusy('device'); setError('');
    try {
      await api.delete('/api/device', { data: { username: profile.username, password } });
      setPassword(''); setMessage('Recovery device removed. Enroll another phone in the Android app.'); await load();
    } catch (failure) { setError(getApiError(failure, 'Could not remove the device.')); }
    finally { setBusy(''); }
  }

  return (
    <main>
      <div className="heading-row">
        <div><h1>Your account</h1><p className="muted">A clear view of your identity and who can access it.</p></div>
        <button className="btn secondary small" onClick={() => signOut()} disabled={!!busy}>Sign out</button>
      </div>
      {error && <p className="notice error" role="alert" style={{ marginBottom: 22 }}>{error}</p>}
      {message && <p className="notice success" role="status" style={{ marginBottom: 22 }}>{message}</p>}
      <div className="account-grid">
        <section className="panel">
          <div className="panel-heading"><h2>Account details</h2><span className="badge">Signed in</span></div>
          <dl className="details">
            <div><dt>Username</dt><dd>{profile?.username ?? 'Loading…'}</dd></div>
            <div><dt>Email address</dt><dd>{profile?.email ?? 'Loading…'}</dd></div>
            <div><dt>Password</dt><dd>Protected with a one-way hash</dd></div>
          </dl>
          <div className="panel-actions"><Link className="btn secondary" href="/services/security">Manage account security</Link><Link className="btn secondary" href="/services/pipeline">Workplace devices</Link>{profile?.is_monitoring_admin && <Link className="btn secondary" href="/services/monitoring">Security monitoring</Link>}</div>
        </section>
        <section className="panel">
          <div className="panel-heading"><h2>Recovery device</h2><span className={'badge' + (profile?.device_enrolled ? '' : ' pending')}>{profile?.device_enrolled ? 'Enrolled' : 'Not enrolled'}</span></div>
          <p className="muted">Use the UCM Android app to enroll your phone. Its device key can approve a password reset with your fingerprint or face.</p>
          {profile?.device_enrolled ? <div className="form-stack" style={{ marginTop: 20 }}>
            <p className="hint">Registered key: {profile.device_fingerprint}</p>
            <p className="security-info">To remove this key, first approve a fresh request with your main phone on the <Link href="/login">sign-in page</Link>, then enter your current password. Lost-phone replacement needs operator assistance in this version.</p>
            <label className="field" htmlFor="device-password">Current password to remove this device
              <input id="device-password" type="password" autoComplete="current-password" value={password}
                onChange={event => setPassword(event.target.value)} maxLength={128} />
            </label>
            <button className="btn danger" disabled={!!busy || !password} onClick={removeDevice}>Remove recovery device</button>
          </div> : <p className="security-info">Enroll while you still know your password. Your biometric data stays on your phone.</p>}
        </section>
        <section className="panel wide">
          <div className="panel-heading"><div><h2>Active sessions</h2><p className="muted">Sign out any session you no longer recognize.</p></div><button className="btn secondary small" onClick={() => load()}>Refresh</button></div>
          <div className="table-scroll">
            <table><thead><tr><th>Device</th><th>Address</th><th>Signed in</th><th>Access</th></tr></thead>
              <tbody>{sessions.map(session => <tr key={session.id}>
                <td className="event-name">{session.client_type === 'android' ? 'Android app' : 'Web browser'} {session.current && <span className="badge">This session</span>}</td>
                <td>{session.ip_address ?? 'Unknown'}</td><td>{new Date(session.created_at).toLocaleString()}</td>
                <td>{session.current ? <span className="muted">Current</span> : <button className="btn secondary small" disabled={!!busy} onClick={() => signOut(session.id)}>Sign out</button>}</td>
              </tr>)}</tbody>
            </table>
          </div>
          {sessions.length === 0 && <p className="empty">Loading active sessions…</p>}
        </section>
      </div>
    </main>
  );
}
