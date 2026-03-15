import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';
import { fetchBuildings, fetchResources } from '../api/resources';
import { fetchReservations, createReservation } from '../api/reservations';
import { fetchWaitlists, joinWaitlist } from '../api/waitlists';
import { TIME_SLOTS, OCCUPYING, ACTIVE_WAITLIST, todayString } from '../utils/reservationSlots';
import './RecreationReservationsPage.css';

export default function RecreationReservationsPage() {
  const { user } = useAuth();

  // Courts (static after mount)
  const [courts, setCourts] = useState([]);
  const [loadingCourts, setLoadingCourts] = useState(true);
  const [courtsError, setCourtsError] = useState(null);

  // Date / time selection
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedTime, setSelectedTime] = useState('');

  // Slot availability data
  const [allReservations, setAllReservations] = useState([]);
  const [userWaitlists, setUserWaitlists] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);

  // Per-court action state: { [courtId]: { loading, message, type } }
  const [actions, setActions] = useState({});

  // Load the SDFC building and its courts on mount
  useEffect(() => {
    async function loadCourts() {
      setLoadingCourts(true);
      setCourtsError(null);
      try {
        const buildings = await fetchBuildings();
        const sdfc = buildings.find(b => b.name.toLowerCase().includes('sdfc'));
        if (!sdfc) throw new Error('Recreation building not found in the system.');
        const resources = await fetchResources({
          buildingId: sdfc.id,
          resourceType: 'recreation_court',
        });
        setCourts(resources);
      } catch (e) {
        setCourtsError(e.message);
      } finally {
        setLoadingCourts(false);
      }
    }
    loadCourts();
  }, []);

  // Reload slot data whenever date + time both change
  useEffect(() => {
    if (!selectedDate || !selectedTime) {
      setAllReservations([]);
      setUserWaitlists([]);
      setActions({});
      return;
    }

    async function loadSlots() {
      setLoadingSlots(true);
      setActions({});
      try {
        const [reservations, waitlists] = await Promise.all([
          fetchReservations(),
          fetchWaitlists({ userId: user.id }),
        ]);
        setAllReservations(reservations);
        setUserWaitlists(waitlists);
      } catch {
        // Non-fatal — availability simply won't display
      } finally {
        setLoadingSlots(false);
      }
    }
    loadSlots();
  }, [selectedDate, selectedTime, user.id]);

  // ── Availability helpers ─────────────────────────────────────────

  function isOccupied(courtId) {
    return allReservations.some(
      r =>
        r.resource_id === courtId &&
        r.reservation_date === selectedDate &&
        r.start_time === selectedTime &&
        OCCUPYING.has(r.status),
    );
  }

  function isUserReserved(courtId) {
    return allReservations.some(
      r =>
        r.user_id === user.id &&
        r.resource_id === courtId &&
        r.reservation_date === selectedDate &&
        r.start_time === selectedTime &&
        OCCUPYING.has(r.status),
    );
  }

  function isUserWaitlisted(courtId) {
    return userWaitlists.some(
      w =>
        w.resource_id === courtId &&
        w.reservation_date === selectedDate &&
        w.start_time === selectedTime &&
        ACTIVE_WAITLIST.has(w.status),
    );
  }

  // ── Action handlers ──────────────────────────────────────────────

  function setCourtAction(courtId, state) {
    setActions(prev => ({ ...prev, [courtId]: state }));
  }

  async function handleReserve(court) {
    setCourtAction(court.id, { loading: true, message: null, type: null });
    try {
      await createReservation({
        user_id: user.id,
        resource_id: court.id,
        reservation_date: selectedDate,
        start_time: selectedTime,
      });
      setCourtAction(court.id, {
        loading: false,
        message: 'Reservation confirmed!',
        type: 'success',
      });
      // Refresh slot data so the UI reflects the new booking
      const [reservations, waitlists] = await Promise.all([
        fetchReservations(),
        fetchWaitlists({ userId: user.id }),
      ]);
      setAllReservations(reservations);
      setUserWaitlists(waitlists);
    } catch (e) {
      setCourtAction(court.id, { loading: false, message: e.message, type: 'error' });
    }
  }

  async function handleWaitlist(court) {
    setCourtAction(court.id, { loading: true, message: null, type: null });
    try {
      await joinWaitlist({
        user_id: user.id,
        resource_id: court.id,
        reservation_date: selectedDate,
        start_time: selectedTime,
      });
      setCourtAction(court.id, {
        loading: false,
        message: "You've been added to the waitlist.",
        type: 'success',
      });
      const waitlists = await fetchWaitlists({ userId: user.id });
      setUserWaitlists(waitlists);
    } catch (e) {
      setCourtAction(court.id, { loading: false, message: e.message, type: 'error' });
    }
  }

  // ── Render ───────────────────────────────────────────────────────

  const today = todayString();
  const hasSelection = Boolean(selectedDate && selectedTime);

  return (
    <div className="rec-page">
      <Navbar />

      <main className="rec-main">
        <div className="rec-inner">

          {/* Breadcrumb */}
          <div className="rec-breadcrumb">
            <Link to="/app" className="rec-back-link">← Dashboard</Link>
          </div>

          {/* Page header */}
          <header className="rec-header">
            <div className="rec-header-icon" aria-hidden="true">
              <CourtIcon />
            </div>
            <div>
              <h1 className="rec-title">Recreation Courts</h1>
              <p className="rec-subtitle">
                SDFC Recreation Center &mdash; Select a date and time slot to check availability.
              </p>
            </div>
          </header>

          {/* Selectors panel */}
          <section className="rec-selectors" aria-label="Date and time selection">
            <div className="rec-selector-row">
              <div className="rec-date-group">
                <label className="rec-label" htmlFor="rec-date-picker">Date</label>
                <input
                  id="rec-date-picker"
                  type="date"
                  className="rec-date-input"
                  value={selectedDate}
                  min={today}
                  onChange={e => setSelectedDate(e.target.value)}
                />
              </div>

              <div className="rec-time-group">
                <span className="rec-label">Time Slot (1 hour)</span>
                <div className="rec-time-slots" role="group" aria-label="Available time slots">
                  {TIME_SLOTS.map(slot => (
                    <button
                      key={slot.value}
                      type="button"
                      className={`rec-time-btn${selectedTime === slot.value ? ' rec-time-btn--active' : ''}`}
                      onClick={() => setSelectedTime(slot.value)}
                    >
                      {slot.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* Courts section */}
          {loadingCourts ? (
            <p className="rec-state-msg">Loading courts&hellip;</p>
          ) : courtsError ? (
            <p className="rec-state-msg rec-state-msg--error">{courtsError}</p>
          ) : courts.length === 0 ? (
            <p className="rec-state-msg">No courts found.</p>
          ) : (
            <>
              {!hasSelection && (
                <div className="rec-prompt-banner">
                  <InfoIcon />
                  <span>Select a date and time slot above to see court availability.</span>
                </div>
              )}

              {hasSelection && loadingSlots && (
                <p className="rec-availability-loading">Checking availability&hellip;</p>
              )}

              {hasSelection && !loadingSlots && (
                <div className="rec-legend">
                  <span className="rec-badge rec-badge--available">Available</span>
                  <span className="rec-badge rec-badge--occupied">Unavailable</span>
                  <span className="rec-badge rec-badge--yours">Your Booking</span>
                </div>
              )}

              <div className="rec-courts-grid">
                {courts.map(court => {
                  const features = court.features
                    ? court.features.split(',').map(f => f.trim()).filter(Boolean)
                    : [];

                  const occupied     = hasSelection && isOccupied(court.id);
                  const userReserved = hasSelection && isUserReserved(court.id);
                  const userWl       = hasSelection && isUserWaitlisted(court.id);
                  const action       = actions[court.id] ?? null;

                  return (
                    <CourtCard
                      key={court.id}
                      court={court}
                      features={features}
                      hasSelection={hasSelection}
                      occupied={occupied}
                      userReserved={userReserved}
                      userWaitlisted={userWl}
                      action={action}
                      onReserve={() => handleReserve(court)}
                      onWaitlist={() => handleWaitlist(court)}
                    />
                  );
                })}
              </div>
            </>
          )}

        </div>
      </main>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Court Card
───────────────────────────────────────────────────────────────── */
function CourtCard({
  court,
  features,
  hasSelection,
  occupied,
  userReserved,
  userWaitlisted,
  action,
  onReserve,
  onWaitlist,
}) {
  let badge = null;
  let actionArea = null;

  if (hasSelection) {
    if (userReserved) {
      badge = <span className="rec-badge rec-badge--yours">Your Booking</span>;
      actionArea = (
        <p className="rec-action-note">You have reserved this slot.</p>
      );
    } else if (occupied) {
      badge = <span className="rec-badge rec-badge--occupied">Unavailable</span>;
      if (userWaitlisted) {
        actionArea = (
          <p className="rec-action-note">You are on the waitlist for this slot.</p>
        );
      } else {
        actionArea = (
          <button
            type="button"
            className="rec-btn rec-btn--waitlist"
            onClick={onWaitlist}
            disabled={action?.loading}
          >
            {action?.loading ? 'Joining…' : 'Join Waitlist'}
          </button>
        );
      }
    } else {
      badge = <span className="rec-badge rec-badge--available">Available</span>;
      actionArea = (
        <button
          type="button"
          className="rec-btn rec-btn--reserve"
          onClick={onReserve}
          disabled={action?.loading}
        >
          {action?.loading ? 'Reserving…' : 'Reserve'}
        </button>
      );
    }
  }

  return (
    <div className={`rec-court-card${occupied && hasSelection ? ' rec-court-card--occupied' : ''}`}>
      <div className="rec-court-header">
        <h3 className="rec-court-name">{court.name}</h3>
        {badge}
      </div>

      <p className="rec-court-capacity">
        <CapacityIcon /> Capacity: {court.capacity}
      </p>

      {features.length > 0 && (
        <ul className="rec-court-features">
          {features.map(f => (
            <li key={f}>
              <CheckIcon /> {f}
            </li>
          ))}
        </ul>
      )}

      {hasSelection && (
        <div className="rec-court-actions">
          {actionArea}
          {action?.message && (
            <p className={`rec-feedback rec-feedback--${action.type}`}>
              {action.message}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Inline SVG icons
───────────────────────────────────────────────────────────────── */
function CourtIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="36" height="36">
      <rect x="2" y="5" width="20" height="14" rx="2" />
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <circle cx="6" cy="8" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" width="13" height="13" aria-hidden="true">
      <path fillRule="evenodd"
        d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z" />
    </svg>
  );
}

function CapacityIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="14" height="14" aria-hidden="true">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" width="18" height="18" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  );
}
