/**
 * Admin / Demo Controls API (Block 14).
 *
 * All calls go to /api/v1/admin-demo/*.
 * The backend requires either DEMO_MODE=true on the server, or an
 * X-Demo-Key header that matches the server's DEMO_KEY env var.
 *
 * For local dev with DEMO_MODE=true, no extra header is needed.
 */

const BASE = '/api/v1/admin-demo';

/** @param {string|null} token  Bearer token from AuthContext */
function headers(token) {
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function post(path, body, token) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: headers(token),
    body: JSON.stringify(body ?? {}),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? `Request failed: ${res.status}`);
  return data;
}

async function get(path, token) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'GET',
    headers: headers(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? `Request failed: ${res.status}`);
  return data;
}

/**
 * Trigger no-show processing.
 * @param {number|null} dtOffsetMinutes
 * @param {string|null} token
 */
export function processNoShows(dtOffsetMinutes, token) {
  return post('/no-shows', { dt_offset_minutes: dtOffsetMinutes || null }, token);
}

/**
 * Send waitlist offers for all released slots.
 * @param {number|null} dtOffsetMinutes
 * @param {string|null} token
 */
export function processOffers(dtOffsetMinutes, token) {
  return post('/process-offers', { dt_offset_minutes: dtOffsetMinutes || null }, token);
}

/**
 * Expire timed-out offers and advance the queue.
 * @param {number|null} dtOffsetMinutes
 * @param {string|null} token
 */
export function processExpirations(dtOffsetMinutes, token) {
  return post('/process-expirations', { dt_offset_minutes: dtOffsetMinutes || null }, token);
}

/**
 * Send reminders for upcoming reservations.
 * @param {number} windowMinutes   Look-ahead window (default 60)
 * @param {number|null} dtOffsetMinutes
 * @param {string|null} token
 */
export function sendReminders(windowMinutes = 60, dtOffsetMinutes, token) {
  return post(
    '/send-reminders',
    { window_minutes: windowMinutes, dt_offset_minutes: dtOffsetMinutes || null },
    token,
  );
}

/**
 * Claim a waitlist offer (demo convenience wrapper).
 * @param {{ userId, waitlistEntryId, lat, lng, dtOffsetMinutes }} opts
 * @param {string|null} token
 */
export function claimWaitlist({ userId, waitlistEntryId, lat, lng, dtOffsetMinutes }, token) {
  return post(
    '/claim-waitlist',
    {
      user_id: userId,
      waitlist_entry_id: waitlistEntryId,
      submitted_latitude: lat,
      submitted_longitude: lng,
      dt_offset_minutes: dtOffsetMinutes || null,
    },
    token,
  );
}

/**
 * Fetch the read-only DB snapshot.
 * @param {string|null} token
 */
export function inspect(token) {
  return get('/inspect', token);
}
