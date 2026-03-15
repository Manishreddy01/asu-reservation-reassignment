/**
 * AuthContext — prototype-friendly auth state.
 *
 * Stores { user, token } in localStorage so the session survives a page refresh.
 * The context exposes:
 *   user    — the logged-in user object, or null
 *   token   — the Bearer token string, or null
 *   login() — call after a successful API response
 *   logout()— clears session and state
 *
 * To upgrade to real JWT/SSO: replace the storage key and session shape here.
 * All consumers (useAuth) stay the same.
 */

import { createContext, useCallback, useContext, useState } from 'react';

const STORAGE_KEY = 'asu_session';

const AuthContext = createContext(null);

function readStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  // Initialise from storage so refresh preserves login
  const [session, setSession] = useState(() => readStorage());

  const login = useCallback((user, token) => {
    const next = { user, token };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setSession(next);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setSession(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user:   session?.user  ?? null,
        token:  session?.token ?? null,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
