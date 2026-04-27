import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import './Toast.css';

const ToastCtx = createContext(null);

let idCounter = 0;

/**
 * Toast types: 'success' | 'error' | 'info'.
 * Usage:
 *   const { toast } = useToast();
 *   toast.success('Reservation confirmed!');
 *   toast.error('Could not connect to server.');
 *   toast.info('Sending email…');
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timersRef = useRef(new Map());

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const handle = timersRef.current.get(id);
    if (handle) {
      clearTimeout(handle);
      timersRef.current.delete(id);
    }
  }, []);

  const push = useCallback(
    (type, message, opts = {}) => {
      const id = ++idCounter;
      const duration = opts.duration ?? (type === 'error' ? 5500 : 3500);
      setToasts((prev) => [...prev, { id, type, message }]);
      const handle = setTimeout(() => dismiss(id), duration);
      timersRef.current.set(id, handle);
      return id;
    },
    [dismiss],
  );

  // Cleanup on unmount.
  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach((h) => clearTimeout(h));
      timers.clear();
    };
  }, []);

  const api = {
    toast: {
      success: (msg, opts) => push('success', msg, opts),
      error:   (msg, opts) => push('error',   msg, opts),
      info:    (msg, opts) => push('info',    msg, opts),
    },
    dismiss,
  };

  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="toast-stack" role="region" aria-live="polite" aria-label="Notifications">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx;
}

function ToastItem({ toast, onDismiss }) {
  return (
    <div className={`toast toast--${toast.type}`} role="status">
      <span className="toast-icon" aria-hidden="true">
        {toast.type === 'success' && <CheckIcon />}
        {toast.type === 'error'   && <AlertIcon />}
        {toast.type === 'info'    && <InfoIcon />}
      </span>
      <span className="toast-msg">{toast.message}</span>
      <button
        type="button"
        className="toast-close"
        aria-label="Dismiss notification"
        onClick={onDismiss}
      >
        ×
      </button>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6"
      strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}
function AlertIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"
      strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}
function InfoIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"
      strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  );
}
