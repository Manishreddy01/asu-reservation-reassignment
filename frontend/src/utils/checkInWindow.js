/**
 * Check-in window helpers — frontend display logic only.
 *
 * Prototype rule (enforced by backend, mirrored here for UI display):
 *   window opens  = reservation start_time − 15 min
 *   window closes = reservation start_time + 15 min
 *
 * The backend provides check_in_deadline = start_time + 15 min as a datetime,
 * so we derive windowOpenAt = check_in_deadline − 30 min.
 *
 * None of this logic enforces actual check-in eligibility — that is the
 * backend's responsibility. This module is purely for UI state display.
 */

/** Returns the check-in window open time as a Date. */
export function windowOpenAt(reservation) {
  const deadline = new Date(reservation.check_in_deadline);
  return new Date(deadline.getTime() - 30 * 60 * 1000);
}

/** Returns the check-in window close time as a Date (equals check_in_deadline). */
export function windowCloseAt(reservation) {
  return new Date(reservation.check_in_deadline);
}

/**
 * Computes the display state for a reservation's check-in window.
 *
 * @param {object} reservation - ReservationResponse from backend
 * @param {Date}   [now]       - Override for current time (useful in tests)
 * @returns {'active' | 'open' | 'upcoming' | 'closed'}
 *
 *   active   — already successfully checked in (status active or reassigned)
 *   open     — window is open right now, check-in is allowed
 *   upcoming — window has not opened yet
 *   closed   — window expired without a check-in
 */
export function getWindowState(reservation, now = new Date()) {
  const { status } = reservation;
  if (status === 'active' || status === 'reassigned') return 'active';
  if (status !== 'reserved') return 'closed'; // completed, no_show, cancelled, etc.
  const open  = windowOpenAt(reservation);
  const close = windowCloseAt(reservation);
  if (now < open)    return 'upcoming';
  if (now <= close)  return 'open';
  return 'closed';
}
