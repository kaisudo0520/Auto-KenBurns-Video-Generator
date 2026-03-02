"""
Render API Router

Handles render job operations including start, cancel, status, and download.
"""

import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import deps
from backend.models.project import Project as ProjectModel
from backend.models.project import ProjectStatus
from backend.models.render_job import RenderJob as RenderJobModel
from backend.models.render_job import JobStatus
from backend.schemas.render_job import (
    CancelRenderResponse,
    RenderHistoryItem,
    RenderJobResponse,
    RenderJobStatusResponse,
    StartRenderResponse,
)
from backend.services.render_service import RenderService

logger = logging.getLogger(__name__)
router = APIRouter()


# Request models
class StartRenderRequest(BaseModel):
    """Request to start a render job."""
    project_id: str


# Response models
class StartRenderResponseWrapper(BaseModel):
    """Response wrapper for start render."""
    success: bool = True
    data: "StartRenderResponse"


class RenderQueueStatusResponse(BaseModel):
    """Response for render queue status."""
    success: bool = True
    data: dict


# ========================================
# Render Job Endpoints
# ========================================

@router.post("/render/start", response_model=StartRenderResponseWrapper, status_code=status.HTTP_202_ACCEPTED)
async def start_render(
    request: StartRenderRequest,
    db: Session = Depends(deps.get_db),
):
    """
    Start rendering a project video.
    """
    # Get project
    project = db.query(ProjectModel).filter(
        ProjectModel.id == request.project_id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": "專案不存在",
            },
        )

    # Check project has images
    if not project.images or len(project.images) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_PROJECT_STATE",
                "message": "專案沒有足夠的圖片進行渲染",
                "details": {
                    "images_count": 0,
                    "minimum_required": 1,
                },
            },
        )

    # Check if project is already being rendered
    if project.status == ProjectStatus.PROCESSING:
        # Check for active render job
        active_job = db.query(RenderJobModel).filter(
            RenderJobModel.project_id == request.project_id,
            RenderJobModel.status.in_([JobStatus.QUEUED, JobStatus.PREPARING, JobStatus.RENDERING, JobStatus.ENCODING])
        ).first()

        if active_job:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "RENDER_IN_PROGRESS",
                    "message": "專案正在渲染中",
                    "details": {
                        "job_id": active_job.id,
                        "status": active_job.status.value,
                    },
                },
            )

    # Create render job
    render_service = RenderService(db)
    job = await render_service.create_render_job(project)

    # 如果项目有音频，根据音频长度自动计算每张图片的显示时长
    audio_duration = 0.0
    if project.audio_tracks and len(project.audio_tracks) > 0:
        # 获取第一个音频文件的时长
        audio_file = project.audio_tracks[0].file
        if audio_file and audio_file.duration:
            audio_duration = float(audio_file.duration)

    # 根据是否有音频来计算总时长
    if audio_duration > 0 and project.images:
        # 根据音频长度和图片数量计算每张图片的显示时长
        image_count = len(project.images)
        # 每张图片的显示时长 = 音频总时长 / 图片数量
        per_image_duration = audio_duration / image_count

        # 更新每张图片的显示时长
        for img in project.images:
            img.duration = per_image_duration
        total_duration = audio_duration
    else:
        # 没有音频时使用图片的默认时长
        total_duration = sum(img.duration for img in project.images)

    # Start render in background (simulated for now)
    # In production, this would queue to a task runner
    await render_service.start_render(job.id, project)

    logger.info(f"Started render job: {job.id} for project: {project.id}, audio_duration: {audio_duration}s, images: {len(project.images)}")

    # Calculate estimated duration
    estimated_duration = int(total_duration * 1.5)  # Rough estimate

    return StartRenderResponseWrapper(
        data=StartRenderResponse(
            job_id=job.id,
            project_id=project.id,
            status=job.status,
            estimated_duration=estimated_duration,
            webSocket_url=f"/ws/render/{job.id}",
        )
    )


@router.post("/render/cancel/{job_id}", response_model=CancelRenderResponse)
async def cancel_render(
    job_id: str,
    db: Session = Depends(deps.get_db),
):
    """
    Cancel a render job.
    """
    job = db.query(RenderJobModel).filter(RenderJobModel.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": "任務不存在",
            },
        )

    # Check if job can be cancelled
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_JOB_STATE",
                "message": f"任務已{job.status.value}，無法取消",
            },
        )

    # Update job status
    job.status = JobStatus.CANCELLED

    # Update project status
    project = job.project
    if project:
        project.status = ProjectStatus.DRAFT

    db.commit()

    logger.info(f"Cancelled render job: {job_id}")

    return CancelRenderResponse(
        job_id=job_id,
        status="cancelled",
    )


@router.get("/render/status/{job_id}", response_model=RenderJobStatusResponse)
async def get_render_status(
    job_id: str,
    db: Session = Depends(deps.get_db),
):
    """
    Get the status of a render job.
    """
    job = db.query(RenderJobModel).filter(RenderJobModel.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": "任務不存在",
            },
        )

    # Build progress info
    progress_info = None
    if job.status in [JobStatus.RENDERING, JobStatus.ENCODING]:
        from backend.schemas.render_job import RenderProgress, StageProgress

        stage_labels = {
            "preparing": "準備階段",
            "loading_images": "載入圖片",
            "detecting_subjects": "偵測主體",
            "generating_paths": "生成路徑",
            "processing_audio": "處理音訊",
            "rendering_frames": "渲染幀",
            "encoding_video": "編碼影片",
            "finalizing": "完成階段",
        }

        progress_info = RenderProgress(
            percentage=job.progress,
            current_frame=job.current_frame,
            total_frames=job.total_frames,
            fps=job.fps,
            eta_seconds=job.eta_seconds,
            stage=job.current_stage,
            stage_progress=StageProgress(
                current=stage_labels.get(job.current_stage.value, job.current_stage.value),
                percentage=min(100, job.progress),
            ),
        )

    return RenderJobStatusResponse(
        id=job.id,
        project_id=job.project_id,
        status=job.status,
        progress=job.progress,
        current_stage=job.current_stage,
        current_frame=job.current_frame,
        total_frames=job.total_frames,
        fps=job.fps,
        eta_seconds=job.eta_seconds,
        output_path=job.output_path,
        output_size=job.output_size,
        output_duration=job.output_duration,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        progress_info=progress_info,
    )


@router.get("/render/history/{project_id}", response_model=dict)
async def get_render_history(
    project_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(deps.get_db),
):
    """
    Get render job history for a project.
    """
    query = db.query(RenderJobModel)

    # Filter by project
    query = query.filter(RenderJobModel.project_id == project_id)

    # Get total count
    total_items = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    jobs = query.order_by(RenderJobModel.created_at.desc()).offset(offset).limit(page_size).all()

    # Build history items
    history_items = []
    for job in jobs:
        history_items.append(RenderHistoryItem(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            output_path=job.output_path,
            file_size=job.output_size,
            duration=job.output_duration,
            error=job.error_message,
            created_at=job.created_at,
            completed_at=job.completed_at,
        ))

    return {
        "success": True,
        "data": history_items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": (total_items + page_size - 1) // page_size,
        }
    }


@router.get("/render/download/{job_id}")
async def download_render(
    job_id: str,
    quality: str = Query("original", description="Quality: original, high, medium, low"),
    db: Session = Depends(deps.get_db),
):
    """
    Download the rendered video.
    """
    job = db.query(RenderJobModel).filter(RenderJobModel.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": "任務不存在",
            },
        )

    # Check if job is completed
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "RENDER_NOT_COMPLETED",
                "message": f"任務尚未完成，目前狀態: {job.status.value}",
            },
        )

    # Check if output file exists
    if not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "OUTPUT_NOT_FOUND",
                "message": "渲染輸出檔案不存在",
            },
        )

    # Determine filename
    filename = os.path.basename(job.output_path)

    logger.info(f"Downloading render output: {job.output_path}")

    return FileResponse(
        path=job.output_path,
        filename=filename,
        media_type="video/mp4",
    )
