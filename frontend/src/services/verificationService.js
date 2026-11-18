import { USE_MOCK_DATA } from '../constants/config';
import { request } from './apiClient';

// Confirmed from FastAPI /docs: POST /verify requires query parameter event_id (integer).
// The endpoint is only called after the user explicitly confirms the action in the UI.
export async function verifyEvent(event) {
  if (USE_MOCK_DATA || event?.demo) {
    throw new Error('Verification is unavailable for synthetic demo records. Switch to live mode and select a real backend record.');
  }
  if (event?.id == null || !Number.isFinite(Number(event.id))) {
    throw new Error('This event does not have a valid numeric backend event ID.');
  }
  return request(`/verify?event_id=${encodeURIComponent(Number(event.id))}`, { method: 'POST' });
}
