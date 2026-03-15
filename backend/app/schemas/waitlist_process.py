"""
Pydantic schemas for Block 12 waitlist offer/expiration/claim endpoints.
"""

import datetime
from pydantic import BaseModel


# ── Offer processing ──────────────────────────────────────────────────────────

class OfferResult(BaseModel):
    """One offer generated during a process-offers run."""

    waitlist_entry_id: int
    reservation_id: int
    user_id: int
    resource_name: str
    reservation_date: datetime.date
    start_time: datetime.time
    offer_expires_at: datetime.datetime


class ProcessOffersResponse(BaseModel):
    """Response for POST /api/v1/waitlists/process-offers."""

    released_reservations_checked: int
    offers_generated: int
    offers: list[OfferResult]


# ── Expiration processing ─────────────────────────────────────────────────────

class ExpirationResult(BaseModel):
    """One waitlist entry expired during a process-expirations run."""

    waitlist_entry_id: int
    user_id: int
    resource_name: str
    reservation_date: datetime.date
    start_time: datetime.time


class ProcessExpirationsResponse(BaseModel):
    """Response for POST /api/v1/waitlists/process-expirations."""

    entries_expired: int
    new_offers_generated: int
    expired: list[ExpirationResult]
    new_offers: list[OfferResult]


# ── Claim ─────────────────────────────────────────────────────────────────────

class ClaimRequest(BaseModel):
    user_id: int
    waitlist_entry_id: int
    submitted_latitude: float
    submitted_longitude: float


class ClaimResponse(BaseModel):
    """Response for POST /api/v1/waitlists/claim."""

    success: bool
    waitlist_entry_id: int
    reservation_id: int
    user_id: int
    resource_name: str
    reservation_date: datetime.date
    start_time: datetime.time
    distance_meters: float
    geofence_radius_meters: float
    result: str
    message: str
