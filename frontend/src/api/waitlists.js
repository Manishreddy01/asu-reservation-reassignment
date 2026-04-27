const BASE = '/api/v1';

/**
 * @param {{ userId?: number, resourceId?: number }} opts
 */
export async function fetchWaitlists({ userId, resourceId } = {}) {
  const params = new URLSearchParams();
  if (userId != null)     params.set('user_id', userId);
  if (resourceId != null) params.set('resource_id', resourceId);

  const res = await fetch(`${BASE}/waitlists?${params}`);
  if (!res.ok) throw new Error('Failed to load waitlist.');
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
export async function joinWaitlist(data) {
  const res = await fetch(`${BASE}/waitlists`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? 'Could not join waitlist. Please try again.');
  return json;
}

/**
 * Remove the student from a waitlist entry.
 * @param {number} entryId
 * @param {number} userId
 */
export async function cancelWaitlistEntry(entryId, userId) {
  const res = await fetch(`${BASE}/waitlists/${entryId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId }),
  });

  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? 'Could not cancel waitlist entry. Please try again.');
  return json;
}
