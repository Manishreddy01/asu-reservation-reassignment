# ASU Campus Reservations — Prototype

A full-stack prototype for managing campus space reservations at Arizona State University. Students reserve study rooms (Library) and recreation courts (SDFC), check in via geofencing, cancel upcoming reservations, and move up a waitlist when slots are released.

---

## Tech Stack

| Layer     | Tech                                      |
|-----------|-------------------------------------------|
| Backend   | Python · FastAPI · SQLAlchemy · SQLite    |
| Frontend  | React · Vite · React Router              |
| Auth      | Mock token (Base64 user_id:email)         |
| Passwords | bcrypt via passlib                        |

---

## Project Structure

```
asu-reservation-reassignment/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── db/           # Database setup
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   └── seeds/        # Seed data
│   ├── main.py
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── api/          # Fetch wrappers
    │   ├── components/   # Shared components
    │   ├── context/      # AuthContext
    │   ├── pages/        # Page components
    │   └── routes/       # React Router config
    └── package.json
```

---

## Running the App

### 1. Backend

```bash
cd backend

# Create and activate virtual environment (first time only)
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Seed the database (first time only)
python -m app.seeds.seed_data

# Start the server
DEMO_MODE=true uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

### 2. Frontend

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start the dev server
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## Demo Credentials

| Role    | Email                    | Password        |
|---------|--------------------------|-----------------|
| Admin   | `admin@asu.edu`          | `admin2024`     |
| Student | `mponnapa@asu.edu`       | `Manish01@vit`  |
| Student | `alice.johnson@asu.edu`  | `password123`   |
| Student | `bob.martinez@asu.edu`   | `password123`   |
| Student | `faisal.alrashid@asu.edu`| `password123`   |

Log in at `/login`. Admins see a **Demo Controls** link in the navbar.

---

## How Reservation States Are Derived

Every reservation carries a `status` field that the backend transitions explicitly.

| Status      | Meaning                                                              |
|-------------|----------------------------------------------------------------------|
| `reserved`  | Booked; student has not checked in yet                              |
| `active`    | Student successfully checked in (within geofence + time window)     |
| `completed` | Reservation period ended after check-in (set manually or by admin)  |
| `no_show`   | Check-in deadline passed with no check-in — pending release         |
| `released`  | No-show processed; slot freed for waitlist reassignment             |
| `reassigned`| A waitlisted student claimed the slot                               |
| `cancelled` | Student explicitly cancelled before the slot started                |

The **dashboard** derives status display from current server time:

- **Active Now** — `status ∈ {active, reassigned}`, today's date
- **Upcoming** — `status = reserved`, end time has NOT passed
- **Missed / No-show** — `status = reserved`, `check_in_deadline < now`, no check-in
  _(These haven't been formally processed yet; they appear in the Missed section immediately.)_
- **History** — `status ∈ {completed, no_show, cancelled, released}`

---

## How Cancellation Works

Students can cancel any upcoming (`reserved`) reservation from their dashboard before the slot starts.

**Flow:**

1. Student clicks **Cancel** on an upcoming reservation card → confirms in a modal.
2. Backend (`POST /reservations/{id}/cancel`) validates:
   - Reservation belongs to the requesting user
   - Status is `reserved`
   - Start time has not yet passed
3. Reservation `status` → `cancelled`.
4. A `cancellation_confirmed` notification + email is sent to the student.
5. If any students are on the **waitlist** for that slot, an offer is immediately sent to the first in queue (FCFS, 5-minute window).
6. The dashboard refreshes automatically — the cancelled reservation moves to **Recent History**.

**Waitlist claim after cancellation:**
The claim flow (`POST /waitlists/claim`) now handles both no-show releases _and_ cancellations. If no released reservation exists but the slot is genuinely free, a new reservation is created directly for the claiming student.

---

## How Demo Seed Data Is Structured

On first startup the seeder (`backend/app/seeds/seed_data.py`) inserts time-aware data relative to the current wall-clock hour so the dashboard looks live immediately:

| Scenario         | Who    | Resource             | When                      |
|------------------|--------|----------------------|---------------------------|
| Active Now       | Alice  | Study Room A101      | Current hour              |
| Active Now       | Emma   | Badminton Court 2    | Current hour (reassigned) |
| Upcoming         | Bob    | Study Room A102      | +2 h today                |
| Upcoming         | Manish | Study Room B201      | +3 h today                |
| Upcoming         | Carol  | Badminton Court 3    | Tomorrow 10 AM            |
| Upcoming         | David  | Study Room B202      | Tomorrow 2 PM             |
| Upcoming         | Alice  | Badminton Court 4    | Day after tomorrow        |
| No-show          | Faisal | Study Room A101      | 3 h ago today             |
| Released         | Carol  | Badminton Court 1    | 2 h ago today             |
| Completed        | David  | Study Room B202      | Yesterday                 |
| Completed        | Alice  | Badminton Court 4    | Yesterday                 |
| Cancelled        | David  | Badminton Court 3    | Tomorrow (pre-cancelled)  |
| Cancelled        | Carol  | Study Room A102      | Day after tomorrow        |

**Waitlist snapshot at startup:**

| Student | Resource          | Date          | Status   |
|---------|-------------------|---------------|----------|
| Faisal  | Badminton Court 1 | Today         | Offered  |
| Alice   | Badminton Court 1 | Today         | Waiting  |
| Bob     | Study Room A101   | Tomorrow      | Waiting  |
| Manish  | Badminton Court 2 | Tomorrow      | Waiting  |

To reset the data, stop the server, delete `backend/app.db`, and restart.

---

## Key Demo Flows

### Reserving a room
1. Log in as a student → **Go to App**
2. Click **Library** or **Recreation** to browse available slots
3. Click **Reserve** on any open slot

### Cancelling a reservation
1. Log in as a student
2. In **Upcoming Reservations**, click **Cancel** on any future slot
3. Confirm in the dialog — the reservation moves to history and the waitlist is notified

### Check-in (geofence)
1. Go to **Check In** from the dashboard
2. Click **Check In** on a reservation whose window is open (15 min before → 15 min after start)
3. Browser requests location; backend validates proximity to the ASU building

### Waitlist & reassignment
1. Admin triggers **No-Show Processing** from Demo Controls → released slots appear
2. Admin triggers **Process Offers** → first waiting student receives an offer notification
3. Waiting student claims the offer from their notifications (or Admin uses **Claim Waitlist** button)
4. Admin triggers **Process Expirations** to cascade the queue if an offer expires

### Reminders
- Admin triggers **Send Reminders** with a time offset to simulate upcoming slots within the window

---

## Demo Controls (`/app/admin`)

Available only to users with `role = admin`. Requires the server to run with `DEMO_MODE=true`.

| Action               | What it does                                                  |
|----------------------|---------------------------------------------------------------|
| Process No-Shows     | Marks overdue un-checked-in reservations as released          |
| Process Offers       | Sends a waitlist offer to the next eligible student           |
| Process Expirations  | Expires timed-out offers and advances the queue               |
| Send Reminders       | Sends reminder notifications for upcoming reservations        |
| Claim Waitlist       | Simulates a student claiming a waitlist offer (with coords)   |
| DB Snapshot          | Read-only view of reservations, waitlist, notifications, logs |

All actions accept an optional **time offset** (minutes) to simulate the clock moving forward without changing any database timestamps.

---

## Email Sending

### Current behavior (no SMTP configured)
All emails are **simulated** — they are written to the `email_logs` table in SQLite and visible in the Admin DB Snapshot. No emails leave the server. This is the default for development.

### Enabling real email delivery
Set the following environment variables before starting the backend:

```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-account@gmail.com
export SMTP_PASSWORD=your-app-password
export SMTP_FROM=noreply@asu.edu
```

When `SMTP_HOST`, `SMTP_USER`, and `SMTP_PASSWORD` are all set, the messaging service attempts real SMTP delivery via STARTTLS. If delivery fails for any reason, the error is logged to stdout and the in-app notification is still created — **the server never crashes due to email misconfiguration**.

**Supported email types:**

| Event                  | Trigger                                         |
|------------------------|-------------------------------------------------|
| `reservation_confirmed`| Student creates a reservation                   |
| `cancellation_confirmed`| Student cancels a reservation                  |
| `reminder`             | Reminder sent before reservation start          |
| `check_in_prompt`      | Check-in window opens                           |
| `no_show`              | Check-in deadline passed without check-in       |
| `waitlist_offer`       | A slot opens and is offered to next in queue    |
| `reassignment_success` | Student successfully claims a waitlist slot     |
| `offer_expired`        | Waitlist offer window closed without claim      |

---

## Environment Variables

| Variable        | Default           | Description                                              |
|-----------------|-------------------|----------------------------------------------------------|
| `DEMO_MODE`     | `false`           | Set to `true` to enable admin demo endpoints             |
| `DEMO_KEY`      | (none)            | Alternative to DEMO_MODE: pass as `X-Demo-Key` header    |
| `SMTP_HOST`     | (none)            | SMTP server hostname — leave unset to simulate only      |
| `SMTP_PORT`     | `587`             | SMTP port                                                |
| `SMTP_USER`     | (none)            | SMTP login username                                      |
| `SMTP_PASSWORD` | (none)            | SMTP login password                                      |
| `SMTP_FROM`     | `noreply@asu.edu` | From address used in outgoing emails                     |

---

## ASU Building Coordinates (for geofence testing)

| Building              | Latitude  | Longitude   |
|-----------------------|-----------|-------------|
| Hayden Library        | 33.4149   | -111.8945   |
| SDFC (Recreation)     | 33.4188   | -111.9318   |

Use these coordinates in the **Claim Waitlist** demo action to pass the geofence check.
The geofence radius is 120 m for both buildings.
