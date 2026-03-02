"""
FileService 測試

測試檔案處理服務
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from backend.services.file_service import FileService
from backend.models.file import File as FileModel
from backend.models.file import FileStatus, FileType


class TestFileService:
    """FileService 測試"""

    @pytest.fixture
    def mock_db(self):
        """建立 mock 資料庫"""
        db = MagicMock(spec=Session)
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()
        return db

    @pytest.fixture
    def file_service(self, mock_db, tmp_path):
        """建立 FileService 實例"""
        with patch("backend.services.file_service.os.makedirs"):
            service = FileService(mock_db)
            # 直接設定路徑
            service.upload_dir = str(tmp_path / "uploads")
            service.images_dir = str(tmp_path / "uploads" / "images")
            service.audios_dir = str(tmp_path / "uploads" / "audios")
            return service

    @pytest.mark.asyncio
    async def test_save_image(self, file_service, mock_db, tmp_path):
        """測試儲存圖片"""
        # 建立測試圖片內容
        content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            with patch("PIL.Image.open") as mock_image:
                mock_img = MagicMock()
                mock_img.size = (1920, 1080)
                mock_image.return_value.__enter__.return_value = mock_img

                result = await file_service.save_image(
                    content=content,
                    filename="test.jpg",
                    content_type="image/jpeg",
                    project_id="project-123"
                )

        # 驗證結果
        assert result.file_type == FileType.IMAGE
        assert result.original_filename == "test.jpg"
        assert result.width == 1920
        assert result.height == 1080
        assert result.status == FileStatus.READY
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_image_invalid_file(self, file_service, mock_db):
        """測試儲存無效圖片"""
        content = b"invalid image data"

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            with patch("PIL.Image.open") as mock_image:
                mock_image.side_effect = Exception("Invalid image")

                result = await file_service.save_image(
                    content=content,
                    filename="test.jpg",
                    content_type="image/jpeg"
                )

        # 驗證：圖片無效時寬高應為 None
        assert result.width is None
        assert result.height is None
        assert result.status == FileStatus.READY

    @pytest.mark.asyncio
    async def test_save_audio(self, file_service, mock_db, tmp_path):
        """測試儲存音訊"""
        content = b"fake audio data"

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            with patch("pydub.AudioSegment.from_file") as mock_audio:
                mock_audio_obj = MagicMock()
                mock_audio_obj.frame_rate = 44100
                mock_audio.return_value = mock_audio_obj

                result = await file_service.save_audio(
                    content=content,
                    filename="test.mp3",
                    content_type="audio/mpeg"
                )

        # 驗證結果
        assert result.file_type == FileType.AUDIO
        assert result.original_filename == "test.mp3"
        assert result.status == FileStatus.READY

    def test_delete_file_success(self, file_service, mock_db, tmp_path):
        """測試刪除檔案"""
        # 建立 mock 檔案紀錄
        file_record = MagicMock(spec=FileModel)
        file_record.id = "file-123"
        file_record.file_path = str(tmp_path / "test.jpg")

        # 建立實際的檔案
        tmp_path.joinpath("test.jpg").write_bytes(b"test")

        mock_db.query.return_value.filter.return_value.first.return_value = file_record

        result = file_service.delete_file("file-123")

        assert result is True
        mock_db.delete.assert_called_once_with(file_record)
        mock_db.commit.assert_called()

    def test_delete_file_not_found(self, file_service, mock_db):
        """測試刪除不存在的檔案"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = file_service.delete_file("nonexistent")

        assert result is False

    def test_get_file(self, file_service, mock_db):
        """測試取得檔案"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = file_service.get_file("file-123")

        mock_db.query.assert_called()
        assert result is None
