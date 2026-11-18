// =====================================================================
// riskService – turns a flat list of backend events into a triage-ready
// list by overlaying OFFICIAL IMD district warnings (Day 1 = today).
//
//   * severity  -> max(backend severity, IMD alert level for that district)
//   * status    -> backend value is respected. If an event is high/critical
//                  and the backend still says "unverified", it is surfaced
//                  as "needs_review" (standard triage rule).
//                  "verified" is NEVER invented here - it only comes from
//                  the backend (see run_enrich_events.py).
//   * risk_reasons / imd_alert -> shown in the details panel so every
//                  colour on the dashboard can be explained.
// =====================================================================
import { dayOne, isRealWarning } from './imdWarningService';
import {
  IMD_COLOR, imdSeverity, maxSeverity, normalizeSeverity, normalizeVerification, severityRank
} from '../constants/severity';

const CITY_ALIASES = {
  bangalore: 'bengaluru', 'bangalore urban': 'bengaluru', 'bengaluru urban': 'bengaluru',
  bombay: 'mumbai', calcutta: 'kolkata', madras: 'chennai', gurgaon: 'gurugram',
  trivandrum: 'thiruvananthapuram', cochin: 'kochi', allahabad: 'prayagraj', poona: 'pune',
  baroda: 'vadodara', banaras: 'varanasi', benares: 'varanasi', mysore: 'mysuru',
  'new delhi': 'delhi', bhubaneswar: 'bhubaneswar', khurda: 'bhubaneswar'
};
const STATE_ALIASES = {
  orissa: 'odisha', uttaranchal: 'uttarakhand', 'nct of delhi': 'delhi', 'delhi nct': 'delhi',
  'jammu and kashmir': 'jammu kashmir', 'jammu kashmir': 'jammu kashmir', pondicherry: 'puducherry'
};

const clean = (s) =>
  String(s ?? '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/&/g, ' and ')
    .replace(/\b(district|dist|city|urban|rural|metropolitan|municipal corporation)\b/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();

const normCity = (s) => { const c = clean(s); return CITY_ALIASES[c] ?? c; };
const normState = (s) => { const c = clean(s); return STATE_ALIASES[c] ?? c; };

// Does an IMD district name refer to this event city?
function districtMatchesCity(districtNorm, cityNorm) {
  if (!districtNorm || !cityNorm) return false;
  if (districtNorm === cityNorm) return true;
  const words = districtNorm.split(' ');
  // "central delhi", "mumbai suburban", "hyderabad" <-> "hyderabad"
  return words.includes(cityNorm) || districtNorm.startsWith(`${cityNorm} `);
}

/** Build a lookup: normalized state -> list of {district, day1} (only real Day-1 warnings). */
function indexWarnings(warnings) {
  const byState = new Map();
  for (const w of warnings || []) {
    const day = dayOne(w);
    if (!isRealWarning(day)) continue;
    const stateKey = normState(w.state);
    if (!byState.has(stateKey)) byState.set(stateKey, []);
    byState.get(stateKey).push({ district: w.district, districtNorm: normCity(w.district), day });
  }
  return byState;
}

/** Highest Day-1 IMD alert that applies to a city/state pair, or null. */
function findAlert(index, city, state, cache) {
  const key = `${normState(state)}|${normCity(city)}`;
  if (cache.has(key)) return cache.get(key);

  const cityNorm = normCity(city);
  const candidates = index.get(normState(state)) || [];
  let best = null;
  for (const c of candidates) {
    if (!districtMatchesCity(c.districtNorm, cityNorm)) continue;
    if (!best || (c.day.colorCode ?? 0) > (best.day.colorCode ?? 0)) best = c;
  }

  const result = best
    ? {
        district: best.district,
        colorCode: best.day.colorCode,
        color: IMD_COLOR[best.day.colorCode]?.name ?? 'unknown',
        label: IMD_COLOR[best.day.colorCode]?.label ?? 'IMD alert',
        severity: imdSeverity(best.day.colorCode),
        types: best.day.warningTypes.filter((t) => t !== 'No Warning'),
        description: best.day.description,
        day: 1
      }
    : null;
  cache.set(key, result);
  return result;
}

// Today's IMD alert describes TODAY. It is attached only to the most recent
// observation of each location (not to last week's history), and only if that
// observation is reasonably fresh.
const OVERLAY_MAX_AGE_HOURS = 72;
const locationKey = (e) => `${normState(e.state)}|${normCity(e.city)}`;

export function enrichEvents(events, imdWarnings) {
  const index = indexWarnings(imdWarnings);
  const cache = new Map();

  const latest = new Map();
  if (index.size) {
    for (const e of events) {
      const t = Date.parse(e.timestamp) || 0;
      const key = locationKey(e);
      const cur = latest.get(key);
      if (!cur || t > cur.t) latest.set(key, { t, id: e.id });
    }
  }

  return events.map((e) => {
    const backendSeverity = normalizeSeverity(e.severity);
    const backendStatus = normalizeVerification(e.verification_status);

    let alert = null;
    if (index.size && latest.get(locationKey(e))?.id === e.id) {
      const ageHours = (Date.now() - new Date(e.timestamp).getTime()) / 3600000;
      const fresh = !e.timestamp || !Number.isFinite(ageHours) || ageHours <= OVERLAY_MAX_AGE_HOURS;
      if (fresh) alert = findAlert(index, e.city, e.state, cache);
    }

    const reasons = Array.isArray(e.risk_reasons) ? [...e.risk_reasons] : [];
    let severity = backendSeverity;
    if (alert && severityRank(alert.severity) > severityRank(backendSeverity)) {
      severity = maxSeverity(backendSeverity, alert.severity);
    }
    if (alert) {
      reasons.push(
        `IMD ${alert.color.toUpperCase()} ${alert.label.split(' – ')[0].toLowerCase()} for ${alert.district} today` +
          (alert.types.length ? `: ${alert.types.join(', ')}` : '')
      );
    }

    let status = backendStatus;
    if (status === 'unverified' && severityRank(severity) >= severityRank('high')) {
      status = 'needs_review';
      reasons.push('High-severity signal not yet verified – queued for review');
    }

    return {
      ...e,
      severity,
      backend_severity: backendSeverity,
      verification_status: status,
      backend_verification_status: backendStatus,
      imd_alert: alert,
      risk_reasons: reasons
    };
  });
}

/** Counts used by the stat cards (distinct IMD districts, not events). */
export function summarizeImd(warnings) {
  let orange = 0;
  let red = 0;
  let yellow = 0;
  for (const w of warnings || []) {
    const day = dayOne(w);
    if (!isRealWarning(day)) continue;
    if (day.colorCode === 4) red += 1;
    else if (day.colorCode === 3) orange += 1;
    else if (day.colorCode === 2) yellow += 1;
  }
  return { red, orange, yellow, priority: red + orange };
}
