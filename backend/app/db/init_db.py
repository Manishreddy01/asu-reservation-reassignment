"""
Database initialization.

Creates all tables (if they don't already exist) and optionally seeds
the database with demo data.

Usage (from the backend/ directory):
    python -m app.db.init_db           # create tables + seed
    python -m app.db.init_db --no-seed # create tables only
"""

import sys
from app.db.database import engine, Base

# Import all models so Base.metadata knows about every table
import app.models  # noqa: F401 — side-effect import


def create_tables() -> None:
    print("[init_db] Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("[init_db] Tables created.")


def run_seeds() -> None:
    from app.db.database import SessionLocal
    from app.seeds.seed_data import seed

    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    seed_flag = "--no-seed" not in sys.argv

    create_tables()

    if seed_flag:
        run_seeds()
    else:
        print("[init_db] Skipping seed data (--no-seed).")

    print("[init_db] Initialization complete.")
