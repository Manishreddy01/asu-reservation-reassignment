const BASE = '/api/v1';

/**
 * Fetches all data needed to render the student dashboard in one request.
 *
 * @param {number} userId
 * @returns {Promise<{
 *   user: object,
 *   active_reservations: Array,
 *   upcoming_reservations: Array,
 *   waitlist_entries: Array,
 *   unread_notifications: Array,
 *   recent_history: Array
 * }>}
 */
export async function fetchDashboard(userId) {
  const res = await fetch(`${BASE}/dashboard/${userId}`);
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? 'Failed to load dashboard.');
  return json;
}
