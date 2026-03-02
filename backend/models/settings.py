"""
SQLAlchemy model for Settings entity.

Represents system configuration key-value pairs.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, Integer

from backend.database.connection import Base


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class Settings(Base):
    """
    Settings model for system configuration.

    Attributes:
        id: Unique identifier (UUID)
        key: Setting key (unique)
        value: Setting value
        type: Value type (string, number, boolean, json)
        description: Human-readable description
        is_system: Whether this is a system setting
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "settings"

    # Primary key
    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Key (must be unique)
    key = Column(String(100), unique=True, nullable=False, index=True)

    # Value
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")  # string, number, boolean, json

    # Description
    description = Column(Text, nullable=True)

    # System flag
    is_system = Column(Integer, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<Settings(key={self.key}, value={self.value})>"
