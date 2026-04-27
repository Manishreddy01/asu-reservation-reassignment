import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

export default function Navbar() {
  const { user } = useAuth();
  const [scrolled, setScrolled] = useState(false);

  // Apply a deeper-shadow style once the page is scrolled past the top.
  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 4);
    }
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`navbar${scrolled ? ' navbar--scrolled' : ''}`}>
      <div className="navbar-inner">

        {/* Logo */}
        <Link to="/" className="navbar-logo">
          <ForkIcon />
          <span className="navbar-logo-text">ASU Campus Reservations</span>
        </Link>

        {/* Actions */}
        <nav className="navbar-actions">
          <Link to="/" className="navbar-link">Home</Link>
          {user && (
            <Link to="/app/notifications" className="navbar-link">Notifications</Link>
          )}
          {user?.role === 'admin' && (
            <Link to="/app/admin" className="navbar-link">Demo Controls</Link>
          )}
          {user ? (
            <Link to="/app" className="navbar-cta">
              Go to App
            </Link>
          ) : (
            <Link to="/login" className="navbar-cta">
              Sign In
            </Link>
          )}
        </nav>

      </div>
    </header>
  );
}

function ForkIcon() {
  return (
    <svg viewBox="0 0 32 36" fill="none" aria-hidden="true" className="navbar-fork">
      <rect x="14" y="0"  width="4" height="36" rx="2" fill="currentColor" />
      <rect x="5"  y="0"  width="3" height="20" rx="1.5" fill="currentColor" />
      <rect x="24" y="0"  width="3" height="20" rx="1.5" fill="currentColor" />
      <rect x="5"  y="17" width="4" height="4"  rx="1" fill="currentColor" />
      <rect x="23" y="17" width="4" height="4"  rx="1" fill="currentColor" />
    </svg>
  );
}
