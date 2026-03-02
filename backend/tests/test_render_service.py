"""
RenderService 測試

測試渲染服務
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from sqlalchemy.orm import Session

from backend.services.render_service import RenderService
from backend.models.project import Project as ProjectModel
from backend.models.project import ProjectStatus
from backend.models.render_job import RenderJob as RenderJobModel
from backend.models.render_job import JobStatus, RenderStage
from backend.models.image_asset import ImageAsset as ImageAssetModel


class TestRenderService:
    """RenderService 測試"""

    @pytest.fixture
    def mock_db(self):
        """建立 mock 資料庫"""
        db = MagicMock(spec=Session)
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()
        return db

    @pytest.fixture
    def render_service(self, mock_db, tmp_path):
        """建立 RenderService 實例"""
        with patch("backend.services.render_service.os.makedirs"):
            service = RenderService(mock_db)
            service.output_dir = str(tmp_path / "output")
            return service

    @pytest.fixture
    def mock_project(self):
        """建立 mock 專案"""
        project = MagicMock(spec=ProjectModel)
        project.id = "project-123"
        project.status = ProjectStatus.DRAFT
        project.fps = MagicMock()
        project.fps.value = 30  # 整數

        # 建立 mock 圖片
        image1 = MagicMock(spec=ImageAssetModel)
        image1.duration = 5.0

        image2 = MagicMock(spec=ImageAssetModel)
        image2.duration = 3.0

        project.images = [image1, image2]

        return project

    @pytest.mark.asyncio
    async def test_create_render_job(self, render_service, mock_db, mock_project):
        """測試建立渲染任務"""
        result = await render_service.create_render_job(mock_project)

        # 驗證任務建立
        assert result.project_id == "project-123"
        assert result.status == JobStatus.QUEUED
        assert result.progress == 0

        # 驗證專案狀態更新
        assert mock_project.status == ProjectStatus.PROCESSING

        # 驗證資料庫操作
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_render_job_calculates_frames(self, render_service, mock_db, mock_project):
        """測試計算總幀數"""
        result = await render_service.create_render_job(mock_project)

        # 30 fps * (5.0 + 3.0) 秒 = 240 幀
        expected_frames = 30 * (5.0 + 3.0)
        assert result.total_frames == expected_frames

    def test_get_job(self, render_service, mock_db):
        """測試取得任務"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = render_service.get_job("job-123")

        mock_db.query.assert_called()
        assert result is None

    def test_get_jobs_by_project(self, render_service, mock_db):
        """測試依專案取得任務"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = render_service.get_jobs_by_project("project-123")

        mock_db.query.assert_called()
        assert isinstance(result, list)

    def test_cancel_job_success(self, render_service, mock_db):
        """測試取消任務"""
        # 建立 mock 任務
        job = MagicMock(spec=RenderJobModel)
        job.id = "job-123"
        job.status = JobStatus.QUEUED

        # 建立 mock 專案
        project = MagicMock(spec=ProjectModel)
        job.project = project

        mock_db.query.return_value.filter.return_value.first.return_value = job

        result = render_service.cancel_job("job-123")

        assert result is True
        assert job.status == JobStatus.CANCELLED
        mock_db.commit.assert_called()

    def test_cancel_job_not_found(self, render_service, mock_db):
        """測試取消不存在的任務"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = render_service.cancel_job("nonexistent")

        assert result is False

    def test_cancel_job_already_finished(self, render_service, mock_db):
        """測試取消已完成的任務"""
        job = MagicMock(spec=RenderJobModel)
        job.status = JobStatus.COMPLETED

        mock_db.query.return_value.filter.return_value.first.return_value = job

        result = render_service.cancel_job("job-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_start_render_job_not_found(self, render_service, mock_db, mock_project):
        """測試開始不存在的任務"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        await render_service.start_render("nonexistent", mock_project)

        # 驗證沒有錯誤且任務狀態未改變
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要完整模擬 render 流程較複雜")
    async def test_start_render_success_full(self, render_service, mock_db, mock_project):
        """測試開始渲染（完整流程）"""
        job = MagicMock(spec=RenderJobModel)
        job.id = "job-123"
        job.status = JobStatus.QUEUED
        job.progress = 0
        job.current_stage = RenderStage.PREPARING
        job.total_frames = 240
        job.current_frame = 0
        job.eta_seconds = 0

        mock_db.query.return_value.filter.return_value.first.return_value = job

        with patch("backend.routers.websocket.broadcast_job_status", new_callable=AsyncMock):
            with patch("backend.routers.websocket.broadcast_job_progress", new_callable=AsyncMock):
                with patch("backend.routers.websocket.broadcast_job_complete", new_callable=AsyncMock):
                    with patch("asyncio.sleep", new_callable=AsyncMock):
                        await render_service.start_render("job-123", mock_project)

        assert job.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_start_render_job_not_found(self, render_service, mock_db, mock_project):
        """測試開始不存在的任務"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        await render_service.start_render("nonexistent", mock_project)

        # 驗證沒有錯誤且任務狀態未改變
        mock_db.commit.assert_not_called()
