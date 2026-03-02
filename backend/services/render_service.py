"""
Render Service

Handles render job creation, management, and progress tracking.
Uses FFmpeg for actual Ken-Burns video rendering.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from backend.models.project import Project as ProjectModel
from backend.models.project import ProjectStatus
from backend.models.render_job import RenderJob as RenderJobModel
from backend.models.render_job import JobStatus, RenderStage
from backend.services.ffmpeg_renderer import FFmpegRenderer

logger = logging.getLogger(__name__)

# 解析度對照表
RESOLUTION_MAP = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4k": (3840, 2160),
}

# 全域活躍渲染器，用於取消時終止 FFmpeg 進程
_active_renderers: Dict[str, FFmpegRenderer] = {}


class RenderService:
    """Service for managing render jobs."""

    def __init__(self, db: Session):
        self.db = db
        self.output_dir = os.path.abspath(os.getenv("OUTPUT_DIR", "./output"))
        os.makedirs(self.output_dir, exist_ok=True)

    async def create_render_job(self, project: ProjectModel) -> RenderJobModel:
        """
        Create a new render job for a project.

        Args:
            project: Project to create job for

        Returns:
            RenderJobModel: Created job
        """
        # Generate job ID
        job_id = str(uuid.uuid4())

        # Calculate total frames
        total_frames = 0
        fps_value = int(project.fps.value)  # FrameRate enum value is a string
        for image in project.images:
            total_frames += int(image.duration * fps_value)

        # Create job
        job = RenderJobModel(
            id=job_id,
            project_id=project.id,
            status=JobStatus.QUEUED,
            progress=0,
            current_stage=RenderStage.PREPARING,
            total_frames=total_frames,
        )

        # Update project status
        project.status = ProjectStatus.PROCESSING

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        logger.info(f"Created render job {job_id} for project {project.id}")

        return job

    async def start_render(self, job_id: str, project: ProjectModel):
        """
        啟動 FFmpeg Ken-Burns 渲染流程

        Args:
            job_id: 任務 ID
            project: 專案
        """
        from backend.routers.websocket import (
            broadcast_job_complete,
            broadcast_job_error,
            broadcast_job_status,
        )

        job = self.db.query(RenderJobModel).filter(RenderJobModel.id == job_id).first()

        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = JobStatus.PREPARING
        job.started_at = datetime.utcnow()
        self.db.commit()

        await broadcast_job_status(job_id, "preparing", "準備渲染")

        try:
            await self._render_with_ffmpeg(job, project)
        except Exception as e:
            logger.error(f"Render failed for job {job_id}: {e}", exc_info=True)
            job.status = JobStatus.FAILED
            job.error_code = "RENDER_FAILED"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            self.db.commit()

            await broadcast_job_error(job_id, str(e), "RENDER_FAILED")
            return
        finally:
            _active_renderers.pop(job_id, None)

        # 檢查是否在渲染過程中被取消
        self.db.refresh(job)
        if job.status == JobStatus.CANCELLED:
            logger.info(f"Job {job_id} was cancelled during rendering, skipping completion")
            return

        # 渲染成功
        output_path = os.path.join(self.output_dir, f"{project.id}.mp4")
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.utcnow()
        job.output_path = output_path
        if os.path.exists(output_path):
            job.output_size = os.path.getsize(output_path)
        self.db.commit()

        project.status = ProjectStatus.COMPLETED
        self.db.commit()

        await broadcast_job_complete(
            job_id,
            output_path=job.output_path,
            file_size=job.output_size,
            duration=job.output_duration,
        )

        logger.info(f"Render completed for job {job_id}")

    async def _render_with_ffmpeg(self, job: RenderJobModel, project: ProjectModel):
        """使用 FFmpeg 進行實際 Ken-Burns 渲染"""
        from backend.routers.websocket import broadcast_job_progress
        from backend.services.kenburns_service import KenBurnsService

        fps_value = int(project.fps.value)
        width, height = RESOLUTION_MAP.get(project.resolution.value, (1920, 1080))

        def _is_cancelled() -> bool:
            self.db.refresh(job)
            return job.status == JobStatus.CANCELLED

        # === 階段 1: 載入圖片 ===
        job.current_stage = RenderStage.LOADING_IMAGES
        job.progress = 5
        self.db.commit()
        await broadcast_job_progress(
            job_id=job.id, progress=5,
            stage="loading_images", stage_label="載入圖片", stage_percentage=0,
        )

        image_paths = []
        for img_asset in project.images:
            if img_asset.file and img_asset.file.file_path:
                image_paths.append(img_asset.file.file_path)

        if not image_paths:
            raise RuntimeError("找不到任何圖片檔案")

        logger.info(f"載入 {len(image_paths)} 張圖片")

        if _is_cancelled():
            return

        # === 階段 2: 處理音訊 ===
        job.current_stage = RenderStage.PROCESSING_AUDIO
        job.progress = 10
        self.db.commit()
        await broadcast_job_progress(
            job_id=job.id, progress=10,
            stage="processing_audio", stage_label="處理音訊", stage_percentage=0,
        )

        audio_paths = []
        for audio_asset in project.audio_tracks:
            if audio_asset.file and audio_asset.file.file_path:
                audio_paths.append(audio_asset.file.file_path)

        # BPM 分析
        bpm = 120.0
        total_audio_duration = 0.0

        if audio_paths:
            kenburns = KenBurnsService()
            try:
                bpm_analysis = kenburns.analyze_music(audio_paths[0])
                bpm = bpm_analysis.bpm
                total_audio_duration = bpm_analysis.duration
                # 如果有多首音訊，加總時長
                for ap in audio_paths[1:]:
                    extra = kenburns.analyze_music(ap)
                    total_audio_duration += extra.duration
                logger.info(f"BPM 分析結果: {bpm:.1f}, 總音訊時長: {total_audio_duration:.1f}s")
            except Exception as e:
                logger.warning(f"BPM 分析失敗，使用預設值: {e}")
                bpm = 120.0

        await broadcast_job_progress(
            job_id=job.id, progress=15,
            stage="processing_audio", stage_label="處理音訊",
            stage_percentage=100,
        )

        if _is_cancelled():
            return

        # === 階段 3: 生成路徑 ===
        job.current_stage = RenderStage.GENERATING_PATHS
        job.progress = 20
        self.db.commit()
        await broadcast_job_progress(
            job_id=job.id, progress=20,
            stage="generating_paths", stage_label="生成 Ken-Burns 路徑",
            stage_percentage=0,
        )

        # 計算總時長
        if total_audio_duration > 0:
            total_duration = total_audio_duration
        else:
            total_duration = sum(img.duration for img in project.images)

        total_frames = int(total_duration * fps_value)
        job.total_frames = total_frames
        job.output_duration = total_duration
        self.db.commit()

        # 建立 FFmpeg 渲染器
        renderer = FFmpegRenderer(output_width=width, output_height=height, fps=fps_value)
        _active_renderers[job.id] = renderer

        # 偵測編碼器
        encoder = await renderer.detect_encoder()

        await broadcast_job_progress(
            job_id=job.id, progress=25,
            stage="generating_paths", stage_label="生成 Ken-Burns 路徑",
            stage_percentage=100,
        )

        if _is_cancelled():
            return

        # === 階段 4: 渲染 + 編碼 ===
        job.current_stage = RenderStage.ENCODING_VIDEO
        job.progress = 30
        self.db.commit()
        await broadcast_job_progress(
            job_id=job.id, progress=30,
            stage="encoding_video", stage_label="FFmpeg 渲染中",
            stage_percentage=0,
        )

        output_path = os.path.join(self.output_dir, f"{project.id}.mp4")
        os.makedirs(self.output_dir, exist_ok=True)

        # 構建 FFmpeg 命令
        cmd = renderer.build_command(
            image_paths=image_paths,
            audio_paths=audio_paths,
            output_path=output_path,
            bpm=bpm,
            total_duration=total_duration,
            encoder=encoder,
        )

        # 進度回調
        async def on_progress(progress_pct: int, current_time: float):
            # 將 FFmpeg 進度映射到 30%-95% 區間
            mapped = 30 + int(progress_pct * 0.65)
            job.progress = mapped
            job.current_frame = int(current_time * fps_value)
            eta = int((total_duration - current_time) * 1.2) if current_time > 0 else 0
            job.eta_seconds = max(0, eta)
            self.db.commit()
            await broadcast_job_progress(
                job_id=job.id,
                progress=mapped,
                current_frame=job.current_frame,
                total_frames=total_frames,
                fps=float(fps_value),
                eta_seconds=job.eta_seconds,
                stage="encoding_video",
                stage_label=f"FFmpeg 渲染中 ({progress_pct}%)",
                stage_percentage=progress_pct,
            )

        # 執行 FFmpeg
        success = await renderer.execute(
            cmd=cmd,
            total_duration=total_duration,
            progress_callback=on_progress,
            cancel_check=_is_cancelled,
        )

        if not success:
            return

        # === 階段 5: 完成 ===
        job.current_stage = RenderStage.FINALIZING
        job.progress = 98
        self.db.commit()
        await broadcast_job_progress(
            job_id=job.id, progress=98,
            stage="finalizing", stage_label="完成中",
            stage_percentage=50,
        )

        # 更新輸出資訊
        job.output_path = output_path
        job.output_duration = total_duration
        if os.path.exists(output_path):
            job.output_size = os.path.getsize(output_path)
        self.db.commit()

    def get_job(self, job_id: str) -> Optional[RenderJobModel]:
        """Get render job by ID."""
        return self.db.query(RenderJobModel).filter(RenderJobModel.id == job_id).first()

    def get_jobs_by_project(self, project_id: str) -> list:
        """Get all jobs for a project."""
        return self.db.query(RenderJobModel).filter(
            RenderJobModel.project_id == project_id
        ).order_by(RenderJobModel.created_at.desc()).all()

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a render job."""
        job = self.get_job(job_id)

        if not job:
            return False

        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        self.db.commit()

        # 終止活躍的 FFmpeg 進程
        renderer = _active_renderers.pop(job_id, None)
        if renderer:
            renderer.terminate()
            logger.info(f"已終止 job {job_id} 的 FFmpeg 進程")

        # Update project status
        project = job.project
        if project:
            project.status = ProjectStatus.DRAFT
            self.db.commit()

        logger.info(f"Cancelled job {job_id}")

        return True
