/**
 * DashboardPage — Block 0 placeholder.
 *
 * This is a minimal protected page that proves the login flow works.
 * It will be replaced by the real student dashboard in Block 4.
 */
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './DashboardPage.css';

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="dash-bg">
      <div className="dash-card">

        {/* ── Top bar ── */}
        <header className="dash-header">
          <div className="dash-logo-row">
            <ForkIcon />
            <span className="dash-brand">ASU Campus Reservations</span>
          </div>
          <button className="dash-logout-btn" onClick={handleLogout}>
            Sign Out
          </button>
        </header>

        {/* ── Body ── */}
        <main className="dash-body">
          <div className="dash-welcome-badge">
            <span className="dash-avatar">{getInitials(user?.full_name)}</span>
          </div>

          <h1 className="dash-welcome">
            Welcome, {user?.full_name?.split(' ')[0]}!
          </h1>
          <p className="dash-email">{user?.email}</p>

          <div className="dash-info-box">
            <p>
              You are signed in as a <strong>{user?.role}</strong>.
            </p>
            <p>
              The full student dashboard is coming in Block 4. From here
              you will be able to view upcoming reservations, waitlist
              positions, and notifications.
            </p>
          </div>

          <div className="dash-modules">
            <ModuleCard
              icon="📚"
              title="Library Study Rooms"
              description="Browse and reserve rooms in Hayden Library."
              to="/app/library"
            />
            <ModuleCard
              icon="🏸"
              title="Recreation Courts"
              description="Reserve badminton courts at the SDFC."
              to="/app/recreation"
            />
            <ModuleCard
              icon="✅"
              title="Check-In"
              description="Location-verified check-in for your reservations."
              coming
            />
          </div>
        </main>

      </div>
    </div>
  );
}

function ModuleCard({ icon, title, description, coming, to }) {
  const inner = (
    <>
      <span className="dash-module-icon">{icon}</span>
      <div>
        <h3 className="dash-module-title">{title}</h3>
        <p className="dash-module-desc">{description}</p>
        {coming && <span className="dash-module-badge">Coming soon</span>}
        {to && <span className="dash-module-badge dash-module-badge--active">Open →</span>}
      </div>
    </>
  );

  if (to) {
    return (
      <Link to={to} className="dash-module-card dash-module-card--link">
        {inner}
      </Link>
    );
  }

  return (
    <div className={`dash-module-card${coming ? ' coming-soon' : ''}`}>
      {inner}
    </div>
  );
}

function getInitials(name = '') {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join('');
}

function ForkIcon() {
  return (
    <svg viewBox="0 0 32 36" fill="none" aria-hidden="true" width="22" height="26">
      <rect x="14" y="0"  width="4" height="36" rx="2" fill="currentColor" />
      <rect x="5"  y="0"  width="3" height="20" rx="1.5" fill="currentColor" />
      <rect x="24" y="0"  width="3" height="20" rx="1.5" fill="currentColor" />
      <rect x="5"  y="17" width="4" height="4"  rx="1" fill="currentColor" />
      <rect x="23" y="17" width="4" height="4"  rx="1" fill="currentColor" />
    </svg>
  );
}
