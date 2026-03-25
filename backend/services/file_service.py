"""
File Service

Handles file processing, storage, and metadata extraction.
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from PIL import Image
from sqlalchemy.orm import Session

from backend.models.file import File as FileModel
from backend.models.file import FileStatus, FileType

logger = logging.getLogger(__name__)


class FileService:
    """Service for handling file operations."""

    def __init__(self, db: Session):
        self.db = db
        self.upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        self.images_dir = os.path.join(self.upload_dir, "images")
        self.audios_dir = os.path.join(self.upload_dir, "audios")

        # Ensure directories exist
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.audios_dir, exist_ok=True)

    async def save_image(
        self,
        content: bytes,
        filename: str,
        content_type: str,
        project_id: Optional[str] = None,
    ) -> FileModel:
        """
        Save an uploaded image file.

        Args:
            content: File content bytes
            filename: Original filename
            content_type: MIME type
            project_id: Optional project ID to associate with

        Returns:
            FileModel: Created file record
        """
        # Generate unique filename with extension whitelist
        file_id = str(uuid.uuid4())
        extension = os.path.splitext(filename)[1].lower()
        allowed_image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
        if extension not in allowed_image_extensions:
            raise ValueError(f"不允許的圖片副檔名: {extension}")
        stored_filename = f"{file_id}{extension}"
        file_path = os.path.join(self.images_dir, stored_filename)

        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(content)

        # Extract image metadata
        width = None
        height = None

        try:
            with Image.open(file_path) as img:
                width, height = img.size
        except Exception as e:
            logger.warning(f"Failed to extract image metadata: {e}")

        # Create database record
        file_record = FileModel(
            id=file_id,
            file_type=FileType.IMAGE,
            original_filename=filename,
            stored_filename=stored_filename,
            file_path=file_path,
            content_type=content_type,
            size=len(content),
            width=width,
            height=height,
            status=FileStatus.READY,
            processed_at=datetime.utcnow(),
        )

        self.db.add(file_record)
        self.db.commit()
        self.db.refresh(file_record)

        logger.info(f"Saved image: {filename} -> {stored_filename}")

        return file_record

    async def save_audio(
        self,
        content: bytes,
        filename: str,
        content_type: str,
        project_id: Optional[str] = None,
    ) -> FileModel:
        """
        Save an uploaded audio file.

        Args:
            content: File content bytes
            filename: Original filename
            content_type: MIME type
            project_id: Optional project ID to associate with

        Returns:
            FileModel: Created file record
        """
        # Generate unique filename with extension whitelist
        file_id = str(uuid.uuid4())
        extension = os.path.splitext(filename)[1].lower()
        allowed_audio_extensions = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".mp4", ".wma"}
        if extension not in allowed_audio_extensions:
            raise ValueError(f"不允許的音訊副檔名: {extension}")
        stored_filename = f"{file_id}{extension}"
        file_path = os.path.join(self.audios_dir, stored_filename)

        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(content)

        # Extract audio metadata (simplified - would use pydub or ffprobe in production)
        duration = None
        sample_rate = None
        loudness = None

        # Try to extract audio metadata using pydub
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(file_path)
            duration = len(audio) / 1000.0  # Convert ms to seconds
            sample_rate = audio.frame_rate
            # Loudness would require additional processing
        except Exception as e:
            logger.warning(f"Failed to extract audio metadata: {e}")

        # Create database record
        file_record = FileModel(
            id=file_id,
            file_type=FileType.AUDIO,
            original_filename=filename,
            stored_filename=stored_filename,
            file_path=file_path,
            content_type=content_type,
            size=len(content),
            duration=duration,
            sample_rate=sample_rate,
            loudness=loudness,
            status=FileStatus.READY,
            processed_at=datetime.utcnow(),
        )

        self.db.add(file_record)
        self.db.commit()
        self.db.refresh(file_record)

        logger.info(f"Saved audio: {filename} -> {stored_filename}")

        return file_record

    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file and its database record.

        Args:
            file_id: File ID to delete

        Returns:
            bool: True if deleted successfully
        """
        file_record = self.db.query(FileModel).filter(FileModel.id == file_id).first()

        if not file_record:
            return False

        # Delete physical file
        try:
            if os.path.exists(file_record.file_path):
                os.remove(file_record.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete physical file: {e}")

        # Delete database record
        self.db.delete(file_record)
        self.db.commit()

        logger.info(f"Deleted file: {file_id}")

        return True

    def get_file(self, file_id: str) -> Optional[FileModel]:
        """Get file by ID."""
        return self.db.query(FileModel).filter(FileModel.id == file_id).first()

    def get_file_by_project(self, project_id: str) -> list:
        """Get all files associated with a project."""
        # This would join through the asset tables
        return []
