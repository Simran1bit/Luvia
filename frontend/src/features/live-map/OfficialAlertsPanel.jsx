import { useEffect, useMemo, useState } from 'react';
import { MapPin, Clock3, ChevronDown, ExternalLink, Building2 } from 'lucide-react';
import { USE_MOCK_DATA, REFRESH_INTERVAL } from '../../constants/config';
import { SEVERITY, normalizeSeverity, severityRank } from '../../constants/severity';
import { request } from '../../services/apiClient';

const COLLAPSED_COUNT = 5;

function untilLabel(value) {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  const ms = d.getTime() - Date.now();
  if (ms <= 0) return 'Expired';
  const h = Math.floor(ms / 3600000);
  if (h < 1) return `Ends in ${Math.max(1, Math.round(ms / 60000))}m`;
  if (h < 48) return `Ends in ${h}h`;
  return `Until ${d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}`;
}

/** Active official CAP alerts (IMD, CWC, INCOIS, SDMAs) collected via NDMA SACHET. */
export default function OfficialAlertsPanel() {
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(!USE_MOCK_DATA);
  const [filter, setFilter] = useState('all');
  const [openId, setOpenId] = useState(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (USE_MOCK_DATA) return undefined;
    let cancelled = false;

    const load = () =>
      request('/alerts?active_only=true&limit=200')
        .then((payload) => { if (!cancelled) { setAlerts(payload?.alerts ?? []); setError(''); } })
        .catch((err) => { if (!cancelled) setError(err?.message || 'Could not load official alerts.'); })
        .finally(() => { if (!cancelled) setLoading(false); });

    load();
    const id = window.setInterval(load, REFRESH_INTERVAL);
    return () => { cancelled = true; window.clearInterval(id); };
  }, []);

  const counts = useMemo(() => {
    const priority = alerts.filter((a) => severityRank(a.severity) >= SEVERITY.high.rank).length;
    return { all: alerts.length, priority, other: alerts.length - priority };
  }, [alerts]);

  const filtered = useMemo(() => {
    if (filter === 'priority') return alerts.filter((a) => severityRank(a.severity) >= SEVERITY.high.rank);
    if (filter === 'other') return alerts.filter((a) => severityRank(a.severity) < SEVERITY.high.rank);
    return alerts;
  }, [alerts, filter]);

  if (USE_MOCK_DATA) return null;

  const visible = expanded ? filtered : filtered.slice(0, COLLAPSED_COUNT);

  return (
    <section className="panel event-list-panel alerts-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">OFFICIAL ALERTS · NDMA SACHET</span>
          <h2>Disaster alerts <span className="count-bubble">{alerts.length}</span></h2>
        </div>
        <div className="treemap-toggle" role="group" aria-label="Alert severity filter">
          <button className={filter === 'all' ? 'on' : ''} onClick={() => setFilter('all')}>All</button>
          <button className={filter === 'priority' ? 'on' : ''} onClick={() => setFilter('priority')}>
            High <span className="toggle-count">{counts.priority}</span>
          </button>
          <button className={filter === 'other' ? 'on' : ''} onClick={() => setFilter('other')}>
            Other <span className="toggle-count">{counts.other}</span>
          </button>
        </div>
      </div>

      <div className="event-list">
        {loading && <div className="empty-inline">Fetching official alerts…</div>}
        {!loading && error && <div className="empty-inline">Alert feed unavailable: {error}</div>}
        {!loading && !error && filtered.length === 0 && (
          <div className="empty-inline">No active official alerts for this filter.</div>
        )}

        {!loading && !error && visible.map((alert) => {
          const sev = normalizeSeverity(alert.severity);
          const open = openId === alert.identifier;
          const until = untilLabel(alert.expires_at);
          return (
            <div key={alert.identifier} className={`alert-item ${open ? 'open' : ''}`}>
              <button
                className={`event-row ${open ? 'selected' : ''}`}
                onClick={() => setOpenId(open ? null : alert.identifier)}
                aria-expanded={open}
              >
                <span className={`event-icon ${sev}`}><i style={{ background: SEVERITY[sev].color }} /></span>
                <span className="event-copy">
                  <strong>
                    {alert.event || 'Official alert'}
                    <b className="sev-chip" style={{ background: SEVERITY[sev].soft, color: SEVERITY[sev].color }}>
                      {SEVERITY[sev].label}
                    </b>
                  </strong>
                  <span><MapPin size={12} />{alert.area || 'Area not specified'}</span>
                  <small>
                    {until && <><Clock3 size={11} />{until} <b>·</b></>}
                    <Building2 size={11} />{alert.sender || 'SACHET'}
                  </small>
                </span>
                <ChevronDown size={16} className="row-chevron alert-chevron" />
              </button>

              {open && (
                <div className="alert-detail">
                  {alert.headline && <p>{alert.headline}</p>}
                  {alert.instruction && <p className="alert-instruction"><strong>Advice:</strong> {alert.instruction}</p>}
                  <div className="alert-meta">
                    {alert.urgency && <span>Urgency: {alert.urgency}</span>}
                    {alert.certainty && <span>Certainty: {alert.certainty}</span>}
                    {alert.link && (
                      <a href={alert.link} target="_blank" rel="noreferrer">
                        Official CAP record <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {filtered.length > COLLAPSED_COUNT && (
        <button className="list-more" onClick={() => setExpanded(!expanded)}>
          {expanded ? 'Show fewer' : `Show more (${filtered.length - COLLAPSED_COUNT} more)`}
        </button>
      )}

      <p className="treemap-note alerts-note">
        Issued by IMD, CWC, INCOIS and state disaster authorities. Select an alert for the full message.{' '}
        <a href="https://sachet.ndma.gov.in/" target="_blank" rel="noreferrer">SACHET portal <ExternalLink size={11} /></a>
      </p>
    </section>
  );
}
