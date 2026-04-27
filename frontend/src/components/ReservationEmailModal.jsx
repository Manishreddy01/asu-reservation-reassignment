import { useEffect, useRef, useState } from 'react';
import './ReservationEmailModal.css';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/* Pre-computed confetti pieces — random positions/colors picked once. */
const CONFETTI = Array.from({ length: 22 }, (_, i) => {
  const palette = ['#8C1D40', '#B5264F', '#FFC627', '#E5A800', '#2E7D32', '#1d4ed8'];
  const seed = (i * 9301 + 49297) % 233280;
  const rand = (offset) => (((seed + offset * 6151) % 233280) / 233280);
  return {
    color: palette[i % palette.length],
    left: 12 + rand(1) * 76,                 // 12–88%
    angle: -45 + rand(2) * 90,               // -45 → +45deg
    distance: 90 + rand(3) * 80,             // 90–170 px travel
    delay: rand(4) * 120,                    // 0–120ms stagger
    size: 6 + rand(5) * 6,                   // 6–12px
    spin: -180 + rand(6) * 360,
  };
});

/**
 * Modal that asks for an email before confirming a reservation OR joining a
 * waitlist. Pre-fills with the logged-in user's email; the student can
 * replace it with whichever inbox they actually monitor.
 *
 * Props:
 *   open                 — show / hide
 *   defaultEmail         — value used to pre-fill the input (typically user.email)
 *   resourceName         — for the modal heading
 *   reservationDate      — YYYY-MM-DD (for the heading)
 *   reservationTimeLabel — pre-formatted time string for display
 *   mode                 — 'reserve' (default) or 'waitlist' — picks copy + button label
 *   onCancel             — called with no args when the user dismisses
 *   onConfirm            — called with the entered email when the user confirms
 *   submitting           — disables the confirm button while a request is in flight
 *   error                — optional error message to render
 */
export default function ReservationEmailModal({
  open,
  defaultEmail,
  resourceName,
  reservationDate,
  reservationTimeLabel,
  mode = 'reserve',
  onCancel,
  onConfirm,
  submitting,
  error,
  success,
}) {
  const [email, setEmail] = useState(defaultEmail ?? '');
  const [touched, setTouched] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) {
      setEmail(defaultEmail ?? '');
      setTouched(false);
      setTimeout(() => inputRef.current?.select(), 30);
    }
  }, [open, defaultEmail]);

  if (!open) return null;

  if (success) {
    return (
      <div className="rem-backdrop" role="dialog" aria-modal="true">
        <div className="rem-modal rem-modal--success">
          <div className="rem-success-burst" aria-hidden="true">
            {CONFETTI.map((c, i) => (
              <span
                key={i}
                className="rem-confetti"
                style={{
                  left: `${c.left}%`,
                  background: c.color,
                  width: `${c.size}px`,
                  height: `${c.size * 0.4}px`,
                  animationDelay: `${c.delay}ms`,
                  '--end-x': `${Math.cos((c.angle * Math.PI) / 180) * c.distance}px`,
                  '--end-y': `${-Math.sin((Math.abs(c.angle) * Math.PI) / 180) * c.distance - 60}px`,
                  '--spin': `${c.spin}deg`,
                }}
              />
            ))}
            <svg className="rem-check-svg" viewBox="0 0 64 64" aria-hidden="true">
              <circle className="rem-check-circle" cx="32" cy="32" r="28" />
              <path className="rem-check-path" d="M20 33 L29 42 L45 24" />
            </svg>
          </div>
          <h2 className="rem-success-title">{success.title}</h2>
          <p className="rem-success-body">{success.message}</p>
        </div>
      </div>
    );
  }

  const trimmed = email.trim();
  const valid = EMAIL_RE.test(trimmed);

  function handleSubmit(e) {
    e.preventDefault();
    setTouched(true);
    if (!valid || submitting) return;
    onConfirm(trimmed);
  }

  const isWaitlist = mode === 'waitlist';
  const title = isWaitlist
    ? 'Where should we send waitlist updates?'
    : 'Where should we send your check-in details?';
  const hint = isWaitlist
    ? "We'll email a confirmation now, and again the moment a slot opens up so you can claim it."
    : "We'll email a confirmation now and three reminder emails with your check-in link as your reservation approaches.";
  const submitLabel = isWaitlist
    ? (submitting ? 'Joining…' : 'Join Waitlist')
    : (submitting ? 'Reserving…' : 'Confirm Reservation');

  return (
    <div className="rem-backdrop" role="dialog" aria-modal="true" onMouseDown={onCancel}>
      <form
        className="rem-modal"
        onSubmit={handleSubmit}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <h2 className="rem-title">{title}</h2>
        <p className="rem-subtitle">
          {resourceName}
          {reservationDate && (
            <> · <span className="rem-when">{reservationDate} at {reservationTimeLabel}</span></>
          )}
        </p>
        <p className="rem-hint">{hint}</p>

        <label className="rem-label" htmlFor="rem-email-input">
          Email for {isWaitlist ? 'waitlist updates' : 'reminders'}
        </label>
        <input
          ref={inputRef}
          id="rem-email-input"
          type="email"
          inputMode="email"
          autoComplete="email"
          className={`rem-input${touched && !valid ? ' rem-input--invalid' : ''}`}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onBlur={() => setTouched(true)}
          placeholder="you@example.com"
          required
        />
        {touched && !valid && (
          <p className="rem-error">Please enter a valid email address.</p>
        )}
        {error && <p className="rem-error">{error}</p>}

        <div className="rem-actions">
          <button
            type="button"
            className="rem-btn rem-btn--ghost"
            onClick={onCancel}
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="rem-btn rem-btn--primary"
            disabled={!valid || submitting}
          >
            {submitLabel}
          </button>
        </div>
      </form>
    </div>
  );
}
