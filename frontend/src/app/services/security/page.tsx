'use client';
import { FormEvent, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import PasswordField from '@/components/PasswordField';
import PasswordStrength from '@/components/PasswordStrength';
import api, { getApiError } from '@/lib/api';

type SecurityEvent = { id: number; event_type: string; risk_level: string; ip_address?: string; created_at: string };
const names: Record<string, string> = {
  REGISTRATION_SUCCEEDED: 'Account created', LOGIN_SUCCEEDED: 'Signed in', LOGIN_FAILED: 'Unsuccessful sign-in',
  PASSWORD_CHANGED: 'Password changed', PASSWORD_CHANGE_FAILED: 'Password change declined',
  LOGOUT: 'Signed out', SESSION_REVOKED: 'Session signed out', DEVICE_ENROLLED: 'Recovery device enrolled',
  DEVICE_REMOVED: 'Recovery device removed', DEVICE_PASSWORD_RESET: 'Password reset approved by device',
  LOGIN_BLOCKED: 'Sign-in restricted',
};

export default function SecurityPage() {
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [eventError, setEventError] = useState('');
  const [changed, setChanged] = useState(false);
  const [busy, setBusy] = useState(false);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [requiresChange, setRequiresChange] = useState(false);
  const loadEvents = useCallback(async () => {
    try { const response = await api.get('/api/security-events'); setEvents(response.data.data.events); setEventError(''); }
    catch { setEventError('Could not load security activity. Refresh to try again.'); }
  }, []);
  useEffect(() => { void api.get('/api/me').then(response => {
    setRequiresChange(Boolean(response.data.data?.password_change_required));
    if (response.data.data?.access_level === 'remote' || response.data.data?.access_level === 'office') void loadEvents();
  }).catch(() => {}); }, [loadEvents]);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    if (password !== confirmation) { setError('The new passwords do not match.'); return; }
    if ([...password.normalize('NFC')].length < 15) { setError('Use at least 15 characters for your new password.'); return; }
    setBusy(true);
    try {
      const response = await api.post('/api/password-change', { current_password: current, new_password: password });
      if (response.data.success) { setChanged(true); setCurrent(''); setPassword(''); setConfirmation(''); }
      else { setError(response.data.data?.reasons?.join(' ') || response.data.message); await loadEvents(); }
    } catch (failure) { setError(getApiError(failure, 'Could not change your password. Try again.')); }
    finally { setBusy(false); }
  }
  return (
    <main>
      <div className="heading-row"><div><h1>Account security</h1><p className="muted">Manage your password and review recent access.</p></div><Link className="btn secondary small" href="/services">Back to account</Link></div>
      {requiresChange && !changed && <p className="notice error" role="alert">Your current password appeared in the local compromised-password list. Change it below to restore access to your account.</p>}
      {changed ? <section className="panel"><h2>Password changed</h2><p className="muted" style={{ margin: '16px 0 24px' }}>All existing sessions have been signed out. Sign in again with your new password.</p><Link href="/login" className="btn">Sign in again</Link></section> :
        <div className="security-grid">
          <section className="panel">
            <div className="panel-heading"><h2>Change password</h2></div>
            <form className="form-stack" onSubmit={submit}>
              <PasswordField id="current-password" label="Current password" value={current} onChange={setCurrent} />
              <PasswordField id="new-password" label="New password" newPassword value={password} onChange={setPassword} hint="15–128 characters. Choose a password you have not used recently." />
              <PasswordStrength password={password} />
              <PasswordField id="confirm-password" label="Confirm new password" newPassword value={confirmation} onChange={setConfirmation} />
              {error && <p className="notice error" role="alert">{error}</p>}
              <button className="btn full" disabled={busy}>{busy ? 'Changing password…' : 'Change password'}</button>
            </form>
            <p className="security-info">Changing your password signs out all devices, including this one. Your enrolled recovery key stays available.</p>
          </section>
          {!requiresChange && <section className="panel">
            <div className="panel-heading"><div><h2>Recent security activity</h2><p className="muted">Your latest 20 account events.</p></div><button className="btn secondary small" onClick={() => loadEvents()}>Refresh</button></div>
            {eventError && <p className="notice error" role="alert">{eventError}</p>}
            <div className="table-scroll"><table><thead><tr><th>Event</th><th>Address</th><th>Time</th></tr></thead>
              <tbody>{events.map(event => <tr key={event.id}><td><span className="event-name">{names[event.event_type] ?? event.event_type.replaceAll('_', ' ').toLowerCase()}</span>{event.risk_level !== 'LOW' && <div className="hint">Review this event</div>}</td><td>{event.ip_address ?? 'Unknown'}</td><td>{new Date(event.created_at).toLocaleString()}</td></tr>)}</tbody></table></div>
            {events.length === 0 && !eventError && <p className="empty">Your sign-ins and password changes will appear here.</p>}
          </section>}
        </div>}
    </main>
  );
}
