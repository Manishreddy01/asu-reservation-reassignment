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
  reservation_confirmed   — slot successfully booked
  reminder                — upcoming reservation reminder
  no_show                 — check-in window expired; slot released
  waitlist_offer          — waitlisted student offered a released slot
  reassignment_success    — waitlist claim succeeded
  offer_expired           — claim window closed without action
  check_in_prompt         — check-in window has just opened
  cancellation_confirmed  — student cancelled a future reservation

Real email delivery:
  If SMTP_HOST, SMTP_USER, and SMTP_PASSWORD are set as environment variables,
  send_event() will attempt to deliver emails via SMTP (TLS on port 587 by default).
  On any SMTP failure the error is logged and the in-app EmailLog row is still
  written — the app never crashes due to an email misconfiguration.

  Environment variables:
    SMTP_HOST      — SMTP server hostname (e.g. smtp.gmail.com)
    SMTP_PORT      — SMTP port, default 587
    SMTP_USER      — SMTP login username
    SMTP_PASSWORD  — SMTP login password
    SMTP_FROM      — From address, default noreply@asu.edu

Duplicate prevention:
  This module does not commit or enforce uniqueness constraints.  Each calling
  service is responsible for its own idempotency (status-machine guards, offer
  de-duplication, etc.).  The one exception is reminder_already_sent(), a helper
  for the reminder endpoint that checks for recent reminder notifications keyed
  on (user_id, check_in_deadline) to avoid re-sending on repeated demo calls.
"""

import datetime as dt
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.email_log import EmailLog, EmailStatus
from app.models.notification import Notification
from app.models.reservation import Reservation
from app.models.resource import Resource
from app.models.user import User

# ── Real SMTP delivery ─────────────────────────────────────────────────────────

def _smtp_send(to_address: str, subject: str, body: str) -> bool:
    """
    Attempt to send a real email via SMTP.
    Reads SMTP config lazily so .env values loaded at startup are picked up.
    Returns True on success, False on any failure (never raises).
    """
    host = os.environ.get("SMTP_HOST", "")
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")

    if not (host and user and password):
        return False

    port = int(os.environ.get("SMTP_PORT", "587"))
    from_addr = os.environ.get("SMTP_FROM", "noreply@asu.edu")

    try:
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(user, password)
            server.send_message(msg)

        print(f"[email] Sent '{subject}' to {to_address} via {host}:{port}")
        return True
    except Exception as exc:
        print(f"[email] SMTP delivery failed to {to_address}: {exc}")
        return False


# ── Slot formatting ────────────────────────────────────────────────────────────

def _fmt(reservation: Reservation) -> tuple[str, str]:
    """Return (slot_date, slot_time) as human-readable strings."""
    slot_date = reservation.reservation_date.strftime("%A, %B %d")
    slot_time = reservation.start_time.strftime("%H:%M")
    return slot_date, slot_time


def _checkin_link() -> str:
    """Public check-in URL for the frontend. Configurable via FRONTEND_URL."""
    base = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return f"{base}/app/check-in"


def _checkin_open_time(reservation: Reservation) -> str:
    """The 'check-in opens at' display time (start - 15 min, HH:MM)."""
    start = dt.datetime.combine(reservation.reservation_date, reservation.start_time)
    return (start - dt.timedelta(minutes=15)).strftime("%H:%M")


# ── Message templates ──────────────────────────────────────────────────────────

def _reservation_confirmed(
    user: User, resource: Resource, reservation: Reservation, **kwargs
) -> dict[str, str]:
    slot_date, slot_time = _fmt(reservation)
    open_time = _checkin_open_time(reservation)
    link = _checkin_link()
    return {
        "title": "Reservation Confirmed",
        "message": (
            f"Your reservation for {resource.name} on {slot_date} at {slot_time} "
            f"is confirmed. Check-in opens at {open_time} (15 min before start)."
        ),
        "subject": f"Reservation Confirmed: {resource.name} on {slot_date}",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"Your reservation has been confirmed:\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Time     : {slot_time}\n\n"
            f"You must check in starting at {open_time} — that's 15 minutes "
            f"before your reservation. The window stays open for 30 minutes "
            f"(until 15 minutes after start). Missing it releases your slot.\n\n"
            f"Check in here: {link}\n\n"
            f"— ASU Reservation System"
        ),
    }


def _cancellation_confirmed(
    user: User, resource: Resource, reservation: Reservation, **kwargs
) -> dict[str, str]:
    slot_date, slot_time = _fmt(reservation)
    return {
        "title": "Reservation Cancelled",
        "message": (
            f"Your reservation for {resource.name} on {slot_date} at {slot_time} "
            f"has been cancelled. The slot has been released."
        ),
        "subject": f"Reservation Cancelled: {resource.name} on {slot_date}",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"Your reservation has been successfully cancelled:\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Time     : {slot_time}\n\n"
            f"The slot has been released and may be offered to students on the waitlist.\n\n"
            f"You can make a new reservation at any time through the ASU Reservation app.\n\n"
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


def _check_in_window_open(
    user: User, resource: Resource, reservation: Reservation, **kwargs
) -> dict[str, str]:
    """First reminder — 15 minutes before start, when the window opens."""
    slot_date, slot_time = _fmt(reservation)
    link = _checkin_link()
    return {
        "title": f"Check-In Open: {resource.name}",
        "message": (
            f"Check-in is now open for {resource.name} at {slot_time}. "
            f"Head to the building and check in to secure your slot."
        ),
        "subject": f"Check-In Is Open: {resource.name} at {slot_time}",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"Your check-in window just opened. You have 30 minutes total — "
            f"15 minutes before your start time and 15 minutes after.\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Start    : {slot_time}\n\n"
            f"Check in here: {link}\n\n"
            f"— ASU Reservation System"
        ),
    }


def _reservation_starting(
    user: User, resource: Resource, reservation: Reservation, **kwargs
) -> dict[str, str]:
    """Second reminder — at start time."""
    slot_date, slot_time = _fmt(reservation)
    link = _checkin_link()
    return {
        "title": f"{resource.name} starting now",
        "message": (
            f"Your reservation for {resource.name} starts now. "
            f"Check in from the building if you haven't already."
        ),
        "subject": f"Starting Now: {resource.name} at {slot_time}",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"Your reservation is starting right now:\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Start    : {slot_time}\n\n"
            f"You still have 15 minutes to check in. After that the slot "
            f"will be released.\n\n"
            f"Check in here: {link}\n\n"
            f"— ASU Reservation System"
        ),
    }


def _waitlist_joined(
    user: User, resource: Resource, entry, **kwargs
) -> dict[str, str]:
    """Confirmation that the student is now on the waitlist for a slot."""
    slot_date = entry.reservation_date.strftime("%A, %B %d")
    slot_time = entry.start_time.strftime("%H:%M")
    return {
        "title": f"You're on the waitlist for {resource.name}",
        "message": (
            f"You're on the waitlist for {resource.name} on {slot_date} at {slot_time}. "
            f"You'll get an email if a spot opens up — you'll have 5 minutes to claim it."
        ),
        "subject": f"Waitlisted: {resource.name} on {slot_date} at {slot_time}",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"You've been added to the waitlist:\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Time     : {slot_time}\n\n"
            f"If a slot opens up before this reservation starts, we'll email "
            f"you a claim offer. The offer is valid for 5 minutes — after that "
            f"it moves to the next student in line, so check your email and "
            f"check in promptly.\n\n"
            f"You can leave the waitlist any time from your dashboard.\n\n"
            f"— ASU Reservation System"
        ),
    }


def _check_in_deadline_approaching(
    user: User, resource: Resource, reservation: Reservation, **kwargs
) -> dict[str, str]:
    """Third reminder — 5 minutes before the check-in deadline."""
    slot_date, slot_time = _fmt(reservation)
    link = _checkin_link()
    return {
        "title": "Only 5 minutes left to check in",
        "message": (
            f"You have 5 minutes left to check in for {resource.name}. "
            f"After that your slot will be released."
        ),
        "subject": f"5 Minutes Left: Check in for {resource.name}",
        "body": (
            f"Hi {user.full_name},\n\n"
            f"This is your final reminder — only 5 minutes are left before "
            f"the check-in window closes.\n\n"
            f"  Resource : {resource.name}\n"
            f"  Date     : {slot_date}\n"
            f"  Start    : {slot_time}\n\n"
            f"If you don't check in before the deadline, your reservation "
            f"will be marked as a no-show and the slot may be reassigned to "
            f"a student on the waitlist.\n\n"
            f"Check in here: {link}\n\n"
            f"— ASU Reservation System"
        ),
    }


# ── Template registry ──────────────────────────────────────────────────────────

_TEMPLATES: dict = {
    "reservation_confirmed":        _reservation_confirmed,
    "cancellation_confirmed":       _cancellation_confirmed,
    "reminder":                     _reminder,
    "no_show":                      _no_show,
    "waitlist_offer":               _waitlist_offer,
    "waitlist_joined":              _waitlist_joined,
    "reassignment_success":         _reassignment_success,
    "offer_expired":                _offer_expired,
    "check_in_prompt":              _check_in_prompt,
    "check_in_window_open":         _check_in_window_open,
    "reservation_starting":         _reservation_starting,
    "check_in_deadline_approaching": _check_in_deadline_approaching,
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
    delivered: bool = False,
) -> EmailLog:
    """Add an EmailLog row to the session. Does NOT commit."""
    e = EmailLog(
        user_id=user_id,
        to_address=to_address,
        subject=subject,
        body=body,
        status=EmailStatus.sent if delivered else EmailStatus.pending,
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
    Attempts real SMTP delivery if configured; falls back to DB-only logging.

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

    # Prefer the address the student gave at booking time; fall back to the
    # account email for legacy reservations or non-reservation events.
    to_address = getattr(reservation, "notification_email", None) or user.email

    delivered = _smtp_send(to_address, content["subject"], content["body"])

    e = create_email_log(
        db,
        user_id=user.id,
        to_address=to_address,
        subject=content["subject"],
        body=content["body"],
        delivered=delivered,
    )
    return n, e


def send_waitlist_event(
    db: Session,
    event_type: str,
    user: User,
    resource: Resource,
    entry,  # WaitlistEntry — typed as Any to avoid a circular import
    **kwargs,
) -> tuple[Notification, EmailLog]:
    """
    Same shape as send_event() but anchored on a WaitlistEntry instead of a
    Reservation. Used for waitlist-only events like 'waitlist_joined' where
    no reservation row exists yet.
    """
    template_fn = _TEMPLATES.get(event_type)
    if template_fn is None:
        raise ValueError(
            f"Unknown messaging event type: {event_type!r}. "
            f"Valid types: {sorted(_TEMPLATES)}"
        )

    content = template_fn(user, resource, entry, **kwargs)

    n = create_notification(
        db,
        user_id=user.id,
        notification_type=event_type,
        title=content["title"],
        message=content["message"],
    )

    to_address = getattr(entry, "notification_email", None) or user.email
    delivered = _smtp_send(to_address, content["subject"], content["body"])

    e = create_email_log(
        db,
        user_id=user.id,
        to_address=to_address,
        subject=content["subject"],
        body=content["body"],
        delivered=delivered,
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
