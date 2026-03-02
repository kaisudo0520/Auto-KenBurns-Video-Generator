"""
Schemas 測試

測試 Pydantic Schemas
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from backend.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectStatus,
    Resolution,
    FrameRate,
    OutputFormat,
    KenBurnsEffect,
)
from backend.schemas.file import FileCreate, FileResponse, FileType, FileStatus
from backend.schemas.image_asset import ImageAssetCreate, ImageAssetResponse, SubjectRegion, BoundingBox
from backend.schemas.audio_asset import AudioAssetCreate, AudioAssetResponse
from backend.schemas.render_job import (
    RenderJobCreate,
    RenderJobResponse,
    JobStatus,
    RenderStage,
    RenderProgress,
)
from backend.schemas.settings import SettingsCreate, SettingsResponse


class TestProjectSchemas:
    """專案 Schema 測試"""

    def test_project_create_valid(self):
        """測試建立有效專案"""
        project = ProjectCreate(name="Test Project", description="Description")
        assert project.name == "Test Project"
        assert project.description == "Description"

    def test_project_create_minimal(self):
        """測試建立最少欄位專案"""
        project = ProjectCreate(name="Test")
        assert project.name == "Test"

    def test_project_name_required(self):
        """測試專案名稱必填"""
        with pytest.raises(ValidationError):
            ProjectCreate()

    def test_project_name_min_length(self):
        """測試專案名稱最短長度"""
        with pytest.raises(ValidationError):
            ProjectCreate(name="")

    def test_frame_rate_enum(self):
        """測試幀率列舉"""
        assert FrameRate.FPS_24.value == "24"
        assert FrameRate.FPS_30.value == "30"
        assert FrameRate.FPS_60.value == "60"

    def test_resolution_enum(self):
        """測試解析度列舉"""
        assert Resolution.RES_720P.value == "720p"
        assert Resolution.RES_1080P.value == "1080p"
        assert Resolution.RES_4K.value == "4k"

    def test_output_format_enum(self):
        """測試輸出格式列舉"""
        assert OutputFormat.MP4_H264.value == "mp4_h264"
        assert OutputFormat.MP4_H265.value == "mp4_h265"

    def test_ken_burns_effect_enum(self):
        """測試 Ken Burns 效果列舉"""
        assert KenBurnsEffect.PAN_LEFT.value == "pan_left"
        assert KenBurnsEffect.ZOOM_IN.value == "zoom_in"
        assert KenBurnsEffect.RANDOM.value == "random"


class TestFileSchemas:
    """檔案 Schema 測試"""

    def test_file_create_valid(self):
        """測試建立有效檔案"""
        file = FileCreate(
            file_type=FileType.IMAGE,
            original_filename="test.jpg",
            content_type="image/jpeg",
            stored_filename="abc123.jpg",
            file_path="/path/to/file",
            size=1024
        )
        assert file.file_type == FileType.IMAGE

    def test_file_type_enum(self):
        """測試檔案類型列舉"""
        assert FileType.IMAGE.value == "image"
        assert FileType.AUDIO.value == "audio"

    def test_file_status_enum(self):
        """測試檔案狀態列舉"""
        assert FileStatus.UPLOADING.value == "uploading"
        assert FileStatus.READY.value == "ready"
        assert FileStatus.ERROR.value == "error"


class TestImageAssetSchemas:
    """圖片資源 Schema 測試"""

    def test_bounding_box_valid(self):
        """測試邊界框驗證"""
        bbox = BoundingBox(x=0.5, y=0.5, width=0.3, height=0.3)
        assert bbox.x == 0.5

    def test_bounding_box_invalid_range(self):
        """測試邊界框數值範圍"""
        with pytest.raises(ValidationError):
            BoundingBox(x=1.5, y=0.5, width=0.3, height=0.3)

    def test_subject_region_valid(self):
        """測試主體區域"""
        region = SubjectRegion(
            type="person",
            bounds=BoundingBox(x=0.4, y=0.1, width=0.2, height=0.3),
            confidence=0.95
        )
        assert region.type == "person"
        assert region.confidence == 0.95

    def test_image_asset_create_valid(self):
        """測試建立圖片資源"""
        asset = ImageAssetCreate(
            project_id="proj-1",
            file_id="file-1",
            order=0,
            duration=5.0
        )
        assert asset.duration == 5.0

    def test_image_asset_duration_range(self):
        """測試圖片時長範圍"""
        with pytest.raises(ValidationError):
            ImageAssetCreate(
                project_id="proj-1",
                file_id="file-1",
                duration=0.5  # 小於最小值 1.0
            )


class TestAudioAssetSchemas:
    """音訊資源 Schema 測試"""

    def test_audio_asset_create_valid(self):
        """測試建立音訊資源"""
        asset = AudioAssetCreate(
            project_id="proj-1",
            file_id="file-1",
            volume=0.8
        )
        assert asset.volume == 0.8

    def test_audio_asset_volume_range(self):
        """測試音量範圍"""
        with pytest.raises(ValidationError):
            AudioAssetCreate(
                project_id="proj-1",
                file_id="file-1",
                volume=1.5  # 大於最大值 1.0
            )


class TestRenderJobSchemas:
    """渲染任務 Schema 測試"""

    def test_job_status_enum(self):
        """測試任務狀態列舉"""
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.RENDERING.value == "rendering"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"

    def test_render_stage_enum(self):
        """測試渲染階段列舉"""
        assert RenderStage.PREPARING.value == "preparing"
        assert RenderStage.LOADING_IMAGES.value == "loading_images"
        assert RenderStage.RENDERING_FRAMES.value == "rendering_frames"
        assert RenderStage.ENCODING_VIDEO.value == "encoding_video"

    def test_render_job_create_valid(self):
        """測試建立渲染任務"""
        job = RenderJobCreate(project_id="proj-1")
        assert job.project_id == "proj-1"


class TestSettingsSchemas:
    """設定 Schema 測試"""

    def test_settings_create_valid(self):
        """測試建立設定"""
        settings = SettingsCreate(
            key="test_key",
            value="test_value",
            value_type="string"
        )
        assert settings.key == "test_key"

    def test_settings_key_required(self):
        """測試設定鍵必填"""
        with pytest.raises(ValidationError):
            SettingsCreate(value="test")

    def test_settings_key_min_length(self):
        """測試設定鍵最短長度"""
        with pytest.raises(ValidationError):
            SettingsCreate(key="", value="test")

    def test_settings_default_values(self):
        """測試設定預設值"""
        settings = SettingsCreate(key="test_key")
        assert settings.value is None
        assert settings.value_type == "string"
        assert settings.is_system is False
