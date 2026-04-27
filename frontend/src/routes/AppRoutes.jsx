import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ProtectedRoute from '../components/ProtectedRoute';
import DashboardPage from '../pages/DashboardPage';
import LandingPage from '../pages/LandingPage';
import LoginPage from '../pages/LoginPage';
import LibraryReservationsPage from '../pages/LibraryReservationsPage';
import RecreationReservationsPage from '../pages/RecreationReservationsPage';
import CheckInPage from '../pages/CheckInPage';
import NotificationsPage from '../pages/NotificationsPage';
import AdminDemoPage from '../pages/AdminDemoPage';

/**
 * Guards /app/admin: user must be logged in AND have role === 'admin'.
 * Non-admin authenticated users are redirected to /app instead of /login.
 */
function AdminRoute({ children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== 'admin') return <Navigate to="/app" replace />;
  return children;
}

/**
 * Central route map.
 *
 * Routes:
 *   /                  → LandingPage                 (public)
 *   /login             → LoginPage                   (public, redirects to /app if already logged in)
 *   /app               → DashboardPage               (protected)
 *   /app/library       → LibraryReservationsPage     (protected)
 *   /app/recreation    → RecreationReservationsPage  (protected)
 *   /app/check-in      → CheckInPage                 (protected)
 *   /app/notifications → NotificationsPage           (protected)
 *   /app/admin         → AdminDemoPage               (admin only)
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

      <Route
        path="/app/notifications"
        element={
          <ProtectedRoute>
            <NotificationsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/app/admin"
        element={
          <AdminRoute>
            <AdminDemoPage />
          </AdminRoute>
        }
      />

      {/* Unknown paths → landing */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
