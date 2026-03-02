"""
SQLAlchemy model for RenderJob entity.

Represents a rendering task for a project.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship

from backend.database.connection import Base
import enum


class JobStatus(str, enum.Enum):
    """Render job status."""
    QUEUED = "queued"
    PREPARING = "preparing"
    RENDERING = "rendering"
    ENCODING = "encoding"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class RenderStage(str, enum.Enum):
    """Render processing stage."""
    PREPARING = "preparing"
    LOADING_IMAGES = "loading_images"
    DETECTING_SUBJECTS = "detecting_subjects"
    GENERATING_PATHS = "generating_paths"
    PROCESSING_AUDIO = "processing_audio"
    RENDERING_FRAMES = "rendering_frames"
    ENCODING_VIDEO = "encoding_video"
    FINALIZING = "finalizing"


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class RenderJob(Base):
    """
    RenderJob model representing a rendering task.

    Attributes:
        id: Unique identifier (UUID)
        project_id: Foreign key to project
        status: Current job status
        progress: Progress percentage (0-100)
        current_stage: Current processing stage
        current_frame: Current frame being rendered
        total_frames: Total frames to render
        fps: Current rendering FPS
        eta_seconds: Estimated time remaining
        output_path: Path to output video file
        output_size: Size of output file in bytes
        output_duration: Duration of output video in seconds
        error_code: Error code if failed
        error_message: Error message if failed
        created_at: Job creation timestamp
        started_at: Job start timestamp
        completed_at: Job completion timestamp
    """

    __tablename__ = "render_jobs"

    # Primary key
    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Foreign key
    project_id = Column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )

    # Status
    status = Column(
        SQLEnum(JobStatus),
        default=JobStatus.QUEUED,
        nullable=False
    )

    # Progress
    progress = Column(Integer, default=0)  # 0-100
    current_stage = Column(
        SQLEnum(RenderStage),
        default=RenderStage.PREPARING,
        nullable=False
    )
    current_frame = Column(Integer, default=0)
    total_frames = Column(Integer, default=0)
    fps = Column(Float, default=0.0)
    eta_seconds = Column(Integer, default=0)

    # Output
    output_path = Column(String(512), nullable=True)
    output_size = Column(Integer, nullable=True)  # bytes
    output_duration = Column(Float, nullable=True)  # seconds

    # Error
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="render_jobs")

    def __repr__(self) -> str:
        return f"<RenderJob(id={self.id}, project_id={self.project_id}, status={self.status})>"
