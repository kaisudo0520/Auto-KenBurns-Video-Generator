"""
Database Initialization Script

This script seeds the database with default settings and configuration.
"""

import json
from datetime import datetime
from typing import List, Dict, Any


# Default system settings
DEFAULT_SETTINGS: List[Dict[str, Any]] = [
    {
        "key": "app.name",
        "value": "Click Merge Ken-Burns",
        "value_type": "string",
        "description": "Application name",
        "is_system": True,
    },
    {
        "key": "app.version",
        "value": "1.0.0",
        "value_type": "string",
        "description": "Application version",
        "is_system": True,
    },
    {
        "key": "render.max_concurrent_jobs",
        "value": "3",
        "value_type": "number",
        "description": "Maximum number of concurrent render jobs",
        "is_system": True,
    },
    {
        "key": "render.temp_directory",
        "value": "./temp",
        "value_type": "string",
        "description": "Temporary directory for render operations",
        "is_system": True,
    },
    {
        "key": "render.output_directory",
        "value": "./output",
        "value_type": "string",
        "description": "Output directory for rendered videos",
        "is_system": True,
    },
    {
        "key": "upload.max_image_size",
        "value": "52428800",
        "value_type": "number",
        "description": "Maximum image upload size in bytes (50MB)",
        "is_system": True,
    },
    {
        "key": "upload.max_audio_size",
        "value": "104857600",
        "value_type": "number",
        "description": "Maximum audio upload size in bytes (100MB)",
        "is_system": True,
    },
    {
        "key": "project.max_images",
        "value": "50",
        "value_type": "number",
        "description": "Maximum number of images per project",
        "is_system": True,
    },
    {
        "key": "project.max_audio_tracks",
        "value": "10",
        "value_type": "number",
        "description": "Maximum number of audio tracks per project",
        "is_system": True,
    },
    {
        "key": "ffmpeg.path",
        "value": "ffmpeg",
        "value_type": "string",
        "description": "Path to FFmpeg executable",
        "is_system": True,
    },
    {
        "key": "ffprobe.path",
        "value": "ffprobe",
        "value_type": "string",
        "description": "Path to FFprobe executable",
        "is_system": True,
    },
]


def get_seed_data() -> List[Dict[str, Any]]:
    """
    Get all seed data for the database.

    Returns:
        List of dictionaries containing seed data
    """
    return DEFAULT_SETTINGS


def get_settings_options() -> Dict[str, Any]:
    """
    Get available settings options.

    Returns:
        Dictionary containing all available options
    """
    return {
        "resolutions": [
            {"value": "720p", "label": "720p (1280x720)", "width": 1280, "height": 720},
            {"value": "1080p", "label": "1080p (1920x1080)", "width": 1920, "height": 1080},
            {"value": "1440p", "label": "1440p (2560x1440)", "width": 2560, "height": 1440},
            {"value": "4k", "label": "4K (3840x2160)", "width": 3840, "height": 2160},
        ],
        "frame_rates": [
            {"value": 24, "label": "24 fps"},
            {"value": 30, "label": "30 fps"},
            {"value": 60, "label": "60 fps"},
        ],
        "output_formats": [
            {"value": "mp4_h264", "label": "MP4 (H.264)", "description": "Best compatibility"},
            {"value": "mp4_h265", "label": "MP4 (H.265/HEVC)", "description": "Better compression"},
        ],
        "encoders": [
            {"value": "h264_nvenc", "label": "NVIDIA H.264", "hardware": True},
            {"value": "h265_nvenc", "label": "NVIDIA H.265", "hardware": True},
            {"value": "libx264", "label": "Software H.264", "hardware": False},
            {"value": "libx265", "label": "Software H.265", "hardware": False},
        ],
        "kenburns_effects": [
            {"value": "pan_left", "label": "Pan Left", "default": False},
            {"value": "pan_right", "label": "Pan Right", "default": False},
            {"value": "pan_up", "label": "Pan Up", "default": False},
            {"value": "pan_down", "label": "Pan Down", "default": False},
            {"value": "zoom_in", "label": "Zoom In", "default": False},
            {"value": "zoom_out", "label": "Zoom Out", "default": False},
            {"value": "compose_pan_zoom", "label": "Pan & Zoom", "default": True},
            {"value": "random", "label": "Random", "default": False},
        ],
        "easing_functions": [
            {"value": "linear", "label": "Linear", "default": False},
            {"value": "ease_in", "label": "Ease In", "default": False},
            {"value": "ease_out", "label": "Ease Out", "default": False},
            {"value": "ease_in_out", "label": "Ease In Out", "default": True},
        ],
    }


# Run as script
if __name__ == "__main__":
    print("Database Seed Data")
    print("=" * 50)
    print(f"\nTotal settings to seed: {len(DEFAULT_SETTINGS)}")
    print("\nSettings:")
    for setting in DEFAULT_SETTINGS:
        print(f"  - {setting['key']}: {setting['value']} ({setting['value_type']})")
