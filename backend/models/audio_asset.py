"""
SQLAlchemy model for AudioAsset entity.

Represents an audio track used in a project.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.database.connection import Base


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class AudioAsset(Base):
    """
    AudioAsset model representing an audio track in a project.

    Attributes:
        id: Unique identifier (UUID)
        project_id: Foreign key to project
        file_id: Foreign key to file record
        order: Playback order in the video
        volume: Volume level (0.0 - 1.0)
        start_time: Start time offset in seconds
        created_at: Creation timestamp
    """

    __tablename__ = "audio_assets"

    # Primary key
    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Foreign keys
    project_id = Column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    file_id = Column(
        String(36),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False
    )

    # Playback settings
    order = Column(Integer, nullable=False, default=0)
    volume = Column(Float, nullable=False, default=1.0)  # 0.0 - 1.0
    start_time = Column(Float, nullable=False, default=0.0)  # seconds

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="audio_tracks")
    file = relationship(
        "File",
        back_populates="audio_assets",
        foreign_keys=[file_id]
    )

    def __repr__(self) -> str:
        return f"<AudioAsset(id={self.id}, project_id={self.project_id}, order={self.order})>"
