import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';
import { fetchNotifications, markNotificationRead } from '../api/notifications';
import './NotificationsPage.css';

/* ─────────────────────────────────────────────────────────────────
   Notification type display map
   Covers all types defined in the backend Notification model.
───────────────────────────────────────────────────────────────── */
const NOTIF_TYPE = {
  reminder:              { label: 'Reminder',        cls: 'nt-type--info'    },
  check_in_prompt:       { label: 'Check-In',        cls: 'nt-type--info'    },
  no_show:               { label: 'No-Show',         cls: 'nt-type--warn'    },
  waitlist_offer:        { label: 'Waitlist Offer',  cls: 'nt-type--offer'   },
  offer_expired:         { label: 'Offer Expired',   cls: 'nt-type--warn'    },
  reservation_confirmed: { label: 'Confirmed',       cls: 'nt-type--success' },
  reassignment_success:  { label: 'Reassignment',    cls: 'nt-type--success' },
};

function typeDisplay(notification_type) {
  return NOTIF_TYPE[notification_type] ?? { label: notification_type, cls: 'nt-type--neutral' };
}

/* ─────────────────────────────────────────────────────────────────
   Relative timestamp
───────────────────────────────────────────────────────────────── */
function fmtRelative(isoStr) {
  const diff = Math.floor((Date.now() - new Date(isoStr)) / 1000);
  if (diff < 60)    return 'Just now';
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`;
  return new Date(isoStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/* ─────────────────────────────────────────────────────────────────
   Main page
───────────────────────────────────────────────────────────────── */
export default function NotificationsPage() {
  const { user } = useAuth();

  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState(null);
  const [filter, setFilter]               = useState('all');   // 'all' | 'unread'
  const [marking, setMarking]             = useState(new Set()); // ids currently being patched

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchNotifications(user.id);
        setNotifications(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user.id]);

  const unreadCount = useMemo(
    () => notifications.filter(n => !n.is_read).length,
    [notifications],
  );

  const displayed = useMemo(
    () => filter === 'unread' ? notifications.filter(n => !n.is_read) : notifications,
    [notifications, filter],
  );

  async function handleMarkRead(id) {
    setMarking(prev => new Set(prev).add(id));
    try {
      await markNotificationRead(id);
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, is_read: true } : n)
      );
    } catch {
      // Non-fatal — notification stays unread; user can retry
    } finally {
      setMarking(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  return (
    <div className="nt-page">
      <Navbar />
      <main className="nt-main">
        <div className="nt-inner">

          {/* ── Header ── */}
          <header className="nt-header">
            <div className="nt-header-left">
              <h1 className="nt-title">Notifications</h1>
              {!loading && !error && unreadCount > 0 && (
                <span className="nt-unread-pill">{unreadCount} unread</span>
              )}
            </div>
            <Link to="/app" className="nt-back-link">← Dashboard</Link>
          </header>

          {/* ── Filter toggle ── */}
          {!loading && !error && notifications.length > 0 && (
            <div className="nt-filter-row">
              <button
                className={`nt-filter-btn${filter === 'all' ? ' nt-filter-btn--active' : ''}`}
                onClick={() => setFilter('all')}
              >
                All
                <span className="nt-filter-count">{notifications.length}</span>
              </button>
              <button
                className={`nt-filter-btn${filter === 'unread' ? ' nt-filter-btn--active' : ''}`}
                onClick={() => setFilter('unread')}
              >
                Unread
                {unreadCount > 0 && (
                  <span className="nt-filter-count nt-filter-count--unread">{unreadCount}</span>
                )}
              </button>
            </div>
          )}

          {/* ── Loading ── */}
          {loading && (
            <div className="nt-state-card">
              <p className="nt-state-msg">Loading notifications&hellip;</p>
            </div>
          )}

          {/* ── Error ── */}
          {error && (
            <div className="nt-state-card nt-state-card--error">
              <p className="nt-state-msg">{error}</p>
            </div>
          )}

          {/* ── Empty states ── */}
          {!loading && !error && notifications.length === 0 && (
            <div className="nt-state-card nt-state-card--empty">
              <span className="nt-empty-icon" aria-hidden="true"><BellIcon size={32} /></span>
              <p className="nt-state-msg">No notifications yet.</p>
              <p className="nt-state-hint">
                You&rsquo;ll receive notifications for reminders, check-in prompts,
                waitlist offers, and reservation updates.
              </p>
            </div>
          )}

          {!loading && !error && notifications.length > 0 && displayed.length === 0 && (
            <div className="nt-state-card nt-state-card--empty">
              <span className="nt-empty-icon" aria-hidden="true"><CheckIcon size={28} /></span>
              <p className="nt-state-msg">All caught up — no unread notifications.</p>
              <button className="nt-show-all-btn" onClick={() => setFilter('all')}>
                Show all notifications
              </button>
            </div>
          )}

          {/* ── Notification list ── */}
          {!loading && !error && displayed.length > 0 && (
            <div className="nt-list">
              {displayed.map(n => (
                <NotificationItem
                  key={n.id}
                  notification={n}
                  isMarking={marking.has(n.id)}
                  onMarkRead={handleMarkRead}
                />
              ))}
            </div>
          )}

        </div>
      </main>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Notification item
───────────────────────────────────────────────────────────────── */
function NotificationItem({ notification: n, isMarking, onMarkRead }) {
  const { label, cls } = typeDisplay(n.notification_type);

  return (
    <div className={`nt-item${n.is_read ? '' : ' nt-item--unread'}`}>
      {/* Unread dot */}
      {!n.is_read && <span className="nt-unread-dot" aria-label="Unread" />}

      <div className="nt-item-body">
        <div className="nt-item-top">
          <span className={`nt-type-badge ${cls}`}>{label}</span>
          <span className="nt-item-time">{fmtRelative(n.created_at)}</span>
        </div>
        <p className="nt-item-title">{n.title}</p>
        <p className="nt-item-msg">{n.message}</p>
      </div>

      {!n.is_read && (
        <button
          className="nt-mark-btn"
          onClick={() => onMarkRead(n.id)}
          disabled={isMarking}
          title="Mark as read"
        >
          {isMarking ? <SpinnerIcon /> : 'Mark read'}
        </button>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Icons
───────────────────────────────────────────────────────────────── */
function BellIcon({ size = 16 }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width={size} height={size}>
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

function CheckIcon({ size = 16 }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" width={size} height={size}>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}

function SpinnerIcon() {
  return <span className="nt-spinner" aria-label="Loading" />;
}
