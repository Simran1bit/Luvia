import { useState } from 'react';
import { MapPin, Clock3, ChevronRight, ShieldCheck, ShieldAlert, CloudLightning } from 'lucide-react';
import { SEVERITY, VERIFICATION, normalizeSeverity, normalizeVerification } from '../constants/severity';

export function timeAgo(value) {
  if (!value) return 'Time unavailable';
  const ms = Date.now() - new Date(value).getTime();
  if (!Number.isFinite(ms)) return 'Time unavailable';
  const m = Math.max(0, Math.floor(ms / 60000));
  if (m < 60) return `${m}m ago`;
  if (m < 1440) return `${Math.floor(m / 60)}h ago`;
  return `${Math.floor(m / 1440)}d ago`;
}

export default function EventList({ events, selected, onSelect }) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? events.slice(0, 40) : events.slice(0, 8);

  return (
    <section className="panel event-list-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">LATEST REPORTS · PRIORITY FIRST</span>
          <h2>Recent incidents <span className="count-bubble">{events.length}</span></h2>
        </div>
        <span className="live-indicator"><i /> Updating</span>
      </div>

      <div className="event-list">
        {visible.map((e) => {
          const sev = normalizeSeverity(e.severity);
          const status = normalizeVerification(e.verification_status);
          return (
            <button
              key={e.id}
              className={`event-row ${selected?.id === e.id ? 'selected' : ''}`}
              onClick={() => onSelect?.(e)}
            >
              <span className={`event-icon ${sev}`}><i style={{ background: SEVERITY[sev].color }} /></span>
              <span className="event-copy">
                <strong>
                  {e.title || e.event_type}
                  <b className="sev-chip" style={{ background: SEVERITY[sev].soft, color: SEVERITY[sev].color }}>{SEVERITY[sev].label}</b>
                </strong>
                <span><MapPin size={12} />{e.city || 'Location unavailable'}, {e.state || '—'}</span>
                <small>
                  <Clock3 size={11} />{timeAgo(e.timestamp)} <b>·</b>
                  <span className={`vstatus ${status}`}>
                    {status === 'verified' ? <ShieldCheck size={11} /> : status === 'needs_review' || status === 'pending' ? <ShieldAlert size={11} /> : null}
                    {VERIFICATION[status]?.label || status}
                  </span>
                  {e.imd_alert && <span className="imd-chip"><CloudLightning size={10} /> IMD {e.imd_alert.color}</span>}
                </small>
              </span>
              <ChevronRight size={16} className="row-chevron" />
            </button>
          );
        })}
        {events.length === 0 && <div className="empty-inline">No incidents match these filters.</div>}
      </div>

      {events.length > 8 && (
        <button className="list-more" onClick={() => setExpanded(!expanded)}>
          {expanded ? 'Show fewer' : `Show more (${Math.min(40, events.length) - 8} more)`}
        </button>
      )}
    </section>
  );
}
