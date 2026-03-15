import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';
import { fetchDashboard } from '../api/dashboard';
import { markNotificationRead } from '../api/notifications';
import './DashboardPage.css';

/* ─────────────────────────────────────────────────────────────────
   Formatting helpers
───────────────────────────────────────────────────────────────── */
function fmtDate(dateStr) {
  // "2026-03-14" → "Sat, Mar 14"
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
  });
}

function fmtTime(timeStr) {
  // "09:00:00" → "9:00 AM"
  const [h, min] = timeStr.split(':').map(Number);
  return new Date(0, 0, 0, h, min).toLocaleTimeString('en-US', {
    hour: 'numeric', minute: '2-digit',
  });
}

function fmtTimeRange(start, end) {
  return `${fmtTime(start)} – ${fmtTime(end)}`;
}

function fmtRelative(isoStr) {
  const diff = Math.floor((Date.now() - new Date(isoStr)) / 1000);
  if (diff < 60)    return 'Just now';
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function getInitials(name = '') {
  return name.split(' ').filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('');
}

/* ─────────────────────────────────────────────────────────────────
   Status display maps
───────────────────────────────────────────────────────────────── */
const RES_STATUS = {
  reserved:   { label: 'Upcoming',   cls: 'ds-status--upcoming' },
  active:     { label: 'Active Now', cls: 'ds-status--active'   },
  reassigned: { label: 'Active',     cls: 'ds-status--active'   },
  released:   { label: 'Released',   cls: 'ds-status--neutral'  },
  completed:  { label: 'Completed',  cls: 'ds-status--neutral'  },
  no_show:    { label: 'No-show',    cls: 'ds-status--warn'     },
  cancelled:  { label: 'Cancelled',  cls: 'ds-status--neutral'  },
};

const WL_STATUS = {
  waiting: { label: 'Waiting',       cls: 'ds-status--upcoming' },
  offered: { label: 'Slot Offered!', cls: 'ds-status--offered'  },
  claimed: { label: 'Claimed',       cls: 'ds-status--neutral'  },
  expired: { label: 'Expired',       cls: 'ds-status--neutral'  },
  removed: { label: 'Removed',       cls: 'ds-status--neutral'  },
};

const NOTIF_TYPE_LABEL = {
  reminder:        'Reminder',
  check_in_prompt: 'Check-in',
  no_show_alert:   'No-show Alert',
  waitlist_offer:  'Waitlist Offer',
  reassignment:    'Reassignment',
};

/* ─────────────────────────────────────────────────────────────────
   Main page
───────────────────────────────────────────────────────────────── */
export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Managed separately so mark-as-read updates immediately without a reload
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const dashboard = await fetchDashboard(user.id);
        setData(dashboard);
        setNotifications(dashboard.unread_notifications);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user.id]);

  async function handleMarkRead(id) {
    try {
      await markNotificationRead(id);
      setNotifications(prev => prev.filter(n => n.id !== id));
    } catch {
      // Non-fatal; notification stays until next page load
    }
  }

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="ds-page">
      <Navbar />

      <main className="ds-main">
        <div className="ds-inner">

          {/* ── Welcome card ── */}
          <section className="ds-welcome">
            <div className="ds-welcome-left">
              <div className="ds-avatar">{getInitials(user?.full_name)}</div>
              <div className="ds-welcome-info">
                <h1 className="ds-welcome-name">{user?.full_name}</h1>
                <p className="ds-welcome-email">{user?.email}</p>
                <span className={`ds-role-badge ds-role-badge--${user?.role}`}>
                  {user?.role}
                </span>
              </div>
            </div>
            <button className="ds-signout-btn" onClick={handleLogout}>
              Sign Out
            </button>
          </section>

          {/* ── Quick actions ── */}
          <div className="ds-quick-actions">
            <Link to="/app/library" className="ds-quick-card ds-quick-card--library">
              <span className="ds-quick-icon"><LibraryIcon /></span>
              <span className="ds-quick-text">
                <span className="ds-quick-title">Library Study Rooms</span>
                <span className="ds-quick-sub">Hayden Library</span>
              </span>
              <span className="ds-quick-arrow">›</span>
            </Link>
            <Link to="/app/recreation" className="ds-quick-card ds-quick-card--recreation">
              <span className="ds-quick-icon"><CourtIcon /></span>
              <span className="ds-quick-text">
                <span className="ds-quick-title">Recreation Courts</span>
                <span className="ds-quick-sub">SDFC Recreation Center</span>
              </span>
              <span className="ds-quick-arrow">›</span>
            </Link>
            <Link to="/app/check-in" className="ds-quick-card ds-quick-card--checkin">
              <span className="ds-quick-icon"><CheckInIcon /></span>
              <span className="ds-quick-text">
                <span className="ds-quick-title">Check In</span>
                <span className="ds-quick-sub">Verify your presence</span>
              </span>
              <span className="ds-quick-arrow">›</span>
            </Link>
          </div>

          {/* ── Loading / error states ── */}
          {loading && (
            <div className="ds-state-card">
              <p className="ds-state-msg">Loading your dashboard&hellip;</p>
            </div>
          )}

          {error && (
            <div className="ds-state-card ds-state-card--error">
              <p className="ds-state-msg">{error}</p>
            </div>
          )}

          {/* ── Data sections ── */}
          {data && (
            <>
              {/* Active Now — only shown when student has a live reservation */}
              {data.active_reservations.length > 0 && (
                <DashSection
                  title="Active Now"
                  count={data.active_reservations.length}
                  accent="active"
                  icon={<ActiveIcon />}
                >
                  {data.active_reservations.map(r => (
                    <ReservationRow key={r.id} reservation={r} variant="active" />
                  ))}
                </DashSection>
              )}

              {/* Upcoming reservations */}
              <DashSection
                title="Upcoming Reservations"
                count={data.upcoming_reservations.length}
                icon={<CalendarIcon />}
              >
                {data.upcoming_reservations.length === 0 ? (
                  <EmptyState>
                    No upcoming reservations.{' '}
                    <Link to="/app/library">Reserve a study room</Link> or{' '}
                    <Link to="/app/recreation">book a court</Link>.
                  </EmptyState>
                ) : (
                  data.upcoming_reservations.map(r => (
                    <ReservationRow key={r.id} reservation={r} />
                  ))
                )}
              </DashSection>

              {/* Waitlist */}
              <DashSection
                title="Waitlist"
                count={data.waitlist_entries.length}
                icon={<QueueIcon />}
              >
                {data.waitlist_entries.length === 0 ? (
                  <EmptyState>Not on any waitlists.</EmptyState>
                ) : (
                  data.waitlist_entries.map(w => (
                    <WaitlistRow key={w.id} entry={w} />
                  ))
                )}
              </DashSection>

              {/* Notifications */}
              <DashSection
                title="Notifications"
                count={notifications.length}
                badge={notifications.length > 0 ? `${notifications.length} unread` : null}
                icon={<BellIcon />}
                footer={<Link to="/app/notifications" className="ds-section-footer-link">View all notifications →</Link>}
              >
                {notifications.length === 0 ? (
                  <EmptyState>All caught up — no unread notifications.</EmptyState>
                ) : (
                  notifications.map(n => (
                    <NotificationRow key={n.id} notification={n} onMarkRead={handleMarkRead} />
                  ))
                )}
              </DashSection>

              {/* Recent history */}
              {data.recent_history.length > 0 && (
                <DashSection
                  title="Recent History"
                  count={data.recent_history.length}
                  icon={<HistoryIcon />}
                  muted
                >
                  {data.recent_history.map(r => (
                    <ReservationRow key={r.id} reservation={r} variant="muted" />
                  ))}
                </DashSection>
              )}
            </>
          )}

        </div>
      </main>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Section wrapper
───────────────────────────────────────────────────────────────── */
function DashSection({ title, count, badge, accent, muted, icon, footer, children }) {
  return (
    <section
      className={[
        'ds-section',
        accent  ? `ds-section--${accent}` : '',
        muted   ? 'ds-section--muted'     : '',
      ].filter(Boolean).join(' ')}
    >
      <header className="ds-section-head">
        <span className="ds-section-icon" aria-hidden="true">{icon}</span>
        <h2 className="ds-section-title">{title}</h2>
        {count > 0 && <span className="ds-section-count">{count}</span>}
        {badge  && <span className="ds-section-badge">{badge}</span>}
      </header>
      <div className="ds-section-body">{children}</div>
      {footer && <div className="ds-section-footer">{footer}</div>}
    </section>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Empty state
───────────────────────────────────────────────────────────────── */
function EmptyState({ children }) {
  return <p className="ds-empty">{children}</p>;
}

/* ─────────────────────────────────────────────────────────────────
   Reservation row  (used for upcoming, active, and history)
───────────────────────────────────────────────────────────────── */
function ReservationRow({ reservation: r, variant }) {
  const meta = RES_STATUS[r.status] ?? { label: r.status, cls: 'ds-status--neutral' };

  return (
    <div className={`ds-row${variant ? ` ds-row--${variant}` : ''}`}>
      <div className="ds-row-info">
        <span className="ds-row-name">{r.resource.name}</span>
        <span className="ds-row-meta">
          {r.resource.building.name}
          {' · '}
          {fmtDate(r.reservation_date)}
          {' · '}
          {fmtTimeRange(r.start_time, r.end_time)}
        </span>
      </div>
      <span className={`ds-status ${meta.cls}`}>{meta.label}</span>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Waitlist row
───────────────────────────────────────────────────────────────── */
function WaitlistRow({ entry: w }) {
  const meta = WL_STATUS[w.status] ?? { label: w.status, cls: 'ds-status--neutral' };

  return (
    <div className={`ds-row${w.status === 'offered' ? ' ds-row--offered' : ''}`}>
      <div className="ds-row-info">
        <span className="ds-row-name">{w.resource.name}</span>
        <span className="ds-row-meta">
          {w.resource.building.name}
          {' · '}
          {fmtDate(w.reservation_date)}
          {' · '}
          {fmtTimeRange(w.start_time, w.end_time)}
        </span>
        {w.status === 'offered' && w.offer_expires_at && (
          <span className="ds-row-offer-note">
            Offer expires at{' '}
            {new Date(w.offer_expires_at).toLocaleTimeString('en-US', {
              hour: 'numeric', minute: '2-digit',
            })}
          </span>
        )}
      </div>
      <span className={`ds-status ${meta.cls}`}>{meta.label}</span>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Notification row
───────────────────────────────────────────────────────────────── */
function NotificationRow({ notification: n, onMarkRead }) {
  const [marking, setMarking] = useState(false);

  async function handleClick() {
    setMarking(true);
    await onMarkRead(n.id);
    // If onMarkRead removes the item from the list, this component unmounts,
    // so we don't reset marking — that's intentional.
  }

  const typeLabel = NOTIF_TYPE_LABEL[n.notification_type] ?? n.notification_type;

  return (
    <div className="ds-notif-row">
      <div className="ds-notif-body">
        <div className="ds-notif-top">
          <span className="ds-notif-type">{typeLabel}</span>
          <span className="ds-notif-time">{fmtRelative(n.created_at)}</span>
        </div>
        <p className="ds-notif-title">{n.title}</p>
        <p className="ds-notif-msg">{n.message}</p>
      </div>
      <button
        type="button"
        className="ds-notif-read-btn"
        onClick={handleClick}
        disabled={marking}
      >
        {marking ? '…' : 'Mark read'}
      </button>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Inline SVG icons
───────────────────────────────────────────────────────────────── */
function LibraryIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="22" height="22">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      <line x1="9" y1="7" x2="15" y2="7" />
      <line x1="9" y1="11" x2="15" y2="11" />
    </svg>
  );
}

function CourtIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="22" height="22">
      <rect x="2" y="5" width="20" height="14" rx="2" />
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <circle cx="6" cy="8" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8"  y1="2" x2="8"  y2="6" />
      <line x1="3"  y1="10" x2="21" y2="10" />
    </svg>
  );
}

function ActiveIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function QueueIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
      <line x1="8" y1="6" x2="21" y2="6" />
      <line x1="8" y1="12" x2="21" y2="12" />
      <line x1="8" y1="18" x2="21" y2="18" />
      <circle cx="3" cy="6"  r="1.5" fill="currentColor" stroke="none" />
      <circle cx="3" cy="12" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="3" cy="18" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

function HistoryIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
      <polyline points="1 4 1 10 7 10" />
      <path d="M3.51 15a9 9 0 1 0 .49-4.79" />
    </svg>
  );
}

function CheckInIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="22" height="22">
      <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}
