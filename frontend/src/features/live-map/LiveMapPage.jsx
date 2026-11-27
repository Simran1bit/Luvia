import React, { useMemo, useState } from 'react';
import { Search, RefreshCw, X, SlidersHorizontal, CloudRain, CircleHelp, ExternalLink, DatabaseZap } from 'lucide-react';

import StatCard from '../../components/StatCard';
import IndiaMap from '../../components/IndiaMap';
import EventDetails from '../../components/EventDetails';
import EventList from '../../components/EventList';
import StateTreemap from '../../components/StateTreemap';
import OfficialAlertsPanel from './OfficialAlertsPanel';
import { isPriority, needsReview, isVerified, normalizeSeverity, severityRank, normalizeVerification, VERIFICATION } from '../../constants/severity';

const ALL_TYPES = 'All event types';
const ALL_STATUSES = 'All statuses';
const STATUS_OPTIONS = ['verified', 'needs_review', 'pending', 'unverified'];
const pretty = (s) => String(s).replaceAll('_', ' ');

const eventKey = (e, index) => e.incident_id ?? e.event_id ?? e.id ?? `${e.city}-${e.timestamp}-${index}`;

export default function LiveMapPage({
  events, selected, setSelected, refreshing, loading, error, lastUpdated, onRefresh, mode, onVerify, imd
}) {
  const [search, setSearch] = useState('');
  const [type, setType] = useState(ALL_TYPES);
  const [status, setStatus] = useState(ALL_STATUSES);
  const [severity, setSeverity] = useState('all');
  // Your dataset is mostly historical observations, so "all time" is the sensible default.
  const [range, setRange] = useState('all');
  const [stateFilter, setStateFilter] = useState(null);
  const [showFilters, setShowFilters] = useState(false);

  // Event-type dropdown is built from the data itself (no more hard-coded list that never matches).
  const typeOptions = useMemo(() => {
    const set = new Set(events.map((e) => e.event_type).filter(Boolean));
    return [ALL_TYPES, ...[...set].sort()];
  }, [events]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return events.filter((e) => {
      if (range !== 'all') {
        const age = (Date.now() - new Date(e.timestamp).getTime()) / 3600000;
        if (e.timestamp && Number.isFinite(age) && age > Number(range)) return false;
      }
      if (q && !`${e.city || ''} ${e.state || ''} ${e.event_type || ''} ${e.title || ''}`.toLowerCase().includes(q)) return false;
      if (type !== ALL_TYPES && e.event_type !== type) return false;
      if (status !== ALL_STATUSES && normalizeVerification(e.verification_status) !== status) return false;
      if (severity !== 'all' && normalizeSeverity(e.severity) !== severity) return false;
      if (stateFilter && e.state !== stateFilter) return false;
      return true;
    });
  }, [events, search, range, type, status, severity, stateFilter]);

  // Priority first -> verified first -> newest first.
  const sorted = useMemo(
    () =>
      [...filtered].sort(
        (a, b) =>
          severityRank(b.severity) - severityRank(a.severity) ||
          (VERIFICATION[normalizeVerification(b.verification_status)]?.rank ?? 0) -
            (VERIFICATION[normalizeVerification(a.verification_status)]?.rank ?? 0) ||
          new Date(b.timestamp || 0) - new Date(a.timestamp || 0)
      ),
    [filtered]
  );

  // Dashboard cards describe the WHOLE loaded dataset, not the active filters.
  const totals = useMemo(() => {
    const seen = new Map();
    events.forEach((e, i) => seen.set(eventKey(e, i), e));
    const all = [...seen.values()];
    return {
      // Every live record is a measurement; hazardous ones carry a hazard event_type.
      observations: all.length,
      records: all.length,
      priorityEvents: all.filter((e) => isPriority(e.severity)).length,
      review: all.filter((e) => needsReview(e.verification_status)).length,
      verified: all.filter((e) => isVerified(e.verification_status)).length
    };
  }, [events]);

  const imdOk = !imd?.error && !imd?.loading && (imd?.warnings?.length ?? 0) > 0;
  const imdSummary = imd?.summary ?? { red: 0, orange: 0, yellow: 0, priority: 0 };
  const highValue = imdOk ? imdSummary.priority : totals.priorityEvents;
  const highSub = imdOk
    ? `${imdSummary.red} red · ${imdSummary.orange} orange IMD districts today${totals.priorityEvents ? ` · ${totals.priorityEvents} reports flagged` : ''}`
    : 'High / critical severity reports';

  const hasFilter = search || type !== ALL_TYPES || status !== ALL_STATUSES || severity !== 'all' || range !== 'all' || stateFilter;
  const clear = () => {
    setSearch(''); setType(ALL_TYPES); setStatus(ALL_STATUSES); setSeverity('all'); setRange('all'); setStateFilter(null);
  };

  const selectedLive = selected ? filtered.find((e) => e.id === selected.id) || null : null;
  // const dataLooksFlat = mode !== 'demo' && !loading && !error && totals.records > 0 && totals.verified === 0 && totals.priorityEvents === 0;

  return (
    <div className="page-stack">
      <div className="filter-toolbar">
        <label className="search-box">
          <Search size={17} />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search state, city or event…" />
          <kbd>⌕</kbd>
        </label>

        <select value={range} onChange={(e) => setRange(e.target.value)} aria-label="Time range">
          <option value="1">Last hour</option>
          <option value="6">Last 6 hours</option>
          <option value="24">Last 24 hours</option>
          <option value="168">Last 7 days</option>
          <option value="all">All available time</option>
        </select>

        <select value={type} onChange={(e) => setType(e.target.value)} aria-label="Event type">
          {typeOptions.map((x) => <option key={x} value={x}>{x === ALL_TYPES ? x : pretty(x)}</option>)}
        </select>

        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Verification status">
          <option value={ALL_STATUSES}>{ALL_STATUSES}</option>
          {STATUS_OPTIONS.map((x) => <option key={x} value={x}>{pretty(x)}</option>)}
        </select>

        <select value={severity} onChange={(e) => setSeverity(e.target.value)} aria-label="Severity">
          <option value="all">All severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <button className="filter-toggle" onClick={() => setShowFilters(!showFilters)}>
          <SlidersHorizontal size={15} /> Filters
        </button>

        <button className="refresh-button" onClick={onRefresh} disabled={refreshing || imd?.loading}>
          <RefreshCw size={15} className={refreshing || imd?.loading ? 'spin' : ''} />
          {refreshing || imd?.loading ? 'Refreshing' : 'Refresh'}
        </button>

        {hasFilter && (
          <button className="clear-button" onClick={clear}><X size={14} /> Clear</button>
        )}
      </div>

      {showFilters && (
        <div className="filter-extra">
          <span>Quick views</span>
          <p>Jump straight to what needs attention. Unknown values are preserved rather than assigned an assumed severity.</p>
          <button onClick={() => { setSeverity('high'); setStatus(ALL_STATUSES); }}>High severity</button>
          <button onClick={() => { setSeverity('all'); setStatus('needs_review'); }}>Needs review</button>
          <button onClick={() => { setSeverity('all'); setStatus('verified'); }}>Verified only</button>
        </div>
      )}

      <div className="data-status-row">
        <span className={`data-mode ${mode === 'demo' ? 'demo' : 'live'}`}>
          <i />{mode === 'demo' ? 'DEMO DATA' : 'CONNECTED DATA'}
        </span>
        <span>
          {loading ? 'Loading weather data…' : error ? `Data unavailable: ${error}` : `${totals.observations} weather observations · ${filtered.length} shown of ${totals.records} loaded records`}
        </span>
        <span className="last-updated">
          Last update: {lastUpdated ? lastUpdated.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }) : '—'}
        </span>
      </div>

      {error && mode !== 'demo' && (
        <div className="error-banner">
          <CircleHelp size={17} />
          <span><strong>Live data could not be refreshed.</strong> {error} Existing data, if any, remains visible.</span>
        </div>
      )}

      {/* {dataLooksFlat && (
        <div className="data-hint">
          <DatabaseZap size={17} />
          <span>
            <strong>Every loaded record is a low-severity, unverified observation.</strong>{' '}
            That is why the dots are all blue and Verified shows 0. Run the backend enrichment script
            (<code>python -m app.ingestion.run_enrich_events --apply</code>) to classify observations against IMD
            thresholds and cross-check them with official IMD district warnings.
          </span>
        </div>
      )} */}

      <div className="method-note imd-note">
        <CloudRain size={17} />
        <div className="imd-note-body">
          <strong>Official IMD district warnings</strong>
          <p>
            {imd?.loading
              ? 'Fetching official warning data…'
              : imd?.error
                ? `Warning feed unavailable: ${imd.error}`
                : `${imd?.warnings?.length ?? 0} district records · ${imdSummary.orange} orange · ${imdSummary.red} red · ${imdSummary.yellow} yellow today (Day 1)`}
          </p>
          {imd?.updatedAt && (
            <p>Retrieved at {imd.updatedAt.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' })}. Counts cover today's (Day 1) forecast only.</p>
          )}
          <a href="https://mausam.imd.gov.in/responsive/districtWiseWarningGIS.php" target="_blank" rel="noreferrer">
            View official IMD source <ExternalLink size={13} />
          </a>
        </div>
      </div>

      <div className="stats-grid">
        <StatCard label="Weather observations" value={totals.observations} tone="blue" sub={mode === 'demo' ? 'Synthetic demo records' : 'Live readings in the loaded window'} />
        <StatCard label="High priority" value={highValue} tone="red" sub={highSub} />
        <StatCard label="Needs review" value={totals.review} tone="amber" sub="High-severity or awaiting assessment" />
        <StatCard label="Verified" value={totals.verified} tone="green" sub="Confirmed by 2+ independent sources" />
      </div>

      <div className="main-dashboard-grid">
        <div className="map-column">
          <IndiaMap events={filtered} selected={selectedLive} onSelect={setSelected} stateFilter={stateFilter} onClearState={() => setStateFilter(null)} />
          <StateTreemap events={filtered} selectedState={stateFilter} onSelect={setStateFilter} />
          <OfficialAlertsPanel />
        </div>

        <div className="side-column">
          <EventDetails event={selectedLive} onClose={() => setSelected(null)} onVerify={onVerify} mode={mode} />
          <EventList events={sorted} selected={selectedLive} onSelect={setSelected} />
        </div>
      </div>

      <div className="method-note">
        <CloudRain size={15} />
        <span>
          Weather observations are measurements, not necessarily separate incidents. Severity combines the stored backend
          classification with today's official IMD district alerts; “Verified” is only shown when the backend has confirmed
          a report. IMD counts are districts, not unique emergencies.
        </span>
      </div>
    </div>
  );
}
