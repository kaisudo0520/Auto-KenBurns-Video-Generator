"""
SQLAlchemy model for Project entity.

Represents a Ken-Burns video project with settings, images, and audio.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from backend.database.connection import Base
import enum


class ProjectStatus(str, enum.Enum):
    """Project status enumeration."""
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Resolution(str, enum.Enum):
    """Video resolution options."""
    RES_720P = "720p"
    RES_1080P = "1080p"
    RES_1440P = "1440p"
    RES_4K = "4k"


class FrameRate(str, enum.Enum):
    """Frame rate options."""
    FPS_24 = "24"
    FPS_30 = "30"
    FPS_60 = "60"


class OutputFormat(str, enum.Enum):
    """Output video format."""
    MP4_H264 = "mp4_h264"
    MP4_H265 = "mp4_h265"


class KenBurnsEffect(str, enum.Enum):
    """Ken-Burns effect type."""
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    PAN_UP = "pan_up"
    PAN_DOWN = "pan_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    COMPOSE_PAN_ZOOM = "compose_pan_zoom"
    RANDOM = "random"


class EasingFunction(str, enum.Enum):
    """Easing function type."""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class Project(Base):
    """
    Project model representing a Ken-Burns video project.

    Attributes:
        id: Unique identifier (UUID)
        name: Project name
        description: Project description
        status: Current project status
        resolution: Output video resolution
        fps: Output frame rate
        output_format: Output video format
        video_bitrate: Video bitrate in bps
        audio_bitrate: Audio bitrate in bps
        kenburns_effect_type: Type of Ken-Burns effect
        kenburns_duration: Duration per image in seconds
        kenburns_easing: Easing function for Ken-Burns
        kenburns_min_zoom: Minimum zoom level
        kenburns_max_zoom: Maximum zoom level
        audio_fade_in: Audio fade in duration in seconds
        audio_fade_out: Audio fade out duration in seconds
        audio_crossfade: Enable audio crossfade
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "projects"

    # Primary key
    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")

    # Status
    status = Column(
        SQLEnum(ProjectStatus),
        default=ProjectStatus.DRAFT,
        nullable=False
    )

    # Output settings
    resolution = Column(
        SQLEnum(Resolution),
        default=Resolution.RES_1080P,
        nullable=False
    )
    fps = Column(
        SQLEnum(FrameRate),
        default=FrameRate.FPS_30,
        nullable=False
    )
    output_format = Column(
        SQLEnum(OutputFormat),
        default=OutputFormat.MP4_H264,
        nullable=False
    )
    video_bitrate = Column(Integer, default=8000000)  # 8 Mbps
    audio_bitrate = Column(Integer, default=192000)    # 192 kbps

    # Ken-Burns settings
    kenburns_effect_type = Column(
        SQLEnum(KenBurnsEffect),
        default=KenBurnsEffect.COMPOSE_PAN_ZOOM,
        nullable=False
    )
    kenburns_duration = Column(Integer, default=5.0)
    kenburns_easing = Column(
        SQLEnum(EasingFunction),
        default=EasingFunction.EASE_IN_OUT,
        nullable=False
    )
    kenburns_min_zoom = Column(Integer, default=1.0)
    kenburns_max_zoom = Column(Integer, default=1.5)

    # Audio fade settings
    audio_fade_in = Column(Integer, default=2.0)
    audio_fade_out = Column(Integer, default=2.0)
    audio_crossfade = Column(Integer, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    images = relationship(
        "ImageAsset",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ImageAsset.order"
    )
    audio_tracks = relationship(
        "AudioAsset",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="AudioAsset.order"
    )
    render_jobs = relationship(
        "RenderJob",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"
