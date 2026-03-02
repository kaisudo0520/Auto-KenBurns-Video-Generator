"""
Database Package

Exports:
    - Base: SQLAlchemy declarative base
    - engine: Database engine
    - SessionLocal: Session factory
    - get_db: Dependency for FastAPI
    - get_db_context: Context manager for database sessions
    - init_db: Initialize database tables
    - drop_db: Drop all database tables
"""

from backend.database.connection import (
    Base,
    engine,
    SessionLocal,
    get_db,
    get_db_context,
    init_db,
    drop_db,
)

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "get_db_context",
    "init_db",
    "drop_db",
]
