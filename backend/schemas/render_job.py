"""
Pydantic schemas for RenderJob entity.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
import enum


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RENDERING = "rendering"
    ENCODING = "encoding"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class RenderStage(str, enum.Enum):
    PREPARING = "preparing"
    LOADING_IMAGES = "loading_images"
    DETECTING_SUBJECTS = "detecting_subjects"
    GENERATING_PATHS = "generating_paths"
    PROCESSING_AUDIO = "processing_audio"
    RENDERING_FRAMES = "rendering_frames"
    ENCODING_VIDEO = "encoding_video"
    FINALIZING = "finalizing"


# ========================================
# Render Progress
# ========================================

class StageProgress(BaseModel):
    """Progress within a stage."""
    current: str
    percentage: int = Field(..., ge=0, le=100)


class RenderProgress(BaseModel):
    """Render progress information."""
    percentage: int = Field(..., ge=0, le=100)
    current_frame: int = 0
    total_frames: int = 0
    fps: float = 0.0
    eta_seconds: int = 0
    stage: RenderStage = RenderStage.PREPARING
    stage_progress: StageProgress


# ========================================
# RenderJob Schemas
# ========================================

class RenderJobBase(BaseModel):
    """Base render job schema."""
    pass


class RenderJobCreate(RenderJobBase):
    """Schema for creating a render job."""
    project_id: str


class RenderJobUpdate(BaseModel):
    """Schema for updating a render job."""
    status: Optional[JobStatus] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    current_stage: Optional[RenderStage] = None
    current_frame: Optional[int] = None
    total_frames: Optional[int] = None
    fps: Optional[float] = None
    eta_seconds: Optional[int] = None
    output_path: Optional[str] = None
    output_size: Optional[int] = None
    output_duration: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class RenderJobResponse(RenderJobBase):
    """Schema for render job response."""
    id: str
    project_id: str
    status: JobStatus
    progress: int
    current_stage: RenderStage
    current_frame: int
    total_frames: int
    fps: float
    eta_seconds: int
    output_path: Optional[str]
    output_size: Optional[int]
    output_duration: Optional[float]
    error_code: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class RenderJobStatusResponse(RenderJobResponse):
    """Schema for render job status with progress."""
    progress_info: Optional[RenderProgress] = None

    model_config = ConfigDict(from_attributes=True)


class RenderJobSummary(BaseModel):
    """Summary of a render job for project listing."""
    job_id: str
    status: JobStatus
    output_path: Optional[str] = None
    created_at: datetime
    progress: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class RenderHistoryItem(BaseModel):
    """Render history item."""
    job_id: str
    status: JobStatus
    progress: int
    output_path: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class StartRenderResponse(BaseModel):
    """Response when starting a render."""
    job_id: str
    project_id: str
    status: JobStatus
    estimated_duration: int  # seconds
    webSocket_url: str


class CancelRenderResponse(BaseModel):
    """Response when cancelling a render."""
    job_id: str
    status: str = "cancelled"


class RenderQueueStatus(BaseModel):
    """Render queue status."""
    running: int
    queued: int
    max_concurrent: int
