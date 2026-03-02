"""
快速渲染 API Router

提供無專案儲存的快速渲染功能：直接上傳圖片和音樂，開始渲染。
"""

import asyncio
import logging
import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from PIL import Image

from backend import deps
from backend.database.connection import SessionLocal
from backend.models.project import Project as ProjectModel
from backend.models.project import ProjectStatus
from backend.models.render_job import RenderJob as RenderJobModel
from backend.models.render_job import JobStatus
from backend.models.file import File as FileModel
from backend.models.image_asset import ImageAsset
from backend.models.audio_asset import AudioAsset
from backend.services.render_service import RenderService

logger = logging.getLogger(__name__)
router = APIRouter()


class QuickRenderResponse(BaseModel):
    """快速渲染回應"""
    job_id: str
    status: str
    estimated_duration: int
    webSocket_url: str


@router.post("/quick-render", status_code=status.HTTP_202_ACCEPTED)
async def quick_render(
    images: List[UploadFile] = File(..., description="圖片檔案（至少1張）"),
    audios: List[UploadFile] = File(default=[], description="音樂檔案（可多首）"),
    image_durations: str = Form("[]", description="每張圖片顯示時長的JSON陣列"),
    db: Session = Depends(deps.get_db),
):
    """
    快速渲染：直接上傳圖片和（可選）音樂，開始渲染Ken-Burns影片。
    """
    # 驗證圖片
    if not images or len(images) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_IMAGES", "message": "請上傳至少一張圖片"},
        )

    if len(images) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TOO_MANY_IMAGES", "message": "圖片數量不能超過50張"},
        )

    # 解析圖片時長
    import json
    try:
        durations = json.loads(image_durations) if image_durations else []
    except json.JSONDecodeError:
        durations = []

    # 驗證檔案類型
    allowed_image_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    allowed_audio_types = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/x-m4a", "audio/mp4"}

    # 上傳目錄
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    temp_project_id = str(uuid.uuid4())
    project_upload_dir = os.path.join(upload_dir, "temp", temp_project_id)
    os.makedirs(project_upload_dir, exist_ok=True)

    saved_images = []

    # 儲存圖片
    for i, img in enumerate(images):
        # 驗證類型
        content_type = img.content_type or ""
        if content_type not in allowed_image_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_IMAGE_TYPE", "message": f"不支援的圖片格式: {content_type}"},
            )

        # 生成檔案名
        ext = content_type.split("/")[-1]
        if ext == "jpeg":
            ext = "jpg"
        filename = f"image_{i}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(project_upload_dir, filename)

        # 儲存檔案
        content = await img.read()
        with open(filepath, "wb") as f:
            f.write(content)

        # 獲取圖片尺寸
        try:
            with Image.open(filepath) as im:
                width, height = im.size
        except Exception:
            width, height = 1920, 1080

        # 創建 File 記錄
        file_record = FileModel(
            id=str(uuid.uuid4()),
            file_type="image",
            original_filename=img.filename or f"image_{i}",
            stored_filename=filename,
            file_path=filepath,
            content_type=content_type,
            size=len(content),
            width=width,
            height=height,
            status="ready",
        )
        db.add(file_record)
        saved_images.append({
            "file": file_record,
            "duration": durations[i] if i < len(durations) else 5.0,
        })

    db.commit()

    # 處理音樂（可選，支援多首）
    audio_records = []
    audio_duration = 0.0

    for audio in audios:
        content_type = audio.content_type or ""
        if content_type not in allowed_audio_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_AUDIO_TYPE", "message": f"不支援的音樂格式: {content_type}"},
            )

        # 儲存音樂
        ext = content_type.split("/")[-1]
        if ext == "x-m4a":
            ext = "m4a"
        audio_filename = f"audio_{uuid.uuid4().hex[:8]}.{ext}"
        audio_filepath = os.path.join(project_upload_dir, audio_filename)

        audio_content = await audio.read()
        with open(audio_filepath, "wb") as f:
            f.write(audio_content)

        # 創建 File 記錄
        audio_record = FileModel(
            id=str(uuid.uuid4()),
            file_type="audio",
            original_filename=audio.filename or "audio",
            stored_filename=audio_filename,
            file_path=audio_filepath,
            content_type=content_type,
            size=len(audio_content),
            status="ready",
        )
        db.add(audio_record)

        # 獲取音樂時長
        try:
            from pydub import AudioSegment
            audio_seg = AudioSegment.from_file(audio_filepath)
            dur = len(audio_seg) / 1000.0  # 毫秒轉秒
            audio_record.duration = dur
            audio_duration += dur
        except Exception as e:
            logger.warning(f"無法獲取音樂時長: {e}")
            audio_record.duration = 60.0
            audio_duration += 60.0  # 預設60秒

        audio_records.append(audio_record)

    if audio_records:
        db.commit()

    # 創建臨時專案
    project = ProjectModel(
        id=temp_project_id,
        name=f"Quick Render {temp_project_id[:8]}",
        description="快速渲染任務",
        status=ProjectStatus.PROCESSING,
    )
    db.add(project)
    db.commit()

    # 計算圖片時長
    if audio_duration > 0 and saved_images:
        # 根據音樂時長均分給每張圖片
        per_image_duration = audio_duration / len(saved_images)
        for img_data in saved_images:
            img_data["duration"] = per_image_duration
        total_duration = audio_duration
    else:
        total_duration = sum(img["duration"] for img in saved_images)

    # 創建 ImageAsset 記錄
    for i, img_data in enumerate(saved_images):
        asset = ImageAsset(
            id=str(uuid.uuid4()),
            project_id=project.id,
            file_id=img_data["file"].id,
            order=i,
            duration=img_data["duration"],
        )
        db.add(asset)

    # 創建 AudioAsset 記錄（支援多首）
    for i, audio_record in enumerate(audio_records):
        audio_asset = AudioAsset(
            id=str(uuid.uuid4()),
            project_id=project.id,
            file_id=audio_record.id,
            order=i,
        )
        db.add(audio_asset)

    db.commit()

    # 創建渲染任務
    render_service = RenderService(db)
    job = await render_service.create_render_job(project)

    job_id = job.id
    project_id = project.id

    logger.info(f"快速渲染任務已建立: job_id={job_id}, images={len(saved_images)}, audio_duration={audio_duration}s")

    # 在背景啟動渲染（使用獨立的 DB session）
    async def _run_render_in_background():
        bg_db = SessionLocal()
        try:
            bg_project = bg_db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
            if not bg_project:
                logger.error(f"背景渲染找不到專案: {project_id}")
                return
            bg_service = RenderService(bg_db)
            await bg_service.start_render(job_id, bg_project)
        except Exception as e:
            logger.error(f"背景渲染異常: {e}", exc_info=True)
        finally:
            bg_db.close()

    asyncio.create_task(_run_render_in_background())

    # 計算預估時間
    estimated_duration = int(total_duration * 1.5)

    return QuickRenderResponse(
        job_id=job_id,
        status="queued",
        estimated_duration=estimated_duration,
        webSocket_url=f"/ws/render/{job_id}",
    )


@router.get("/quick-render/status/{job_id}")
async def get_quick_render_status(
    job_id: str,
    db: Session = Depends(deps.get_db),
):
    """獲取快速渲染任務狀態"""
    job = db.query(RenderJobModel).filter(RenderJobModel.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "任務不存在"},
        )

    response = {
        "job_id": job.id,
        "status": job.status.value,
        "progress": job.progress,
    }

    if job.status == JobStatus.COMPLETED:
        response["output_path"] = job.output_path
        response["output_url"] = f"/api/v1/render/download/{job.id}"

    return response
