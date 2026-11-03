'use client';
import { FormEvent, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import AuthShell from '@/components/AuthShell';
import PasswordField from '@/components/PasswordField';
import api, { getApiError } from '@/lib/api';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setBusy(true);
    try {
      const response = await api.post('/api/login', { username, password });
      if (response.data.success) {
        router.push(response.data.data?.password_change_required ? '/services/security' : '/services/pipeline');
        router.refresh();
      }
      else setError(response.data.message);
    } catch (failure) { setError(getApiError(failure, 'Cannot reach UCM. Check that the server is running.')); }
    finally { setBusy(false); }
  }

  return (
    <AuthShell title="Your account. In safe hands." description="One clear place to sign in, manage your password, and control who has access to your account.">
      <h2>Welcome back</h2><p>Sign in to your UCM account.</p>
      <form className="form-stack" onSubmit={submit}>
        <label className="field" htmlFor="username">Username
          <input id="username" autoComplete="username" value={username} maxLength={64}
            onChange={event => setUsername(event.target.value)} required placeholder="Your username" />
        </label>
        <PasswordField id="password" label="Password" value={password} onChange={setPassword} />
        {error && <p className="notice error" role="alert">{error}</p>}
        <button className="btn full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <p className="hint">Forgot your password? Use your enrolled UCM Android app to approve a reset.</p>
      </form>
      <div className="form-bottom">New to UCM? <Link className="text-link" href="/register">Create an account</Link></div>
    </AuthShell>
  );
}
