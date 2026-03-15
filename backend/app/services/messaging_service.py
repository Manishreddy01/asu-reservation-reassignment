"""
Centralized messaging service (Block 13).

Provides reusable helpers for creating in-app Notification and EmailLog rows,
and a template registry covering all notification event types used in the system.

Design:
  - All template functions are pure — they take (user, resource, reservation, **kwargs)
    and return a dict with keys: title, message, subject, body.
  - send_event() is the single entry point callers should use.  It resolves the
    template, creates both rows, and adds them to the session without committing.
    The caller owns the transaction.
  - create_notification() and create_email_log() are available for cases where
    only one artifact is needed.

Supported event types:
  reservation_confirmed  — slot successfully booked
  reminder               — upcoming reservation reminder
  no_show                — check-in window expired; slot released
  waitlist_offer         — waitlisted student offered a released slot
  reassignment_success   — waitlist claim succeeded
  offer_expired          — claim window closed without action
  check_in_prompt        — check-in window has just opened

Duplicate prevention:
  This module does not commit or enforce uniqueness constraints.  Each calling
  service is responsible for its own idempotency (status-machine guards, offer
  de-duplication, etc.).  The one exception is reminder_already_sent(), a helper
  for the reminder endpoint that checks for recent reminder notifications keyed
  on (user_id, check_in_deadline) to avoid re-sending on repeated demo calls.
"""

import datetime as dt
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.email_log import EmailLog, EmailStatus
from app.models.notification import Notification
from app.models.reservation import Reservation
from app.models.resource import Resource
from app.models.user import User


# ── Slot formatting ────────────────────────────────────────────────────────────

def _fmt(reservation: Reservation) -> tuple[str, str]:
    """Return (slot_date, slot_time) as human-readable strings."""
    slot_date = reservation.reservation_date.strftime("%A, %B %d")
    slot_time = reservation.start_time.strftime("%H:%M")
    return slot_date, slot_time


# ── Message templates ──────────────────────────────────────────────────────────

def _reservation_confirmed(
    user: User, resource: Resource, reservation: Reservation, **kwargs
) -> dict[str, str]:
    slot_date, slot_time = _fmt(reservation)
    return {
        "title": "Reservation Confirmed",
        "message": (
            f"Your reservation for {resource.name} on {slot_date} at {slot_time} "
            f"is confirmed. Check in within 15 minutes of your start time."
        ),
        "subject": f"Reservation Confirmed: {resource.name} on {slot_date}",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"Your reservation has been confirmed:\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Time     : {slot_time}\n\n"
            f"Check-in opens 15 minutes before your start time. "
            f"Be sure to check in from inside the building to keep your slot.\n\n"
            f"— ASU Reservation System"
        ),
    }


def _reminder(
    user: User, resource: Resource, reservation: Reservation,
    minutes_before: int = 15, **kwargs
) -> dict[str, str]:
    slot_date, slot_time = _fmt(reservation)
    return {
        "title": f"Reminder: {resource.name} starting at {slot_time}",
        "message": (
            f"Your reservation for {resource.name} starts at {slot_time} on {slot_date}. "
            f"Check-in is now open — head to the building and check in."
        ),
        "subject": f"Reminder: Your {resource.name} Reservation Starts Soon",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"This is a reminder for your upcoming reservation:\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Time     : {slot_time}\n\n"
            f"Check-in is now open. Please check in from inside the building "
            f"within 15 minutes of your start time to avoid being marked as a no-show.\n\n"
            f"— ASU Reservation System"
        ),
    }


def _no_show(
    user: User, resource: Resource, reservation: Reservation, **kwargs
) -> dict[str, str]:
    slot_date, slot_time = _fmt(reservation)
    return {
        "title": "Reservation Missed — Slot Released",
        "message": (
            f"Your reservation for {resource.name} on {slot_date} at {slot_time} "
            f"was not checked in before the deadline. "
            f"The slot has been released and may be offered to another student."
        ),
        "subject": f"Missed Check-In: Your {resource.name} Reservation Has Been Released",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"We noticed you did not check in for your reservation:\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Time     : {slot_time}\n\n"
            f"Because the check-in window has passed, your reservation has been "
            f"released and may be reassigned to another student on the waitlist.\n\n"
            f"If you believe this is an error, please contact ASU support.\n\n"
            f"— ASU Reservation System"
        ),
    }


def _waitlist_offer(
    user: User, resource: Resource, reservation: Reservation,
    offer_window_minutes: int = 5, **kwargs
) -> dict[str, str]:
    slot_date, slot_time = _fmt(reservation)
    return {
        "title": "You Have a Waitlist Offer!",
        "message": (
            f"A slot has opened for {resource.name} on {slot_date} at {slot_time}. "
            f"You have {offer_window_minutes} minutes to claim it. "
            f"Open the app and check in to confirm your spot."
        ),
        "subject": f"Waitlist Offer: {resource.name} on {slot_date} at {slot_time}",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"Good news — a reservation slot has become available:\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Time     : {slot_time}\n\n"
            f"You have {offer_window_minutes} minutes to claim this slot. "
            f"Open the ASU Reservation app and check in from the building to confirm.\n\n"
            f"If you do not claim it within the window, the offer will move to the next "
            f"student on the waitlist.\n\n"
            f"— ASU Reservation System"
        ),
    }


def _reassignment_success(
    user: User, resource: Resource, reservation: Reservation, **kwargs
) -> dict[str, str]:
    slot_date, slot_time = _fmt(reservation)
    return {
        "title": "Reservation Confirmed!",
        "message": (
            f"You have successfully claimed the waitlist slot for "
            f"{resource.name} on {slot_date} at {slot_time}. "
            f"Your reservation is now active. Enjoy!"
        ),
        "subject": f"Reservation Confirmed: {resource.name} on {slot_date}",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"Your waitlist claim was successful! Here are your reservation details:\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Time     : {slot_time}\n\n"
            f"You are checked in. Have a great session!\n\n"
            f"— ASU Reservation System"
        ),
    }


def _offer_expired(
    user: User, resource: Resource, reservation: Reservation, **kwargs
) -> dict[str, str]:
    slot_date, slot_time = _fmt(reservation)
    return {
        "title": "Waitlist Offer Expired",
        "message": (
            f"Your offer for {resource.name} on {slot_date} at {slot_time} "
            f"has expired. The slot has been passed to the next student on the waitlist."
        ),
        "subject": f"Offer Expired: {resource.name} on {slot_date}",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"Unfortunately, your waitlist offer has expired:\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Time     : {slot_time}\n\n"
            f"The slot has been passed to the next student on the waitlist. "
            f"You may join the waitlist again if the slot becomes available.\n\n"
            f"— ASU Reservation System"
        ),
    }


def _check_in_prompt(
    user: User, resource: Resource, reservation: Reservation, **kwargs
) -> dict[str, str]:
    slot_date, slot_time = _fmt(reservation)
    return {
        "title": "Check-In Window Is Open",
        "message": (
            f"Your check-in window for {resource.name} on {slot_date} at {slot_time} "
            f"is now open. Check in from the building within 15 minutes to keep your spot."
        ),
        "subject": f"Check In Now: {resource.name} at {slot_time}",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"Your check-in window is now open:\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Time     : {slot_time}\n\n"
            f"You have 15 minutes from your reservation start time to check in "
            f"from inside the building. Missing this window will release your slot.\n\n"
            f"— ASU Reservation System"
        ),
    }


# ── Template registry ──────────────────────────────────────────────────────────

_TEMPLATES: dict = {
    "reservation_confirmed": _reservation_confirmed,
    "reminder":              _reminder,
    "no_show":               _no_show,
    "waitlist_offer":        _waitlist_offer,
    "reassignment_success":  _reassignment_success,
    "offer_expired":         _offer_expired,
    "check_in_prompt":       _check_in_prompt,
}


# ── Core creation helpers ──────────────────────────────────────────────────────

def create_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
) -> Notification:
    """Add a Notification row to the session. Does NOT commit."""
    n = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        is_read=False,
    )
    db.add(n)
    return n


def create_email_log(
    db: Session,
    user_id: int,
    to_address: str,
    subject: str,
    body: str,
) -> EmailLog:
    """Add an EmailLog row to the session. Does NOT commit."""
    e = EmailLog(
        user_id=user_id,
        to_address=to_address,
        subject=subject,
        body=body,
        status=EmailStatus.sent,
    )
    db.add(e)
    return e


# ── Paired creation entry point ────────────────────────────────────────────────

def send_event(
    db: Session,
    event_type: str,
    user: User,
    resource: Resource,
    reservation: Reservation,
    **kwargs,
) -> tuple[Notification, EmailLog]:
    """
    Create a paired Notification + EmailLog for the given event type.

    event_type must be a key in _TEMPLATES.
    Extra kwargs are forwarded to the template (e.g., offer_window_minutes=5).
    Does NOT commit — the caller owns the transaction.

    Raises ValueError for unknown event_type.
    """
    template_fn = _TEMPLATES.get(event_type)
    if template_fn is None:
        raise ValueError(
            f"Unknown messaging event type: {event_type!r}. "
            f"Valid types: {sorted(_TEMPLATES)}"
        )

    content = template_fn(user, resource, reservation, **kwargs)

    n = create_notification(
        db,
        user_id=user.id,
        notification_type=event_type,
        title=content["title"],
        message=content["message"],
    )
    e = create_email_log(
        db,
        user_id=user.id,
        to_address=user.email,
        subject=content["subject"],
        body=content["body"],
    )
    return n, e


# ── Duplicate guard for reminders ──────────────────────────────────────────────

def reminder_already_sent(
    db: Session,
    user_id: int,
    check_in_deadline: dt.datetime,
) -> bool:
    """
    Return True if a 'reminder' notification was already created for this user
    within a 3-hour window anchored on check_in_deadline.

    Prevents duplicate reminders when the send-reminders endpoint is called
    repeatedly in a demo session.  The window is per-slot because
    check_in_deadline is unique per user (overlapping reservations are blocked
    at booking time).
    """
    window_start = check_in_deadline - dt.timedelta(hours=3)
    return (
        db.query(Notification)
        .filter(
            and_(
                Notification.user_id == user_id,
                Notification.notification_type == "reminder",
                Notification.created_at >= window_start,
            )
        )
        .first()
        is not None
    )
