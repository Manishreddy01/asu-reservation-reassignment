/**
 * Admin / Demo Controls — Block 14
 *
 * Single-page demo presenter tool.
 * Access: logged-in users only (any role); backend enforces DEMO_MODE gate.
 * Navigate to: /app/admin
 */

import { useState } from 'react';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';
import {
  processNoShows,
  processOffers,
  processExpirations,
  sendReminders,
  claimWaitlist,
  inspect,
} from '../api/adminDemo';
import './AdminDemoPage.css';

// ── helpers ───────────────────────────────────────────────────────────────────

function fmtDate(d) {
  if (!d) return '—';
  const [y, m, day] = d.split('-').map(Number);
  return new Date(y, m - 1, day).toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
  });
}

function fmtTime(t) {
  if (!t) return '—';
  const [h, min] = t.split(':').map(Number);
  return new Date(0, 0, 0, h, min).toLocaleTimeString('en-US', {
    hour: 'numeric', minute: '2-digit',
  });
}

const STATUS_COLORS = {
  reserved: '#2563eb', active: '#16a34a', released: '#d97706',
  reassigned: '#7c3aed', completed: '#6b7280', no_show: '#dc2626',
  cancelled: '#6b7280', waiting: '#2563eb', offered: '#d97706',
  claimed: '#16a34a', expired: '#dc2626', removed: '#6b7280',
};

function StatusBadge({ value }) {
  const color = STATUS_COLORS[value] ?? '#6b7280';
  return (
    <span style={{
      fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase',
      padding: '2px 8px', borderRadius: 99, letterSpacing: '0.04em',
      background: color + '20', color,
    }}>
      {value}
    </span>
  );
}

function JsonPanel({ data, error }) {
  if (error) return <pre className="adp-json adp-json--error">{error}</pre>;
  if (!data) return null;
  return <pre className="adp-json">{JSON.stringify(data, null, 2)}</pre>;
}

// ── sub-components ────────────────────────────────────────────────────────────

function ActionCard({ title, description, onRun, loading, children }) {
  return (
    <div className="adp-card">
      <div className="adp-card-header">
        <div>
          <div className="adp-card-title">{title}</div>
          <div className="adp-card-desc">{description}</div>
        </div>
        <button
          className="adp-btn adp-btn--primary"
          onClick={onRun}
          disabled={loading}
        >
          {loading ? 'Running…' : 'Run'}
        </button>
      </div>
      {children}
    </div>
  );
}

function OffsetInput({ value, onChange }) {
  return (
    <label className="adp-offset-label">
      <span>⏱ Time offset (minutes)</span>
      <input
        type="number"
        className="adp-input"
        placeholder="0"
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{ width: 100 }}
      />
      <span className="adp-hint">+ forward, − backward</span>
    </label>
  );
}

// ── Inspect tables ─────────────────────────────────────────────────────────────

function InspectSection({ data }) {
  const [tab, setTab] = useState('reservations');

  const tabs = [
    { id: 'reservations',       label: `Reservations (${data.recent_reservations.length})` },
    { id: 'released',           label: `Released (${data.released_reservations.length})` },
    { id: 'waitlist',           label: `Waitlist (${data.recent_waitlist.length})` },
    { id: 'notifications',      label: `Notifications (${data.recent_notifications.length})` },
    { id: 'check_in_logs',      label: `Check-in Logs (${data.recent_check_in_logs.length})` },
  ];

  return (
    <div className="adp-inspect">
      <div className="adp-tabs">
        {tabs.map(t => (
          <button
            key={t.id}
            className={`adp-tab ${tab === t.id ? 'adp-tab--active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'reservations' && (
        <ReservationTable rows={data.recent_reservations} title="Recent Reservations (latest 20)" />
      )}
      {tab === 'released' && (
        <ReservationTable rows={data.released_reservations} title="Released Reservations" />
      )}
      {tab === 'waitlist' && (
        <WaitlistTable rows={data.recent_waitlist} />
      )}
      {tab === 'notifications' && (
        <NotificationsTable rows={data.recent_notifications} />
      )}
      {tab === 'check_in_logs' && (
        <CheckInTable rows={data.recent_check_in_logs} />
      )}
    </div>
  );
}

function ReservationTable({ rows, title }) {
  if (!rows.length) return <p className="adp-empty">No reservations found.</p>;
  return (
    <div className="adp-table-wrap">
      {title && <p className="adp-table-title">{title}</p>}
      <table className="adp-table">
        <thead>
          <tr>
            <th>ID</th><th>User</th><th>Resource</th>
            <th>Date</th><th>Time</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.id}>
              <td>{r.id}</td>
              <td>{r.user_id}</td>
              <td>{r.resource?.name ?? r.resource_id}</td>
              <td>{fmtDate(r.reservation_date)}</td>
              <td>{fmtTime(r.start_time)} – {fmtTime(r.end_time)}</td>
              <td><StatusBadge value={r.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WaitlistTable({ rows }) {
  if (!rows.length) return <p className="adp-empty">No waitlist entries.</p>;
  return (
    <div className="adp-table-wrap">
      <table className="adp-table">
        <thead>
          <tr>
            <th>ID</th><th>User</th><th>Resource</th>
            <th>Date</th><th>Time</th><th>Status</th><th>Expires</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(e => (
            <tr key={e.id}>
              <td>{e.id}</td>
              <td>{e.user_id}</td>
              <td>{e.resource?.name ?? e.resource_id}</td>
              <td>{fmtDate(e.reservation_date)}</td>
              <td>{fmtTime(e.start_time)}</td>
              <td><StatusBadge value={e.status} /></td>
              <td style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                {e.offer_expires_at
                  ? new Date(e.offer_expires_at).toLocaleTimeString()
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NotificationsTable({ rows }) {
  if (!rows.length) return <p className="adp-empty">No notifications.</p>;
  return (
    <div className="adp-table-wrap">
      <table className="adp-table">
        <thead>
          <tr>
            <th>ID</th><th>User</th><th>Type</th><th>Title</th><th>Read</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(n => (
            <tr key={n.id}>
              <td>{n.id}</td>
              <td>{n.user_id}</td>
              <td style={{ fontSize: '0.75rem' }}>{n.notification_type}</td>
              <td style={{ maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {n.title}
              </td>
              <td>{n.is_read ? '✓' : '·'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CheckInTable({ rows }) {
  if (!rows.length) return <p className="adp-empty">No check-in logs.</p>;
  return (
    <div className="adp-table-wrap">
      <table className="adp-table">
        <thead>
          <tr>
            <th>ID</th><th>Res.</th><th>User</th>
            <th>Distance (m)</th><th>Geofence</th><th>Result</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(l => (
            <tr key={l.id}>
              <td>{l.id}</td>
              <td>{l.reservation_id}</td>
              <td>{l.user_id}</td>
              <td>{l.distance_to_building_meters?.toFixed(1)}</td>
              <td>{l.was_within_geofence ? '✓ Inside' : '✗ Outside'}</td>
              <td><StatusBadge value={l.result} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AdminDemoPage() {
  const { token } = useAuth();

  // Per-action state: { loading, result, error }
  const [noShowState,    setNoShowState]    = useState({});
  const [offersState,    setOffersState]    = useState({});
  const [expireState,    setExpireState]    = useState({});
  const [reminderState,  setReminderState]  = useState({});
  const [claimState,     setClaimState]     = useState({});
  const [inspectState,   setInspectState]   = useState({});

  // Shared time-offset inputs
  const [noShowOffset,   setNoShowOffset]   = useState('');
  const [offersOffset,   setOffersOffset]   = useState('');
  const [expireOffset,   setExpireOffset]   = useState('');
  const [reminderOffset, setReminderOffset] = useState('');
  const [reminderWindow, setReminderWindow] = useState('60');

  // Claim inputs
  const [claimUserId,    setClaimUserId]    = useState('');
  const [claimEntryId,   setClaimEntryId]   = useState('');
  const [claimLat,       setClaimLat]       = useState('33.4149');
  const [claimLng,       setClaimLng]       = useState('-111.8945');
  const [claimOffset,    setClaimOffset]    = useState('');

  function toInt(v) { const n = parseInt(v, 10); return isNaN(n) ? null : n; }
  function toFloat(v) { const n = parseFloat(v); return isNaN(n) ? null : n; }

  async function run(setter, fn) {
    setter({ loading: true });
    try {
      const result = await fn();
      setter({ result });
    } catch (e) {
      setter({ error: e.message });
    }
  }

  const forbidden403 =
    (noShowState.error ?? offersState.error ?? expireState.error ??
     reminderState.error ?? claimState.error ?? inspectState.error ?? '')
      .includes('403') ||
    (noShowState.error ?? offersState.error ?? expireState.error ??
     reminderState.error ?? claimState.error ?? inspectState.error ?? '')
      .toLowerCase().includes('demo mode');

  return (
    <div className="adp-page">
      <Navbar />
      <main className="adp-main">
        <div className="adp-inner">

          {/* Header */}
          <div className="adp-page-header">
            <div>
              <h1 className="adp-page-title">Admin / Demo Controls</h1>
              <p className="adp-page-subtitle">
                Developer and presenter tools — trigger core flows without waiting for real time to pass.
              </p>
            </div>
            <span className="adp-badge-demo">DEMO ONLY</span>
          </div>

          {/* 403 Banner */}
          {forbidden403 && (
            <div className="adp-banner adp-banner--warn">
              <strong>Demo mode is not enabled.</strong> Start the backend with{' '}
              <code>DEMO_MODE=true uvicorn main:app --reload</code>, or set{' '}
              <code>DEMO_KEY=&lt;secret&gt;</code> and add{' '}
              <code>X-Demo-Key: &lt;secret&gt;</code> to each request.
            </div>
          )}

          {/* ── Section 1: Actions ── */}
          <h2 className="adp-section-title">Actions</h2>

          {/* No-show */}
          <ActionCard
            title="1. Process No-Shows"
            description="Mark expired reservations as released and notify affected students."
            loading={noShowState.loading}
            onRun={() => run(setNoShowState, () => processNoShows(toInt(noShowOffset), token))}
          >
            <OffsetInput value={noShowOffset} onChange={setNoShowOffset} />
            <JsonPanel data={noShowState.result} error={noShowState.error} />
          </ActionCard>

          {/* Process offers */}
          <ActionCard
            title="2. Process Waitlist Offers"
            description="Send claim offers to the first waiting student for each released slot (FCFS)."
            loading={offersState.loading}
            onRun={() => run(setOffersState, () => processOffers(toInt(offersOffset), token))}
          >
            <OffsetInput value={offersOffset} onChange={setOffersOffset} />
            <JsonPanel data={offersState.result} error={offersState.error} />
          </ActionCard>

          {/* Process expirations */}
          <ActionCard
            title="3. Process Offer Expirations"
            description="Expire timed-out offers and advance the queue to the next student. Use offset ≥ 6 to jump past the 5-min window."
            loading={expireState.loading}
            onRun={() => run(setExpireState, () => processExpirations(toInt(expireOffset), token))}
          >
            <OffsetInput value={expireOffset} onChange={setExpireOffset} />
            <JsonPanel data={expireState.result} error={expireState.error} />
          </ActionCard>

          {/* Send reminders */}
          <ActionCard
            title="4. Send Reminders"
            description="Generate reminder notifications for upcoming reservations within the look-ahead window."
            loading={reminderState.loading}
            onRun={() =>
              run(setReminderState, () =>
                sendReminders(toInt(reminderWindow) ?? 60, toInt(reminderOffset), token),
              )
            }
          >
            <div className="adp-row">
              <label className="adp-offset-label">
                <span>Window (minutes)</span>
                <input
                  type="number"
                  className="adp-input"
                  value={reminderWindow}
                  onChange={e => setReminderWindow(e.target.value)}
                  style={{ width: 100 }}
                />
              </label>
              <OffsetInput value={reminderOffset} onChange={setReminderOffset} />
            </div>
            <JsonPanel data={reminderState.result} error={reminderState.error} />
          </ActionCard>

          {/* Claim waitlist */}
          <div className="adp-card">
            <div className="adp-card-header">
              <div>
                <div className="adp-card-title">5. Claim Waitlist Offer</div>
                <div className="adp-card-desc">
                  Exercise the full geofence-validated claim path. Use building coords to pass, or distant coords to demo a failure.
                </div>
              </div>
              <button
                className="adp-btn adp-btn--primary"
                onClick={() =>
                  run(setClaimState, () =>
                    claimWaitlist(
                      {
                        userId: toInt(claimUserId),
                        waitlistEntryId: toInt(claimEntryId),
                        lat: toFloat(claimLat),
                        lng: toFloat(claimLng),
                        dtOffsetMinutes: toInt(claimOffset),
                      },
                      token,
                    ),
                  )
                }
                disabled={claimState.loading}
              >
                {claimState.loading ? 'Running…' : 'Run'}
              </button>
            </div>
            <div className="adp-claim-grid">
              <label className="adp-field">
                <span>User ID</span>
                <input className="adp-input" type="number" value={claimUserId}
                  onChange={e => setClaimUserId(e.target.value)} placeholder="e.g. 1" />
              </label>
              <label className="adp-field">
                <span>Waitlist Entry ID</span>
                <input className="adp-input" type="number" value={claimEntryId}
                  onChange={e => setClaimEntryId(e.target.value)} placeholder="e.g. 2" />
              </label>
              <label className="adp-field">
                <span>Latitude</span>
                <input className="adp-input" type="number" step="any" value={claimLat}
                  onChange={e => setClaimLat(e.target.value)} />
              </label>
              <label className="adp-field">
                <span>Longitude</span>
                <input className="adp-input" type="number" step="any" value={claimLng}
                  onChange={e => setClaimLng(e.target.value)} />
              </label>
            </div>
            <div className="adp-coords-hint">
              <strong>Coords inside geofence:</strong>{' '}
              Library 33.4149, -111.8945 &nbsp;|&nbsp; SDFC 33.4188, -111.9318
            </div>
            <OffsetInput value={claimOffset} onChange={setClaimOffset} />
            <JsonPanel data={claimState.result} error={claimState.error} />
          </div>

          {/* ── Section 2: Inspect ── */}
          <div className="adp-section-row">
            <h2 className="adp-section-title" style={{ margin: 0 }}>DB Snapshot</h2>
            <button
              className="adp-btn adp-btn--ghost"
              onClick={() => run(setInspectState, () => inspect(token))}
              disabled={inspectState.loading}
            >
              {inspectState.loading ? 'Loading…' : 'Refresh Snapshot'}
            </button>
          </div>

          {inspectState.error && (
            <JsonPanel error={inspectState.error} />
          )}

          {inspectState.result && (
            <InspectSection data={inspectState.result} />
          )}

          {!inspectState.result && !inspectState.error && !inspectState.loading && (
            <div className="adp-empty-state">
              Click <strong>Refresh Snapshot</strong> to load a read-only view of the database.
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
