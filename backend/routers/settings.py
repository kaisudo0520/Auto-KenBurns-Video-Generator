"""
Settings API Router

Handles system settings, options, and status queries.
"""

import logging
import os
import platform
import subprocess
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import deps

logger = logging.getLogger(__name__)
router = APIRouter()


# ========================================
# Settings Response Models
# ========================================

class ResolutionOption(BaseModel):
    """Resolution option."""
    value: str
    label: str
    width: int
    height: int


class FrameRateOption(BaseModel):
    """Frame rate option."""
    value: int
    label: str


class OutputFormatOption(BaseModel):
    """Output format option."""
    value: str
    label: str
    description: str


class EncoderOption(BaseModel):
    """Encoder option."""
    value: str
    label: str
    hardware: bool


class KenBurnsEffectOption(BaseModel):
    """Ken-Burns effect option."""
    value: str
    label: str
    default: bool = False


class EasingFunctionOption(BaseModel):
    """Easing function option."""
    value: str
    label: str
    default: bool = False


class SettingsOptionsResponse(BaseModel):
    """Response for settings options."""
    success: bool = True
    data: dict


class SystemStatusResponse(BaseModel):
    """Response for system status."""
    success: bool = True
    data: dict


# ========================================
# Settings Endpoints
# ========================================

@router.get("/settings/options", response_model=SettingsOptionsResponse)
async def get_settings_options():
    """
    Get available settings options.
    """
    return SettingsOptionsResponse(
        data={
            "resolutions": [
                ResolutionOption(value="720p", label="HD (1280x720)", width=1280, height=720),
                ResolutionOption(value="1080p", label="Full HD (1920x1080)", width=1920, height=1080),
                ResolutionOption(value="1440p", label="QHD (2560x1440)", width=2560, height=1440),
                ResolutionOption(value="4k", label="4K (3840x2160)", width=3840, height=2160),
            ],
            "frame_rates": [
                FrameRateOption(value=24, label="24 fps (電影)"),
                FrameRateOption(value=30, label="30 fps (標準)"),
                FrameRateOption(value=60, label="60 fps (流暢)"),
            ],
            "output_formats": [
                OutputFormatOption(value="mp4_h264", label="MP4 (H.264)", description="相容性最佳"),
                OutputFormatOption(value="mp4_h265", label="MP4 (H.265/HEVC)", description="壓縮率較高"),
            ],
            "encoders": [
                EncoderOption(value="h264_nvenc", label="NVIDIA H.264", hardware=True),
                EncoderOption(value="h265_nvenc", label="NVIDIA H.265", hardware=True),
                EncoderOption(value="libx264", label="Software H.264", hardware=False),
                EncoderOption(value="libx265", label="Software H.265", hardware=False),
            ],
            "kenburns_effects": [
                KenBurnsEffectOption(value="pan_left", label="向左平移"),
                KenBurnsEffectOption(value="pan_right", label="向右平移"),
                KenBurnsEffectOption(value="pan_up", label="向上平移"),
                KenBurnsEffectOption(value="pan_down", label="向下平移"),
                KenBurnsEffectOption(value="zoom_in", label="放大"),
                KenBurnsEffectOption(value="zoom_out", label="縮小"),
                KenBurnsEffectOption(value="compose_pan_zoom", label="組合 (平移+縮放)", default=True),
                KenBurnsEffectOption(value="random", label="隨機"),
            ],
            "easing_functions": [
                EasingFunctionOption(value="linear", label="線性"),
                EasingFunctionOption(value="ease_in", label="緩入"),
                EasingFunctionOption(value="ease_out", label="緩出"),
                EasingFunctionOption(value="ease_in_out", label="緩入緩出", default=True),
            ],
        }
    )


@router.get("/settings/system", response_model=SystemStatusResponse)
async def get_system_status():
    """
    Get system hardware and service status.
    """
    # Get GPU information
    gpu_info = {
        "available": False,
        "name": None,
        "memory_total": 0,
        "memory_used": 0,
        "cuda_version": None,
        "nvenc_available": False,
    }

    # Try to get GPU info (simplified - would use pynvml in production)
    try:
        # Check for NVIDIA GPU via nvidia-smi
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if lines:
                parts = lines[0].split(",")
                gpu_info = {
                    "available": True,
                    "name": parts[0].strip() if len(parts) > 0 else "Unknown",
                    "memory_total": int(parts[1].strip().split()[0]) if len(parts) > 1 else 0,
                    "memory_used": int(parts[2].strip().split()[0]) if len(parts) > 2 else 0,
                    "cuda_version": parts[3].strip() if len(parts) > 3 else None,
                    "nvenc_available": True,
                }
    except (subprocess.SubprocessError, FileNotFoundError, IndexError, ValueError):
        # GPU not available or nvidia-smi not found
        pass

    # Get storage information
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    output_dir = os.getenv("OUTPUT_DIR", "./output")

    storage_info = {
        "temp_used": 0,
        "temp_total": 100 * 1024 * 1024 * 1024,  # 100 GB placeholder
        "output_used": 0,
        "output_total": 200 * 1024 * 1024 * 1024,  # 200 GB placeholder
    }

    # Try to get actual storage info
    try:
        for path, key in [(upload_dir, "temp"), (output_dir, "output")]:
            if os.path.exists(path):
                stat = os.statvfs(path) if hasattr(os, 'statvfs') else None
                if stat:
                    storage_info[f"{key}_total"] = stat.f_blocks * stat.f_frsize
                    storage_info[f"{key}_used"] = (stat.f_blocks - stat.f_bfree) * stat.f_frsize
    except Exception as e:
        logger.warning(f"Failed to get storage info: {e}")

    # Get render queue status (simplified - would query actual queue in production)
    queue_info = {
        "running": 0,
        "queued": 0,
        "max_concurrent": 3,
    }

    # Get version info
    version_info = {
        "api": "1.0.0",
        "ffmpeg": "unknown",
        "engine": "1.0.0",
    }

    # Try to get FFmpeg version
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Extract version from output
            first_line = result.stdout.split("\n")[0]
            version_info["ffmpeg"] = first_line.replace("ffmpeg version ", "").split(" ")[0]
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return SystemStatusResponse(
        data={
            "gpu": gpu_info,
            "storage": storage_info,
            "render_queue": queue_info,
            "version": version_info,
        }
    )


@router.post("/settings/validate", status_code=status.HTTP_200_OK)
async def validate_settings(
    request: dict,
    db: Session = Depends(deps.get_db),
):
    """
    Validate project settings.

    Can validate either by project_id or directly by settings object.
    """
    from backend.models.project import Project as ProjectModel

    warnings = []
    errors = []

    # Validate by project_id
    if "project_id" in request:
        project = db.query(ProjectModel).filter(
            ProjectModel.id == request["project_id"]
        ).first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "PROJECT_NOT_FOUND",
                    "message": "專案不存在",
                },
            )

        # Check if project has images
        if not project.images or len(project.images) == 0:
            errors.append({
                "field": "images",
                "message": "專案沒有圖片",
            })

        # Check if project has audio when using high resolution
        if project.resolution.value == "4k" and not project.audio_tracks:
            warnings.append({
                "field": "audio",
                "message": "4K 解析度建議搭配音訊使用",
            })

    # Validate directly by settings
    elif "settings" in request:
        settings = request["settings"]

        # Check resolution vs GPU availability
        if settings.get("resolution") == "4k":
            # Would check GPU availability here
            pass

    # Return validation result
    is_valid = len(errors) == 0

    return {
        "success": True,
        "data": {
            "valid": is_valid,
            "warnings": warnings,
            "errors": errors,
        }
    }
