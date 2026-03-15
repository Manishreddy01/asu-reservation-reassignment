const BASE = '/api/v1';

/**
 * @param {{ userId?: number, resourceId?: number }} opts
 * @returns {Promise<Array>}
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
 * @param {{ user_id: number, resource_id: number, reservation_date: string, start_time: string }} data
 * @returns {Promise<object>}
 * @throws {Error} with backend detail message on failure
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
