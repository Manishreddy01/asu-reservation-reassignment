"""
Seed data for the ASU Reservation Reassignment prototype.

Scenarios inserted:
  1. Users       — 6 students + 1 admin
  2. Buildings   — ASU Hayden Library, SDFC Recreation Center
  3. Resources   — 4 study rooms (Library) + 4 badminton courts (SDFC)
  4. Reservations (various statuses):
       - active        : Alice has checked in to study room A101 right now
       - reserved      : Bob has a future booking (no check-in yet)
       - no_show       : Carol's morning slot expired without check-in
       - released      : Carol's slot has been freed for reassignment
       - reassigned    : A released court was claimed by a waitlisted student
       - completed     : Yesterday's booking that ended normally
       - cancelled     : A booking David cancelled
  5. Waitlist    — two students waiting on the same room, one offered/one waiting
  6. Notifications — reminders, check-in prompts, no-show alerts, waitlist offers
  7. CheckInLogs — one success, one outside-geofence failure
  8. EmailLogs   — reminder emails, waitlist offer email
"""

import datetime
from zoneinfo import ZoneInfo

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.building import Building
from app.models.resource import Resource, ResourceType
from app.models.reservation import Reservation, ReservationStatus
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.models.notification import Notification
from app.models.check_in_log import CheckInLog
from app.models.email_log import EmailLog, EmailStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
AZ = ZoneInfo("America/Phoenix")   # ASU is in Arizona (no DST)


def _dt(date: datetime.date, hour: int, minute: int = 0) -> datetime.datetime:
    """Build a timezone-aware datetime in Arizona time."""
    return datetime.datetime(date.year, date.month, date.day, hour, minute, tzinfo=AZ)


def _hash(password: str) -> str:
    return pwd_context.hash(password)


# ---------------------------------------------------------------------------
# Reference dates (relative to today so demos always look current)
# ---------------------------------------------------------------------------
TODAY = datetime.date.today()
YESTERDAY = TODAY - datetime.timedelta(days=1)
TOMORROW = TODAY + datetime.timedelta(days=1)


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
    admin  = User(full_name="Demo Admin",       email="admin@asu.edu",           hashed_password=_hash("admin2024"),   role=UserRole.admin)

    db.add_all([alice, bob, carol, david, emma, faisal, admin])
    db.flush()   # assigns IDs before relationships

    # ------------------------------------------------------------------
    # 2. Buildings (placeholder coords — swap for real ASU GPS later)
    # ------------------------------------------------------------------
    library = Building(
        name="Hayden Library",
        latitude=33.4183,
        longitude=-111.9346,
        geofence_radius_meters=100.0,
    )
    sdfc = Building(
        name="SDFC Recreation Center",
        latitude=33.4255,
        longitude=-111.9323,
        geofence_radius_meters=100.0,
    )
    db.add_all([library, sdfc])
    db.flush()

    # ------------------------------------------------------------------
    # 3. Resources
    # ------------------------------------------------------------------
    # Library study rooms
    room_a101 = Resource(building_id=library.id, resource_type=ResourceType.study_room, name="Study Room A101", capacity=4, features="Whiteboard, TV screen, HDMI")
    room_a102 = Resource(building_id=library.id, resource_type=ResourceType.study_room, name="Study Room A102", capacity=6, features="Whiteboard, projector, conference table")
    room_b201 = Resource(building_id=library.id, resource_type=ResourceType.study_room, name="Study Room B201", capacity=2, features="Standing desk, quiet zone")
    room_b202 = Resource(building_id=library.id, resource_type=ResourceType.study_room, name="Study Room B202", capacity=8, features="Whiteboard, TV screen, group seating")

    # SDFC badminton courts
    court_1 = Resource(building_id=sdfc.id, resource_type=ResourceType.recreation_court, name="Badminton Court 1", capacity=4, features="Net, shuttlecocks provided")
    court_2 = Resource(building_id=sdfc.id, resource_type=ResourceType.recreation_court, name="Badminton Court 2", capacity=4, features="Net, shuttlecocks provided")
    court_3 = Resource(building_id=sdfc.id, resource_type=ResourceType.recreation_court, name="Badminton Court 3", capacity=4, features="Net, shuttlecocks provided")
    court_4 = Resource(building_id=sdfc.id, resource_type=ResourceType.recreation_court, name="Badminton Court 4", capacity=4, features="Net, shuttlecocks provided")

    db.add_all([room_a101, room_a102, room_b201, room_b202, court_1, court_2, court_3, court_4])
    db.flush()

    # ------------------------------------------------------------------
    # 4. Reservations
    # ------------------------------------------------------------------

    # ── Scenario A: Alice has an ACTIVE reservation today (checked in) ──
    alice_checkin_time = _dt(TODAY, 9, 7)   # checked in at 9:07 AM
    res_alice_active = Reservation(
        user_id=alice.id,
        resource_id=room_a101.id,
        reservation_date=TODAY,
        start_time=datetime.time(9, 0),
        end_time=datetime.time(10, 0),
        status=ReservationStatus.active,
        check_in_deadline=_dt(TODAY, 9, 15),
        checked_in_at=alice_checkin_time,
    )

    # ── Scenario B: Bob has a RESERVED slot later today (no check-in yet) ──
    res_bob_reserved = Reservation(
        user_id=bob.id,
        resource_id=room_a102.id,
        reservation_date=TODAY,
        start_time=datetime.time(14, 0),
        end_time=datetime.time(15, 0),
        status=ReservationStatus.reserved,
        check_in_deadline=_dt(TODAY, 14, 15),
        checked_in_at=None,
    )

    # ── Scenario C: Carol is a NO-SHOW this morning ──
    res_carol_noshw = Reservation(
        user_id=carol.id,
        resource_id=room_b201.id,
        reservation_date=TODAY,
        start_time=datetime.time(8, 0),
        end_time=datetime.time(9, 0),
        status=ReservationStatus.no_show,
        check_in_deadline=_dt(TODAY, 8, 15),
        checked_in_at=None,
    )

    # ── Scenario D: Released court — Carol's slot freed and now on waitlist ──
    res_carol_released = Reservation(
        user_id=carol.id,
        resource_id=court_1.id,
        reservation_date=TODAY,
        start_time=datetime.time(10, 0),
        end_time=datetime.time(11, 0),
        status=ReservationStatus.released,
        check_in_deadline=_dt(TODAY, 10, 15),
        checked_in_at=None,
    )

    # ── Scenario E: Reassigned court — Emma claimed a released slot ──
    res_emma_reassigned = Reservation(
        user_id=emma.id,
        resource_id=court_2.id,
        reservation_date=TODAY,
        start_time=datetime.time(11, 0),
        end_time=datetime.time(12, 0),
        status=ReservationStatus.reassigned,
        check_in_deadline=_dt(TODAY, 11, 15),
        checked_in_at=_dt(TODAY, 11, 4),
    )

    # ── Scenario F: Yesterday's COMPLETED booking (David) ──
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

    # ── Scenario G: David CANCELLED a tomorrow booking ──
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

    # ── Scenario H: Bob also has a future RESERVED court (to show multi-resource) ──
    res_bob_court = Reservation(
        user_id=bob.id,
        resource_id=court_4.id,
        reservation_date=TOMORROW,
        start_time=datetime.time(9, 0),
        end_time=datetime.time(10, 0),
        status=ReservationStatus.reserved,
        check_in_deadline=_dt(TOMORROW, 9, 15),
        checked_in_at=None,
    )

    db.add_all([
        res_alice_active, res_bob_reserved, res_carol_noshw,
        res_carol_released, res_emma_reassigned,
        res_david_completed, res_david_cancelled, res_bob_court,
    ])
    db.flush()

    # ------------------------------------------------------------------
    # 5. Waitlist entries
    #    Two students waiting on Court 1 (Carol's released slot, today 10–11 AM)
    # ------------------------------------------------------------------
    now_az = datetime.datetime.now(AZ)
    offer_sent = now_az - datetime.timedelta(minutes=1)
    offer_expires = offer_sent + datetime.timedelta(minutes=5)

    # Faisal was first — currently in "offered" state (offer sent 1 min ago)
    wl_faisal = WaitlistEntry(
        user_id=faisal.id,
        resource_id=court_1.id,
        reservation_date=TODAY,
        start_time=datetime.time(10, 0),
        end_time=datetime.time(11, 0),
        status=WaitlistStatus.offered,
        offer_sent_at=offer_sent,
        offer_expires_at=offer_expires,
    )

    # Emma was second — still waiting (behind Faisal)
    # (Note: Emma also has a separate reassigned reservation — she's active on Court 2)
    wl_alice_court1 = WaitlistEntry(
        user_id=alice.id,
        resource_id=court_1.id,
        reservation_date=TODAY,
        start_time=datetime.time(10, 0),
        end_time=datetime.time(11, 0),
        status=WaitlistStatus.waiting,
    )

    # Bob is on waitlist for Study Room A101 tomorrow (Alice's regular slot)
    wl_bob_room = WaitlistEntry(
        user_id=bob.id,
        resource_id=room_a101.id,
        reservation_date=TOMORROW,
        start_time=datetime.time(9, 0),
        end_time=datetime.time(10, 0),
        status=WaitlistStatus.waiting,
    )

    db.add_all([wl_faisal, wl_alice_court1, wl_bob_room])
    db.flush()

    # ------------------------------------------------------------------
    # 6. Notifications
    # ------------------------------------------------------------------
    db.add_all([
        # Reminder sent to Bob before his 2 PM booking
        Notification(
            user_id=bob.id,
            notification_type="reminder",
            title="Reservation Reminder",
            message="Your reservation for Study Room A102 starts at 2:00 PM today. "
                    "Check-in opens at 1:45 PM.",
            is_read=False,
        ),
        # Check-in prompt sent to Alice when window opened
        Notification(
            user_id=alice.id,
            notification_type="check_in_prompt",
            title="Check-In Window is Open",
            message="Your reservation for Study Room A101 starts at 9:00 AM. "
                    "You can check in now until 9:15 AM.",
            is_read=True,
        ),
        # Reservation confirmed for Alice after successful check-in
        Notification(
            user_id=alice.id,
            notification_type="reservation_confirmed",
            title="Check-In Successful",
            message="You have successfully checked in to Study Room A101. "
                    "Enjoy your session!",
            is_read=True,
        ),
        # No-show alert for Carol
        Notification(
            user_id=carol.id,
            notification_type="no_show",
            title="Reservation Marked as No-Show",
            message="Your reservation for Study Room B201 at 8:00 AM was marked "
                    "as a no-show because check-in was not completed in time.",
            is_read=False,
        ),
        # Waitlist offer sent to Faisal for Court 1
        Notification(
            user_id=faisal.id,
            notification_type="waitlist_offer",
            title="A Spot Just Opened!",
            message="Badminton Court 1 (10:00 AM today) is now available. "
                    "You have 5 minutes to claim this reservation. Open the app to check in.",
            is_read=False,
        ),
        # Emma was notified her reassignment to Court 2 succeeded
        Notification(
            user_id=emma.id,
            notification_type="reassignment_success",
            title="Reservation Reassigned to You",
            message="You have been reassigned Badminton Court 2 for 11:00 AM today. "
                    "Your check-in has been recorded.",
            is_read=True,
        ),
    ])
    db.flush()

    # ------------------------------------------------------------------
    # 7. CheckInLogs
    # ------------------------------------------------------------------
    db.add_all([
        # Alice's successful check-in at Library
        CheckInLog(
            reservation_id=res_alice_active.id,
            user_id=alice.id,
            submitted_latitude=33.4181,     # slightly inside the Library geofence
            submitted_longitude=-111.9344,
            distance_to_building_meters=28.4,
            was_within_geofence=True,
            was_within_time_window=True,
            result="success",
        ),
        # Carol's failed attempt — she was too far from the Library
        CheckInLog(
            reservation_id=res_carol_noshw.id,
            user_id=carol.id,
            submitted_latitude=33.4140,     # ~470 m away — outside radius
            submitted_longitude=-111.9380,
            distance_to_building_meters=472.1,
            was_within_geofence=False,
            was_within_time_window=True,
            result="outside_geofence",
        ),
        # Emma's successful check-in at SDFC for the reassigned court
        CheckInLog(
            reservation_id=res_emma_reassigned.id,
            user_id=emma.id,
            submitted_latitude=33.4257,     # just inside SDFC geofence
            submitted_longitude=-111.9321,
            distance_to_building_meters=31.7,
            was_within_geofence=True,
            was_within_time_window=True,
            result="success",
        ),
    ])
    db.flush()

    # ------------------------------------------------------------------
    # 8. EmailLogs (mock inbox)
    # ------------------------------------------------------------------
    db.add_all([
        # Reminder to Bob before 2 PM booking
        EmailLog(
            user_id=bob.id,
            to_address="bob.martinez@asu.edu",
            subject="[ASU] Reminder: Your Study Room A102 reservation is at 2:00 PM",
            body=(
                "Hi Bob,\n\n"
                "This is a reminder that your reservation for Study Room A102 in Hayden Library "
                "begins at 2:00 PM today.\n\n"
                "The check-in window opens at 1:45 PM and closes at 2:15 PM. "
                "Please open the ASU Reservation app and press Check-In while you are inside the building.\n\n"
                "If you do not check in by 2:15 PM, your reservation will be released to the waitlist.\n\n"
                "– ASU Reservation System"
            ),
            status=EmailStatus.sent,
        ),
        # No-show notification to Carol
        EmailLog(
            user_id=carol.id,
            to_address="carol.nguyen@asu.edu",
            subject="[ASU] Your reservation was released due to no check-in",
            body=(
                "Hi Carol,\n\n"
                "Your reservation for Study Room B201 at 8:00 AM today was released because "
                "check-in was not completed within the allowed window.\n\n"
                "The room has been offered to students on the waitlist.\n\n"
                "You can make a new reservation at any time through the ASU Reservation app.\n\n"
                "– ASU Reservation System"
            ),
            status=EmailStatus.sent,
        ),
        # Waitlist offer to Faisal
        EmailLog(
            user_id=faisal.id,
            to_address="faisal.alrashid@asu.edu",
            subject="[ASU] A spot just opened — Badminton Court 1 at 10:00 AM",
            body=(
                "Hi Faisal,\n\n"
                "Good news! A reservation for Badminton Court 1 at 10:00 AM today has just become "
                "available.\n\n"
                "You are next on the waitlist. You have 5 minutes to claim this spot. "
                "Open the ASU Reservation app and check in while you are inside the SDFC building.\n\n"
                "If you do not respond within 5 minutes, the offer will move to the next student "
                "on the waitlist.\n\n"
                "– ASU Reservation System"
            ),
            status=EmailStatus.sent,
        ),
        # Reassignment success email to Emma
        EmailLog(
            user_id=emma.id,
            to_address="emma.patel@asu.edu",
            subject="[ASU] Reservation confirmed — Badminton Court 2 at 11:00 AM",
            body=(
                "Hi Emma,\n\n"
                "You have been successfully reassigned Badminton Court 2 for 11:00 AM today. "
                "Your check-in has been recorded.\n\n"
                "Enjoy your game!\n\n"
                "– ASU Reservation System"
            ),
            status=EmailStatus.sent,
        ),
    ])

    db.commit()
    print("  [seed] Done. Database populated with demo data.")
