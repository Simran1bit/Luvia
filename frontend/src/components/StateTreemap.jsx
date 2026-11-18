import { useMemo, useState } from 'react';
import { SEVERITY, isPriority, maxSeverity, normalizeSeverity, normalizeVerification } from '../constants/severity';

// Tile size  = number of distinct incidents (priority-only or all, your choice).
// Tile color = WORST severity seen in that state (red = critical/high, amber = medium, blue = low).
export default function StateTreemap({ events, selectedState, onSelect }) {
  const [metric, setMetric] = useState(null); // null = automatic

  const stats = useMemo(() => {
    const map = new Map();
    for (const e of events) {
      if (!e.state || e.state === 'State unavailable') continue;
      const key = e.incident_id || e.id;
      if (!map.has(e.state)) map.set(e.state, { name: e.state, ids: new Set(), priorityIds: new Set(), reviewIds: new Set(), verifiedIds: new Set(), worst: 'unknown' });
      const s = map.get(e.state);
      const sev = normalizeSeverity(e.severity);
      const status = normalizeVerification(e.verification_status);
      s.ids.add(key);
      s.worst = maxSeverity(s.worst, sev);
      if (isPriority(sev)) s.priorityIds.add(key);
      if (status === 'needs_review' || status === 'pending') s.reviewIds.add(key);
      if (status === 'verified') s.verifiedIds.add(key);
    }
    return [...map.values()].map((s) => ({
      name: s.name, worst: s.worst,
      total: s.ids.size, priority: s.priorityIds.size, review: s.reviewIds.size, verified: s.verifiedIds.size
    }));
  }, [events]);

  const anyPriority = stats.some((s) => s.priority > 0);
  const active = metric ?? (anyPriority ? 'priority' : 'all');

  const tiles = useMemo(() => {
    const rows = stats
      .map((s) => ({ ...s, count: active === 'priority' ? s.priority : s.total }))
      .filter((s) => s.count > 0)
      .sort((a, b) => b.count - a.count);
    return rows;
  }, [stats, active]);

  const max = Math.max(1, ...tiles.map((t) => t.count));

  return (
    <section className="panel treemap-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">REGIONAL ACTIVITY</span>
          <h2>State activity <span className="muted-title">({active === 'priority' ? 'high-severity incidents' : 'all distinct reports'})</span></h2>
        </div>
        <div className="treemap-toggle" role="group" aria-label="Treemap metric">
          <button className={active === 'priority' ? 'on' : ''} onClick={() => setMetric('priority')}>Priority</button>
          <button className={active === 'all' ? 'on' : ''} onClick={() => setMetric('all')}>All reports</button>
        </div>
      </div>

      <div className="treemap-grid">
        {tiles.map((s) => (
          <button
            key={s.name}
            title={`${s.name}: ${s.count} ${active === 'priority' ? 'high-severity' : 'distinct'} incidents · worst severity ${SEVERITY[s.worst].label}`}
            onClick={() => onSelect(selectedState === s.name ? null : s.name)}
            className={`state-tile sev-${s.worst} ${selectedState === s.name ? 'active' : ''}`}
            style={{ flexGrow: Math.max(1, s.count), flexBasis: `${Math.max(12, Math.round((s.count / max) * 28))}%` }}
          >
            <span>{s.name}</span>
            <strong>{s.count}</strong>
            <em>
              {s.review > 0 && <b className="tile-chip review">{s.review} review</b>}
              {s.verified > 0 && <b className="tile-chip verified">{s.verified} verified</b>}
            </em>
          </button>
        ))}
        {tiles.length === 0 && (
          <div className="empty-inline">
            {active === 'priority' ? 'No high-severity incidents for this filter.' : 'No state activity for this filter.'}
          </div>
        )}
      </div>

      <p className="treemap-note">
        Tile size = distinct incident IDs. Tile colour = worst severity in the state
        (<i className="legend-dot" style={{ background: SEVERITY.high.color }} /> high/critical,{' '}
        <i className="legend-dot" style={{ background: SEVERITY.medium.color }} /> medium,{' '}
        <i className="legend-dot" style={{ background: SEVERITY.low.color }} /> low). Select a tile to filter the dashboard.
        {!anyPriority && ' No high-severity incidents are present in the loaded data, so all reports are shown.'}
      </p>
    </section>
  );
}
