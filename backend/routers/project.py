"""
Project API Router

Handles project CRUD operations and asset management.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import deps
from backend.models.project import Project as ProjectModel
from backend.models.project import ProjectStatus
from backend.models.file import File as FileModel
from backend.models.image_asset import ImageAsset
from backend.models.audio_asset import AudioAsset
from backend.schemas.project import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListItem,
    ProjectResponse,
    ProjectUpdate,
)
from backend.schemas.image_asset import ImageAssetResponse
from backend.schemas.audio_asset import AudioAssetResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# Response models
class ProjectResponseWrapper(BaseModel):
    """Response wrapper for project."""
    success: bool = True
    data: "ProjectResponse"


class ProjectDetailResponseWrapper(BaseModel):
    """Response wrapper for project detail."""
    success: bool = True
    data: "ProjectDetailResponse"


class ProjectListResponse(BaseModel):
    """Response for project list."""
    success: bool = True
    data: List[ProjectListItem]
    pagination: dict


class AddImagesResponse(BaseModel):
    """Response for adding images to project."""
    success: bool = True
    data: dict


class AddAudioResponse(BaseModel):
    """Response for adding audio to project."""
    success: bool = True
    data: dict


# ========================================
# Project CRUD Endpoints
# ========================================

@router.post("/projects", response_model=ProjectResponseWrapper, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(deps.get_db),
):
    """
    Create a new Ken-Burns video project.
    """
    # Create project model
    db_project = ProjectModel(
        name=project.name,
        description=project.description,
    )

    # Apply custom settings if provided
    if project.settings:
        if project.settings.resolution:
            db_project.resolution = project.settings.resolution
        if project.settings.fps:
            db_project.fps = project.settings.fps
        if project.settings.output_format:
            db_project.output_format = project.settings.output_format
        if project.settings.video_bitrate:
            db_project.video_bitrate = project.settings.video_bitrate
        if project.settings.audio_bitrate:
            db_project.audio_bitrate = project.settings.audio_bitrate

        # Ken-Burns settings
        if project.settings.kenburns:
            kb = project.settings.kenburns
            if kb.effect_type:
                db_project.kenburns_effect_type = kb.effect_type
            if kb.duration:
                db_project.kenburns_duration = kb.duration
            if kb.easing:
                db_project.kenburns_easing = kb.easing
            if kb.min_zoom:
                db_project.kenburns_min_zoom = kb.min_zoom
            if kb.max_zoom:
                db_project.kenburns_max_zoom = kb.max_zoom

        # Audio fade settings
        if project.settings.audio_fade:
            af = project.settings.audio_fade
            if af.fade_in is not None:
                db_project.audio_fade_in = af.fade_in
            if af.fade_out is not None:
                db_project.audio_fade_out = af.fade_out
            if af.crossfade is not None:
                db_project.audio_crossfade = af.crossfade

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    logger.info(f"Created project: {db_project.id}")

    return ProjectResponseWrapper(
        data=ProjectResponse(
            id=db_project.id,
            name=db_project.name,
            description=db_project.description,
            status=db_project.status,
            resolution=db_project.resolution,
            fps=db_project.fps,
            output_format=db_project.output_format,
            video_bitrate=db_project.video_bitrate,
            audio_bitrate=db_project.audio_bitrate,
            kenburns_effect_type=db_project.kenburns_effect_type,
            kenburns_duration=db_project.kenburns_duration,
            kenburns_easing=db_project.kenburns_easing,
            kenburns_min_zoom=db_project.kenburns_min_zoom,
            kenburns_max_zoom=db_project.kenburns_max_zoom,
            audio_fade_in=db_project.audio_fade_in,
            audio_fade_out=db_project.audio_fade_out,
            audio_crossfade=db_project.audio_crossfade,
            created_at=db_project.created_at,
            updated_at=db_project.updated_at,
        )
    )


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    db: Session = Depends(deps.get_db),
):
    """
    Get list of all projects with pagination.
    """
    query = db.query(ProjectModel)

    # Apply status filter
    if status_filter:
        try:
            status_enum = ProjectStatus(status_filter)
            query = query.filter(ProjectModel.status == status_enum)
        except ValueError:
            pass

    # Get total count
    total_items = query.count()

    # Apply sorting
    allowed_sort_fields = {"created_at", "updated_at", "name", "status"}
    if sort_by not in allowed_sort_fields:
        sort_by = "created_at"
    sort_column = getattr(ProjectModel, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    projects = query.offset(offset).limit(page_size).all()

    # Build response
    project_items = []
    for p in projects:
        project_items.append(ProjectListItem(
            id=p.id,
            name=p.name,
            description=p.description,
            status=p.status,
            created_at=p.created_at,
            updated_at=p.updated_at,
            images_count=len(p.images) if p.images else 0,
            audio_count=len(p.audio_tracks) if p.audio_tracks else 0,
        ))

    return ProjectListResponse(
        data=project_items,
        pagination={
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": (total_items + page_size - 1) // page_size,
        }
    )


@router.get("/projects/{project_id}", response_model=ProjectDetailResponseWrapper)
async def get_project(
    project_id: str,
    db: Session = Depends(deps.get_db),
):
    """
    Get detailed information about a project.
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": "專案不存在",
            },
        )

    # Get latest render job
    latest_render = None
    if project.render_jobs:
        completed_jobs = [j for j in project.render_jobs if j.status.value == "completed"]
        if completed_jobs:
            latest_render = completed_jobs[-1]

    # Build images response
    images = []
    for img in project.images:
        images.append(ImageAssetResponse(
            id=img.id,
            project_id=img.project_id,
            file_id=img.file_id,
            order=img.order,
            duration=img.duration,
            subject_regions=img.subject_regions,
            created_at=img.created_at,
            filename=img.file.original_filename if img.file else None,
            width=img.file.width if img.file else None,
            height=img.file.height if img.file else None,
            file_size=img.file.size if img.file else None,
        ))

    # Build audio response
    audio_tracks = []
    for audio in project.audio_tracks:
        audio_tracks.append(AudioAssetResponse(
            id=audio.id,
            project_id=audio.project_id,
            file_id=audio.file_id,
            order=audio.order,
            volume=audio.volume,
            start_time=audio.start_time,
            created_at=audio.created_at,
            filename=audio.file.original_filename if audio.file else None,
            duration=audio.file.duration if audio.file else None,
            file_size=audio.file.size if audio.file else None,
        ))

    return ProjectDetailResponseWrapper(
        data=ProjectDetailResponse(
            id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        resolution=project.resolution,
        fps=project.fps,
        output_format=project.output_format,
        video_bitrate=project.video_bitrate,
        audio_bitrate=project.audio_bitrate,
        kenburns_effect_type=project.kenburns_effect_type,
        kenburns_duration=project.kenburns_duration,
        kenburns_easing=project.kenburns_easing,
        kenburns_min_zoom=project.kenburns_min_zoom,
        kenburns_max_zoom=project.kenburns_max_zoom,
        audio_fade_in=project.audio_fade_in,
        audio_fade_out=project.audio_fade_out,
        audio_crossfade=project.audio_crossfade,
        created_at=project.created_at,
        updated_at=project.updated_at,
        images=images,
        audio=audio_tracks,
        latest_render=latest_render,
        )
    )


@router.put("/projects/{project_id}", response_model=ProjectResponseWrapper)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    db: Session = Depends(deps.get_db),
):
    """
    Update project information.
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": "專案不存在",
            },
        )

    # Check if project is being rendered
    if project.status == ProjectStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "RENDER_IN_PROGRESS",
                "message": "無法更新正在渲染中的專案",
            },
        )

    # Update basic fields
    if project_update.name is not None:
        project.name = project_update.name
    if project_update.description is not None:
        project.description = project_update.description
    if project_update.status is not None:
        project.status = project_update.status

    # Update settings
    if project_update.settings:
        if project_update.settings.resolution:
            project.resolution = project_update.settings.resolution
        if project_update.settings.fps:
            project.fps = project_update.settings.fps
        if project_update.settings.output_format:
            project.output_format = project_update.settings.output_format
        if project_update.settings.video_bitrate:
            project.video_bitrate = project_update.settings.video_bitrate
        if project_update.settings.audio_bitrate:
            project.audio_bitrate = project_update.settings.audio_bitrate

        # Ken-Burns settings
        if project_update.settings.kenburns:
            kb = project_update.settings.kenburns
            if kb.effect_type:
                project.kenburns_effect_type = kb.effect_type
            if kb.duration is not None:
                project.kenburns_duration = kb.duration
            if kb.easing:
                project.kenburns_easing = kb.easing
            if kb.min_zoom is not None:
                project.kenburns_min_zoom = kb.min_zoom
            if kb.max_zoom is not None:
                project.kenburns_max_zoom = kb.max_zoom

        # Audio fade settings
        if project_update.settings.audio_fade:
            af = project_update.settings.audio_fade
            if af.fade_in is not None:
                project.audio_fade_in = af.fade_in
            if af.fade_out is not None:
                project.audio_fade_out = af.fade_out
            if af.crossfade is not None:
                project.audio_crossfade = af.crossfade

    db.commit()
    db.refresh(project)

    logger.info(f"Updated project: {project.id}")

    return ProjectResponseWrapper(
        data=ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            status=project.status,
            resolution=project.resolution,
            fps=project.fps,
            output_format=project.output_format,
            video_bitrate=project.video_bitrate,
            audio_bitrate=project.audio_bitrate,
            kenburns_effect_type=project.kenburns_effect_type,
            kenburns_duration=project.kenburns_duration,
            kenburns_easing=project.kenburns_easing,
            kenburns_min_zoom=project.kenburns_min_zoom,
            kenburns_max_zoom=project.kenburns_max_zoom,
            audio_fade_in=project.audio_fade_in,
            audio_fade_out=project.audio_fade_out,
            audio_crossfade=project.audio_crossfade,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
    )


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: Session = Depends(deps.get_db),
):
    """
    Delete a project and all associated resources.
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": "專案不存在",
            },
        )

    # Check if project is being rendered
    if project.status == ProjectStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "RENDER_IN_PROGRESS",
                "message": "無法刪除正在渲染中的專案",
            },
        )

    db.delete(project)
    db.commit()

    logger.info(f"Deleted project: {project_id}")

    return None


# ========================================
# Project Asset Management Endpoints
# ========================================

class AddImagesRequest(BaseModel):
    """Request to add images to project."""
    file_ids: List[str]
    order: int = 0
    duration: float = 5.0


@router.post("/projects/{project_id}/images", response_model=AddImagesResponse)
async def add_images_to_project(
    project_id: str,
    request: AddImagesRequest,
    db: Session = Depends(deps.get_db),
):
    """
    Add uploaded images to a project.
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": "專案不存在",
            },
        )

    # Verify files exist and are images
    added_ids = []
    for file_id in request.file_ids:
        file = db.query(FileModel).filter(
            FileModel.id == file_id,
            FileModel.file_type == "image"
        ).first()

        if not file:
            continue

        # Check if already added
        existing = db.query(ImageAsset).filter(
            ImageAsset.project_id == project_id,
            ImageAsset.file_id == file_id
        ).first()

        if existing:
            continue

        # Create image asset
        asset = ImageAsset(
            project_id=project_id,
            file_id=file_id,
            order=request.order,
            duration=request.duration,
        )
        db.add(asset)
        added_ids.append(asset.id)

    db.commit()

    logger.info(f"Added {len(added_ids)} images to project {project_id}")

    return AddImagesResponse(
        data={
            "added": added_ids,
            "project_images_count": len(project.images) + len(added_ids),
        }
    )


@router.delete("/projects/{project_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_image_from_project(
    project_id: str,
    image_id: str,
    db: Session = Depends(deps.get_db),
):
    """
    Remove an image from a project.
    """
    asset = db.query(ImageAsset).filter(
        ImageAsset.id == image_id,
        ImageAsset.project_id == project_id
    ).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "IMAGE_NOT_FOUND",
                "message": "圖片不存在於專案中",
            },
        )

    db.delete(asset)
    db.commit()

    logger.info(f"Removed image {image_id} from project {project_id}")

    return None


class AddAudioRequest(BaseModel):
    """Request to add audio to project."""
    file_ids: List[str]
    order: int = 0


@router.post("/projects/{project_id}/audio", response_model=AddAudioResponse)
async def add_audio_to_project(
    project_id: str,
    request: AddAudioRequest,
    db: Session = Depends(deps.get_db),
):
    """
    Add uploaded audio to a project.
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": "專案不存在",
            },
        )

    # Verify files exist and are audio
    added_ids = []
    for file_id in request.file_ids:
        file = db.query(FileModel).filter(
            FileModel.id == file_id,
            FileModel.file_type == "audio"
        ).first()

        if not file:
            continue

        # Check if already added
        existing = db.query(AudioAsset).filter(
            AudioAsset.project_id == project_id,
            AudioAsset.file_id == file_id
        ).first()

        if existing:
            continue

        # Create audio asset
        asset = AudioAsset(
            project_id=project_id,
            file_id=file_id,
            order=request.order,
        )
        db.add(asset)
        added_ids.append(asset.id)

    db.commit()

    logger.info(f"Added {len(added_ids)} audio tracks to project {project_id}")

    return AddAudioResponse(
        data={
            "added": added_ids,
            "project_audio_count": len(project.audio_tracks) + len(added_ids),
        }
    )


@router.delete("/projects/{project_id}/audio/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_audio_from_project(
    project_id: str,
    audio_id: str,
    db: Session = Depends(deps.get_db),
):
    """
    Remove an audio track from a project.
    """
    asset = db.query(AudioAsset).filter(
        AudioAsset.id == audio_id,
        AudioAsset.project_id == project_id
    ).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "AUDIO_NOT_FOUND",
                "message": "音訊不存在於專案中",
            },
        )

    db.delete(asset)
    db.commit()

    logger.info(f"Removed audio {audio_id} from project {project_id}")

    return None
