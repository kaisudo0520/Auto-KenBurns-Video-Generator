"""
Database Initialization Script

This script initializes the database with tables and default data.
Can be run directly or imported as a module.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.connection import engine, Base, SessionLocal
from backend.database.seed import get_seed_data, get_settings_options

# Import all models
from backend.models.project import Project
from backend.models.file import File
from backend.models.image_asset import ImageAsset
from backend.models.audio_asset import AudioAsset
from backend.models.render_job import RenderJob
from backend.models.settings import Settings


def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")


def drop_tables():
    """Drop all database tables."""
    print("Dropping database tables...")
    Base.metadata.drop_all(bind=engine)
    print("Tables dropped successfully.")


def seed_settings(db):
    """Seed default settings into the database."""
    print("Seeding settings...")

    # Check if settings already exist
    existing = db.query(Settings).first()
    if existing:
        print("Settings already exist, skipping seed.")
        return

    # Add default settings
    seed_data = get_seed_data()
    for setting_data in seed_data:
        setting = Settings(**setting_data)
        db.add(setting)

    db.commit()
    print(f"Seeded {len(seed_data)} settings.")


def reset_database():
    """Reset the database by dropping and recreating all tables."""
    print("Resetting database...")
    drop_tables()
    create_tables()

    db = SessionLocal()
    try:
        seed_settings(db)
    finally:
        db.close()

    print("Database reset complete.")


def init_database():
    """Initialize the database."""
    print("Initializing database...")
    create_tables()

    db = SessionLocal()
    try:
        seed_settings(db)
    finally:
        db.close()

    print("Database initialization complete.")


def show_tables():
    """Show all tables in the database."""
    print("\nDatabase tables:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database initialization script")
    parser.add_argument(
        "action",
        choices=["init", "reset", "seed", "show-tables"],
        help="Action to perform",
    )

    args = parser.parse_args()

    if args.action == "init":
        init_database()
    elif args.action == "reset":
        reset_database()
    elif args.action == "seed":
        db = SessionLocal()
        try:
            seed_settings(db)
        finally:
            db.close()
    elif args.action == "show-tables":
        show_tables()
