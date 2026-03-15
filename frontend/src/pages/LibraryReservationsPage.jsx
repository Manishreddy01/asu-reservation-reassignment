import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';
import { fetchBuildings, fetchResources } from '../api/resources';
import { fetchReservations, createReservation } from '../api/reservations';
import { fetchWaitlists, joinWaitlist } from '../api/waitlists';
import './LibraryReservationsPage.css';

/** Fixed 1-hour slots available for booking */
const TIME_SLOTS = [
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

/** Statuses that occupy a slot (prevent a new reservation) */
const OCCUPYING = new Set(['reserved', 'active', 'reassigned']);

/** Active waitlist statuses */
const ACTIVE_WAITLIST = new Set(['waiting', 'offered']);

/** Returns today's date as YYYY-MM-DD using local time */
function todayString() {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

export default function LibraryReservationsPage() {
  const { user } = useAuth();

  // Rooms (static after mount)
  const [rooms, setRooms] = useState([]);
  const [loadingRooms, setLoadingRooms] = useState(true);
  const [roomsError, setRoomsError] = useState(null);

  // Date / time selection
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedTime, setSelectedTime] = useState('');

  // Slot availability data
  const [allReservations, setAllReservations] = useState([]);
  const [userWaitlists, setUserWaitlists] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);

  // Per-room action state: { [roomId]: { loading, message, type } }
  const [actions, setActions] = useState({});

  // Load the library building and its study rooms on mount
  useEffect(() => {
    async function loadRooms() {
      setLoadingRooms(true);
      setRoomsError(null);
      try {
        const buildings = await fetchBuildings();
        const library = buildings.find(b => b.name.toLowerCase().includes('library'));
        if (!library) throw new Error('Library building not found in the system.');
        const resources = await fetchResources({
          buildingId: library.id,
          resourceType: 'study_room',
        });
        setRooms(resources);
      } catch (e) {
        setRoomsError(e.message);
      } finally {
        setLoadingRooms(false);
      }
    }
    loadRooms();
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

  function isOccupied(roomId) {
    return allReservations.some(
      r =>
        r.resource_id === roomId &&
        r.reservation_date === selectedDate &&
        r.start_time === selectedTime &&
        OCCUPYING.has(r.status),
    );
  }

  function isUserReserved(roomId) {
    return allReservations.some(
      r =>
        r.user_id === user.id &&
        r.resource_id === roomId &&
        r.reservation_date === selectedDate &&
        r.start_time === selectedTime &&
        OCCUPYING.has(r.status),
    );
  }

  function isUserWaitlisted(roomId) {
    return userWaitlists.some(
      w =>
        w.resource_id === roomId &&
        w.reservation_date === selectedDate &&
        w.start_time === selectedTime &&
        ACTIVE_WAITLIST.has(w.status),
    );
  }

  // ── Action handlers ──────────────────────────────────────────────

  function setRoomAction(roomId, state) {
    setActions(prev => ({ ...prev, [roomId]: state }));
  }

  async function handleReserve(room) {
    setRoomAction(room.id, { loading: true, message: null, type: null });
    try {
      await createReservation({
        user_id: user.id,
        resource_id: room.id,
        reservation_date: selectedDate,
        start_time: selectedTime,
      });
      setRoomAction(room.id, {
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
      setRoomAction(room.id, { loading: false, message: e.message, type: 'error' });
    }
  }

  async function handleWaitlist(room) {
    setRoomAction(room.id, { loading: true, message: null, type: null });
    try {
      await joinWaitlist({
        user_id: user.id,
        resource_id: room.id,
        reservation_date: selectedDate,
        start_time: selectedTime,
      });
      setRoomAction(room.id, {
        loading: false,
        message: "You've been added to the waitlist.",
        type: 'success',
      });
      const waitlists = await fetchWaitlists({ userId: user.id });
      setUserWaitlists(waitlists);
    } catch (e) {
      setRoomAction(room.id, { loading: false, message: e.message, type: 'error' });
    }
  }

  // ── Render ───────────────────────────────────────────────────────

  const today = todayString();
  const hasSelection = Boolean(selectedDate && selectedTime);

  return (
    <div className="lib-page">
      <Navbar />

      <main className="lib-main">
        <div className="lib-inner">

          {/* Breadcrumb */}
          <div className="lib-breadcrumb">
            <Link to="/app" className="lib-back-link">← Dashboard</Link>
          </div>

          {/* Page header */}
          <header className="lib-header">
            <div className="lib-header-icon" aria-hidden="true">
              <LibraryIcon />
            </div>
            <div>
              <h1 className="lib-title">Library Study Rooms</h1>
              <p className="lib-subtitle">
                Hayden Library &mdash; Select a date and time slot to check availability.
              </p>
            </div>
          </header>

          {/* Selectors panel */}
          <section className="lib-selectors" aria-label="Date and time selection">
            <div className="lib-selector-row">
              <div className="lib-date-group">
                <label className="lib-label" htmlFor="lib-date-picker">Date</label>
                <input
                  id="lib-date-picker"
                  type="date"
                  className="lib-date-input"
                  value={selectedDate}
                  min={today}
                  onChange={e => setSelectedDate(e.target.value)}
                />
              </div>

              <div className="lib-time-group">
                <span className="lib-label">Time Slot (1 hour)</span>
                <div className="lib-time-slots" role="group" aria-label="Available time slots">
                  {TIME_SLOTS.map(slot => (
                    <button
                      key={slot.value}
                      type="button"
                      className={`lib-time-btn${selectedTime === slot.value ? ' lib-time-btn--active' : ''}`}
                      onClick={() => setSelectedTime(slot.value)}
                    >
                      {slot.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* Rooms section */}
          {loadingRooms ? (
            <p className="lib-state-msg">Loading rooms&hellip;</p>
          ) : roomsError ? (
            <p className="lib-state-msg lib-state-msg--error">{roomsError}</p>
          ) : rooms.length === 0 ? (
            <p className="lib-state-msg">No study rooms found.</p>
          ) : (
            <>
              {!hasSelection && (
                <div className="lib-prompt-banner">
                  <InfoIcon />
                  <span>Select a date and time slot above to see room availability.</span>
                </div>
              )}

              {hasSelection && loadingSlots && (
                <p className="lib-availability-loading">Checking availability&hellip;</p>
              )}

              {hasSelection && !loadingSlots && (
                <div className="lib-legend">
                  <span className="lib-badge lib-badge--available">Available</span>
                  <span className="lib-badge lib-badge--occupied">Unavailable</span>
                  <span className="lib-badge lib-badge--yours">Your Booking</span>
                </div>
              )}

              <div className="lib-rooms-grid">
                {rooms.map(room => {
                  const features = room.features
                    ? room.features.split(',').map(f => f.trim()).filter(Boolean)
                    : [];

                  const occupied     = hasSelection && isOccupied(room.id);
                  const userReserved = hasSelection && isUserReserved(room.id);
                  const userWl       = hasSelection && isUserWaitlisted(room.id);
                  const action       = actions[room.id] ?? null;

                  return (
                    <RoomCard
                      key={room.id}
                      room={room}
                      features={features}
                      hasSelection={hasSelection}
                      occupied={occupied}
                      userReserved={userReserved}
                      userWaitlisted={userWl}
                      action={action}
                      onReserve={() => handleReserve(room)}
                      onWaitlist={() => handleWaitlist(room)}
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
   Room Card
───────────────────────────────────────────────────────────────── */
function RoomCard({
  room,
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
      badge = <span className="lib-badge lib-badge--yours">Your Booking</span>;
      actionArea = (
        <p className="lib-action-note">You have reserved this slot.</p>
      );
    } else if (occupied) {
      badge = <span className="lib-badge lib-badge--occupied">Unavailable</span>;
      if (userWaitlisted) {
        actionArea = (
          <p className="lib-action-note">You are on the waitlist for this slot.</p>
        );
      } else {
        actionArea = (
          <button
            type="button"
            className="lib-btn lib-btn--waitlist"
            onClick={onWaitlist}
            disabled={action?.loading}
          >
            {action?.loading ? 'Joining…' : 'Join Waitlist'}
          </button>
        );
      }
    } else {
      badge = <span className="lib-badge lib-badge--available">Available</span>;
      actionArea = (
        <button
          type="button"
          className="lib-btn lib-btn--reserve"
          onClick={onReserve}
          disabled={action?.loading}
        >
          {action?.loading ? 'Reserving…' : 'Reserve'}
        </button>
      );
    }
  }

  return (
    <div className={`lib-room-card${occupied && hasSelection ? ' lib-room-card--occupied' : ''}`}>
      <div className="lib-room-header">
        <h3 className="lib-room-name">{room.name}</h3>
        {badge}
      </div>

      <p className="lib-room-capacity">
        <CapacityIcon /> Capacity: {room.capacity}
      </p>

      {features.length > 0 && (
        <ul className="lib-room-features">
          {features.map(f => (
            <li key={f}>
              <CheckIcon /> {f}
            </li>
          ))}
        </ul>
      )}

      {hasSelection && (
        <div className="lib-room-actions">
          {actionArea}
          {action?.message && (
            <p className={`lib-feedback lib-feedback--${action.type}`}>
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
function LibraryIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="36" height="36">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      <line x1="9" y1="7" x2="15" y2="7" />
      <line x1="9" y1="11" x2="15" y2="11" />
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
