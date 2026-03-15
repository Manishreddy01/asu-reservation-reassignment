/**
 * Authentication API module.
 *
 * Calls the backend POST /api/v1/auth/login endpoint.
 * The Vite dev proxy forwards /api → http://localhost:8000.
 *
 * To upgrade to real ASU SSO, replace the body of `login` here
 * without touching any other file.
 */

const BASE = '/api/v1';

/**
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{ user: object, mock_token: string }>}
 * @throws {Error} with a human-readable message on failure
 */
export async function loginRequest(email, password) {
  const response = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json();

  if (!response.ok) {
    // Backend returns { detail: "..." } for 4xx errors
    throw new Error(data.detail ?? 'Login failed. Please try again.');
  }

  return data; // { user, mock_token, token_type, note }
}
