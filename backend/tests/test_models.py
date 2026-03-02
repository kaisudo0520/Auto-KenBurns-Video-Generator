"""
Models 測試

測試資料模型
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.connection import Base
from backend.models.project import Project
from backend.models.file import File, FileType, FileStatus
from backend.models.image_asset import ImageAsset
from backend.models.audio_asset import AudioAsset
from backend.models.render_job import RenderJob, JobStatus, RenderStage
from backend.models.settings import Settings


class TestModels:
    """Models 測試"""

    @pytest.fixture
    def engine(self):
        """建立測試用 engine"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=engine)
        return engine

    @pytest.fixture
    def db_session(self, engine):
        """建立測試用資料庫 session"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_create_project(self, db_session):
        """測試建立專案"""
        project = Project(
            id="project-1",
            name="Test Project",
            description="Test Description",
            status="draft"
        )
        db_session.add(project)
        db_session.commit()

        result = db_session.query(Project).filter(Project.id == "project-1").first()
        assert result.name == "Test Project"
        assert result.status == "draft"

    def test_project_default_values(self, db_session):
        """測試專案預設值"""
        project = Project(
            id="project-2",
            name="Test"
        )
        db_session.add(project)
        db_session.commit()

        result = db_session.query(Project).filter(Project.id == "project-2").first()
        assert result.status == "draft"
        assert result.fps == "30"

    def test_create_file(self, db_session):
        """測試建立檔案"""
        file = File(
            id="file-1",
            file_type=FileType.IMAGE,
            original_filename="test.jpg",
            stored_filename="abc123.jpg",
            file_path="/path/to/file",
            content_type="image/jpeg",
            size=1024,
            status=FileStatus.READY
        )
        db_session.add(file)
        db_session.commit()

        result = db_session.query(File).filter(File.id == "file-1").first()
        assert result.original_filename == "test.jpg"
        assert result.file_type == FileType.IMAGE

    def test_create_image_asset(self, db_session):
        """測試建立圖片資源"""
        # 先建立專案和檔案
        project = Project(id="proj-1", name="Test", status="draft")
        file = File(
            id="file-1",
            file_type=FileType.IMAGE,
            original_filename="test.jpg",
            stored_filename="test.jpg",
            file_path="/test.jpg",
            content_type="image/jpeg",
            size=100,
            status=FileStatus.READY
        )
        db_session.add_all([project, file])
        db_session.commit()

        image = ImageAsset(
            id="img-1",
            project_id="proj-1",
            file_id="file-1",
            order=0,
            duration=5.0
        )
        db_session.add(image)
        db_session.commit()

        result = db_session.query(ImageAsset).filter(ImageAsset.id == "img-1").first()
        assert result.duration == 5.0
        assert result.order == 0

    def test_create_audio_asset(self, db_session):
        """測試建立音訊資源"""
        project = Project(id="proj-1", name="Test", status="draft")
        file = File(
            id="file-1",
            file_type=FileType.AUDIO,
            original_filename="test.mp3",
            stored_filename="test.mp3",
            file_path="/test.mp3",
            content_type="audio/mpeg",
            size=1000,
            status=FileStatus.READY
        )
        db_session.add_all([project, file])
        db_session.commit()

        audio = AudioAsset(
            id="audio-1",
            project_id="proj-1",
            file_id="file-1",
            order=0,
            volume=1.0
        )
        db_session.add(audio)
        db_session.commit()

        result = db_session.query(AudioAsset).filter(AudioAsset.id == "audio-1").first()
        assert result.volume == 1.0

    def test_create_render_job(self, db_session):
        """測試建立渲染任務"""
        project = Project(id="proj-1", name="Test", status="draft")
        db_session.add(project)
        db_session.commit()

        job = RenderJob(
            id="job-1",
            project_id="proj-1",
            status=JobStatus.QUEUED,
            progress=0,
            current_stage=RenderStage.PREPARING,
            total_frames=100
        )
        db_session.add(job)
        db_session.commit()

        result = db_session.query(RenderJob).filter(RenderJob.id == "job-1").first()
        assert result.status == JobStatus.QUEUED
        assert result.progress == 0

    def test_render_job_status_transitions(self, db_session):
        """測試任務狀態轉換"""
        project = Project(id="proj-1", name="Test", status="draft")
        db_session.add(project)
        db_session.commit()

        job = RenderJob(
            id="job-1",
            project_id="proj-1",
            status=JobStatus.QUEUED,
            progress=0,
            current_stage=RenderStage.PREPARING,
            total_frames=100
        )
        db_session.add(job)
        db_session.commit()

        # 更新狀態
        job.status = JobStatus.RENDERING
        job.progress = 50
        db_session.commit()

        result = db_session.query(RenderJob).filter(RenderJob.id == "job-1").first()
        assert result.status == JobStatus.RENDERING
        assert result.progress == 50

    def test_create_settings(self, db_session):
        """測試建立設定"""
        setting = Settings(
            id="setting-1",
            key="max_upload_size",
            value="100MB",
            value_type="string",
            is_system=False
        )
        db_session.add(setting)
        db_session.commit()

        result = db_session.query(Settings).filter(Settings.key == "max_upload_size").first()
        assert result.value == "100MB"

    def test_project_relationships(self, db_session):
        """測試專案關聯"""
        project = Project(id="proj-1", name="Test", status="draft")
        db_session.add(project)
        db_session.commit()

        file = File(
            id="file-1",
            file_type=FileType.IMAGE,
            original_filename="test.jpg",
            stored_filename="test.jpg",
            file_path="/test.jpg",
            content_type="image/jpeg",
            size=100,
            status=FileStatus.READY
        )
        db_session.add(file)
        db_session.commit()

        image = ImageAsset(
            id="img-1",
            project_id="proj-1",
            file_id="file-1",
            order=0,
            duration=5.0
        )
        db_session.add(image)
        db_session.commit()

        # 驗證關聯
        result = db_session.query(Project).filter(Project.id == "proj-1").first()
        assert len(result.images) == 1
        assert result.images[0].id == "img-1"
