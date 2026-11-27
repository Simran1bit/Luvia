export const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA !== 'false';
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
// How far back the dashboard loads live observations from the backend.
export const LIVE_WINDOW_HOURS = Math.max(1, Number(import.meta.env.VITE_LIVE_WINDOW_HOURS) || 48);
export const REFRESH_INTERVAL =Math.max(5000, Number(import.meta.env.VITE_REFRESH_INTERVAL) || 30000);
export const THEME_RANGES = { dawn: [5, 8], morning: [8, 16], evening: [16, 19], night: [19, 5] };
export function themeForHour(hour) {
  if (hour >= 5 && hour < 8) return 'dawn';
  if (hour >= 8 && hour < 16) return 'morning';
  if (hour >= 16 && hour < 19) return 'evening';
  return 'night';
}
