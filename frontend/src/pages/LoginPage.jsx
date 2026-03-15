import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { loginRequest } from '../api/auth';
import { useAuth } from '../context/AuthContext';
import './LoginPage.css';

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  // Already logged in → go straight to app (declarative, safe in StrictMode)
  if (user) {
    return <Navigate to="/app" replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = await loginRequest(email, password);
      login(data.user, data.mock_token);
      navigate('/app', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-bg">
      <div className="login-card">

        {/* ── Card header ── */}
        <div className="login-header">
          <div className="login-logo-row">
            <AsuForkIcon />
            <span className="login-brand">ASU</span>
          </div>
          <h1 className="login-title">Campus Reservations</h1>
          <p className="login-subtitle">
            Reserve study rooms and recreation courts at ASU facilities.
          </p>
        </div>

        {/* ── Divider ── */}
        <div className="login-divider" />

        {/* ── Form ── */}
        <form className="login-form" onSubmit={handleSubmit} noValidate>

          {error && (
            <div className="login-error" role="alert">
              <ErrorIcon />
              <span>{error}</span>
            </div>
          )}

          <div className="login-field">
            <label htmlFor="email" className="login-label">
              ASU Email
            </label>
            <input
              id="email"
              type="email"
              className="login-input"
              placeholder="yourname@asu.edu"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoComplete="email"
              autoFocus
              required
              disabled={loading}
            />
          </div>

          <div className="login-field">
            <label htmlFor="password" className="login-label">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="login-input"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            className="login-btn"
            disabled={loading || !email || !password}
          >
            {loading ? <Spinner /> : 'Sign In'}
          </button>

        </form>

        {/* ── Footer note ── */}
        <p className="login-footer">
          Prototype system &mdash; Arizona State University
        </p>
      </div>
    </div>
  );
}

/* ── Inline micro-components ───────────────────────────────────────── */

function AsuForkIcon() {
  // ASU pitchfork-inspired trident shape (simplified SVG)
  return (
    <svg
      className="login-fork-icon"
      viewBox="0 0 32 36"
      fill="none"
      aria-hidden="true"
    >
      <rect x="14" y="0"  width="4" height="36" rx="2" fill="currentColor" />
      <rect x="5"  y="0"  width="3" height="20" rx="1.5" fill="currentColor" />
      <rect x="24" y="0"  width="3" height="20" rx="1.5" fill="currentColor" />
      <rect x="5"  y="17" width="4" height="4"  rx="1" fill="currentColor" />
      <rect x="23" y="17" width="4" height="4"  rx="1" fill="currentColor" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18" aria-hidden="true" style={{ flexShrink: 0 }}>
      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 8a1 1 0 110 2 1 1 0 010-2z" clipRule="evenodd" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="login-spinner" viewBox="0 0 24 24" fill="none" aria-label="Loading">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeDasharray="32" strokeDashoffset="12" />
    </svg>
  );
}
