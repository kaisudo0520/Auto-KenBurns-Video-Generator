"""
Pydantic schemas for Settings entity.
"""

from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, Field, ConfigDict


# ========================================
# Settings Schemas
# ========================================

class SettingsBase(BaseModel):
    """Base settings schema."""
    key: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class SettingsCreate(SettingsBase):
    """Schema for creating a setting."""
    value: Optional[str] = None
    value_type: str = "string"
    is_system: bool = False


class SettingsUpdate(BaseModel):
    """Schema for updating a setting."""
    value: Optional[str] = None
    value_type: Optional[str] = None
    description: Optional[str] = None


class SettingsResponse(SettingsBase):
    """Schema for settings response."""
    id: str
    value: Optional[str]
    value_type: str
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SettingsValue(BaseModel):
    """Schema for settings value with parsed type."""
    key: str
    value: Union[str, int, float, bool, dict, list]
    value_type: str


# ========================================
# System Status Schemas
# ========================================

class GPUInfo(BaseModel):
    """GPU 資訊。"""
    available: bool
    name: Optional[str] = None
    memory_total: Optional[int] = None  # MB
    memory_used: Optional[int] = None   # MB
    driver_version: Optional[str] = None  # NVIDIA 驅動版本（由 nvidia-smi 查詢）
    nvenc_available: Optional[bool] = None


class StorageInfo(BaseModel):
    """Storage information."""
    temp_used: int      # bytes
    temp_total: int     # bytes
    output_used: int    # bytes
    output_total: int   # bytes


class VersionInfo(BaseModel):
    """Version information."""
    api: str
    ffmpeg: str
    engine: str


class SystemStatus(BaseModel):
    """System status."""
    gpu: GPUInfo
    storage: StorageInfo
    render_queue: dict  # RenderQueueStatus
    version: VersionInfo


# ========================================
# Settings Options Schemas
# ========================================

class ResolutionConfig(BaseModel):
    """Resolution configuration."""
    value: str
    label: str
    width: int
    height: int


class FrameRateConfig(BaseModel):
    """Frame rate configuration."""
    value: int
    label: str


class OutputFormatConfig(BaseModel):
    """Output format configuration."""
    value: str
    label: str
    description: str


class EncoderConfig(BaseModel):
    """Encoder configuration."""
    value: str
    label: str
    hardware: bool


class KenBurnsEffectConfig(BaseModel):
    """Ken-Burns effect configuration."""
    value: str
    label: str
    default: Optional[bool] = None


class EasingFunctionConfig(BaseModel):
    """Easing function configuration."""
    value: str
    label: str
    default: Optional[bool] = None


class SettingsOptions(BaseModel):
    """All available settings options."""
    resolutions: list[ResolutionConfig]
    frame_rates: list[FrameRateConfig]
    output_formats: list[OutputFormatConfig]
    encoders: list[EncoderConfig]
    kenburns_effects: list[KenBurnsEffectConfig]
    easing_functions: list[EasingFunctionConfig]
