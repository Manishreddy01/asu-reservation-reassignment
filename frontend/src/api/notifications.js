const BASE = '/api/v1';

/**
 * Fetches notifications for a user, newest first.
 *
 * @param {number} userId
 * @param {{ unreadOnly?: boolean }} [opts]
 * @returns {Promise<Array>}
 */
export async function fetchNotifications(userId, { unreadOnly = false } = {}) {
  const params = new URLSearchParams({ user_id: userId });
  if (unreadOnly) params.set('unread_only', 'true');
  const res = await fetch(`${BASE}/notifications?${params}`);
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? 'Failed to load notifications.');
  return json;
}

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
