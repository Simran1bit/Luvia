import { request } from './apiClient';
import { IMD_COLOR, IMD_WARNING_TYPES } from '../constants/severity';

const DEFAULT_SOURCE_URL = 'https://mausam.imd.gov.in/responsive/districtWiseWarningGIS.php';

export async function getImdWarnings({ district, limit = 756 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (district?.trim()) params.set('district', district.trim());

  const payload = await request(`/imd-warnings/?${params.toString()}`);
  if (!payload || !Array.isArray(payload.warnings)) {
    throw new Error('IMD warnings API returned an unexpected response. Expected a warnings array.');
  }

  return {
    source: payload.source ?? 'India Meteorological Department (IMD)',
    sourceUrl: payload.source_url ?? DEFAULT_SOURCE_URL,
    count: payload.count ?? payload.warnings.length,
    warnings: payload.warnings.map(normalizeImdWarning)
  };
}

// The IMD feed numbers its colours in reverse (4 = green ... 1 = red; every
// "No Warning" district carries 4). Convert to an alert level 1 green ... 4 red,
// which is what IMD_COLOR and the rest of the app expect. 0/missing -> null.
const FEED_COLOR_TO_LEVEL = { 4: 1, 3: 2, 2: 3, 1: 4 };
const feedColorToLevel = (value) => FEED_COLOR_TO_LEVEL[Number(value)] ?? null;

// "Day_1", "day 1", 1 and "1" all become 1.
function parseDay(value) {
  const n = Number(String(value ?? '').replace(/\D/g, ''));
  return Number.isFinite(n) && n > 0 ? n : null;
}

function normalizeImdWarning(raw = {}) {
  const days = Array.isArray(raw.days)
    ? raw.days.map((day) => {
        const codes = String(day.warning_code ?? day.warningCode ?? '')
          .split(',')
          .map((code) => code.trim())
          .filter(Boolean);
        const colorCode = feedColorToLevel(day.color_code ?? day.colorCode);

        return {
          day: parseDay(day.day),
          warningCodes: codes,
          warningTypes: codes.map((code) => IMD_WARNING_TYPES[Number(code)] ?? `Unknown warning (${code})`),
          colorCode,
          severityColor: IMD_COLOR[colorCode]?.name ?? 'unknown',
          description: day.description ?? null
        };
      })
    : [];

  return {
    source: raw.source ?? 'IMD',
    sourceUrl: raw.source_url ?? null,
    district: raw.district ?? 'Unknown district',
    state: raw.state ?? null,
    issueDate: raw.issue_date ?? null,
    updatedAt: raw.updated_at ?? null,
    fetchedAt: raw.fetched_at ?? null,
    days
  };
}

// Today's forecast entry (Day 1) for a normalized warning record.
export function dayOne(warning) {
  return warning?.days?.find((d) => d.day === 1) ?? warning?.days?.[0] ?? null;
}

// A real warning = at least one code other than "1" (No Warning) AND colour yellow or worse.
export function isRealWarning(day) {
  if (!day) return false;
  const hasCode = day.warningCodes.some((c) => c !== '1');
  return hasCode && (day.colorCode ?? 0) >= 2;
}
