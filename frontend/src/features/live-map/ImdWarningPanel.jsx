
import React, { useEffect, useMemo, useState } from 'react';
import { getImdWarnings } from '../../services/imdWarningService';
import { CloudLightning, ExternalLink, RefreshCw, Search } from 'lucide-react';

const COLORS = {
  green: '#16834a',
  yellow: '#d6a300',
  orange: '#e87520',
  red: '#d93636',
  unknown: '#718096'
};

function formatDate(value) {
  if (!value) return 'Not supplied';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export default function ImdWarningsPanel() {
  const [records, setRecords] = useState([]);
  const [sourceUrl, setSourceUrl] = useState(
    'https://mausam.imd.gov.in/responsive/districtWiseWarningGIS.php'
  );
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [lastFetched, setLastFetched] = useState(null);

  async function loadWarnings(isRefresh = false) {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    setError('');

    try {
      const result = await getImdWarnings({ limit: 756 });
      setRecords(result.warnings);
      setSourceUrl(result.sourceUrl);
      setLastFetched(new Date());
    } catch (err) {
      setError(err.message || 'Unable to load IMD warnings.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadWarnings();
  }, []);

  const activeRecords = useMemo(() => {
    return records.filter((record) =>
      record.days?.some((day) =>
        day.warningCodes?.some((code) => code !== '1')
      )
    );
  }, [records]);

  const filteredRecords = useMemo(() => {
    const query = search.trim().toLowerCase();

    return activeRecords
      .filter((record) =>
        `${record.district} ${record.state || ''}`
          .toLowerCase()
          .includes(query)
      )
      .sort((a, b) => {
        const maxSeverity = (record) =>
          Math.max(
            0,
            ...(record.days || []).map((day) => Number(day.colorCode) || 0)
          );

        return maxSeverity(b) - maxSeverity(a);
      })
      .slice(0, 30);
  }, [activeRecords, search]);

  const latestUpdate = useMemo(() => {
    const dates = records
      .map((record) => Date.parse(record.updatedAt || ''))
      .filter(Number.isFinite);

    return dates.length ? Math.max(...dates) : null;
  }, [records]);

  const isStale =
    latestUpdate !== null &&
    Date.now() - latestUpdate > 36 * 60 * 60 * 1000;

  return (
    <section className="imd-panel">
      <div className="imd-panel-header">
        <div className="imd-heading">
          <span className="imd-heading-icon">
            <CloudLightning size={21} />
          </span>
          <div>
            <h2>IMD Official District Warnings</h2>
            <p>India Meteorological Department · Five-day outlook</p>
          </div>
        </div>

        <a
          className="imd-source-link"
          href={sourceUrl}
          target="_blank"
          rel="noreferrer"
        >
          Official IMD source <ExternalLink size={14} />
        </a>
      </div>

      <div className="imd-summary">
        <div>
          <strong>{records.length}</strong>
          <span>District records loaded</span>
        </div>
        <div>
          <strong>{activeRecords.length}</strong>
          <span>With warning codes</span>
        </div>

        <button
          className="imd-refresh"
          onClick={() => loadWarnings(true)}
          disabled={loading || refreshing}
        >
          <RefreshCw
            size={15}
            className={refreshing ? 'spin' : ''}
          />
          {refreshing ? 'Refreshing…' : 'Refresh warnings'}
        </button>
      </div>

      {lastFetched && (
        <p className="imd-updated">
          Retrieved by LUVIA: {formatDate(lastFetched)}
          {latestUpdate && ` · Latest source update: ${formatDate(latestUpdate)}`}
        </p>
      )}

      {isStale && (
        <div className="imd-notice">
          Source data may be more than 36 hours old. Verify the latest
          advisory on the official IMD website before acting on a warning.
        </div>
      )}

      {error && (
        <div className="imd-error">
          {error}
          {records.length > 0 && ' Previously loaded records are still shown.'}
          <button onClick={() => loadWarnings(true)}>Retry</button>
        </div>
      )}

      <label className="imd-search">
        <Search size={17} />
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search district or state…"
        />
      </label>

      <div className="imd-legend">
        {[
          ['green', 'No warning'],
          ['yellow', 'Yellow'],
          ['orange', 'Orange'],
          ['red', 'Red']
        ].map(([color, label]) => (
          <span key={color}>
            <i style={{ background: COLORS[color] }} />
            {label}
          </span>
        ))}
      </div>

      {loading ? (
        <p className="imd-empty">Loading official IMD warnings…</p>
      ) : filteredRecords.length === 0 ? (
        <p className="imd-empty">
          {records.length === 0
            ? 'No warning records were returned.'
            : 'No matching district warnings found.'}
        </p>
      ) : (
        <div className="imd-record-list">
          {filteredRecords.map((record) => (
            <article
              className="imd-record"
              key={`${record.district}-${record.issueDate || ''}`}
            >
              <div className="imd-record-title">
                <div>
                  <h3>{record.district}</h3>
                  <p>
                    {record.state || 'State not supplied by IMD'}
                    {' · Issued: '}
                    {record.issueDate || 'Date not supplied'}
                  </p>
                </div>
                <span className="imd-badge">Official data</span>
              </div>

              <div className="imd-days">
                {record.days.map((day) => {
                  const color =
                    COLORS[day.severityColor] || COLORS.unknown;
                  const hasWarning = day.warningCodes?.some(
                    (code) => code !== '1'
                  );

                  return (
                    <div
                      key={day.day}
                      className={`imd-day ${hasWarning ? 'has-warning' : ''}`}
                    >
                      <span>Day {day.day}</span>
                      <i style={{ background: color }} />
                      <strong>
                        {day.warningCodes?.length
                          ? day.warningCodes.join(', ')
                          : '—'}
                      </strong>
                      <small>
                        {day.warningTypes?.length
                          ? day.warningTypes.join(' / ')
                          : 'No code supplied'}
                      </small>
                    </div>
                  );
                })}
              </div>
            </article>
          ))}

          {activeRecords.length > filteredRecords.length && (
            <p className="imd-more">
              Showing {filteredRecords.length} matching districts.
              Search to narrow the list.
            </p>
          )}
        </div>
      )}

      <p className="imd-disclaimer">
        Warning codes and color levels are supplied by IMD. Forecast days
        are shown as Day 1–5 because exact local validity times are not
        supplied consistently. Check the official IMD source for the
        latest advisory. This panel is not an emergency alert service.
      </p>
    </section>
  );
}
