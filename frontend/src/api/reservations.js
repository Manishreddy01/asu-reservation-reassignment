const BASE = '/api/v1';

/**
 * Fetch runtime config flags (demo_mode, etc.).
 * Returns { demo_mode: boolean }.
 */
export async function fetchConfig() {
  const res = await fetch(`${BASE}/config`);
  if (!res.ok) return { demo_mode: false };
  return res.json();
}

/**
 * Fetch near-future test time slots (DEMO_MODE only).
 * Returns an array of { label, value, end_time, is_test_slot } or [] if
 * demo mode is off / endpoint unavailable.
 */
export async function fetchTestSlots() {
  const res = await fetch(`${BASE}/reservations/test-slots`);
  if (!res.ok) return [];
  return res.json();
}

/**
 * Fetch reservations, optionally filtered by userId or status.
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
 * @param {{
 *   user_id: number,
 *   resource_id: number,
 *   reservation_date: string,
 *   start_time: string,
 *   notification_email: string,
 * }} data
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

/**
 * Cancel a future reservation on behalf of the given user.
 * @param {number} reservationId
 * @param {number} userId
 */
export async function cancelReservation(reservationId, userId) {
  const res = await fetch(`${BASE}/reservations/${reservationId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId }),
  });

  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? 'Cancellation failed. Please try again.');
  return json;
}
