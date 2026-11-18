import { API_BASE_URL } from '../constants/config';
export async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers: { Accept: 'application/json', ...(options.headers || {}) } });
  if (!response.ok) throw new Error(`API request failed (${response.status}) for ${path}`);
  return response.status === 204 ? null : response.json();
}
