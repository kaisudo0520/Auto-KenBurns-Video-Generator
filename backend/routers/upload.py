"""
Upload API Router

Handles file upload operations for images and audio files.
"""

import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import deps
from backend.models.file import File as FileModel
from backend.models.file import FileStatus, FileType
from backend.schemas.file import (
    AudioFileResponse,
    FileResponse,
    ImageFileResponse,
)
from backend.services.file_service import FileService

logger = logging.getLogger(__name__)
router = APIRouter()

# Allowed file types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/wav", "audio/aac", "audio/flac", "audio/ogg"}

# File size limits (bytes)
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100 MB


# Response models
class UploadSuccessResponse(BaseModel):
    """Successful upload response."""
    success: bool = True
    data: dict


class BatchUploadItem(BaseModel):
    """Item in batch upload response."""
    file_id: Optional[str] = None
    filename: str
    status: str
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """Batch upload response."""
    success: bool = True
    data: dict


# ========================================
# Image Upload Endpoints
# ========================================

@router.post("/upload/image", response_model=ImageFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    project_id: Optional[str] = None,
    db: Session = Depends(deps.get_db),
):
    """
    Upload a single image file.

    Supported formats: JPEG, PNG, WebP, BMP
    Max size: 50 MB
    """
    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": "不支持的文件類型",
                "details": {
                    "allowed_types": list(ALLOWED_IMAGE_TYPES),
                    "received_type": file.content_type,
                },
            },
        )

    # Read file content to check size
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": "檔案大小超過限制",
                "details": {
                    "max_size": MAX_IMAGE_SIZE,
                    "received_size": len(content),
                },
            },
        )

    # Process and save file
    try:
        file_service = FileService(db)
        file_record = await file_service.save_image(
            content=content,
            filename=file.filename,
            content_type=file.content_type,
            project_id=project_id,
        )

        return ImageFileResponse(
            file_id=file_record.id,
            filename=file_record.original_filename,
            content_type=file_record.content_type,
            size=file_record.size,
            width=file_record.width or 0,
            height=file_record.height or 0,
            uploaded_at=file_record.created_at,
            status=file_record.status,
        )

    except Exception as e:
        logger.error(f"Failed to upload image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "UPLOAD_FAILED",
                "message": "上傳失敗，請重試",
            },
        )


@router.post("/upload/images", response_model=BatchUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_images(
    files: List[UploadFile] = File(...),
    project_id: Optional[str] = None,
    db: Session = Depends(deps.get_db),
):
    """
    Upload multiple image files in batch.

    Supported formats: JPEG, PNG, WebP, BMP
    Max size: 50 MB per file
    """
    uploaded_items: List[BatchUploadItem] = []
    failed_items: List[BatchUploadItem] = []

    file_service = FileService(db)

    for file in files:
        try:
            # Validate file type
            if file.content_type not in ALLOWED_IMAGE_TYPES:
                failed_items.append(BatchUploadItem(
                    filename=file.filename,
                    status="failed",
                    error="INVALID_FILE_TYPE",
                ))
                continue

            # Read and validate file size
            content = await file.read()
            if len(content) > MAX_IMAGE_SIZE:
                failed_items.append(BatchUploadItem(
                    filename=file.filename,
                    status="failed",
                    error="FILE_TOO_LARGE",
                ))
                continue

            # Save file
            file_record = await file_service.save_image(
                content=content,
                filename=file.filename,
                content_type=file.content_type,
                project_id=project_id,
            )

            uploaded_items.append(BatchUploadItem(
                file_id=file_record.id,
                filename=file.filename,
                status="success",
            ))

        except Exception as e:
            logger.error(f"Failed to upload image {file.filename}: {e}")
            failed_items.append(BatchUploadItem(
                filename=file.filename,
                status="failed",
                error="UPLOAD_FAILED",
            ))

    return BatchUploadResponse(
        data={
            "uploaded": uploaded_items,
            "failed": failed_items,
        }
    )


# ========================================
# Audio Upload Endpoints
# ========================================

@router.post("/upload/audio", response_model=AudioFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    file: UploadFile = File(...),
    project_id: Optional[str] = None,
    db: Session = Depends(deps.get_db),
):
    """
    Upload a single audio file.

    Supported formats: MP3, WAV, AAC, FLAC, OGG
    Max size: 100 MB
    """
    # Validate file type
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": "不支持的檔案類型",
                "details": {
                    "allowed_types": list(ALLOWED_AUDIO_TYPES),
                    "received_type": file.content_type,
                },
            },
        )

    # Read file content to check size
    content = await file.read()
    if len(content) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": "檔案大小超過限制",
                "details": {
                    "max_size": MAX_AUDIO_SIZE,
                    "received_size": len(content),
                },
            },
        )

    # Process and save file
    try:
        file_service = FileService(db)
        file_record = await file_service.save_audio(
            content=content,
            filename=file.filename,
            content_type=file.content_type,
            project_id=project_id,
        )

        return AudioFileResponse(
            file_id=file_record.id,
            filename=file_record.original_filename,
            content_type=file_record.content_type,
            size=file_record.size,
            duration=file_record.duration or 0.0,
            sample_rate=file_record.sample_rate or 0,
            loudness=file_record.loudness or 0.0,
            uploaded_at=file_record.created_at,
            status=file_record.status,
        )

    except Exception as e:
        logger.error(f"Failed to upload audio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "UPLOAD_FAILED",
                "message": "上傳失敗，請重試",
            },
        )


@router.post("/upload/audios", response_model=BatchUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_audios(
    files: List[UploadFile] = File(...),
    project_id: Optional[str] = None,
    db: Session = Depends(deps.get_db),
):
    """
    Upload multiple audio files in batch.

    Supported formats: MP3, WAV, AAC, FLAC, OGG
    Max size: 100 MB per file
    """
    uploaded_items: List[BatchUploadItem] = []
    failed_items: List[BatchUploadItem] = []

    file_service = FileService(db)

    for file in files:
        try:
            # Validate file type
            if file.content_type not in ALLOWED_AUDIO_TYPES:
                failed_items.append(BatchUploadItem(
                    filename=file.filename,
                    status="failed",
                    error="INVALID_FILE_TYPE",
                ))
                continue

            # Read and validate file size
            content = await file.read()
            if len(content) > MAX_AUDIO_SIZE:
                failed_items.append(BatchUploadItem(
                    filename=file.filename,
                    status="failed",
                    error="FILE_TOO_LARGE",
                ))
                continue

            # Save file
            file_record = await file_service.save_audio(
                content=content,
                filename=file.filename,
                content_type=file.content_type,
                project_id=project_id,
            )

            uploaded_items.append(BatchUploadItem(
                file_id=file_record.id,
                filename=file.filename,
                status="success",
            ))

        except Exception as e:
            logger.error(f"Failed to upload audio {file.filename}: {e}")
            failed_items.append(BatchUploadItem(
                filename=file.filename,
                status="failed",
                error="UPLOAD_FAILED",
            ))

    return BatchUploadResponse(
        data={
            "uploaded": uploaded_items,
            "failed": failed_items,
        }
    )


# ========================================
# File Status and Delete Endpoints
# ========================================

@router.get("/upload/{file_id}", response_model=FileResponse)
async def get_upload_status(
    file_id: str,
    db: Session = Depends(deps.get_db),
):
    """Get upload status for a file."""
    file_record = db.query(FileModel).filter(FileModel.id == file_id).first()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "FILE_NOT_FOUND",
                "message": "檔案不存在",
            },
        )

    return FileResponse(
        id=file_record.id,
        file_type=file_record.file_type,
        original_filename=file_record.original_filename,
        stored_filename=file_record.stored_filename,
        file_path=file_record.file_path,
        content_type=file_record.content_type,
        size=file_record.size,
        width=file_record.width,
        height=file_record.height,
        duration=file_record.duration,
        sample_rate=file_record.sample_rate,
        loudness=file_record.loudness,
        status=file_record.status,
        error_message=file_record.error_message,
        created_at=file_record.created_at,
        processed_at=file_record.processed_at,
    )


@router.delete("/upload/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    db: Session = Depends(deps.get_db),
):
    """Delete an uploaded file."""
    file_record = db.query(FileModel).filter(FileModel.id == file_id).first()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "FILE_NOT_FOUND",
                "message": "檔案不存在",
            },
        )

    # Delete physical file
    try:
        if os.path.exists(file_record.file_path):
            os.remove(file_record.file_path)
    except Exception as e:
        logger.warning(f"Failed to delete physical file: {e}")

    # Delete database record
    db.delete(file_record)
    db.commit()

    return None
