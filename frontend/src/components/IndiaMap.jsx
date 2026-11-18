import { Fragment, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import { MapPin, RotateCcw } from 'lucide-react';
import { SEVERITY, VERIFICATION, normalizeSeverity, normalizeVerification, severityRank } from '../constants/severity';

function FocusMap({ selected }) {
  const map = useMap();
  useEffect(() => {
    if (selected?.latitude != null && selected?.longitude != null) {
      map.flyTo([selected.latitude, selected.longitude], Math.max(map.getZoom(), 6), { duration: 0.8 });
    }
  }, [selected, map]);
  useEffect(() => {
    const reset = () => map.flyTo([22.9, 79.2], 4.5, { duration: 0.8 });
    window.addEventListener('luvia-reset-map', reset);
    return () => window.removeEventListener('luvia-reset-map', reset);
  }, [map]);
  return null;
}

// Higher = more important. Used to pick the "worst" event when many share one location.
const importance = (e) =>
  severityRank(e.severity) * 100 +
  (VERIFICATION[normalizeVerification(e.verification_status)]?.rank ?? 0) * 10 +
  (e.imd_alert ? 5 : 0);

function groupByLocation(events) {
  const groups = new Map();
  for (const e of events) {
    const lat = Number(e.latitude);
    const lon = Number(e.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    const key = `${lat.toFixed(3)},${lon.toFixed(3)}`;
    const g = groups.get(key);
    if (!g) groups.set(key, { key, lat, lon, top: e, count: 1 });
    else {
      g.count += 1;
      if (importance(e) > importance(g.top)) g.top = e;
    }
  }
  // Ascending importance => critical dots are painted LAST (on top of blue ones).
  return [...groups.values()].sort((a, b) => importance(a.top) - importance(b.top));
}

function ringStyle(status, isSelected) {
  if (isSelected) return { color: '#0f2a4a', weight: 3, dashArray: null };
  if (status === 'verified') return { color: '#14966e', weight: 3, dashArray: null };
  if (status === 'needs_review' || status === 'pending') return { color: '#b45309', weight: 2.5, dashArray: '3 3' };
  return { color: '#ffffff', weight: 2, dashArray: null };
}

export default function IndiaMap({ events, selected, onSelect, stateFilter, onClearState }) {
  const groups = useMemo(() => groupByLocation(events), [events]);

  const counts = useMemo(() => {
    const c = { priority: 0, medium: 0, low: 0, verified: 0, review: 0 };
    for (const g of groups) {
      const sev = normalizeSeverity(g.top.severity);
      if (sev === 'critical' || sev === 'high') c.priority += 1;
      else if (sev === 'medium') c.medium += 1;
      else c.low += 1;
      const st = normalizeVerification(g.top.verification_status);
      if (st === 'verified') c.verified += 1;
      if (st === 'needs_review' || st === 'pending') c.review += 1;
    }
    return c;
  }, [groups]);

  return (
    <section className="map-card">
      <div className="map-heading">
        <div>
          <span className="eyebrow">GEOGRAPHIC OVERVIEW</span>
          <h2>India live map</h2>
        </div>
        <button
          className="icon-button"
          onClick={() => { onClearState?.(); window.dispatchEvent(new CustomEvent('luvia-reset-map')); }}
          title="Reset map"
        >
          <RotateCcw size={16} />
        </button>
      </div>

      {stateFilter && (
        <div className="map-filter-note">
          <MapPin size={14} /> Showing {stateFilter}
          <button onClick={onClearState}>Clear</button>
        </div>
      )}

      <div className="map-canvas">
        <MapContainer center={[22.9, 79.2]} zoom={4.5} minZoom={3.5} maxZoom={10} scrollWheelZoom zoomControl attributionControl preferCanvas>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FocusMap selected={selected} />

          {groups.map((g) => {
            const e = g.top;
            const sev = normalizeSeverity(e.severity);
            const status = normalizeVerification(e.verification_status);
            const isSelected = selected?.id === e.id;
            const ring = ringStyle(status, isSelected);
            const loud = sev === 'critical' || sev === 'high';
            const color = SEVERITY[sev].color;

            return (
              <Fragment key={g.key}>
                {loud && (
                  <CircleMarker
                    center={[g.lat, g.lon]}
                    radius={sev === 'critical' ? 17 : 14}
                    interactive={false}
                    pathOptions={{ stroke: false, fillColor: color, fillOpacity: 0.22 }}
                  />
                )}
                <CircleMarker
                  center={[g.lat, g.lon]}
                  radius={isSelected ? 11 : loud ? 8 : sev === 'medium' ? 7 : 5.5}
                  pathOptions={{ ...ring, fillColor: color, fillOpacity: 0.95 }}
                  eventHandlers={{ click: () => onSelect(e) }}
                >
                  <Popup>
                    <strong>{e.title}</strong>
                    <br />
                    {e.city || 'Location unavailable'}, {e.state || '—'}
                    <br />
                    <span>
                      <b style={{ color }}>{SEVERITY[sev].label}</b> · {VERIFICATION[status]?.label || status}
                    </span>
                    {e.imd_alert && (
                      <>
                        <br />
                        <span>IMD {e.imd_alert.color} alert today{e.imd_alert.types.length ? `: ${e.imd_alert.types.join(', ')}` : ''}</span>
                      </>
                    )}
                    {g.count > 1 && (
                      <>
                        <br />
                        <small>{g.count} reports at this location</small>
                      </>
                    )}
                    <br />
                    <button className="popup-action" onClick={() => onSelect(e)}>View details</button>
                  </Popup>
                </CircleMarker>
              </Fragment>
            );
          })}
        </MapContainer>
        {groups.length === 0 && <div className="map-empty">No events with usable coordinates in this view.</div>}
      </div>

      <div className="map-legend">
        <span><i className="legend-dot" style={{ background: SEVERITY.high.color }} /> High / critical <b>{counts.priority}</b></span>
        <span><i className="legend-dot" style={{ background: SEVERITY.medium.color }} /> Medium <b>{counts.medium}</b></span>
        <span><i className="legend-dot" style={{ background: SEVERITY.low.color }} /> Low <b>{counts.low}</b></span>
        <span><i className="legend-ring review" /> Needs review <b>{counts.review}</b></span>
        <span><i className="legend-ring verified" /> Verified <b>{counts.verified}</b></span>
        <span className="map-count">{groups.length} locations · {events.length} reports</span>
      </div>
    </section>
  );
}
