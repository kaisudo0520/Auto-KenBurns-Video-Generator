"""
FastAPI Application Dependencies

Provides common dependencies for database sessions, authentication, etc.
"""

import logging
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal

logger = logging.getLogger(__name__)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Get current user ID from authorization header.

    For now, returns a default user ID.
    In production, this would validate JWT token.

    Args:
        authorization: Authorization header

    Returns:
        str: User ID
    """
    # TODO: Implement proper authentication
    # For now, return a default user
    return "default_user"


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Verify API key from header.

    Args:
        x_api_key: API key header

    Returns:
        str: API key

    Raises:
        HTTPException: If API key is invalid
    """
    if not x_api_key:
        # Allow no key in development
        return "dev_key"
    return x_api_key
