/**
 * Shared reservation slot helpers used by Library and Recreation pages.
 */

/** Fixed 1-hour time slots available for booking. */
export const TIME_SLOTS = [
  { label: '8:00 AM',  value: '08:00:00' },
  { label: '9:00 AM',  value: '09:00:00' },
  { label: '10:00 AM', value: '10:00:00' },
  { label: '11:00 AM', value: '11:00:00' },
  { label: '12:00 PM', value: '12:00:00' },
  { label: '1:00 PM',  value: '13:00:00' },
  { label: '2:00 PM',  value: '14:00:00' },
  { label: '3:00 PM',  value: '15:00:00' },
  { label: '4:00 PM',  value: '16:00:00' },
  { label: '5:00 PM',  value: '17:00:00' },
];

/** Reservation statuses that occupy a slot and block new bookings. */
export const OCCUPYING = new Set(['reserved', 'active', 'reassigned']);

/** Waitlist statuses that count as an active waitlist position. */
export const ACTIVE_WAITLIST = new Set(['waiting', 'offered']);

/** Returns today's date as a YYYY-MM-DD string using local browser time. */
export function todayString() {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}
