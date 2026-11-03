'use client';
import { FormEvent, useState } from 'react';
import Link from 'next/link';
import AuthShell from '@/components/AuthShell';
import PasswordField from '@/components/PasswordField';
import PasswordStrength from '@/components/PasswordStrength';
import api, { getApiError } from '@/lib/api';

export default function Register() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [created, setCreated] = useState(false);
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    if (password !== confirmation) { setError('The passwords do not match. Enter the same password twice.'); return; }
    if ([...password.normalize('NFC')].length < 15) { setError('Use at least 15 characters. A few unrelated words work well.'); return; }
    setBusy(true);
    try {
      const response = await api.post('/api/register', { username, email, password });
      if (response.data.success) { setCreated(true); setPassword(''); setConfirmation(''); }
      else setError(response.data.data?.reasons?.join(' ') || response.data.message);
    } catch (failure) { setError(getApiError(failure, 'Cannot reach UCM. Check that the server is running.')); }
    finally { setBusy(false); }
  }
  return (
    <AuthShell title="A stronger start." description="Create your account with a memorable passphrase. Add your phone as a recovery device whenever you are ready.">
      <h2>Create an account</h2><p>A few details. A password only you know.</p>
      {created ? <div className="form-stack"><p className="notice success" role="status">Your account is ready. Sign in with your new password.</p><Link className="btn full" href="/login">Go to sign in</Link></div> :
        <form className="form-stack" onSubmit={submit}>
          <label className="field" htmlFor="username">Username
            <input id="username" value={username} onChange={event => setUsername(event.target.value)} required
              minLength={3} maxLength={64} pattern={'[A-Za-z0-9_.\\-]+'} autoComplete="username" placeholder="Choose a username" />
            <small>Letters, numbers, dots, underscores, and hyphens.</small>
          </label>
          <label className="field" htmlFor="email">Email address
            <input id="email" type="email" value={email} onChange={event => setEmail(event.target.value)}
              required maxLength={254} autoComplete="email" placeholder="you@example.com" />
          </label>
          <PasswordField id="password" label="Password" newPassword value={password} onChange={setPassword}
            hint="Use 15–128 characters. Spaces and password managers are welcome." />
          <PasswordStrength password={password} />
          <PasswordField id="confirmation" label="Confirm password" newPassword value={confirmation} onChange={setConfirmation} />
          {error && <p className="notice error" role="alert">{error}</p>}
          <button className="btn full" disabled={busy}>{busy ? 'Creating your account…' : 'Create account'}</button>
          <p className="hint">Common passwords are checked locally and rejected. Your password is stored as a one-way hash.</p>
        </form>}
      <div className="form-bottom">Already registered? <Link className="text-link" href="/login">Sign in</Link></div>
    </AuthShell>
  );
}
