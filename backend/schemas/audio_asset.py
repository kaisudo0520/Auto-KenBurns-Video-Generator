"""
Pydantic schemas for AudioAsset entity.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ========================================
# AudioAsset Schemas
# ========================================

class AudioAssetBase(BaseModel):
    """Base audio asset schema."""
    order: int = 0
    volume: float = Field(default=1.0, ge=0.0, le=1.0)
    start_time: float = Field(default=0.0, ge=0.0)


class AudioAssetCreate(AudioAssetBase):
    """Schema for creating an audio asset."""
    project_id: str
    file_id: str


class AudioAssetUpdate(BaseModel):
    """Schema for updating an audio asset."""
    order: Optional[int] = None
    volume: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    start_time: Optional[float] = Field(default=None, ge=0.0)


class AudioAssetResponse(AudioAssetBase):
    """Schema for audio asset response."""
    id: str
    project_id: str
    file_id: str
    created_at: datetime

    # Additional fields from joined file
    filename: Optional[str] = None
    duration: Optional[float] = None
    file_size: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AudioAssetWithFileResponse(AudioAssetResponse):
    """Schema for audio asset with file details."""
    file: Optional["FileResponse"] = None

    model_config = ConfigDict(from_attributes=True)


# Import at bottom to avoid circular imports
from backend.schemas.file import FileResponse
