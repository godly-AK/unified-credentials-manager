'use client';
import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import api from '@/lib/api';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [authenticated, setAuthenticated] = useState(false);
  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const profile = await api.get('/api/me');
        if (!active) return;
        if (!profile.data.success) { setAuthenticated(false); router.replace('/login'); return; }
        if (profile.data.data?.password_change_required && pathname === '/services/security') {
          setAuthenticated(true); return;
        }
        const trust = await api.get('/api/trust/status');
        if (!active) return;
        if (trust.data.level === 'remote' || trust.data.level === 'office') setAuthenticated(true);
        else { setAuthenticated(false); router.replace('/login'); }
      } catch { if (active) { setAuthenticated(false); router.replace('/login'); } }
    };
    void check();
    const timer = window.setInterval(() => { void check(); }, 10000);
    return () => { active = false; window.clearInterval(timer); };
  }, [router, pathname]);
  return authenticated ? <>{children}</> : <p className="loading" role="status">Checking your session…</p>;
}
