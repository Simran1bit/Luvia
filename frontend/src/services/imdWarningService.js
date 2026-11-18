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
        const colorCode = Number(day.color_code ?? day.colorCode);

        return {
          day: parseDay(day.day),
          warningCodes: codes,
          warningTypes: codes.map((code) => IMD_WARNING_TYPES[Number(code)] ?? `Unknown warning (${code})`),
          colorCode: Number.isFinite(colorCode) ? colorCode : null,
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
