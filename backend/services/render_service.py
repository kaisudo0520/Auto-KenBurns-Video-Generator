"""
Render Service

Handles render job creation, management, and progress tracking.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.project import Project as ProjectModel
from backend.models.project import ProjectStatus
from backend.models.render_job import RenderJob as RenderJobModel
from backend.models.render_job import JobStatus, RenderStage

logger = logging.getLogger(__name__)


class RenderService:
    """Service for managing render jobs."""

    def __init__(self, db: Session):
        self.db = db
        self.output_dir = os.getenv("OUTPUT_DIR", "./output")
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
        Start the render process (simulated).

        In production, this would queue to a proper task runner.

        Args:
            job_id: Job ID to start
            project: Project being rendered
        """
        # 延遲導入避免循環依賴
        from backend.routers.websocket import (
            broadcast_job_complete,
            broadcast_job_error,
            broadcast_job_progress,
            broadcast_job_status,
        )

        job = self.db.query(RenderJobModel).filter(RenderJobModel.id == job_id).first()

        if not job:
            logger.error(f"Job {job_id} not found")
            return

        # Update job status
        job.status = JobStatus.PREPARING
        job.started_at = datetime.utcnow()
        self.db.commit()

        # Broadcast status
        await broadcast_job_status(job_id, "preparing", "準備渲染")

        # Simulate render process (in production, this would be handled by a task runner)
        try:
            await self._simulate_render(job, project)
        except Exception as e:
            logger.error(f"Render failed for job {job_id}: {e}")
            job.status = JobStatus.FAILED
            job.error_code = "RENDER_FAILED"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            self.db.commit()

            await broadcast_job_error(job_id, str(e), "RENDER_FAILED")
            return

        # Job completed successfully
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.utcnow()
        job.output_path = os.path.join(self.output_dir, f"{project.id}.mp4")
        self.db.commit()

        # Update project status
        project.status = ProjectStatus.COMPLETED
        self.db.commit()

        # Broadcast completion
        await broadcast_job_complete(
            job_id,
            output_path=job.output_path,
            file_size=job.output_size,
            duration=job.output_duration,
        )

        logger.info(f"Render completed for job {job_id}")

    async def _simulate_render(self, job: RenderJobModel, project: ProjectModel):
        """
        Simulate the render process.

        In production, this would call the actual rendering engine.
        """
        # 延遲導入避免循環依賴
        from backend.routers.websocket import (
            broadcast_job_progress,
        )

        # Get fps value - FrameRate enum value is a string
        fps_value = int(project.fps.value)

        stages = [
            (RenderStage.PREPARING, 5, "準備階段"),
            (RenderStage.LOADING_IMAGES, 10, "載入圖片"),
            (RenderStage.DETECTING_SUBJECTS, 20, "偵測主體"),
            (RenderStage.GENERATING_PATHS, 10, "生成路徑"),
            (RenderStage.PROCESSING_AUDIO, 15, "處理音訊"),
            (RenderStage.RENDERING_FRAMES, 30, "渲染幀"),
            (RenderStage.ENCODING_VIDEO, 8, "編碼影片"),
            (RenderStage.FINALIZING, 2, "完成階段"),
        ]

        total_images = len(project.images)

        for stage, weight, label in stages:
            job.current_stage = stage
            job.progress = 0
            self.db.commit()

            await broadcast_job_progress(
                job_id=job.id,
                progress=0,
                stage=stage.value,
                stage_label=label,
                stage_percentage=0,
            )

            # Simulate stage work
            if stage == RenderStage.RENDERING_FRAMES:
                # Simulate rendering each image
                for i, image in enumerate(project.images):
                    image_progress = int(100 * (i + 1) / total_images)

                    # Update job progress
                    job.current_frame = int(i * image.duration * fps_value)
                    job.progress = 50 + int(30 * (i + 1) / total_images)
                    job.eta_seconds = int((total_images - i - 1) * image.duration * 1.5)
                    self.db.commit()

                    await broadcast_job_progress(
                        job_id=job.id,
                        progress=job.progress,
                        current_frame=job.current_frame,
                        total_frames=job.total_frames,
                        fps=30.0,
                        eta_seconds=job.eta_seconds,
                        stage=stage.value,
                        stage_label=f"處理第 {i + 1} 張圖片 / 共 {total_images} 張",
                        stage_percentage=image_progress,
                    )

                    # Simulate work
                    await asyncio.sleep(0.5)
            else:
                # Simulate other stages
                for p in range(0, 101, 10):
                    job.progress = job.progress + int(weight * 0.1)
                    self.db.commit()

                    await broadcast_job_progress(
                        job_id=job.id,
                        progress=job.progress,
                        stage=stage.value,
                        stage_label=label,
                        stage_percentage=p,
                    )

                    await asyncio.sleep(0.2)

        # Finalize output
        job.output_size = 15000000  # Placeholder
        job.output_duration = sum(img.duration for img in project.images)
        job.output_path = os.path.join(self.output_dir, f"{project.id}.mp4")

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

        # Update project status
        project = job.project
        if project:
            project.status = ProjectStatus.DRAFT
            self.db.commit()

        logger.info(f"Cancelled job {job_id}")

        return True
