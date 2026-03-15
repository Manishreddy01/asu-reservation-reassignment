"""
ASU Reservation Reassignment System — FastAPI application entry point.

All API routes live under /api/v1.
Interactive docs: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.db.init_db import create_tables

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ASU Reservation Reassignment API",
    description=(
        "Prototype API for managing ASU study room and recreation court reservations. "
        "Supports location-verified check-in, automatic no-show detection, "
        "and waitlist reassignment."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server (and any localhost origin) during development
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite default
        "http://localhost:3000",   # fallback
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Startup — ensure tables exist (idempotent; won't re-seed)
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup() -> None:
    create_tables()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
