"""
KenBurnsService 整合測試

使用 Mock 方式測試服務與 API 的整合
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# 將 backend 目錄加入 Python 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 直接 import 模組，避免觸發 services/__init__.py
import importlib.util
spec = importlib.util.spec_from_file_location(
    "kenburns_service",
    backend_dir / "services" / "kenburns_service.py"
)
kenburns_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kenburns_module)

KenBurnsService = kenburns_module.KenBurnsService
EffectType = kenburns_module.EffectType
BPMAnalysis = kenburns_module.BPMAnalysis


class TestKenBurnsServiceIntegration:
    """KenBurns 服務整合測試"""

    def test_analyze_music_with_mock(self):
        """測試音樂分析（使用 Mock）"""
        service = KenBurnsService()

        # Mock librosa
        with patch('librosa.load') as mock_load, \
             patch('librosa.beat.beat_track') as mock_beat, \
             patch('librosa.frames_to_time') as mock_time, \
             patch('librosa.get_duration') as mock_duration:

            # 設定 mock 回傳值
            mock_load.return_value = (Mock(), 44100)
            mock_beat.return_value = (120.0, [0, 10, 20, 30])
            mock_time.return_value = [0.0, 0.5, 1.0, 1.5]
            mock_duration.return_value = 180.0

            # 執行分析
            result = service.analyze_music('/fake/path.mp3')

            # 驗證結果
            assert result.bpm == 120.0
            assert result.beat_duration == 0.5
            assert result.duration == 180.0
            assert len(result.onset_times) == 4

    def test_generate_slideshow_with_multiple_audios(self):
        """測試多首音樂的幻燈片生成"""
        service = KenBurnsService()

        images = [
            {"path": "/fake/img1.jpg", "width": 1920, "height": 1080, "subject_regions": []},
            {"path": "/fake/img2.jpg", "width": 1920, "height": 1080, "subject_regions": []}
        ]
        audio_files = ["/fake/audio1.mp3", "/fake/audio2.mp3"]

        # Mock analyze_music 和 _get_audio_duration
        with patch.object(service, 'analyze_music') as mock_analyze, \
             patch.object(service, '_get_audio_duration') as mock_duration:

            mock_analyze.return_value = BPMAnalysis(
                bpm=120.0,
                beat_duration=0.5,
                duration=60.0,
                onset_times=[]
            )
            mock_duration.return_value = 60.0

            segments = service.generate_slideshow(images, audio_files, pairing_mode="N:N")

            # 驗證結果
            assert len(segments) == 2

    def test_error_handling_invalid_bpm(self):
        """測試錯誤處理 - BPM 為 0"""
        service = KenBurnsService()

        # 測試 BPM 為 0 的情況
        duration = service.calculate_effect_duration(0)

        # 應該使用預設 BPM 120
        assert duration > 0
        assert 0.5 <= duration <= 4.0

    def test_error_handling_negative_bpm(self):
        """測試錯誤處理 - BPM 為負數"""
        service = KenBurnsService()

        duration = service.calculate_effect_duration(-10)

        assert duration > 0

    def test_safe_zone_with_empty_regions(self):
        """測試安全區計算 - 空區域"""
        service = KenBurnsService()

        safe_zone = service._calculate_safe_zone([])

        x, y, w, h = safe_zone
        assert 0 <= x < 1
        assert 0 <= y < 1
        assert 0 < w <= 1
        assert 0 < h <= 1

    def test_safe_zone_with_head_region(self):
        """測試安全區計算 - 有頭部區域"""
        service = KenBurnsService()

        regions = [
            {"type": "head", "bounds": {"x": 0.4, "y": 0.1, "width": 0.2, "height": 0.25}}
        ]

        safe_zone = service._calculate_safe_zone(regions)

        x, y, w, h = safe_zone
        # 頭部區域應該被保護
        assert x <= 0.4 + 0.25  # 允許一些邊界


class TestKenBurnsEffectTypes:
    """效果類型測試"""

    def test_all_effect_types_available(self):
        """測試所有效果類型都可使用"""
        effect_types = list(EffectType)

        # 驗證所有預期的效果類型都存在
        expected = [
            "ZOOM_IN", "ZOOM_OUT",
            "PAN_LEFT", "PAN_RIGHT", "PAN_UP", "PAN_DOWN",
            "DIAGONAL_UP_LEFT", "DIAGONAL_UP_RIGHT",
            "DIAGONAL_DOWN_LEFT", "DIAGONAL_DOWN_RIGHT",
            "ROTATE_CW", "ROTATE_CCW",
            "COMPOSE"
        ]

        for effect_name in expected:
            assert hasattr(EffectType, effect_name), f"Missing effect type: {effect_name}"

    def test_effect_type_enum_values(self):
        """測試效果類型枚舉值"""
        # 驗證每個效果類型都有值
        assert EffectType.ZOOM_IN.value is not None
        assert EffectType.PAN_LEFT.value is not None
        assert EffectType.ROTATE_CW.value is not None
