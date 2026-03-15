const BASE = '/api/v1';

/**
 * Fetch reservations, optionally filtered by userId or status.
 * Called with no args to retrieve all reservations (used for slot availability checks).
 *
 * @param {{ userId?: number, status?: string }} opts
 * @returns {Promise<Array>}
 */
export async function fetchReservations({ userId, status } = {}) {
  const params = new URLSearchParams();
  if (userId != null) params.set('user_id', userId);
  if (status)         params.set('status', status);

  const res = await fetch(`${BASE}/reservations?${params}`);
  if (!res.ok) throw new Error('Failed to load reservations.');
  return res.json();
}

/**
 * @param {{ user_id: number, resource_id: number, reservation_date: string, start_time: string }} data
 * @returns {Promise<object>}
 * @throws {Error} with backend detail message on failure
 */
export async function createReservation(data) {
  const res = await fetch(`${BASE}/reservations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? 'Reservation failed. Please try again.');
  return json;
}
