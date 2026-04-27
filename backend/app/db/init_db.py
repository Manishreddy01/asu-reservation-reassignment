"""
Database initialization.

Creates all tables (if they don't already exist) and optionally seeds
the database with demo data.

Usage (from the backend/ directory):
    python -m app.db.init_db           # create tables + seed
    python -m app.db.init_db --no-seed # create tables only
"""

import sys
from sqlalchemy import inspect, text
from app.db.database import engine, Base

# Import all models so Base.metadata knows about every table
import app.models  # noqa: F401 — side-effect import


def create_tables() -> None:
    print("[init_db] Creating tables...")
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()
    print("[init_db] Tables created.")


def _apply_lightweight_migrations() -> None:
    """
    Idempotent column additions for the prototype's SQLite DB.
    create_all only creates missing tables — it does not alter existing ones.
    Each entry: (table, column, ddl).
    """
    additions = [
        ("reservations",      "notification_email", "VARCHAR(255)"),
        ("waitlist_entries",  "notification_email", "VARCHAR(255)"),
    ]
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, ddl in additions:
            if not inspector.has_table(table):
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column in existing:
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
            print(f"[init_db] Added column {table}.{column}")


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
