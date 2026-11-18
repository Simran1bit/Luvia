import { useMemo, useState } from 'react';
import { ShieldCheck, AlertCircle, ExternalLink, ClipboardCheck, CloudLightning } from 'lucide-react';
import {
  SEVERITY, VERIFICATION, normalizeSeverity, normalizeVerification, severityRank
} from '../../constants/severity';

const PAGE_SIZE = 50;
const TABS = [
  { key: 'review', label: 'Needs review' },
  { key: 'verified', label: 'Verified' },
  { key: 'all', label: 'All records' }
];

export default function VerificationPage({ events, onSelect }) {
  const [tab, setTab] = useState('review');
  const [visible, setVisible] = useState(PAGE_SIZE);

  const { review, verified } = useMemo(() => {
    const r = [];
    const v = [];
    for (const e of events) {
      const s = normalizeVerification(e.verification_status);
      if (s === 'needs_review' || s === 'pending') r.push(e);
      else if (s === 'verified') v.push(e);
    }
    return { review: r, verified: v };
  }, [events]);

  const rows = useMemo(() => {
    const base = tab === 'review' ? review : tab === 'verified' ? verified : events;
    return [...base].sort(
      (a, b) =>
        severityRank(b.severity) - severityRank(a.severity) ||
        new Date(b.timestamp || 0) - new Date(a.timestamp || 0)
    );
  }, [tab, review, verified, events]);

  const counts = { review: review.length, verified: verified.length, all: events.length };

  return (
    <div className="page-stack">
      <div className="page-title">
        <div>
          <span className="eyebrow">TRUST & EVIDENCE</span>
          <h1>Verification console</h1>
          <p>Inspect source records and their current verification status. Highest severity first.</p>
        </div>
        <span className="data-tag">{events.some((e) => e.demo) ? 'DEMO DATA' : 'API DATA'}</span>
      </div>

      <div className="verification-summary">
        <div className="panel verify-metric">
          <span className="verify-metric-icon amber"><AlertCircle /></span>
          <div><small>Needs review</small><strong>{review.length}</strong></div>
        </div>
        <div className="panel verify-metric">
          <span className="verify-metric-icon green"><ShieldCheck /></span>
          <div><small>Marked verified</small><strong>{verified.length}</strong></div>
        </div>
        <div className="panel verify-metric">
          <span className="verify-metric-icon blue"><ClipboardCheck /></span>
          <div><small>Total records</small><strong>{events.length}</strong></div>
        </div>
      </div>

      <section className="panel verification-table-panel">
        <div className="panel-heading">
          <div>
            <h2>Reports to inspect</h2>
            <p>Choose a record to open its incident details.</p>
          </div>
          <div className="treemap-toggle" role="tablist">
            {TABS.map((t) => (
              <button key={t.key} role="tab" className={tab === t.key ? 'on' : ''} onClick={() => { setTab(t.key); setVisible(PAGE_SIZE); }}>
                {t.label} ({counts[t.key]})
              </button>
            ))}
          </div>
        </div>

        <div className="table-scroll">
          <table>
            <thead>
              <tr><th>Incident</th><th>Severity</th><th>Location</th><th>Reported</th><th>Status</th><th>Evidence</th><th></th></tr>
            </thead>
            <tbody>
              {rows.slice(0, visible).map((e) => {
                const sev = normalizeSeverity(e.severity);
                const st = normalizeVerification(e.verification_status);
                return (
                  <tr key={e.id}>
                    <td><strong>{(e.event_type || 'Unknown event').replaceAll('_', ' ')}</strong><small>{e.incident_id || e.id}</small></td>
                    <td><span className="sev-chip" style={{ background: SEVERITY[sev].soft, color: SEVERITY[sev].color }}>{SEVERITY[sev].label}</span></td>
                    <td>{e.city || '—'}, {e.state || '—'}</td>
                    <td>{e.timestamp ? new Date(e.timestamp).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : 'Unavailable'}</td>
                    <td><span className={`table-status ${st === 'verified' ? 'verified' : 'review'}`}>{VERIFICATION[st]?.label || st}</span></td>
                    <td>
                      {e.source_url
                        ? <a href={e.source_url} target="_blank" rel="noreferrer" className="table-link">Source <ExternalLink size={12} /></a>
                        : e.imd_alert
                          ? <span className="imd-chip"><CloudLightning size={10} /> IMD {e.imd_alert.color}</span>
                          : 'Not linked'}
                    </td>
                    <td><button className="small-outline" onClick={() => onSelect(e)}>Inspect</button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rows.length === 0 && <div className="empty-inline">No reports in this view.</div>}
        </div>

        {rows.length > visible && (
          <button className="list-more" onClick={() => setVisible(visible + PAGE_SIZE)}>
            Show {Math.min(PAGE_SIZE, rows.length - visible)} more ({rows.length - visible} remaining)
          </button>
        )}
      </section>

      <div className="notice-card">
        <AlertCircle size={18} />
        <p>
          <strong>Verification requests are available from incident details in live mode.</strong> Select a record and use
          “Run backend verification” to send the confirmed POST /verify?event_id=… request. Synthetic demo records cannot be verified.
        </p>
      </div>
    </div>
  );
}
