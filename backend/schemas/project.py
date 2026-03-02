"""
Pydantic schemas for Project entity.
"""

import enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# Enums
class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Resolution(str, enum.Enum):
    RES_720P = "720p"
    RES_1080P = "1080p"
    RES_1440P = "1440p"
    RES_4K = "4k"


class FrameRate(str, enum.Enum):
    FPS_24 = "24"
    FPS_30 = "30"
    FPS_60 = "60"


class OutputFormat(str, enum.Enum):
    MP4_H264 = "mp4_h264"
    MP4_H265 = "mp4_h265"


class KenBurnsEffect(str, enum.Enum):
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    PAN_UP = "pan_up"
    PAN_DOWN = "pan_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    COMPOSE_PAN_ZOOM = "compose_pan_zoom"
    RANDOM = "random"


class EasingFunction(str, enum.Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"



# ========================================
# Ken-Burns Settings Schemas
# ========================================

class KenBurnsSettingsBase(BaseModel):
    """Base Ken-Burns settings."""
    effect_type: KenBurnsEffect = KenBurnsEffect.COMPOSE_PAN_ZOOM
    duration: float = Field(default=5.0, ge=1.0, le=30.0)
    easing: EasingFunction = EasingFunction.EASE_IN_OUT
    min_zoom: float = Field(default=1.0, ge=1.0)
    max_zoom: float = Field(default=1.5, ge=1.0)


class KenBurnsSettingsCreate(KenBurnsSettingsBase):
    """Schema for creating Ken-Burns settings."""
    pass


class KenBurnsSettingsUpdate(BaseModel):
    """Schema for updating Ken-Burns settings."""
    effect_type: Optional[KenBurnsEffect] = None
    duration: Optional[float] = Field(default=None, ge=1.0, le=30.0)
    easing: Optional[EasingFunction] = None
    min_zoom: Optional[float] = Field(default=None, ge=1.0)
    max_zoom: Optional[float] = Field(default=None, ge=1.0)


class KenBurnsSettingsResponse(KenBurnsSettingsBase):
    """Schema for Ken-Burns settings response."""
    model_config = ConfigDict(from_attributes=True)


# ========================================
# Audio Fade Settings Schemas
# ========================================

class AudioFadeSettingsBase(BaseModel):
    """Base audio fade settings."""
    fade_in: float = Field(default=2.0, ge=0.0, le=10.0)
    fade_out: float = Field(default=2.0, ge=0.0, le=10.0)
    crossfade: bool = True


class AudioFadeSettingsCreate(AudioFadeSettingsBase):
    """Schema for creating audio fade settings."""
    pass


class AudioFadeSettingsUpdate(BaseModel):
    """Schema for updating audio fade settings."""
    fade_in: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    fade_out: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    crossfade: Optional[bool] = None


class AudioFadeSettingsResponse(AudioFadeSettingsBase):
    """Schema for audio fade settings response."""
    model_config = ConfigDict(from_attributes=True)


# ========================================
# Render Settings Schemas
# ========================================

class RenderSettingsBase(BaseModel):
    """Base render settings."""
    resolution: Resolution = Resolution.RES_1080P
    fps: FrameRate = FrameRate.FPS_30
    output_format: OutputFormat = OutputFormat.MP4_H264
    video_bitrate: int = Field(default=8000000, ge=1000000, le=100000000)
    audio_bitrate: int = Field(default=192000, ge=64000, le=512000)


class RenderSettingsCreate(RenderSettingsBase):
    """Schema for creating render settings."""
    kenburns: Optional[KenBurnsSettingsCreate] = None
    audio_fade: Optional[AudioFadeSettingsCreate] = None


class RenderSettingsUpdate(BaseModel):
    """Schema for updating render settings."""
    resolution: Optional[Resolution] = None
    fps: Optional[FrameRate] = None
    output_format: Optional[OutputFormat] = None
    video_bitrate: Optional[int] = Field(default=None, ge=1000000, le=100000000)
    audio_bitrate: Optional[int] = Field(default=None, ge=64000, le=512000)
    kenburns: Optional[KenBurnsSettingsUpdate] = None
    audio_fade: Optional[AudioFadeSettingsUpdate] = None


class RenderSettingsResponse(RenderSettingsBase):
    """Schema for render settings response."""
    kenburns: KenBurnsSettingsResponse
    audio_fade: AudioFadeSettingsResponse

    model_config = ConfigDict(from_attributes=True)


# ========================================
# Project Schemas
# ========================================

class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    settings: Optional[RenderSettingsCreate] = None


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    settings: Optional[RenderSettingsUpdate] = None


class ProjectListItem(BaseModel):
    """Schema for project list item."""
    id: str
    name: str
    description: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    images_count: int = 0
    audio_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: str
    status: ProjectStatus
    resolution: Resolution
    fps: FrameRate
    output_format: OutputFormat
    video_bitrate: int
    audio_bitrate: int
    kenburns_effect_type: KenBurnsEffect
    kenburns_duration: float
    kenburns_easing: EasingFunction
    kenburns_min_zoom: float
    kenburns_max_zoom: float
    audio_fade_in: float
    audio_fade_out: float
    audio_crossfade: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectDetailResponse(ProjectResponse):
    """Schema for detailed project response with relations."""
    images: List["ImageAssetResponse"] = []
    audio: List["AudioAssetResponse"] = []
    latest_render: Optional["RenderJobSummary"] = None

    model_config = ConfigDict(from_attributes=True)


# Import at bottom to avoid circular imports
from backend.schemas.image_asset import ImageAssetResponse
from backend.schemas.audio_asset import AudioAssetResponse
from backend.schemas.render_job import RenderJobSummary
