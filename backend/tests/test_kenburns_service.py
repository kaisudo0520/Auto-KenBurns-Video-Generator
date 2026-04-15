"""
KenBurnsService 單元測試

使用 TDD 方式驗證服務功能：
1. 測試 BPM 分析
2. 測試動作持續時間計算
3. 測試效果生成
4. 測試安全區計算
5. 測試幻燈片生成
"""

import sys
import os
from pathlib import Path

# 避免循環 import：直接添加到路徑
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
EffectSegment = kenburns_module.EffectSegment
ImageSegment = kenburns_module.ImageSegment

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestKenBurnsServiceInit:
    """測試服務初始化"""

    def test_service_init_default(self):
        """測試預設初始化"""
        service = KenBurnsService()
        assert service.SAFE_ZONE_MARGIN == 0.15
        assert service.HEAD_SAFE_MARGIN == 0.25
        assert service.DEFAULT_MIN_ZOOM == 1.0
        assert service.DEFAULT_MAX_ZOOM == 1.8

    def test_service_init_custom_random_seed(self):
        """測試自訂隨機種子"""
        service = KenBurnsService()
        # 驗證 random 物件存在
        assert hasattr(service, 'random')


class TestCalculateEffectDuration:
    """測試動作持續時間計算"""

    def test_low_bpm_slow_movement(self):
        """低 BPM (<80) 應該產生較慢的動作（以小節為單位）"""
        service = KenBurnsService()

        # BPM = 60 -> 一小節 = 4秒, 2~4 小節 = 8~16秒 (clamp to 10s max)
        duration = service.calculate_effect_duration(60)

        assert service.MIN_EFFECT_DURATION <= duration <= service.MAX_EFFECT_DURATION

    def test_medium_bpm_standard_movement(self):
        """中 BPM (80-140) 應該產生標準動作（以小節為單位）"""
        service = KenBurnsService()

        # BPM = 120 -> 一小節 = 2秒, 2~4 小節 = 4~8秒
        duration = service.calculate_effect_duration(120)

        assert service.MIN_EFFECT_DURATION <= duration <= service.MAX_EFFECT_DURATION

    def test_high_bpm_fast_movement(self):
        """高 BPM (>140) 應該產生較短的動作（以小節為單位）"""
        service = KenBurnsService()

        # BPM = 160 -> 一小節 = 1.5秒, 2~4 小節 = 3~6秒
        duration = service.calculate_effect_duration(160)

        assert service.MIN_EFFECT_DURATION <= duration <= service.MAX_EFFECT_DURATION

    def test_duration_with_multiplier(self):
        """測試倍數影響"""
        service = KenBurnsService()

        base_duration = service.calculate_effect_duration(120, base_multiplier=1.0)
        doubled_duration = service.calculate_effect_duration(120, base_multiplier=2.0)

        # 倍數應該影響持續時間
        assert doubled_duration > base_duration


class TestSelectNextEffect:
    """測試效果選擇"""

    def test_avoids_repeating_same_effect(self):
        """避免重複選擇相同效果"""
        service = KenBurnsService()

        # 建立一個只有 ZOOM_IN 的歷史記錄
        previous_effects = [
            EffectSegment(
                effect_type=EffectType.ZOOM_IN,
                start_time=0.0,
                end_time=1.0,
                start_zoom=1.0,
                end_zoom=1.5,
                start_x=0.1,
                end_x=0.2,
                start_y=0.1,
                end_y=0.2,
            )
        ]

        # 選擇下一個效果，應該不是 ZOOM_IN
        next_effect = service._select_next_effect(previous_effects)

        # 應該避免重複
        assert next_effect != EffectType.ZOOM_IN

    def test_empty_previous_effects(self):
        """空的歷史記錄應該返回隨機效果"""
        service = KenBurnsService()

        effect = service._select_next_effect([])

        # 應該返回一個有效的心得類型
        assert effect in EffectType


class TestCalculateSafeZone:
    """測試安全區計算"""

    def test_no_subject_regions_default(self):
        """無主體區域時使用預設邊界"""
        service = KenBurnsService()

        safe_zone = service._calculate_safe_zone([])

        # 應該有合理的邊界
        x, y, w, h = safe_zone
        assert 0 <= x < 1
        assert 0 <= y < 1
        assert 0 < w <= 1
        assert 0 < h <= 1

    def test_with_head_region(self):
        """有頭部區域時優先保護"""
        service = KenBurnsService()

        subject_regions = [
            {"type": "head", "bounds": {"x": 0.4, "y": 0.1, "width": 0.2, "height": 0.25}}
        ]

        safe_zone = service._calculate_safe_zone(subject_regions)

        # 應該返回頭部區域（加上安全邊界）
        x, y, w, h = safe_zone
        # 頭部應該在安全區內
        assert x <= 0.4
        assert y <= 0.1

    def test_with_body_region(self):
        """有身體區域時使用身體範圍"""
        service = KenBurnsService()

        subject_regions = [
            {"type": "body", "bounds": {"x": 0.3, "y": 0.35, "width": 0.4, "height": 0.5}}
        ]

        safe_zone = service._calculate_safe_zone(subject_regions)

        x, y, w, h = safe_zone

        # 應該以身體區域為基礎
        assert w > 0
        assert h > 0


class TestCalculatePan:
    """測試平移座標計算"""

    def test_pan_left_direction(self):
        """左移效果的座標計算"""
        service = KenBurnsService()
        safe_zone = (0.1, 0.1, 0.8, 0.8)

        start_x, start_y, end_x, end_y = service._calculate_pan(
            EffectType.PAN_LEFT, safe_zone, 1.0, 1.5
        )

        # 左移：起點在右，終點在左
        assert start_x > end_x

    def test_pan_right_direction(self):
        """右移效果的座標計算"""
        service = KenBurnsService()
        safe_zone = (0.1, 0.1, 0.8, 0.8)

        start_x, start_y, end_x, end_y = service._calculate_pan(
            EffectType.PAN_RIGHT, safe_zone, 1.0, 1.5
        )

        # 右移：起點在左，終點在右
        assert start_x < end_x

    def test_pan_up_direction(self):
        """上移效果的座標計算"""
        service = KenBurnsService()
        safe_zone = (0.1, 0.1, 0.8, 0.8)

        start_x, start_y, end_x, end_y = service._calculate_pan(
            EffectType.PAN_UP, safe_zone, 1.0, 1.5
        )

        # 上移：起點在下，終點在上
        assert start_y > end_y

    def test_pan_down_direction(self):
        """下移效果的座標計算"""
        service = KenBurnsService()
        safe_zone = (0.1, 0.1, 0.8, 0.8)

        start_x, start_y, end_x, end_y = service._calculate_pan(
            EffectType.PAN_DOWN, safe_zone, 1.0, 1.5
        )

        # 下移：起點在上，終點在下
        assert start_y < end_y


class TestGenerateContinuousEffects:
    """測試持續效果生成"""

    def test_generates_effects_within_duration(self):
        """產生的效果應該在指定時長內"""
        service = KenBurnsService()

        bpm_analysis = BPMAnalysis(bpm=120.0, beat_duration=0.5)

        segment = service.generate_continuous_effects(
            image_path="/fake/image.jpg",
            duration=5.0,
            bpm_analysis=bpm_analysis,
        )

        # 效果的結束時間不應該超過總時長
        for effect in segment.effects:
            assert effect.end_time <= 5.0

    def test_effects_have_valid_zoom(self):
        """效果應該有有效的縮放值"""
        service = KenBurnsService()

        bpm_analysis = BPMAnalysis(bpm=120.0, beat_duration=0.5)

        segment = service.generate_continuous_effects(
            image_path="/fake/image.jpg",
            duration=5.0,
            bpm_analysis=bpm_analysis,
            min_zoom=1.0,
            max_zoom=1.8,
        )

        for effect in segment.effects:
            assert 1.0 <= effect.start_zoom <= 1.8
            assert 1.0 <= effect.end_zoom <= 1.8

    def test_fade_duration_reasonable(self):
        """淡入淡出時間應該合理"""
        service = KenBurnsService()

        bpm_analysis = BPMAnalysis(bpm=120.0, beat_duration=0.5)

        # 短時長
        segment_short = service.generate_continuous_effects(
            image_path="/fake/image.jpg",
            duration=2.0,
            bpm_analysis=bpm_analysis,
        )

        assert segment_short.fade_in_duration <= 0.5
        assert segment_short.fade_out_duration <= 0.5

        # 長時長
        segment_long = service.generate_continuous_effects(
            image_path="/fake/image.jpg",
            duration=30.0,
            bpm_analysis=bpm_analysis,
        )

        assert segment_long.fade_in_duration <= 3.0
        assert segment_long.fade_out_duration <= 3.0

    def test_with_subject_regions(self):
        """有主體區域時應該正確處理"""
        service = KenBurnsService()

        bpm_analysis = BPMAnalysis(bpm=120.0, beat_duration=0.5)
        subject_regions = [
            {"type": "head", "bounds": {"x": 0.4, "y": 0.1, "width": 0.2, "height": 0.25}}
        ]

        segment = service.generate_continuous_effects(
            image_path="/fake/image.jpg",
            duration=5.0,
            bpm_analysis=bpm_analysis,
            subject_regions=subject_regions,
        )

        # 應該產生了效果
        assert len(segment.effects) > 0


class TestGenerateSlideshow:
    """測試幻燈片生成"""

    def test_one_to_n_mode(self):
        """1:N 配對模式測試"""
        service = KenBurnsService()

        images = [
            {"path": "/fake/image1.jpg", "width": 1920, "height": 1080, "subject_regions": []}
        ]
        audio_files = ["/fake/audio1.mp3", "/fake/audio2.mp3"]

        # Mock _get_audio_duration 和 analyze_music
        with patch.object(service, '_get_audio_duration', return_value=10.0):
            with patch.object(service, 'analyze_music', return_value=BPMAnalysis(bpm=120.0, beat_duration=0.5)):
                segments = service.generate_slideshow(images, audio_files, pairing_mode="1:N")

        # 應該只有一個圖片段落
        assert len(segments) == 1

    def test_n_to_n_mode(self):
        """N:N 配對模式測試"""
        service = KenBurnsService()

        images = [
            {"path": "/fake/image1.jpg", "width": 1920, "height": 1080, "subject_regions": []},
            {"path": "/fake/image2.jpg", "width": 1920, "height": 1080, "subject_regions": []},
        ]
        audio_files = ["/fake/audio1.mp3", "/fake/audio2.mp3"]

        with patch.object(service, '_get_audio_duration', return_value=10.0):
            with patch.object(service, 'analyze_music', return_value=BPMAnalysis(bpm=120.0, beat_duration=0.5)):
                segments = service.generate_slideshow(images, audio_files, pairing_mode="N:N")

        # 應該有兩個段落
        assert len(segments) == 2

    def test_empty_input_returns_empty(self):
        """空輸入應該返回空列表"""
        service = KenBurnsService()

        segments = service.generate_slideshow([], [], pairing_mode="1:N")

        assert segments == []


class TestGenerateFFmpegFilters:
    """測試 FFmpeg 濾鏡生成"""

    def test_generates_valid_filter_string(self):
        """應該生成有效的濾鏡字串"""
        service = KenBurnsService()

        segment = ImageSegment(
            image_path="/fake/image.jpg",
            start_time=0.0,
            end_time=5.0,
            fade_in_duration=0.5,
            fade_out_duration=0.5,
            effects=[
                EffectSegment(
                    effect_type=EffectType.ZOOM_IN,
                    start_time=0.0,
                    end_time=2.5,
                    start_zoom=1.0,
                    end_zoom=1.5,
                    start_x=0.1,
                    end_x=0.2,
                    start_y=0.1,
                    end_y=0.2,
                )
            ]
        )

        filter_str = service.generate_ffmpeg_filters(segment, output_width=1920, output_height=1080)

        # 應該包含 zoompan 和 fade
        assert "zoompan" in filter_str.lower() or "scale" in filter_str.lower()
        assert "fade" in filter_str.lower()

    def test_includes_fade_for_short_duration(self):
        """短時長應該包含淡入淡出"""
        service = KenBurnsService()

        segment = ImageSegment(
            image_path="/fake/image.jpg",
            start_time=0.0,
            end_time=3.0,
            fade_in_duration=0.3,
            fade_out_duration=0.3,
            effects=[
                EffectSegment(
                    effect_type=EffectType.PAN_LEFT,
                    start_time=0.0,
                    end_time=3.0,
                    start_zoom=1.0,
                    end_zoom=1.2,
                    start_x=0.2,
                    end_x=0.1,
                    start_y=0.1,
                    end_y=0.1,
                )
            ]
        )

        filter_str = service.generate_ffmpeg_filters(segment)

        # 應該包含 fade
        assert "fade" in filter_str.lower()


class TestEffectType:
    """測試效果類型枚舉"""

    def test_all_effect_types_defined(self):
        """所有效果類型都應該被定義"""
        expected_types = [
            "ZOOM_IN",
            "ZOOM_OUT",
            "PAN_LEFT",
            "PAN_RIGHT",
            "PAN_UP",
            "PAN_DOWN",
            "DIAGONAL_UP_LEFT",
            "DIAGONAL_UP_RIGHT",
            "DIAGONAL_DOWN_LEFT",
            "DIAGONAL_DOWN_RIGHT",
            "ROTATE_CW",
            "ROTATE_CCW",
            "COMPOSE",
        ]

        for type_name in expected_types:
            assert hasattr(EffectType, type_name)


class TestComputeFaceSafeParams:
    """測試臉部安全參數計算（含 Overscan offset 鉗制）"""

    @staticmethod
    def _make_face_region(cx: float, cy: float, w: float = 0.15, h: float = 0.20):
        """建立臉部區域（cx/cy 為中心座標）"""
        return [{
            "type": "face",
            "bounds": {"x": cx - w / 2, "y": cy - h / 2, "width": w, "height": h},
            "confidence": 0.95,
        }]

    def test_center_face_no_clamp(self):
        """臉部在中心時，cx_offset ~0；cy_offset 略負（head_cy = face_cy - 0.2×fh 頭髮修正）"""
        regions = self._make_face_region(0.5, 0.5)
        result = KenBurnsService.compute_face_safe_params(
            subject_regions=regions,
            default_pan_amp_x=0.08, default_pan_amp_y=0.05,
            zoom_amp=0.20,
        )
        assert result is not None
        assert abs(result["cx_offset"]) < 0.01
        # head_cy = 0.5 - 0.04 = 0.46 → cy_offset_raw = -0.04
        # 新算法會在可行範圍內逼近，但不超過 |raw|
        assert -0.05 <= result["cy_offset"] <= 0.0
        # 新欄位存在
        assert "pan_bias_x" in result
        assert "pan_bias_y" in result
        assert "zoom_amp_cap" in result

    def test_edge_face_offset_clamped(self):
        """臉部在邊緣時，offset 應被鉗制到安全範圍"""
        regions = self._make_face_region(0.9, 0.5)
        result = KenBurnsService.compute_face_safe_params(
            subject_regions=regions,
            default_pan_amp_x=0.08, default_pan_amp_y=0.05,
            zoom_amp=0.20,
        )
        assert result is not None
        # 原始 cx_offset = 0.9 - 0.5 = 0.4，應被鉗制
        assert result["cx_offset"] < 0.4
        # offset 不應為負（臉在右邊，偏移也應朝右或為 0）
        assert result["cx_offset"] >= 0.0

    def test_left_edge_face_offset_clamped(self):
        """臉部在左邊緣時，cx_offset 應被鉗制為負值但在安全範圍內"""
        regions = self._make_face_region(0.08, 0.5)
        result = KenBurnsService.compute_face_safe_params(
            subject_regions=regions,
            default_pan_amp_x=0.08, default_pan_amp_y=0.05,
            zoom_amp=0.20,
        )
        assert result is not None
        # 原始 cx_offset = 0.08 - 0.5 = -0.42
        assert result["cx_offset"] > -0.42
        assert result["cx_offset"] <= 0.0

    def test_corner_face_both_axes_clamped(self):
        """臉部在角落時，雙軸都應被鉗制"""
        regions = self._make_face_region(0.9, 0.9)
        result = KenBurnsService.compute_face_safe_params(
            subject_regions=regions,
            default_pan_amp_x=0.08, default_pan_amp_y=0.05,
            zoom_amp=0.20,
        )
        assert result is not None
        # 原始 offset = (0.4, 0.4)，應被大幅鉗制
        assert result["cx_offset"] < 0.4
        assert result["cy_offset"] < 0.4

    def test_offset_clamped_within_boundary(self):
        """offset + pan + DC bias 在 viewport 邊界內，不會超出 image"""
        base_zoom = 1.15

        for cx in [0.1, 0.3, 0.5, 0.7, 0.9]:
            regions = self._make_face_region(cx, 0.5)
            result = KenBurnsService.compute_face_safe_params(
                subject_regions=regions,
                default_pan_amp_x=0.10, default_pan_amp_y=0.07,
                zoom_amp=0.28,
            )
            if result is None:
                continue
            # 用實際套用的 zoom_amp_cap 計算 z_min
            eff_amp = result["zoom_amp_cap"]
            z_min = max(1.0, base_zoom - eff_amp / 2.0)
            half_over_zmin = 0.5 * (1.0 - 1.0 / z_min)

            # 極端 pan 產生的最大位移量：a*(1+|bias|)/z_min
            bias = result["pan_bias_x"]
            a = result["safe_pan_amp_x"]
            max_pan_contrib_neg = a * (1.0 + abs(bias)) / z_min
            offset = result["cx_offset"]

            # viewport_top at z_min 最小值 = half_over_zmin + offset - max_pan_contrib_neg
            vp_top_min = half_over_zmin + offset - max_pan_contrib_neg
            # 允許 0.005 誤差（pan_amp 最低 0.005 下限造成）
            assert vp_top_min >= -0.01, (
                f"cx={cx}: vp_top_min={vp_top_min:.4f} 越過 image 邊界"
            )

    def test_large_zoom_amp_tight_offset(self):
        """大 zoom_amp 讓 z_min 接近 1.0，offset 應幾乎為 0"""
        regions = self._make_face_region(0.8, 0.5)
        result = KenBurnsService.compute_face_safe_params(
            subject_regions=regions,
            default_pan_amp_x=0.10, default_pan_amp_y=0.07,
            zoom_amp=0.28,  # z_min = 1.15 - 0.14 = 1.01
        )
        assert result is not None
        # z_min ≈ 1.01，overscan 裕度極小，offset 應被大幅鉗制
        assert abs(result["cx_offset"]) < 0.02

    def test_no_faces_returns_none(self):
        """無臉部時應回傳 None"""
        result = KenBurnsService.compute_face_safe_params(
            subject_regions=[],
            default_pan_amp_x=0.08, default_pan_amp_y=0.05,
            zoom_amp=0.20,
        )
        assert result is None

    def test_non_face_type_returns_none(self):
        """只有 body 類型（非 face）時應回傳 None"""
        regions = [{"type": "body", "bounds": {"x": 0.3, "y": 0.2, "width": 0.4, "height": 0.6}, "confidence": 0.9}]
        result = KenBurnsService.compute_face_safe_params(
            subject_regions=regions,
            default_pan_amp_x=0.08, default_pan_amp_y=0.05,
            zoom_amp=0.20,
        )
        assert result is None


# 整合測試 - 端到端流程
class TestEndToEnd:
    """端到端流程測試"""

    def test_full_pipeline_mock(self):
        """完整流程測試（使用 Mock）"""
        service = KenBurnsService()

        # 模擬輸入
        images = [
            {"path": "/fake/image.jpg", "width": 1920, "height": 1080, "subject_regions": []}
        ]
        audio_files = ["/fake/audio.mp3"]

        # Mock analyze_music 返回包含 duration 的 BPMAnalysis
        with patch.object(service, 'analyze_music', return_value=BPMAnalysis(bpm=120.0, beat_duration=0.5, duration=10.0)):
            # 生成幻燈片
            segments = service.generate_slideshow(images, audio_files, pairing_mode="1:N")

        # 驗證結果
        assert len(segments) == 1
        segment = segments[0]

        # 應該有效果
        assert len(segment.effects) > 0

        # 應該能生成 FFmpeg 濾鏡
        filter_str = service.generate_ffmpeg_filters(segment)
        assert filter_str is not None
        assert len(filter_str) > 0
