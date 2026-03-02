"""
Pydantic schemas for File entity.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
import enum


class FileType(str, enum.Enum):
    IMAGE = "image"
    AUDIO = "audio"


class FileStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


# ========================================
# File Schemas
# ========================================

class FileBase(BaseModel):
    """Base file schema."""
    original_filename: str
    content_type: str


class FileCreate(FileBase):
    """Schema for creating a file record."""
    stored_filename: str
    file_path: str
    size: int = Field(..., gt=0)
    file_type: FileType
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    sample_rate: Optional[int] = None


class FileUpdate(BaseModel):
    """Schema for updating a file."""
    status: Optional[FileStatus] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    sample_rate: Optional[float] = None
    loudness: Optional[float] = None
    error_message: Optional[str] = None


class FileResponse(FileBase):
    """Schema for file response."""
    id: str
    file_type: FileType
    stored_filename: str
    file_path: str
    size: int
    width: Optional[int]
    height: Optional[int]
    duration: Optional[float]
    sample_rate: Optional[int]
    loudness: Optional[float]
    status: FileStatus
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ImageFileResponse(BaseModel):
    """Schema for image file response."""
    file_id: str
    filename: str
    content_type: str
    size: int
    width: int
    height: int
    uploaded_at: datetime
    status: FileStatus

    model_config = ConfigDict(from_attributes=True)


class AudioFileResponse(BaseModel):
    """Schema for audio file response."""
    file_id: str
    filename: str
    content_type: str
    size: int
    duration: float
    sample_rate: int
    loudness: float
    uploaded_at: datetime
    status: FileStatus

    model_config = ConfigDict(from_attributes=True)
