'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import api from '@/lib/api';

export default function Navbar() {
  const pathname = usePathname() ?? '';
  const [access, setAccess] = useState<'guest' | 'pending' | 'remote' | 'office'>('guest');
  const checkAccess = useCallback(async () => {
    try {
      await api.get('/api/me');
      const trust = await api.get<{ level: string }>('/api/trust/status');
      setAccess(trust.data.level === 'office' ? 'office' : trust.data.level === 'remote' ? 'remote' : 'pending');
    } catch { setAccess('guest'); }
  }, []);
  useEffect(() => {
    void checkAccess();
    const update = () => { void checkAccess(); };
    window.addEventListener('ucm-auth-change', update);
    window.addEventListener('focus', update);
    const interval = window.setInterval(update, 15000);
    return () => {
      window.removeEventListener('ucm-auth-change', update);
      window.removeEventListener('focus', update);
      window.clearInterval(interval);
    };
  }, [checkAccess, pathname]);
  return (
    <header className="site-header">
      <Link className="brand" href="/" aria-label="UCM home">
        <span className="brand-mark">U</span>
        <span>UCM</span><span className="brand-caption">Unified Credentials Manager</span>
      </Link>
      <nav className="nav-links" aria-label="Main navigation">
        <Link className="nav-project" href="/about" aria-current={pathname === '/about' ? 'page' : undefined}>How it works</Link>
        {(access === 'remote' || access === 'office') && <Link href="/services" aria-current={pathname === '/services' ? 'page' : undefined}>My account</Link>}
        {access === 'office' && <Link href="/services/confidential" aria-current={pathname === '/services/confidential' ? 'page' : undefined}>Confidential</Link>}
        {access === 'guest' && <Link className="nav-signin" href="/login" aria-current={pathname === '/login' ? 'page' : undefined}>Sign in</Link>}
        {access === 'pending' && <Link className="nav-signin" href="/login" aria-current={pathname === '/login' ? 'page' : undefined}>Continue approval</Link>}
        {(access === 'remote' || access === 'office') && <Link href="/login" aria-current={pathname === '/login' ? 'page' : undefined}>Sign-in status</Link>}
      </nav>
    </header>
  );
}
