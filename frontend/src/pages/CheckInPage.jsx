import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';
import { fetchDashboard } from '../api/dashboard';
import {
  getWindowState,
  windowOpenAt,
  windowCloseAt,
} from '../utils/checkInWindow';
import { todayString } from '../utils/reservationSlots';
import './CheckInPage.css';

/* ─────────────────────────────────────────────────────────────────
   Formatting helpers (local — same pattern as DashboardPage)
───────────────────────────────────────────────────────────────── */
function fmtDate(dateStr) {
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
  });
}

function fmtTime(timeStr) {
  const [h, min] = timeStr.split(':').map(Number);
  return new Date(0, 0, 0, h, min).toLocaleTimeString('en-US', {
    hour: 'numeric', minute: '2-digit',
  });
}

function fmtDateTime(dateObj) {
  return dateObj.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

function fmtCheckedInAt(isoStr) {
  return new Date(isoStr).toLocaleTimeString('en-US', {
    hour: 'numeric', minute: '2-digit',
  });
}

/* ─────────────────────────────────────────────────────────────────
   Window state display config
───────────────────────────────────────────────────────────────── */
const WINDOW_STATE_DISPLAY = {
  active:   { label: 'Checked In',     cls: 'ci-badge--active'   },
  open:     { label: 'Window Open',    cls: 'ci-badge--open'     },
  upcoming: { label: 'Window Upcoming',cls: 'ci-badge--upcoming' },
  closed:   { label: 'Window Closed',  cls: 'ci-badge--closed'   },
};

/* Sort order: open first, then active, then upcoming, then closed */
const SORT_ORDER = { open: 0, active: 1, upcoming: 2, closed: 3 };

function sortedReservations(reservations) {
  const now = new Date();
  return [...reservations].sort((a, b) => {
    const wa = getWindowState(a, now);
    const wb = getWindowState(b, now);
    const diff = SORT_ORDER[wa] - SORT_ORDER[wb];
    if (diff !== 0) return diff;
    if (a.reservation_date !== b.reservation_date) {
      return a.reservation_date < b.reservation_date ? -1 : 1;
    }
    return a.start_time < b.start_time ? -1 : 1;
  });
}

/* ─────────────────────────────────────────────────────────────────
   Main page
───────────────────────────────────────────────────────────────── */
export default function CheckInPage() {
  const { user } = useAuth();

  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);
  const [reservations, setReservations] = useState([]);

  // Per-reservation check-in state keyed by reservation id
  // { phase: null|'locating'|'located'|'denied'|'geo-error'|'no-support', coords: obj|null }
  const [ciStates, setCiStates] = useState({});

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchDashboard(user.id);
        // Combine active (checked-in today) and upcoming (reserved, today+future)
        const combined = [
          ...data.active_reservations,
          ...data.upcoming_reservations,
        ];
        setReservations(combined);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user.id]);

  const today = todayString();

  // Split into today's reservations (actionable) and future (informational)
  const todayReservations = useMemo(
    () => sortedReservations(reservations.filter(r => r.reservation_date === today)),
    [reservations, today],
  );
  const futureReservations = useMemo(
    () => sortedReservations(reservations.filter(r => r.reservation_date > today)),
    [reservations, today],
  );

  function setCiState(id, val) {
    setCiStates(prev => ({ ...prev, [id]: val }));
  }

  function handleCheckIn(reservationId) {
    if (!navigator.geolocation) {
      setCiState(reservationId, { phase: 'no-support', coords: null });
      return;
    }
    setCiState(reservationId, { phase: 'locating', coords: null });
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCiState(reservationId, {
          phase: 'located',
          coords: {
            lat: pos.coords.latitude.toFixed(5),
            lng: pos.coords.longitude.toFixed(5),
            accuracy: Math.round(pos.coords.accuracy),
          },
        });
      },
      (err) => {
        const phase = err.code === err.PERMISSION_DENIED ? 'denied' : 'geo-error';
        setCiState(reservationId, { phase, coords: null });
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  function handleRetry(reservationId) {
    setCiState(reservationId, null);
  }

  return (
    <div className="ci-page">
      <Navbar />
      <main className="ci-main">
        <div className="ci-inner">

          {/* ── Page header ── */}
          <header className="ci-header">
            <div className="ci-header-left">
              <h1 className="ci-title">Check In</h1>
              <p className="ci-subtitle">
                Confirm your presence within 15 minutes of your reservation start time.
              </p>
            </div>
            <Link to="/app" className="ci-back-link">
              ← Dashboard
            </Link>
          </header>

          {/* ── Loading ── */}
          {loading && (
            <div className="ci-state-card">
              <p className="ci-state-msg">Loading your reservations&hellip;</p>
            </div>
          )}

          {/* ── Error ── */}
          {error && (
            <div className="ci-state-card ci-state-card--error">
              <p className="ci-state-msg">{error}</p>
            </div>
          )}

          {/* ── Empty state ── */}
          {!loading && !error && reservations.length === 0 && (
            <div className="ci-state-card ci-state-card--empty">
              <span className="ci-empty-icon" aria-hidden="true">
                <MapPinIcon size={32} />
              </span>
              <p className="ci-state-msg">No reservations available for check-in.</p>
              <p className="ci-state-hint">
                <Link to="/app/library">Reserve a study room</Link> or{' '}
                <Link to="/app/recreation">book a court</Link> to get started.
              </p>
            </div>
          )}

          {/* ── Today's reservations ── */}
          {!loading && !error && todayReservations.length > 0 && (
            <section className="ci-section">
              <h2 className="ci-section-title">Today</h2>
              <div className="ci-cards">
                {todayReservations.map(r => (
                  <ReservationCard
                    key={r.id}
                    reservation={r}
                    ciState={ciStates[r.id] ?? null}
                    onCheckIn={handleCheckIn}
                    onRetry={handleRetry}
                  />
                ))}
              </div>
            </section>
          )}

          {/* ── Future reservations (informational) ── */}
          {!loading && !error && futureReservations.length > 0 && (
            <section className="ci-section">
              <h2 className="ci-section-title">Upcoming</h2>
              <p className="ci-section-hint">
                Check-in is only available on the day of your reservation.
              </p>
              <div className="ci-cards">
                {futureReservations.map(r => (
                  <ReservationCard
                    key={r.id}
                    reservation={r}
                    ciState={null}
                    onCheckIn={handleCheckIn}
                    onRetry={handleRetry}
                    futureOnly
                  />
                ))}
              </div>
            </section>
          )}

        </div>
      </main>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Reservation card
───────────────────────────────────────────────────────────────── */
function ReservationCard({ reservation: r, ciState, onCheckIn, onRetry, futureOnly }) {
  const now = new Date();
  const windowState = getWindowState(r, now);
  const display = WINDOW_STATE_DISPLAY[windowState];
  const openTime  = windowOpenAt(r);
  const closeTime = windowCloseAt(r);

  const isToday = !futureOnly;

  return (
    <div className={`ci-card ci-card--${windowState}`}>

      {/* ── Card header ── */}
      <div className="ci-card-head">
        <div className="ci-card-title-row">
          <span className="ci-resource-name">{r.resource.name}</span>
          <span className={`ci-badge ${display.cls}`}>{display.label}</span>
        </div>
        <div className="ci-card-meta">
          <span className="ci-meta-building">
            <LocationDotIcon />
            {r.resource.building.name}
          </span>
          <span className="ci-meta-sep" aria-hidden="true">·</span>
          <span>{fmtDate(r.reservation_date)}</span>
          <span className="ci-meta-sep" aria-hidden="true">·</span>
          <span>{fmtTime(r.start_time)} – {fmtTime(r.end_time)}</span>
        </div>
      </div>

      {/* ── Window timing info ── */}
      {isToday && windowState !== 'active' && (
        <div className="ci-window-row">
          <ClockIcon />
          <span>
            {windowState === 'upcoming' && (
              <>Check-in opens at <strong>{fmtDateTime(openTime)}</strong></>
            )}
            {windowState === 'open' && (
              <>Window open until <strong>{fmtDateTime(closeTime)}</strong></>
            )}
            {windowState === 'closed' && (
              <>Window closed at <strong>{fmtDateTime(closeTime)}</strong></>
            )}
          </span>
        </div>
      )}

      {/* ── Action area ── */}
      {isToday && (
        <div className="ci-action-area">
          {windowState === 'active' && (
            <AlreadyCheckedIn checkedInAt={r.checked_in_at} />
          )}

          {windowState === 'open' && (
            <CheckInFlow
              reservationId={r.id}
              ciState={ciState}
              onCheckIn={onCheckIn}
              onRetry={onRetry}
            />
          )}

          {windowState === 'upcoming' && (
            <button className="ci-btn ci-btn--disabled" disabled>
              <ClockIcon />
              Opens at {fmtDateTime(openTime)}
            </button>
          )}

          {windowState === 'closed' && (
            <button className="ci-btn ci-btn--disabled" disabled>
              Window expired
            </button>
          )}
        </div>
      )}

      {/* Future-only: no action, just info */}
      {futureOnly && (
        <div className="ci-action-area">
          <p className="ci-future-note">
            Check-in available on {fmtDate(r.reservation_date)} from{' '}
            <strong>{fmtDateTime(openTime)}</strong> to{' '}
            <strong>{fmtDateTime(closeTime)}</strong>.
          </p>
        </div>
      )}

    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Already checked in banner
───────────────────────────────────────────────────────────────── */
function AlreadyCheckedIn({ checkedInAt }) {
  return (
    <div className="ci-success-banner">
      <CheckCircleIcon />
      <div>
        <span className="ci-success-label">Checked in</span>
        {checkedInAt && (
          <span className="ci-success-time"> at {fmtCheckedInAt(checkedInAt)}</span>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Check-in flow (open window only)
───────────────────────────────────────────────────────────────── */
function CheckInFlow({ reservationId, ciState, onCheckIn, onRetry }) {
  const phase = ciState?.phase ?? null;

  if (!phase) {
    return (
      <div className="ci-flow">
        <p className="ci-flow-hint">
          <LocationDotIcon />
          Your location will be requested to verify proximity to the building.
        </p>
        <button
          className="ci-btn ci-btn--primary"
          onClick={() => onCheckIn(reservationId)}
        >
          <MapPinIcon size={18} />
          Check In
        </button>
      </div>
    );
  }

  if (phase === 'locating') {
    return (
      <div className="ci-flow-status ci-flow-status--locating">
        <span className="ci-spinner" aria-label="Locating" />
        <p className="ci-flow-status-msg">Requesting your location&hellip;</p>
      </div>
    );
  }

  if (phase === 'located') {
    const { lat, lng, accuracy } = ciState.coords;
    return (
      <div className="ci-flow-status ci-flow-status--located">
        <div className="ci-flow-row">
          <CheckCircleIcon />
          <span className="ci-flow-status-msg ci-flow-status-msg--success">
            Location access granted
          </span>
        </div>
        <p className="ci-flow-coords">
          {lat}, {lng} &nbsp;·&nbsp; ±{accuracy} m
        </p>
        <div className="ci-pending-notice">
          <InfoIcon />
          <div>
            <p className="ci-pending-title">Ready for geofence verification</p>
            <p className="ci-pending-body">
              Backend check-in endpoint not yet integrated. This location will be
              submitted once the endpoint is available.
            </p>
          </div>
        </div>
        <button className="ci-retry-btn" onClick={() => onRetry(reservationId)}>
          Reset
        </button>
      </div>
    );
  }

  if (phase === 'denied') {
    return (
      <div className="ci-flow-status ci-flow-status--error">
        <div className="ci-flow-row">
          <WarningIcon />
          <span className="ci-flow-status-msg ci-flow-status-msg--error">
            Location access denied
          </span>
        </div>
        <p className="ci-flow-error-body">
          Check-in requires location permission. Please allow access in your browser
          settings and try again.
        </p>
        <button className="ci-retry-btn" onClick={() => onRetry(reservationId)}>
          Try again
        </button>
      </div>
    );
  }

  if (phase === 'geo-error') {
    return (
      <div className="ci-flow-status ci-flow-status--error">
        <div className="ci-flow-row">
          <WarningIcon />
          <span className="ci-flow-status-msg ci-flow-status-msg--error">
            Unable to retrieve location
          </span>
        </div>
        <p className="ci-flow-error-body">
          Could not get your location. Check your device settings and try again.
        </p>
        <button className="ci-retry-btn" onClick={() => onRetry(reservationId)}>
          Try again
        </button>
      </div>
    );
  }

  if (phase === 'no-support') {
    return (
      <div className="ci-flow-status ci-flow-status--error">
        <div className="ci-flow-row">
          <WarningIcon />
          <span className="ci-flow-status-msg ci-flow-status-msg--error">
            Geolocation not supported
          </span>
        </div>
        <p className="ci-flow-error-body">
          Your browser does not support geolocation. Try a different browser.
        </p>
      </div>
    );
  }

  return null;
}

/* ─────────────────────────────────────────────────────────────────
   Inline SVG icons
───────────────────────────────────────────────────────────────── */
function MapPinIcon({ size = 16 }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" width={size} height={size}>
      <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

function LocationDotIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
      <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function CheckCircleIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}
