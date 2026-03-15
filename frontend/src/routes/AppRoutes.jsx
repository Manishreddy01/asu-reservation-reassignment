import { Navigate, Route, Routes } from 'react-router-dom';
import ProtectedRoute from '../components/ProtectedRoute';
import DashboardPage from '../pages/DashboardPage';
import LandingPage from '../pages/LandingPage';
import LoginPage from '../pages/LoginPage';

/**
 * Central route map.
 *
 * Current routes:
 *   /           → LandingPage   (public)
 *   /login      → LoginPage     (public, redirects to /app if already logged in)
 *   /app        → DashboardPage (protected)
 *
 * Future routes (add here as blocks are implemented):
 *   /app/library      → Block 2 — Library reservation module
 *   /app/recreation   → Block 3 — Recreation court module
 *   /app/checkin      → Block 5 — Check-in interface
 *   /app/notifications → Block 6 — Notifications
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

      {/* Unknown paths → landing */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
