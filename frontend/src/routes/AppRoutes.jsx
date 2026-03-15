import { Navigate, Route, Routes } from 'react-router-dom';
import ProtectedRoute from '../components/ProtectedRoute';
import DashboardPage from '../pages/DashboardPage';
import LandingPage from '../pages/LandingPage';
import LoginPage from '../pages/LoginPage';
import LibraryReservationsPage from '../pages/LibraryReservationsPage';
import RecreationReservationsPage from '../pages/RecreationReservationsPage';
import CheckInPage from '../pages/CheckInPage';

/**
 * Central route map.
 *
 * Current routes:
 *   /                  → LandingPage                 (public)
 *   /login             → LoginPage                   (public, redirects to /app if already logged in)
 *   /app               → DashboardPage               (protected)
 *   /app/library       → LibraryReservationsPage     (protected) — Block 2
 *   /app/recreation    → RecreationReservationsPage  (protected) — Block 3
 *
 * Future routes (add here as blocks are implemented):
 *   /app/notifications  → Block 6 — Notifications
 */
export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />

      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/app/library"
        element={
          <ProtectedRoute>
            <LibraryReservationsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/app/recreation"
        element={
          <ProtectedRoute>
            <RecreationReservationsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/app/check-in"
        element={
          <ProtectedRoute>
            <CheckInPage />
          </ProtectedRoute>
        }
      />

      {/* Unknown paths → landing */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
