import { USE_MOCK_DATA } from '../constants/config';
import { demoEvents } from '../mocks/events';
import { request } from './apiClient';
import { normalizeSeverity, normalizeVerification } from '../constants/severity';

// Verified from the user's running FastAPI /docs and responses:
// GET /events -> { events: [...] }
// GET /events/{event_id} -> { event: {...}, sources: [...] }
// GET /map -> { events: [...] }
// GET /analytics -> { total_events, verified_events, events_by_severity, events_by_type }
export async function getEvents() {
  if (USE_MOCK_DATA) return { events: demoEvents, mode: 'demo' };
  const payload = await request('/events');
  const events = Array.isArray(payload) ? payload : payload?.events;
  if (!Array.isArray(events)) throw new Error('GET /events returned an unexpected response. Expected an object containing an events array.');
  return { events: events.map(normalizeEvent), mode: 'live' };
}

export async function getMapEvents() {
  if (USE_MOCK_DATA) return { events: demoEvents, mode: 'demo' };
  const payload = await request('/map');
  const events = Array.isArray(payload) ? payload : payload?.events;
  if (!Array.isArray(events)) throw new Error('GET /map returned an unexpected response. Expected an object containing an events array.');
  return { events: events.map(normalizeEvent), mode: 'live' };
}

export async function getAnalytics() {
  if (USE_MOCK_DATA) return null;
  return request('/analytics');
}

export async function getEventDetails(eventId) {
  if (USE_MOCK_DATA) return null;
  if (eventId == null || eventId === '') throw new Error('An event ID is required to load event details.');
  const payload = await request(`/events/${encodeURIComponent(eventId)}`);
  if (!payload || typeof payload !== 'object' || !payload.event) {
    throw new Error('GET /events/{event_id} returned an unexpected response. Expected an event object and optional sources array.');
  }
  return {
    event: normalizeEvent(payload.event),
    sources: Array.isArray(payload.sources) ? payload.sources : []
  };
}

export function normalizeEvent(raw = {}) {
  const id = raw.id ?? raw.event_id ?? raw.incident_id ?? null;
  return {
    ...raw,
    id,
    incident_id: raw.incident_id ?? raw.event_id ?? raw.id ?? null,
    event_type: raw.event_type ?? raw.type ?? 'Unknown event',
    title: raw.title ?? raw.event_type ?? raw.type ?? 'Weather report',
    description: raw.description ?? null,
    city: raw.city ?? raw.location_name ?? raw.location ?? null,
    state: raw.state ?? raw.region ?? null,
    latitude: numberOrNull(raw.latitude ?? raw.lat),
    longitude: numberOrNull(raw.longitude ?? raw.lon ?? raw.lng),
    timestamp: raw.timestamp ?? raw.event_timestamp ?? raw.created_at ?? null,
    severity: normalizeSeverity(raw.severity),
    verification_status: normalizeVerification(raw.verification_status ?? raw.status),
    risk_reasons: Array.isArray(raw.risk_reasons) ? raw.risk_reasons : [],
    source_url: raw.source_url ?? raw.url ?? null,
    confidence_score: raw.confidence_score ?? raw.credibility_score ?? raw.verification_score ?? null,
    demo: Boolean(raw.demo)
  };
}
function numberOrNull(value) {
  const n = Number(value);
  return value == null || value === '' || !Number.isFinite(n) ? null : n;
}
