// =====================================================================
// LUVIA – single source of truth for severity, verification and IMD codes.
// Every component imports from here, so colours/labels never drift apart.
// =====================================================================

// ---- Severity -------------------------------------------------------
export const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'unknown'];

export const SEVERITY = {
  critical: { label: 'Critical', rank: 4, color: '#dc2626', soft: '#fde2e2' },
  high:     { label: 'High',     rank: 3, color: '#ef4444', soft: '#ffe3e3' },
  medium:   { label: 'Medium',   rank: 2, color: '#f59e0b', soft: '#fff0d7' },
  low:      { label: 'Low',      rank: 1, color: '#3b82f6', soft: '#e1f0ff' },
  unknown:  { label: 'Unknown',  rank: 0, color: '#64748b', soft: '#eef3f8' }
};

const SEVERITY_ALIASES = {
  severe: 'high', extreme: 'critical', extremely_high: 'critical', red: 'critical',
  orange: 'high', significant: 'medium', moderate: 'medium', yellow: 'medium',
  minor: 'low', green: 'low', normal: 'low', info: 'low', none: 'low'
};

export function normalizeSeverity(value) {
  const key = String(value ?? '').trim().toLowerCase().replace(/[\s-]+/g, '_');
  if (SEVERITY[key]) return key;
  if (SEVERITY_ALIASES[key]) return SEVERITY_ALIASES[key];
  return 'unknown';
}

export const severityRank = (value) => SEVERITY[normalizeSeverity(value)].rank;
export const isPriority = (value) => severityRank(value) >= SEVERITY.high.rank;
export const maxSeverity = (a, b) => (severityRank(a) >= severityRank(b) ? normalizeSeverity(a) : normalizeSeverity(b));

// ---- Verification ---------------------------------------------------
export const VERIFICATION = {
  verified:     { label: 'Verified',     rank: 3, color: '#14966e' },
  needs_review: { label: 'Needs review', rank: 2, color: '#e99a1a' },
  pending:      { label: 'Pending',      rank: 1, color: '#e99a1a' },
  unverified:   { label: 'Unverified',   rank: 0, color: '#64748b' },
  rejected:     { label: 'Rejected',     rank: -1, color: '#94a3b8' }
};

export function normalizeVerification(value) {
  const key = String(value ?? '').trim().toLowerCase().replace(/[\s-]+/g, '_');
  if (!key || key === 'unknown' || key === 'none' || key === 'null') return 'unverified';
  if (VERIFICATION[key]) return key;
  if (key.includes('unverif')) return 'unverified';
  if (key.includes('review')) return 'needs_review';
  if (key.includes('pend')) return 'pending';
  if (key.includes('verif')) return 'verified';
  if (key.includes('reject') || key.includes('false')) return 'rejected';
  return 'unverified';
}

export const isVerified = (v) => normalizeVerification(v) === 'verified';
export const needsReview = (v) => ['needs_review', 'pending'].includes(normalizeVerification(v));

// ---- IMD district-warning feed -------------------------------------
// IMD order of alert levels: No Warning (green) -> Watch (yellow) -> Alert (orange) -> Warning (red).
// Your imdWarningService already used 1=green ... 4=red. If your feed ever turns out to be
// inverted, change ONLY this table - nothing else in the app needs to move.
export const IMD_COLOR = {
  1: { name: 'green',  label: 'No warning',          severity: 'low',      css: '#16834a' },
  2: { name: 'yellow', label: 'Watch – be aware',    severity: 'medium',   css: '#d6a300' },
  3: { name: 'orange', label: 'Alert – be prepared', severity: 'high',     css: '#e87520' },
  4: { name: 'red',    label: 'Warning – take action', severity: 'critical', css: '#d93636' }
};

export const IMD_WARNING_TYPES = {
  1: 'No Warning', 2: 'Heavy Rain', 3: 'Heavy Snow', 4: 'Thunderstorm & Lightning',
  5: 'Hailstorm', 6: 'Dust Storm', 7: 'Dust Raising Winds', 8: 'Strong Surface Winds',
  9: 'Heat Wave', 10: 'Hot Day', 11: 'Warm Night', 12: 'Cold Wave', 13: 'Cold Day',
  14: 'Ground Frost', 15: 'Fog', 16: 'Very Heavy Rain', 17: 'Extremely Heavy Rain'
};

export const imdSeverity = (colorCode) => IMD_COLOR[Number(colorCode)]?.severity ?? 'unknown';
