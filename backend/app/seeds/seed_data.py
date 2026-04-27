"""
Seed data for the ASU Reservation Reassignment prototype.

Time-aware scenarios (all relative to NOW so the dashboard looks live immediately):

  ACTIVE NOW
    - Alice  → Study Room A101, current hour (checked in 10 min ago)
    - Emma   → Badminton Court 2, current hour (reassigned + checked in)

  UPCOMING (future, not yet started)
    - Bob    → Study Room A102, +2 h from now today
    - Manish → Study Room B201, +3 h from now today
    - Carol  → Badminton Court 3, tomorrow morning
    - David  → Study Room B202, tomorrow afternoon

  MISSED / NO-SHOW (today, deadline passed, unprocessed)
    - Faisal → Study Room A101 earlier this morning (no check-in)

  RELEASED (no-show processed, available for reassignment)
    - Carol  → Badminton Court 1, earlier slot today

  COMPLETED (yesterday)
    - David  → Study Room B202 yesterday
    - Alice  → Badminton Court 4 yesterday

  CANCELLED
    - David  → Badminton Court 3 tomorrow (pre-cancelled)
    - Carol  → Study Room A102 two days out (cancelled)

  WAITLIST
    - Faisal → Court 1 today (offered — first in queue for Carol's released slot)
    - Alice  → Court 1 today (waiting — second in queue)
    - Bob    → Study Room A101 tomorrow (waiting — slot is taken by a reservation)
    - Manish → Court 2 tomorrow (waiting)

  NOTIFICATIONS — a realistic variety already present on first load

  EMAIL LOGS — matching the notifications above
"""

import datetime
from zoneinfo import ZoneInfo

import bcrypt as _bcrypt
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.check_in_log import CheckInLog
from app.models.email_log import EmailLog, EmailStatus
from app.models.notification import Notification
from app.models.reservation import Reservation, ReservationStatus
from app.models.resource import Resource, ResourceType
from app.models.user import User, UserRole
from app.models.waitlist import WaitlistEntry, WaitlistStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
AZ = ZoneInfo("America/Phoenix")


def _dt(date: datetime.date, hour: int, minute: int = 0) -> datetime.datetime:
    """Build a timezone-aware datetime in Arizona time."""
    return datetime.datetime(date.year, date.month, date.day, hour, minute, tzinfo=AZ)


def _hash(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


# ---------------------------------------------------------------------------
# Reference dates & hours (relative to now so demos always look current)
# ---------------------------------------------------------------------------
_NOW_AZ = datetime.datetime.now(AZ)
TODAY   = datetime.date.today()
YESTERDAY = TODAY - datetime.timedelta(days=1)
TOMORROW  = TODAY + datetime.timedelta(days=1)
DAY_AFTER = TODAY + datetime.timedelta(days=2)

# "Active" hour = current wall-clock hour, clamped to [8, 21] for valid slots.
_H = max(8, min(_NOW_AZ.hour, 21))

# Time slots derived from current hour
ACTIVE_H    = _H                          # currently in progress
UPCOMING_H1 = min(_H + 2, 22)            # +2 h
UPCOMING_H2 = min(_H + 3, 22)            # +3 h
PAST_H1     = max(_H - 3, 8)             # no-show (3 h ago)
PAST_H2     = max(_H - 2, 8)             # released (2 h ago)

# ---------------------------------------------------------------------------
# Main seeder
# ---------------------------------------------------------------------------
def seed(db: Session) -> None:
    """
    Populate the database with demo data.
    Safe to call multiple times — skips seeding if users already exist.
    """
    if db.query(User).count() > 0:
        print("  [seed] Data already present — skipping.")
        return

    print("  [seed] Inserting seed data...")

    # ------------------------------------------------------------------
    # 1. Users
    # ------------------------------------------------------------------
    alice  = User(full_name="Alice Johnson",    email="alice.johnson@asu.edu",   hashed_password=_hash("password123"), role=UserRole.student)
    bob    = User(full_name="Bob Martinez",     email="bob.martinez@asu.edu",    hashed_password=_hash("password123"), role=UserRole.student)
    carol  = User(full_name="Carol Nguyen",     email="carol.nguyen@asu.edu",    hashed_password=_hash("password123"), role=UserRole.student)
    david  = User(full_name="David Kim",        email="david.kim@asu.edu",       hashed_password=_hash("password123"), role=UserRole.student)
    emma   = User(full_name="Emma Patel",       email="emma.patel@asu.edu",      hashed_password=_hash("password123"), role=UserRole.student)
    faisal = User(full_name="Faisal Al-Rashid", email="faisal.alrashid@asu.edu", hashed_password=_hash("password123"), role=UserRole.student)
    manish = User(full_name="Manish Ponnapa",   email="mponnapa@asu.edu",        hashed_password=_hash("Manish01@vit"), role=UserRole.student)
    admin  = User(full_name="Demo Admin",       email="admin@asu.edu",           hashed_password=_hash("admin2024"),   role=UserRole.admin)

    db.add_all([alice, bob, carol, david, emma, faisal, manish, admin])
    db.flush()

    # ------------------------------------------------------------------
    # 2. Buildings
    # ------------------------------------------------------------------
    library = Building(
        name="Hayden Library",
        latitude=33.4140,
        longitude=-111.8954,
        geofence_radius_meters=200.0,
    )
    sdfc = Building(
        name="SDFC Recreation Center",
        latitude=33.416524007686434,
        longitude=-111.93042783018929,
        geofence_radius_meters=200.0,
    )
    db.add_all([library, sdfc])
    db.flush()

    # ------------------------------------------------------------------
    # 3. Resources
    # ------------------------------------------------------------------
    room_a101 = Resource(building_id=library.id, resource_type=ResourceType.study_room, name="Study Room A101", capacity=4, features="Whiteboard, TV screen, HDMI")
    room_a102 = Resource(building_id=library.id, resource_type=ResourceType.study_room, name="Study Room A102", capacity=6, features="Whiteboard, projector, conference table")
    room_b201 = Resource(building_id=library.id, resource_type=ResourceType.study_room, name="Study Room B201", capacity=2, features="Standing desk, quiet zone")
    room_b202 = Resource(building_id=library.id, resource_type=ResourceType.study_room, name="Study Room B202", capacity=8, features="Whiteboard, TV screen, group seating")

    court_1 = Resource(building_id=sdfc.id, resource_type=ResourceType.recreation_court, name="Badminton Court 1", capacity=4, features="Net, shuttlecocks provided")
    court_2 = Resource(building_id=sdfc.id, resource_type=ResourceType.recreation_court, name="Badminton Court 2", capacity=4, features="Net, shuttlecocks provided")
    court_3 = Resource(building_id=sdfc.id, resource_type=ResourceType.recreation_court, name="Badminton Court 3", capacity=4, features="Net, shuttlecocks provided")
    court_4 = Resource(building_id=sdfc.id, resource_type=ResourceType.recreation_court, name="Badminton Court 4", capacity=4, features="Net, shuttlecocks provided")

    db.add_all([room_a101, room_a102, room_b201, room_b202, court_1, court_2, court_3, court_4])
    db.flush()

    # ------------------------------------------------------------------
    # 4. Reservations
    # ------------------------------------------------------------------

    # ── ACTIVE NOW: Alice checked in to Study Room A101 this hour ──
    alice_checkin_time = _dt(TODAY, ACTIVE_H) + datetime.timedelta(minutes=8)
    res_alice_active = Reservation(
        user_id=alice.id,
        resource_id=room_a101.id,
        reservation_date=TODAY,
        start_time=datetime.time(ACTIVE_H, 0),
        end_time=datetime.time(min(ACTIVE_H + 1, 23), 0),
        status=ReservationStatus.active,
        check_in_deadline=_dt(TODAY, ACTIVE_H, 15),
        checked_in_at=alice_checkin_time,
    )

    # ── ACTIVE NOW: Emma reassigned & checked in to Court 2 this hour ──
    emma_checkin_time = _dt(TODAY, ACTIVE_H) + datetime.timedelta(minutes=5)
    res_emma_active = Reservation(
        user_id=emma.id,
        resource_id=court_2.id,
        reservation_date=TODAY,
        start_time=datetime.time(ACTIVE_H, 0),
        end_time=datetime.time(min(ACTIVE_H + 1, 23), 0),
        status=ReservationStatus.reassigned,
        check_in_deadline=_dt(TODAY, ACTIVE_H, 15),
        checked_in_at=emma_checkin_time,
    )

    # ── UPCOMING: Bob reserved Study Room A102 in 2 hours ──
    res_bob_upcoming = Reservation(
        user_id=bob.id,
        resource_id=room_a102.id,
        reservation_date=TODAY,
        start_time=datetime.time(UPCOMING_H1, 0),
        end_time=datetime.time(min(UPCOMING_H1 + 1, 23), 0),
        status=ReservationStatus.reserved,
        check_in_deadline=_dt(TODAY, UPCOMING_H1, 15),
        checked_in_at=None,
    )

    # ── UPCOMING: Manish reserved Study Room B201 in 3 hours ──
    res_manish_upcoming = Reservation(
        user_id=manish.id,
        resource_id=room_b201.id,
        reservation_date=TODAY,
        start_time=datetime.time(UPCOMING_H2, 0),
        end_time=datetime.time(min(UPCOMING_H2 + 1, 23), 0),
        status=ReservationStatus.reserved,
        check_in_deadline=_dt(TODAY, UPCOMING_H2, 15),
        checked_in_at=None,
    )

    # ── UPCOMING: Carol reserved Court 3 tomorrow at 10 AM ──
    res_carol_tomorrow = Reservation(
        user_id=carol.id,
        resource_id=court_3.id,
        reservation_date=TOMORROW,
        start_time=datetime.time(10, 0),
        end_time=datetime.time(11, 0),
        status=ReservationStatus.reserved,
        check_in_deadline=_dt(TOMORROW, 10, 15),
        checked_in_at=None,
    )

    # ── UPCOMING: David reserved Study Room B202 tomorrow at 2 PM ──
    res_david_upcoming = Reservation(
        user_id=david.id,
        resource_id=room_b202.id,
        reservation_date=TOMORROW,
        start_time=datetime.time(14, 0),
        end_time=datetime.time(15, 0),
        status=ReservationStatus.reserved,
        check_in_deadline=_dt(TOMORROW, 14, 15),
        checked_in_at=None,
    )

    # ── UPCOMING: Alice reserved Court 4 day after tomorrow ──
    res_alice_future = Reservation(
        user_id=alice.id,
        resource_id=court_4.id,
        reservation_date=DAY_AFTER,
        start_time=datetime.time(9, 0),
        end_time=datetime.time(10, 0),
        status=ReservationStatus.reserved,
        check_in_deadline=_dt(DAY_AFTER, 9, 15),
        checked_in_at=None,
    )

    # ── NO-SHOW (unprocessed): Faisal missed Study Room A101 3 hours ago ──
    res_faisal_noshow = Reservation(
        user_id=faisal.id,
        resource_id=room_a101.id,
        reservation_date=TODAY,
        start_time=datetime.time(PAST_H1, 0),
        end_time=datetime.time(min(PAST_H1 + 1, 23), 0),
        status=ReservationStatus.no_show,
        check_in_deadline=_dt(TODAY, PAST_H1, 15),
        checked_in_at=None,
    )

    # ── RELEASED: Carol's Court 1 slot from 2 hours ago (no-show processed) ──
    res_carol_released = Reservation(
        user_id=carol.id,
        resource_id=court_1.id,
        reservation_date=TODAY,
        start_time=datetime.time(PAST_H2, 0),
        end_time=datetime.time(min(PAST_H2 + 1, 23), 0),
        status=ReservationStatus.released,
        check_in_deadline=_dt(TODAY, PAST_H2, 15),
        checked_in_at=None,
    )

    # ── COMPLETED: David used Study Room B202 yesterday ──
    res_david_completed = Reservation(
        user_id=david.id,
        resource_id=room_b202.id,
        reservation_date=YESTERDAY,
        start_time=datetime.time(15, 0),
        end_time=datetime.time(16, 0),
        status=ReservationStatus.completed,
        check_in_deadline=_dt(YESTERDAY, 15, 15),
        checked_in_at=_dt(YESTERDAY, 15, 8),
    )

    # ── COMPLETED: Alice used Court 4 yesterday ──
    res_alice_completed = Reservation(
        user_id=alice.id,
        resource_id=court_4.id,
        reservation_date=YESTERDAY,
        start_time=datetime.time(11, 0),
        end_time=datetime.time(12, 0),
        status=ReservationStatus.completed,
        check_in_deadline=_dt(YESTERDAY, 11, 15),
        checked_in_at=_dt(YESTERDAY, 11, 3),
    )

    # ── CANCELLED: David cancelled a Court 3 booking (was for tomorrow) ──
    res_david_cancelled = Reservation(
        user_id=david.id,
        resource_id=court_3.id,
        reservation_date=TOMORROW,
        start_time=datetime.time(13, 0),
        end_time=datetime.time(14, 0),
        status=ReservationStatus.cancelled,
        check_in_deadline=_dt(TOMORROW, 13, 15),
        checked_in_at=None,
    )

    # ── CANCELLED: Carol cancelled Study Room A102 booking ──
    res_carol_cancelled = Reservation(
        user_id=carol.id,
        resource_id=room_a102.id,
        reservation_date=DAY_AFTER,
        start_time=datetime.time(13, 0),
        end_time=datetime.time(14, 0),
        status=ReservationStatus.cancelled,
        check_in_deadline=_dt(DAY_AFTER, 13, 15),
        checked_in_at=None,
    )

    db.add_all([
        res_alice_active, res_emma_active,
        res_bob_upcoming, res_manish_upcoming, res_carol_tomorrow, res_david_upcoming,
        res_alice_future,
        res_faisal_noshow, res_carol_released,
        res_david_completed, res_alice_completed,
        res_david_cancelled, res_carol_cancelled,
    ])
    db.flush()

    # ------------------------------------------------------------------
    # 5. Waitlist entries
    # ------------------------------------------------------------------
    now_az = datetime.datetime.now(AZ)
    offer_sent = now_az - datetime.timedelta(minutes=1)
    offer_expires = offer_sent + datetime.timedelta(minutes=5)

    # Faisal is first on Court 1 (Carol's released slot) — offer currently live
    wl_faisal_court1 = WaitlistEntry(
        user_id=faisal.id,
        resource_id=court_1.id,
        reservation_date=TODAY,
        start_time=datetime.time(PAST_H2, 0),
        end_time=datetime.time(min(PAST_H2 + 1, 23), 0),
        status=WaitlistStatus.offered,
        offer_sent_at=offer_sent,
        offer_expires_at=offer_expires,
    )

    # Alice is second on Court 1 (same released slot, waiting behind Faisal)
    wl_alice_court1 = WaitlistEntry(
        user_id=alice.id,
        resource_id=court_1.id,
        reservation_date=TODAY,
        start_time=datetime.time(PAST_H2, 0),
        end_time=datetime.time(min(PAST_H2 + 1, 23), 0),
        status=WaitlistStatus.waiting,
    )

    # Bob on Study Room A101 tomorrow (someone else holds that slot) — waiting
    wl_bob_room = WaitlistEntry(
        user_id=bob.id,
        resource_id=room_a101.id,
        reservation_date=TOMORROW,
        start_time=datetime.time(9, 0),
        end_time=datetime.time(10, 0),
        status=WaitlistStatus.waiting,
    )

    # Manish on Court 2 tomorrow — waiting
    wl_manish_court2 = WaitlistEntry(
        user_id=manish.id,
        resource_id=court_2.id,
        reservation_date=TOMORROW,
        start_time=datetime.time(11, 0),
        end_time=datetime.time(12, 0),
        status=WaitlistStatus.waiting,
    )

    db.add_all([wl_faisal_court1, wl_alice_court1, wl_bob_room, wl_manish_court2])
    db.flush()

    # ------------------------------------------------------------------
    # 6. Notifications
    # ------------------------------------------------------------------
    db.add_all([
        # Alice: check-in prompt (already read — she checked in)
        Notification(
            user_id=alice.id,
            notification_type="check_in_prompt",
            title="Check-In Window is Open",
            message=f"Your reservation for Study Room A101 starts at {ACTIVE_H}:00. "
                    f"You can check in now until {ACTIVE_H}:15.",
            is_read=True,
        ),
        # Alice: confirmation after successful check-in
        Notification(
            user_id=alice.id,
            notification_type="reservation_confirmed",
            title="Check-In Successful",
            message="You have successfully checked in to Study Room A101. Enjoy your session!",
            is_read=True,
        ),
        # Alice: reminder for her Court 4 booking in two days
        Notification(
            user_id=alice.id,
            notification_type="reminder",
            title="Reservation Reminder",
            message=f"Your reservation for Badminton Court 4 on {DAY_AFTER.strftime('%A, %B %d')} "
                    f"at 9:00 is confirmed.",
            is_read=False,
        ),
        # Bob: reminder for upcoming Study Room A102
        Notification(
            user_id=bob.id,
            notification_type="reminder",
            title="Reservation Reminder",
            message=f"Your Study Room A102 reservation starts at {UPCOMING_H1}:00 today. "
                    f"Check-in opens at {UPCOMING_H1 - 1}:45.",
            is_read=False,
        ),
        # Manish: confirmation for B201 booking
        Notification(
            user_id=manish.id,
            notification_type="reservation_confirmed",
            title="Reservation Confirmed",
            message=f"Study Room B201 at {UPCOMING_H2}:00 today is confirmed. "
                    "Check in within 15 minutes of your start time.",
            is_read=False,
        ),
        # Carol: no-show alert for released Court 1 slot
        Notification(
            user_id=carol.id,
            notification_type="no_show",
            title="Reservation Missed — Slot Released",
            message=f"Your reservation for Badminton Court 1 at {PAST_H2}:00 today "
                    "was released due to missed check-in.",
            is_read=False,
        ),
        # Carol: cancellation confirmation for A102
        Notification(
            user_id=carol.id,
            notification_type="cancellation_confirmed",
            title="Reservation Cancelled",
            message=f"Your reservation for Study Room A102 on {DAY_AFTER.strftime('%A, %B %d')} "
                    "at 13:00 has been cancelled.",
            is_read=False,
        ),
        # David: completion notification
        Notification(
            user_id=david.id,
            notification_type="reservation_confirmed",
            title="Session Complete",
            message="Your Study Room B202 session yesterday completed successfully.",
            is_read=True,
        ),
        # David: cancellation confirmation
        Notification(
            user_id=david.id,
            notification_type="cancellation_confirmed",
            title="Reservation Cancelled",
            message="Your Badminton Court 3 reservation for tomorrow at 13:00 has been cancelled.",
            is_read=False,
        ),
        # Emma: reassignment success
        Notification(
            user_id=emma.id,
            notification_type="reassignment_success",
            title="Reservation Confirmed!",
            message=f"You have successfully claimed Badminton Court 2 at {ACTIVE_H}:00 today. "
                    "Your reservation is now active.",
            is_read=True,
        ),
        # Faisal: waitlist offer for Court 1
        Notification(
            user_id=faisal.id,
            notification_type="waitlist_offer",
            title="You Have a Waitlist Offer!",
            message=f"Badminton Court 1 at {PAST_H2}:00 today is available. "
                    "You have 5 minutes to claim it — open the app and check in.",
            is_read=False,
        ),
        # Faisal: no-show alert for Study Room A101
        Notification(
            user_id=faisal.id,
            notification_type="no_show",
            title="Reservation Missed — Slot Released",
            message=f"Your Study Room A101 reservation at {PAST_H1}:00 today "
                    "was released due to missed check-in.",
            is_read=False,
        ),
    ])
    db.flush()

    # ------------------------------------------------------------------
    # 7. CheckInLogs
    # ------------------------------------------------------------------
    db.add_all([
        CheckInLog(
            reservation_id=res_alice_active.id,
            user_id=alice.id,
            submitted_latitude=33.4151,     # ~26 m inside Library geofence
            submitted_longitude=-111.8943,
            distance_to_building_meters=26.1,
            was_within_geofence=True,
            was_within_time_window=True,
            result="success",
        ),
        CheckInLog(
            reservation_id=res_emma_active.id,
            user_id=emma.id,
            submitted_latitude=33.4190,     # ~24 m inside SDFC geofence
            submitted_longitude=-111.9316,
            distance_to_building_meters=24.3,
            was_within_geofence=True,
            was_within_time_window=True,
            result="success",
        ),
        # Faisal's failed attempt at Study Room A101 (too far from Library)
        CheckInLog(
            reservation_id=res_faisal_noshow.id,
            user_id=faisal.id,
            submitted_latitude=33.4050,     # ~1100 m away — clearly outside radius
            submitted_longitude=-111.8900,
            distance_to_building_meters=1112.4,
            was_within_geofence=False,
            was_within_time_window=True,
            result="outside_geofence",
        ),
        # David's successful check-in yesterday
        CheckInLog(
            reservation_id=res_david_completed.id,
            user_id=david.id,
            submitted_latitude=33.4147,     # ~22 m inside Library geofence
            submitted_longitude=-111.8947,
            distance_to_building_meters=22.1,
            was_within_geofence=True,
            was_within_time_window=True,
            result="success",
        ),
    ])
    db.flush()

    # ------------------------------------------------------------------
    # 8. EmailLogs
    # ------------------------------------------------------------------
    db.add_all([
        EmailLog(
            user_id=bob.id,
            to_address="bob.martinez@asu.edu",
            subject=f"[ASU] Reminder: Study Room A102 at {UPCOMING_H1}:00 today",
            body=(
                f"Hi Bob,\n\n"
                f"Your Study Room A102 reservation starts at {UPCOMING_H1}:00 today. "
                f"Check-in opens at {UPCOMING_H1 - 1}:45.\n\n— ASU Reservation System"
            ),
            status=EmailStatus.sent,
        ),
        EmailLog(
            user_id=carol.id,
            to_address="carol.nguyen@asu.edu",
            subject="[ASU] Your reservation was released due to no check-in",
            body=(
                f"Hi Carol,\n\n"
                f"Your Badminton Court 1 reservation at {PAST_H2}:00 today was released.\n\n"
                "— ASU Reservation System"
            ),
            status=EmailStatus.sent,
        ),
        EmailLog(
            user_id=faisal.id,
            to_address="faisal.alrashid@asu.edu",
            subject=f"[ASU] A spot just opened — Badminton Court 1 at {PAST_H2}:00",
            body=(
                f"Hi Faisal,\n\n"
                f"Badminton Court 1 at {PAST_H2}:00 today is now available. "
                "You have 5 minutes to claim it.\n\n— ASU Reservation System"
            ),
            status=EmailStatus.sent,
        ),
        EmailLog(
            user_id=emma.id,
            to_address="emma.patel@asu.edu",
            subject=f"[ASU] Reservation confirmed — Badminton Court 2 at {ACTIVE_H}:00",
            body=(
                f"Hi Emma,\n\n"
                f"You've claimed Badminton Court 2 at {ACTIVE_H}:00 today. Enjoy!\n\n"
                "— ASU Reservation System"
            ),
            status=EmailStatus.sent,
        ),
        EmailLog(
            user_id=david.id,
            to_address="david.kim@asu.edu",
            subject="[ASU] Reservation cancelled — Badminton Court 3",
            body=(
                "Hi David,\n\nYour Badminton Court 3 reservation for tomorrow at 13:00 "
                "has been cancelled.\n\n— ASU Reservation System"
            ),
            status=EmailStatus.sent,
        ),
    ])

    db.commit()
    print("  [seed] Done. Database populated with demo data.")
