const BASE = '/api/v1';

/**
 * Marks a single notification as read.
 *
 * @param {number} notificationId
 * @returns {Promise<{ id: number, is_read: boolean }>}
 */
export async function markNotificationRead(notificationId) {
  const res = await fetch(`${BASE}/notifications/${notificationId}/read`, {
    method: 'PATCH',
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? 'Failed to mark notification as read.');
  return json;
}
