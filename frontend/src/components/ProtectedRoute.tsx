'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);
  useEffect(() => {
    let active = true;
    api.get('/api/me').then(response => {
      if (active && response.data.success) setAuthenticated(true);
      else if (active) router.replace('/login');
    }).catch(() => { if (active) router.replace('/login'); });
    return () => { active = false; };
  }, [router]);
  return authenticated ? <>{children}</> : <p className="loading" role="status">Checking your session…</p>;
}
