"""
SQLAlchemy model for File entity.

Represents uploaded image and audio files stored in the system.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship

from backend.database.connection import Base
import enum


class FileType(str, enum.Enum):
    """File type enumeration."""
    IMAGE = "image"
    AUDIO = "audio"


class FileStatus(str, enum.Enum):
    """File processing status."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class File(Base):
    """
    File model representing an uploaded file.

    Attributes:
        id: Unique identifier (UUID)
        file_type: Type of file (image/audio)
        original_filename: Original filename when uploaded
        stored_filename: Actual stored filename on disk
        file_path: Full path to stored file
        content_type: MIME type of the file
        size: File size in bytes
        width: Image width (for images)
        height: Image height (for images)
        duration: Audio duration in seconds (for audio)
        sample_rate: Audio sample rate (for audio)
        status: Current processing status
        error_message: Error message if status is ERROR
        created_at: Upload timestamp
        processed_at: Processing completion timestamp
    """

    __tablename__ = "files"

    # Primary key
    id = Column(String(36), primary_key=True, default=generate_uuid)

    # File type
    file_type = Column(SQLEnum(FileType), nullable=False)

    # Filenames
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)

    # File info
    content_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)  # bytes

    # Image specific (nullable for audio)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # Audio specific (nullable for image)
    duration = Column(Float, nullable=True)  # seconds
    sample_rate = Column(Integer, nullable=True)  # Hz
    loudness = Column(Float, nullable=True)  # LUFS

    # Status
    status = Column(
        SQLEnum(FileStatus),
        default=FileStatus.UPLOADING,
        nullable=False
    )
    error_message = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    image_assets = relationship(
        "ImageAsset",
        back_populates="file",
        foreign_keys="ImageAsset.file_id"
    )
    audio_assets = relationship(
        "AudioAsset",
        back_populates="file",
        foreign_keys="AudioAsset.file_id"
    )

    def __repr__(self) -> str:
        return f"<File(id={self.id}, filename={self.original_filename}, type={self.file_type})>"
