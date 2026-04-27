/**
 * Check-in API module.
 *
 * Calls POST /api/v1/check-in to verify the student's location against the
 * building geofence and mark the reservation as active on success.
 *
 * No auth token required — the backend validates ownership via user_id + reservation_id.
 */

const BASE = '/api/v1';

/**
 * Submit a check-in attempt.
 *
 * @param {{ user_id: number, reservation_id: number, submitted_latitude: number, submitted_longitude: number }} data
 * @returns {Promise<{
 *   reservation_id: number,
 *   user_id: number,
 *   distance_meters: number,
 *   geofence_radius_meters: number,
 *   within_geofence: boolean,
 *   within_time_window: boolean,
 *   reservation_status: string,
 *   result: 'success' | 'outside_geofence' | 'outside_time_window',
 *   message: string
 * }>}
 * @throws {Error} with backend detail message on failure
 */
export async function submitCheckIn(data) {
  const res = await fetch(`${BASE}/check-in`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? 'Check-in failed. Please try again.');
  return json;
}
