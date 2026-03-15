"""
Central API router.
Import all sub-routers here and include them in a single object
that main.py mounts under /api/v1.
"""

from fastapi import APIRouter

from app.api import auth, buildings, check_in, dashboard, no_shows, notifications, reservations, resources, waitlists

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(buildings.router)
api_router.include_router(resources.router)
api_router.include_router(reservations.router)
api_router.include_router(waitlists.router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
api_router.include_router(check_in.router)
api_router.include_router(no_shows.router)
