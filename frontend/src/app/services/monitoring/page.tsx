'use client';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import api, { getApiError } from '@/lib/api';

type Risk = 'LOW' | 'MEDIUM' | 'HIGH';
type SecurityEvent = {
  id: number;
  event_type: string;
  username: string | null;
  ip_address: string | null;
  risk_level: Risk;
  details: Record<string, unknown>;
  created_at: string;
};
type Review = { reviewed_by: string; note: string; reviewed_at: string };
type Alert = SecurityEvent & { review: Review | null };
type Summary = { period_hours: number; events: number; failed_logins: number; high_risk_events: number; open_high_risk_alerts: number };
type Overview = {
  period_days: number;
  risk_counts: Partial<Record<Risk, number>>;
  top_event_types: { event_type: string; count: number }[];
  daily_events: { day: string; count: number }[];
  requests: { id: string; username: string; created_at: string; phone: boolean; node_a: boolean; node_b: boolean; expired: boolean }[];
};
type Filters = { username: string; risk: '' | Risk; event_type: string };
type Status = 'loading' | 'ready' | 'needs-phone' | 'forbidden' | 'error';

const initialFilters: Filters = { username: '', risk: '', event_type: '' };

function formatEvent(value: string) { return value.replaceAll('_', ' ').toLowerCase(); }
function formatTime(value: string) { return new Date(value).toLocaleString(); }
function describeDetails(details: Record<string, unknown>) {
  const labels: Record<string, string> = { reason: 'Reason', failures_in_10_minutes: 'Failed attempts in 10 minutes', node_id: 'Node', slot: 'Slot' };
  return Object.entries(details).map(([key, value]) =>
    `${labels[key] ?? key.replaceAll('_', ' ')}: ${typeof value === 'object' ? JSON.stringify(value) : String(value)}`,
  ).join(' · ');
}

export default function MonitoringPage() {
  const [status, setStatus] = useState<Status>('loading');
  const [summary, setSummary] = useState<Summary>();
  const [overview, setOverview] = useState<Overview>();
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [nextBefore, setNextBefore] = useState<number | null>(null);
  const [nextAlertBefore, setNextAlertBefore] = useState<number | null>(null);
  const [draft, setDraft] = useState<Filters>(initialFilters);
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [selectedAlert, setSelectedAlert] = useState<number | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const eventParams = useCallback((beforeId?: number) => ({
    ...(filters.username.trim() ? { username: filters.username.trim() } : {}),
    ...(filters.risk ? { risk: filters.risk } : {}),
    ...(filters.event_type.trim() ? { event_type: filters.event_type.trim().toUpperCase() } : {}),
    ...(beforeId ? { before_id: beforeId } : {}),
  }), [filters]);

  const load = useCallback(async () => {
    setStatus('loading');
    try {
      const profile = await api.get('/api/me');
      if (!profile.data.data.is_monitoring_admin) { setStatus('forbidden'); return; }
      try {
        const [counts, listed, highRisk, overviewResult] = await Promise.all([
          api.get<Summary>('/api/admin/monitoring/summary'),
          api.get<{ events: SecurityEvent[]; next_before_id: number | null }>('/api/admin/monitoring/events', { params: eventParams() }),
          api.get<{ alerts: Alert[]; next_before_id: number | null }>('/api/admin/monitoring/alerts'),
          api.get<Overview>('/api/admin/monitoring/overview'),
        ]);
        setSummary(counts.data);
        setOverview(overviewResult.data);
        setEvents(listed.data.events);
        setNextBefore(listed.data.next_before_id);
        setAlerts(highRisk.data.alerts);
        setNextAlertBefore(highRisk.data.next_before_id);
        setError('');
        setStatus('ready');
      } catch (failure) {
        const message = getApiError(failure, 'Could not load monitoring. Refresh and try again.');
        setError(message);
        setStatus(message.includes('Approve this login') ? 'needs-phone' : 'error');
      }
    } catch { setStatus('error'); setError('Your session could not be checked. Sign in again.'); }
  }, [eventParams]);

  useEffect(() => { void load(); }, [load]);

  async function loadMore() {
    if (!nextBefore || busy) return;
    setBusy(true);
    try {
      const response = await api.get<{ events: SecurityEvent[]; next_before_id: number | null }>(
        '/api/admin/monitoring/events', { params: eventParams(nextBefore) },
      );
      setEvents(current => [...current, ...response.data.events]);
      setNextBefore(response.data.next_before_id);
    } catch (failure) { setError(getApiError(failure, 'Could not load more events.')); }
    finally { setBusy(false); }
  }

  async function loadMoreAlerts() {
    if (!nextAlertBefore || busy) return;
    setBusy(true);
    try {
      const response = await api.get<{ alerts: Alert[]; next_before_id: number | null }>(
        '/api/admin/monitoring/alerts', { params: { before_id: nextAlertBefore } },
      );
      setAlerts(current => [...current, ...response.data.alerts]);
      setNextAlertBefore(response.data.next_before_id);
    } catch (failure) { setError(getApiError(failure, 'Could not load older alerts.')); }
    finally { setBusy(false); }
  }

  async function review(event: FormEvent) {
    event.preventDefault();
    if (selectedAlert === null) return;
    setBusy(true); setError('');
    try {
      await api.post(`/api/admin/monitoring/alerts/${selectedAlert}/review`, { note: note.trim() });
      setSelectedAlert(null); setNote('');
      await load();
    } catch (failure) {
      const message = getApiError(failure, 'Could not record this review.');
      setError(message);
      if (message.includes('Approve this login')) setStatus('needs-phone');
    }
    finally { setBusy(false); }
  }

  return <main>
    <div className="heading-row">
      <div><span className="eyebrow">Administrator access</span><h1>Security monitoring</h1><p className="muted">Review activity across accounts and record the outcome of high-risk alerts.</p></div>
      <Link className="btn secondary small" href="/services">Back to account</Link>
    </div>
    {status === 'loading' && <p className="loading" role="status">Checking monitoring access…</p>}
    {status === 'forbidden' && <section className="panel"><h2>Administrator access required</h2><p className="muted">A database operator must grant this role to an enrolled account.</p></section>}
    {status === 'needs-phone' && <section className="panel"><h2>Approve on your main phone</h2><p className="muted">Cross-account monitoring needs a fresh phone approval for this session.</p><div className="panel-actions"><Link href="/services/pipeline" className="btn">Open login pipeline</Link><button className="btn secondary" onClick={() => void load()}>Try again</button></div></section>}
    {status === 'error' && <section className="panel"><h2>Monitoring is unavailable</h2><p className="muted">{error}</p><div className="panel-actions"><button className="btn secondary" onClick={() => void load()}>Try again</button></div></section>}
    {status === 'ready' && <>
      <div className="monitor-stats" aria-label="Security activity in the last 24 hours">
        <div className="panel"><span>Events in 24 hours</span><strong>{summary?.events ?? 0}</strong></div>
        <div className="panel"><span>Failed sign-ins</span><strong>{summary?.failed_logins ?? 0}</strong></div>
        <div className="panel"><span>High-risk events</span><strong>{summary?.high_risk_events ?? 0}</strong></div>
        <div className="panel"><span>Open alerts</span><strong>{summary?.open_high_risk_alerts ?? 0}</strong></div>
      </div>
      {overview && <div className="monitor-visual-grid">
        <section className="panel monitor-section"><h2>Activity by day</h2><p className="muted">Security events during the last seven days.</p>
          <div className="monitor-bars" role="img" aria-label={overview.daily_events.map(item => `${item.day}: ${item.count} events`).join('; ')}>
            {overview.daily_events.map(item => <div className="monitor-bar-column" key={item.day}>
              <strong>{item.count}</strong><div className="monitor-bar-track"><span style={{ height: `${Math.max(item.count ? 8 : 0, item.count / Math.max(1, ...overview.daily_events.map(day => day.count)) * 100)}%` }} /></div>
              <small>{new Date(`${item.day}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short' })}</small>
            </div>)}
          </div>
        </section>
        <section className="panel monitor-section"><h2>Risk analysis</h2><p className="muted">Events are classified by server rules. A high risk label calls for review; it is not proof of an attack.</p>
          <div className="monitor-risk-counts">{(['HIGH', 'MEDIUM', 'LOW'] as const).map(risk => <div key={risk}><span className={`monitor-risk risk-${risk.toLowerCase()}`}>{risk.toLowerCase()}</span><strong>{overview.risk_counts[risk] ?? 0}</strong></div>)}</div>
          <h3>Most common events</h3><div className="monitor-top-events">{overview.top_event_types.map(item => <div key={item.event_type}><span>{formatEvent(item.event_type)}</span><strong>{item.count}</strong></div>)}</div>
        </section>
      </div>}
      {overview && <section className="panel monitor-section"><div className="panel-heading"><div><h2>Login requests</h2><p className="muted">Latest 25 requests from the last seven days. Each tablet must sign the same request for office access.</p></div></div>
        <div className="table-scroll"><table><thead><tr><th>When</th><th>Account</th><th>Pixel</th><th>Node A</th><th>Node B</th><th>Result</th></tr></thead><tbody>
          {overview.requests.map(item => <tr key={item.id}><td>{formatTime(item.created_at)}</td><td>{item.username}</td><td>{item.phone ? 'Approved' : 'Waiting'}</td><td>{item.node_a ? 'Approved' : 'Waiting'}</td><td>{item.node_b ? 'Approved' : 'Waiting'}</td><td>{item.phone && item.node_a && item.node_b ? 'Office' : item.phone ? 'Remote' : item.expired ? 'Expired' : 'Pending'}</td></tr>)}
        </tbody></table></div>{overview.requests.length === 0 && <p className="empty">No login requests in this period.</p>}
      </section>}
      {error && <p className="notice error" role="alert">{error}</p>}
      <section className="panel monitor-section">
        <div className="panel-heading"><div><h2>High-risk alerts</h2><p className="muted">Review the event and record what you checked. The source event stays in the audit trail.</p></div><button className="btn secondary small" onClick={() => void load()}>Refresh</button></div>
        {alerts.length === 0 && <p className="empty">No high-risk events have been recorded.</p>}
        <div className="monitor-alerts">{alerts.map(alert => <article className="monitor-alert" key={alert.id}>
          <div><span className="eyebrow">{alert.review ? 'Reviewed' : 'Open alert'}</span><h3>{formatEvent(alert.event_type)}</h3><p className="muted">{alert.username ?? 'System'} · {formatTime(alert.created_at)} · {alert.ip_address ?? 'Address unavailable'}</p>
            {Object.keys(alert.details ?? {}).length > 0 && <p className="monitor-detail">{describeDetails(alert.details)}</p>}
            {alert.review && <p className="monitor-detail">Reviewed by {alert.review.reviewed_by}: {alert.review.note}</p>}
          </div>
          {!alert.review && <button className="btn secondary small" onClick={() => { setSelectedAlert(alert.id); setNote(''); }}>Record review</button>}
        </article>)}</div>
        {nextAlertBefore && <div className="panel-actions"><button className="btn secondary" disabled={busy} onClick={() => void loadMoreAlerts()}>Load older alerts</button></div>}
        {selectedAlert !== null && <form className="monitor-review" onSubmit={review}>
          <label className="field" htmlFor="review-note">Review note for alert #{selectedAlert}<textarea id="review-note" value={note} onChange={event => setNote(event.target.value)} minLength={8} maxLength={500} required placeholder="What did you verify and what action was taken?" /></label>
          <div className="panel-actions"><button className="btn" disabled={busy || note.trim().length < 8}>Save review</button><button type="button" className="btn secondary" onClick={() => { setSelectedAlert(null); setNote(''); }}>Cancel</button></div>
        </form>}
      </section>
      <section className="panel monitor-section">
        <div className="panel-heading"><div><h2>Audit events</h2><p className="muted">Filter by account, severity, or exact event type. Newest events appear first.</p></div></div>
        <form className="monitor-filters" onSubmit={event => { event.preventDefault(); setFilters(draft); }}>
          <label className="field" htmlFor="monitor-username">Account<input id="monitor-username" value={draft.username} onChange={event => setDraft(current => ({ ...current, username: event.target.value }))} maxLength={128} placeholder="Exact username" /></label>
          <label className="field" htmlFor="monitor-risk">Risk<select id="monitor-risk" value={draft.risk} onChange={event => setDraft(current => ({ ...current, risk: event.target.value as Filters['risk'] }))}><option value="">All</option><option value="HIGH">High</option><option value="MEDIUM">Medium</option><option value="LOW">Low</option></select></label>
          <label className="field" htmlFor="monitor-event">Event type<input id="monitor-event" value={draft.event_type} onChange={event => setDraft(current => ({ ...current, event_type: event.target.value }))} maxLength={80} placeholder="LOGIN_FAILED" /></label>
          <button className="btn" type="submit">Apply filters</button>
        </form>
        <div className="table-scroll"><table><thead><tr><th>When</th><th>Account</th><th>Event</th><th>Risk</th><th>Address</th></tr></thead><tbody>
          {events.map(item => <tr key={item.id}><td>{formatTime(item.created_at)}</td><td>{item.username ?? 'System'}</td><td className="event-name">{formatEvent(item.event_type)}</td><td><span className={`monitor-risk risk-${item.risk_level.toLowerCase()}`}>{item.risk_level.toLowerCase()}</span></td><td>{item.ip_address ?? '—'}</td></tr>)}
        </tbody></table></div>
        {events.length === 0 && <p className="empty">No events match these filters.</p>}
        {nextBefore && <div className="panel-actions"><button className="btn secondary" disabled={busy} onClick={() => void loadMore()}>Load older events</button></div>}
      </section>
    </>}
  </main>;
}
