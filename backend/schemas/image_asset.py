"""
Pydantic schemas for ImageAsset entity.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ========================================
# Bounding Box and Subject Region
# ========================================

class BoundingBox(BaseModel):
    """Bounding box for region detection."""
    x: float = Field(..., ge=0, le=1)
    y: float = Field(..., ge=0, le=1)
    width: float = Field(..., ge=0, le=1)
    height: float = Field(..., ge=0, le=1)


class SubjectRegion(BaseModel):
    """Subject region detected in image."""
    type: str  # 'person', 'face', 'object'
    bounds: BoundingBox
    confidence: float = Field(..., ge=0, le=1)


# ========================================
# ImageAsset Schemas
# ========================================

class ImageAssetBase(BaseModel):
    """Base image asset schema."""
    order: int = 0
    duration: float = Field(default=5.0, ge=1.0)  # 最小1秒，無上限（跟著音樂總長）


class ImageAssetCreate(ImageAssetBase):
    """Schema for creating an image asset."""
    project_id: str
    file_id: str
    subject_regions: Optional[List[SubjectRegion]] = None


class ImageAssetUpdate(BaseModel):
    """Schema for updating an image asset."""
    order: Optional[int] = None
    duration: Optional[float] = Field(default=None, ge=1.0)  # 無上限
    subject_regions: Optional[List[SubjectRegion]] = None


class ImageAssetResponse(ImageAssetBase):
    """Schema for image asset response."""
    id: str
    project_id: str
    file_id: str
    subject_regions: Optional[str]  # JSON string from DB
    created_at: datetime

    # Additional fields from joined file
    filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ImageAssetWithFileResponse(ImageAssetResponse):
    """Schema for image asset with file details."""
    file: Optional["FileResponse"] = None

    model_config = ConfigDict(from_attributes=True)


# Import at bottom to avoid circular imports
from backend.schemas.file import FileResponse
