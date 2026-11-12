'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import api, { getApiError } from '@/lib/api';

type OfficeData = {
  content: string;
  documents: { title: string; category: string; summary: string }[];
};

export default function ConfidentialPage() {
  const [data, setData] = useState<OfficeData | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'locked' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const refresh = useCallback(async () => {
    try {
      const response = await api.get<OfficeData>('/api/data/office');
      setData(response.data); setState('ready');
    } catch (failure) {
      setData(null);
      const code = (failure as { response?: { status?: number } }).response?.status;
      setState(code === 401 || code === 403 ? 'locked' : 'error');
      setMessage(getApiError(failure, 'Could not load the office workspace.'));
    }
  }, []);
  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => { void refresh(); }, 15000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  return <main>
    <div className="heading-row"><div><span className="eyebrow">OFFICE ACCESS</span><h1>Confidential workspace</h1>
      <p className="muted">Available while your main phone and two distinct trusted nodes have approved this session.</p></div>
      {state === 'ready' && <span className="badge">Office verified</span>}
    </div>
    {state === 'loading' && <section className="panel"><p role="status">Checking office access…</p></section>}
    {state === 'locked' && <section className="panel"><h2>Office access required</h2><p className="muted">Your office approval has expired or is incomplete. Sign in again and let two trusted nodes approve.</p><div className="panel-actions"><Link className="btn" href="/login">Start a fresh approval</Link><Link className="btn secondary" href="/services">Remote workspace</Link></div></section>}
    {state === 'error' && <section className="panel"><p className="notice error" role="alert">{message}</p><div className="panel-actions"><button className="btn secondary" onClick={() => void refresh()}>Try again</button></div></section>}
    {state === 'ready' && data && <>
      <section className="panel office-intro"><h2>Office session verified</h2><p>{data.content}</p><span className="office-example">Example documents</span></section>
      <div className="office-documents">{data.documents.map(document => <article className="panel office-document" key={document.title}>
        <span className="eyebrow">{document.category}</span><h2>{document.title}</h2><p className="muted">{document.summary}</p>
      </article>)}</div>
    </>}
  </main>;
}
