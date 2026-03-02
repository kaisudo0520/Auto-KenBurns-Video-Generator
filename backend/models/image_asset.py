"""
SQLAlchemy model for ImageAsset entity.

Represents an image used in a project with display settings.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend.database.connection import Base


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class ImageAsset(Base):
    """
    ImageAsset model representing an image in a project.

    Attributes:
        id: Unique identifier (UUID)
        project_id: Foreign key to project
        file_id: Foreign key to file record
        order: Display order in the video
        duration: Display duration in seconds
        subject_regions: JSON string of detected subject regions
        created_at: Creation timestamp
    """

    __tablename__ = "image_assets"

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

    # Display settings
    order = Column(Integer, nullable=False, default=0)
    duration = Column(Float, nullable=False, default=5.0)  # seconds

    # Subject detection data (JSON string)
    subject_regions = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="images")
    file = relationship(
        "File",
        back_populates="image_assets",
        foreign_keys=[file_id]
    )

    def __repr__(self) -> str:
        return f"<ImageAsset(id={self.id}, project_id={self.project_id}, order={self.order})>"
