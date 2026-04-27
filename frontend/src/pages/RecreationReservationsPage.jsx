import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import ReservationEmailModal from '../components/ReservationEmailModal';
import { ResourceGridSkeleton } from '../components/Skeleton';
import { useToast } from '../components/Toast';
import { useAuth } from '../context/AuthContext';
import { fetchBuildings, fetchResources } from '../api/resources';
import { fetchReservations, createReservation, fetchConfig, fetchTestSlots } from '../api/reservations';
import { fetchWaitlists, joinWaitlist } from '../api/waitlists';
import { TIME_SLOTS, OCCUPYING, ACTIVE_WAITLIST, todayString, getEffectiveSlots } from '../utils/reservationSlots';
import './RecreationReservationsPage.css';

export default function RecreationReservationsPage() {
  const { user } = useAuth();
  const { toast } = useToast();

  // Courts (static after mount)
  const [courts, setCourts] = useState([]);
  const [loadingCourts, setLoadingCourts] = useState(true);
  const [courtsError, setCourtsError] = useState(null);

  // Date / time selection
  const [selectedDate, setSelectedDate] = useState(todayString());
  const [selectedTime, setSelectedTime] = useState('');

  // Slot availability data
  const [allReservations, setAllReservations] = useState([]);
  const [userWaitlists, setUserWaitlists] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);

  // Per-court action state: { [courtId]: { loading, message, type } }
  const [actions, setActions] = useState({});

  // Email-prompt modal state for both reserve and waitlist flows.
  // Shape: { court, mode: 'reserve' | 'waitlist', submitting, error } | null
  const [emailModal, setEmailModal] = useState(null);

  // Demo / test-mode state
  const [demoMode, setDemoMode] = useState(false);
  const [testSlots, setTestSlots] = useState([]);

  // Fetch config + test slots on mount
  useEffect(() => {
    fetchConfig().then(cfg => {
      setDemoMode(cfg.demo_mode);
      if (cfg.demo_mode) {
        fetchTestSlots().then(setTestSlots);
      }
    });
  }, []);

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

  function handleReserve(court) {
    setEmailModal({ court, mode: 'reserve', submitting: false, error: null });
  }

  function handleWaitlist(court) {
    setEmailModal({ court, mode: 'waitlist', submitting: false, error: null });
  }

  async function handleConfirmModal(notificationEmail) {
    if (!emailModal) return;
    const { court, mode } = emailModal;
    setEmailModal({ ...emailModal, submitting: true, error: null });
    setCourtAction(court.id, { loading: true, message: null, type: null });
    try {
      if (mode === 'reserve') {
        await createReservation({
          user_id: user.id,
          resource_id: court.id,
          reservation_date: selectedDate,
          start_time: selectedTime,
          notification_email: notificationEmail,
        });
        setCourtAction(court.id, { loading: false, message: null, type: 'success' });
        toast.success(`Booked ${court.name} — confirmation sent to ${notificationEmail}.`);
        setEmailModal(prev => prev && {
          ...prev,
          submitting: false,
          success: {
            title: "You're booked!",
            message: `${court.name} is confirmed. Check ${notificationEmail} for the check-in link.`,
          },
        });
      } else {
        await joinWaitlist({
          user_id: user.id,
          resource_id: court.id,
          reservation_date: selectedDate,
          start_time: selectedTime,
          notification_email: notificationEmail,
        });
        setCourtAction(court.id, { loading: false, message: null, type: 'success' });
        toast.success(`On the waitlist for ${court.name}. We'll email ${notificationEmail} when a slot opens.`);
        setEmailModal(prev => prev && {
          ...prev,
          submitting: false,
          success: {
            title: "You're on the list!",
            message: `We'll email ${notificationEmail} the moment ${court.name} opens up.`,
          },
        });
      }
      const [reservations, waitlists] = await Promise.all([
        fetchReservations(),
        fetchWaitlists({ userId: user.id }),
      ]);
      setAllReservations(reservations);
      setUserWaitlists(waitlists);
      setTimeout(() => setEmailModal(null), 1300);
    } catch (e) {
      setCourtAction(court.id, { loading: false, message: e.message, type: 'error' });
      setEmailModal(prev => prev && { ...prev, submitting: false, error: e.message });
      toast.error(e.message);
    }
  }

  // ── Render ───────────────────────────────────────────────────────

  const today = todayString();
  const effectiveSlots = getEffectiveSlots(testSlots, selectedDate);
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
                  {effectiveSlots.map(slot => (
                    <button
                      key={slot.value}
                      type="button"
                      className={`rec-time-btn${selectedTime === slot.value ? ' rec-time-btn--active' : ''}${slot.is_test_slot ? ' rec-time-btn--test' : ''}`}
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
            <div className="rec-courts-grid">
              <ResourceGridSkeleton count={4} />
            </div>
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

      <ReservationEmailModal
        open={Boolean(emailModal)}
        defaultEmail={user.email}
        resourceName={emailModal?.court?.name}
        reservationDate={selectedDate}
        reservationTimeLabel={
          getEffectiveSlots(testSlots, selectedDate).find(s => s.value === selectedTime)?.label
          ?? selectedTime
        }
        mode={emailModal?.mode}
        onCancel={() => setEmailModal(null)}
        onConfirm={handleConfirmModal}
        submitting={emailModal?.submitting}
        error={emailModal?.error}
        success={emailModal?.success}
      />
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
