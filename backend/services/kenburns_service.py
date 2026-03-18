"""
Ken-Burns Effect Service - 動漫音樂影片版

根據音樂BPM自動調整Ken-Burns效果，支援：
- 持續動態動作切換（放大/縮小/平移）
- 音樂節奏分析與同步
- 畫面淡入淡出
- 動漫人物主體偵測
"""

import logging
import math
import random
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class EffectType(Enum):
    """效果類型"""
    ZOOM_IN = "zoom_in"           # 放大
    ZOOM_OUT = "zoom_out"         # 縮小
    PAN_LEFT = "pan_left"         # 左移
    PAN_RIGHT = "pan_right"       # 右移
    PAN_UP = "pan_up"             # 上移
    PAN_DOWN = "pan_down"        # 下移
    DIAGONAL_UP_LEFT = "diag_up_left"
    DIAGONAL_UP_RIGHT = "diag_up_right"
    DIAGONAL_DOWN_LEFT = "diag_down_left"
    DIAGONAL_DOWN_RIGHT = "diag_down_right"
    ROTATE_CW = "rotate_cw"       # 順時針旋轉
    ROTATE_CCW = "rotate_ccw"    # 逆時針旋轉
    COMPOSE = "compose"           # 組合動作


@dataclass
class BPMAnalysis:
    """音樂BPM分析結果"""
    bpm: float
    beats_per_measure: int = 4
    beat_duration: float = 0.5    # 每拍持續時間(秒)
    onset_times: List[float] = None  # 节拍时间点
    duration: float = 0.0          # 音訊總時長(秒)

    def __post_init__(self):
        if self.onset_times is None:
            self.onset_times = []


@dataclass
class EffectSegment:
    """單一動作片段"""
    effect_type: EffectType
    start_time: float
    end_time: float
    start_zoom: float
    end_zoom: float
    start_x: float
    end_x: float
    start_y: float
    end_y: float
    rotation: float = 0.0
    easing: str = "ease_in_out"


@dataclass
class ImageSegment:
    """圖片片段（包含持續的Ken-Burns動作）"""
    image_path: str
    start_time: float
    end_time: float
    fade_in_duration: float = 0.5   # 淡入時間
    fade_out_duration: float = 0.5  # 淡出時間
    effects: List[EffectSegment] = None

    def __post_init__(self):
        if self.effects is None:
            self.effects = []


class KenBurnsService:
    """服務：根據音樂BPM生成Ken-Burns效果"""

    # 安全邊界（避免裁切動漫人物）
    SAFE_ZONE_MARGIN = 0.15
    # 動漫人物頭部安全邊界
    HEAD_SAFE_MARGIN = 0.25

    # 預設縮放範圍
    DEFAULT_MIN_ZOOM = 1.0
    DEFAULT_MAX_ZOOM = 1.8

    # 動作切換間隔限制（秒）：基於小節計算，此為安全上下限
    MIN_EFFECT_DURATION = 2.5   # 最小動作持續時間
    MAX_EFFECT_DURATION = 10.0  # 最大動作持續時間

    def __init__(self):
        self.random = random.Random()

    def analyze_music(self, audio_path: str) -> BPMAnalysis:
        """
        分析音樂檔案，取得BPM和節拍時間點

        Args:
            audio_path: 音訊檔案路徑

        Returns:
            BPMAnalysis: 包含BPM和節拍資訊
        """
        try:
            # 使用 librosa 分析音樂
            import librosa

            # 載入音訊
            y, sr = librosa.load(audio_path, sr=None)

            # 估算BPM（librosa >= 0.10 回傳 numpy 陣列）
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            bpm = float(np.atleast_1d(tempo)[0])

            # 取得節拍時間點
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)

            # 計算每拍持續時間
            beat_duration = 60.0 / bpm if bpm > 0 else 0.5

            # 取得音訊總時長
            audio_duration = float(librosa.get_duration(y=y, sr=sr))

            logger.info(f"Music analysis: BPM={bpm:.1f}, beats={len(beat_times)}, duration={audio_duration:.1f}s")

            return BPMAnalysis(
                bpm=bpm,
                beat_duration=beat_duration,
                onset_times=beat_times.tolist() if hasattr(beat_times, 'tolist') else list(beat_times),
                duration=audio_duration
            )

        except ImportError:
            logger.warning("librosa not installed, using default BPM")
            # 回退：假設預設BPM
            return BPMAnalysis(bpm=120.0, beat_duration=0.5)
        except Exception as e:
            logger.error(f"Music analysis failed: {e}")
            return BPMAnalysis(bpm=120.0, beat_duration=0.5)

    def calculate_effect_duration(self, bpm: float, base_multiplier: float = 1.0) -> float:
        """
        根據BPM計算動作切換間隔

        高BPM -> 動作切換更頻繁
        低BPM -> 動作更緩慢悠長

        Args:
            bpm: 音樂BPM
            base_multiplier: 基礎倍數

        Returns:
            動作持續時間（秒）
        """
        # 防止除以零
        if bpm <= 0:
            bpm = 120.0  # 預設 BPM

        # 以小節 (bar) 為單位計算動作持續時間
        # 一小節 = 4 拍（4/4 拍號），時長 = 240 / BPM 秒
        bar_duration = 240.0 / bpm

        # 每個動作持續 2~4 小節，自然隨 BPM 縮放：
        # BPM 60 → bar=4.0s → 8-16s (clamp to 10s max)
        # BPM 80 → bar=3.0s → 6-12s (clamp to 10s max)
        # BPM 120 → bar=2.0s → 4-8s
        # BPM 160 → bar=1.5s → 3-6s
        bars_per_effect = random.uniform(2, 4)

        duration = bar_duration * bars_per_effect * base_multiplier

        # 限制範圍
        return max(self.MIN_EFFECT_DURATION, min(self.MAX_EFFECT_DURATION, duration))

    def generate_continuous_effects(
        self,
        image_path: str,
        duration: float,
        bpm_analysis: BPMAnalysis,
        min_zoom: float = DEFAULT_MIN_ZOOM,
        max_zoom: float = DEFAULT_MAX_ZOOM,
        subject_regions: Optional[List[Dict]] = None,
    ) -> ImageSegment:
        """
        為單張圖片生成持續的Ken-Burns效果序列

        根據音樂BPM，在整個時長內持續切換動作

        Args:
            image_path: 圖片路徑
            duration: 總持續時間（秒）
            bpm_analysis: BPM分析結果
            min_zoom: 最小縮放
            max_zoom: 最大縮放
            subject_regions: 主體區域（用於安全邊界計算）

        Returns:
            ImageSegment: 包含所有動作片段
        """
        # 參數驗證
        if duration <= 0:
            logger.warning(f"Invalid duration {duration}, using default 1.0")
            duration = 1.0

        if min_zoom <= 0:
            min_zoom = self.DEFAULT_MIN_ZOOM

        if max_zoom <= min_zoom:
            max_zoom = min_zoom + 0.5

        effects = []
        current_time = 0.0

        # 計算安全邊界
        safe_zone = self._calculate_safe_zone(
            subject_regions if subject_regions else []
        )

        while current_time < duration:
            # 計算這個片段的持續時間
            segment_duration = self.calculate_effect_duration(
                bpm_analysis.bpm,
                base_multiplier=random.uniform(0.8, 1.2)  # 隨機微調
            )

            # 確保不超過剩餘時間
            if current_time + segment_duration > duration:
                segment_duration = duration - current_time
                if segment_duration < 0.5:  # 太小就跳過
                    break

            # 隨機選擇效果類型（避免重複）
            effect_type = self._select_next_effect(effects)

            # 計算縮放
            start_zoom = random.uniform(min_zoom, max_zoom)
            end_zoom = random.uniform(min_zoom, max_zoom)

            # 計算平移（基於效果類型）
            start_x, start_y, end_x, end_y = self._calculate_pan(
                effect_type, safe_zone, start_zoom, end_zoom
            )

            effect = EffectSegment(
                effect_type=effect_type,
                start_time=current_time,
                end_time=current_time + segment_duration,
                start_zoom=start_zoom,
                end_zoom=end_zoom,
                start_x=start_x,
                end_x=end_x,
                start_y=start_y,
                end_y=end_y,
                easing="ease_in_out"
            )

            effects.append(effect)
            current_time += segment_duration

        # 淡入淡出時間
        fade_in = min(0.5, duration * 0.1)
        fade_out = min(0.5, duration * 0.1)

        return ImageSegment(
            image_path=image_path,
            start_time=0.0,
            end_time=duration,
            fade_in_duration=fade_in,
            fade_out_duration=fade_out,
            effects=effects
        )

    def _select_next_effect(self, previous_effects: List[EffectSegment]) -> EffectType:
        """選擇下一個動作（避免重複）"""
        available = list(EffectType)

        # 避免連續使用相同效果
        if previous_effects:
            last_type = previous_effects[-1].effect_type
            available.remove(last_type)

        return random.choice(available)

    def _calculate_pan(
        self,
        effect_type: EffectType,
        safe_zone: Tuple[float, float, float, float],
        start_zoom: float,
        end_zoom: float,
    ) -> Tuple[float, float, float, float]:
        """計算平移座標"""
        sx, sy, sw, sh = safe_zone

        # 根據效果類型計算方向
        if effect_type == EffectType.PAN_LEFT:
            # 從右向左
            start_x = sx + sw * 0.2
            end_x = sx
            start_y = sy + (sh - sh / start_zoom) / 2
            end_y = sy + (sh - sh / end_zoom) / 2
        elif effect_type == EffectType.PAN_RIGHT:
            # 從左向右
            start_x = sx
            end_x = sx + sw * 0.2
            start_y = sy + (sh - sh / start_zoom) / 2
            end_y = sy + (sh - sh / end_zoom) / 2
        elif effect_type == EffectType.PAN_UP:
            # 從下向上
            start_x = sx + (sw - sw / start_zoom) / 2
            end_x = sx + (sw - sw / end_zoom) / 2
            start_y = sy + sh * 0.2
            end_y = sy
        elif effect_type == EffectType.PAN_DOWN:
            # 從上向下
            start_x = sx + (sw - sw / start_zoom) / 2
            end_x = sx + (sw - sw / end_zoom) / 2
            start_y = sy
            end_y = sy + sh * 0.2
        elif effect_type == EffectType.ZOOM_IN:
            # 放大
            start_x = sx + (sw - sw / start_zoom) / 2
            end_x = sx + (sw - sw / end_zoom) / 2
            start_y = sy + (sh - sh / start_zoom) / 2
            end_y = sy + (sh - sh / end_zoom) / 2
        elif effect_type == EffectType.ZOOM_OUT:
            # 縮小
            start_x = sx + (sw - sw / start_zoom) / 2
            end_x = sx + (sw - sw / end_zoom) / 2
            start_y = sy + (sh - sh / start_zoom) / 2
            end_y = sy + (sh - sh / end_zoom) / 2
        elif effect_type == EffectType.DIAGONAL_UP_RIGHT:
            start_x = sx
            end_x = sx + sw * 0.15
            start_y = sy + sh * 0.15
            end_y = sy
        elif effect_type == EffectType.DIAGONAL_UP_LEFT:
            start_x = sx + sw * 0.15
            end_x = sx
            start_y = sy + sh * 0.15
            end_y = sy
        elif effect_type == EffectType.DIAGONAL_DOWN_RIGHT:
            start_x = sx
            end_x = sx + sw * 0.15
            start_y = sy
            end_y = sy + sh * 0.15
        elif effect_type == EffectType.DIAGONAL_DOWN_LEFT:
            start_x = sx + sw * 0.15
            end_x = sx
            start_y = sy
            end_y = sy + sh * 0.15
        elif effect_type == EffectType.ROTATE_CW:
            # 順時針旋轉效果 - 輕微平移模擬旋轉視角
            start_x = sx + (sw - sw / start_zoom) / 2
            end_x = sx + (sw - sw / end_zoom) / 2 + sw * 0.05
            start_y = sy + (sh - sh / start_zoom) / 2
            end_y = sy + (sh - sh / end_zoom) / 2 - sh * 0.05
        elif effect_type == EffectType.ROTATE_CCW:
            # 逆時針旋轉效果 - 輕微平移模擬旋轉視角
            start_x = sx + (sw - sw / start_zoom) / 2 + sw * 0.05
            end_x = sx + (sw - sw / end_zoom) / 2
            start_y = sy + (sh - sh / start_zoom) / 2 - sh * 0.05
            end_y = sy + (sh - sh / end_zoom) / 2
        elif effect_type == EffectType.COMPOSE:
            # 組合效果 - 多方向同時移動 + 縮放
            # 對角線移動 + 輕微縮放
            start_x = sx + sw * 0.1
            end_x = sx + sw * 0.2
            start_y = sy + sh * 0.1
            end_y = sy + sh * 0.2
        else:
            # 默認：輕微的組合動作
            start_x = sx + sw * 0.1
            end_x = sx
            start_y = sy
            end_y = sy + sh * 0.1

        return start_x, start_y, end_x, end_y

    def _calculate_safe_zone(self, subject_regions: List[Dict]) -> Tuple[float, float, float, float]:
        """
        計算安全邊界

        優先保護動漫人物的臉部和身體
        """
        if not subject_regions:
            # 默認：保留中心區域
            margin = self.SAFE_ZONE_MARGIN
            return (margin, margin, 1 - 2*margin, 1 - 2*margin)

        # 找到所有人體區域
        min_x, min_y = 1.0, 1.0
        max_x, max_y = 0.0, 0.0
        head_region = None
        face_region = None

        for region in subject_regions:
            region_type = region.get("type", "body")
            bounds = region.get("bounds", {})

            x = bounds.get("x", 0)
            y = bounds.get("y", 0)
            w = bounds.get("width", 0)
            h = bounds.get("height", 0)

            if region_type == "face":
                # 只保護五官核心（不含頭髮），邊距縮小
                face_margin = self.HEAD_SAFE_MARGIN * 0.5
                face_region = (
                    max(0, x - face_margin),
                    max(0, y - face_margin),
                    min(1.0, w + 2 * face_margin),
                    min(1.0, h + 2 * face_margin),
                )
            elif region_type == "head":
                # 頭部區域特別保護
                head_region = (
                    x - self.HEAD_SAFE_MARGIN,
                    y - self.HEAD_SAFE_MARGIN,
                    w + 2*self.HEAD_SAFE_MARGIN,
                    h + 2*self.HEAD_SAFE_MARGIN
                )
            else:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x + w)
                max_y = max(max_y, y + h)

        # 優先順序：face > head > body
        if face_region:
            return face_region

        if head_region:
            return head_region

        # 否則使用身體區域
        if max_x > min_x and max_y > min_y:
            padding = 0.1
            width = max_x - min_x + 2 * padding
            height = max_y - min_y + 2 * padding
            return (
                max(0.0, min_x - padding),
                max(0.0, min_y - padding),
                min(1.0, width),
                min(1.0, height)
            )

        # 默認返回
        margin = self.SAFE_ZONE_MARGIN
        return (margin, margin, 1 - 2*margin, 1 - 2*margin)

    @staticmethod
    def compute_face_safe_params(
        subject_regions: List[Dict],
        default_pan_amp_x: float,
        default_pan_amp_y: float,
        zoom_amp: float,
        margin: float = 0.01,
    ) -> Optional[Dict]:
        """
        根據臉部偵測結果計算安全的平移參數

        數學原理：
        1. 中心偏移：將平移基準從影像中心偏移到臉部中心
        2. 安全振幅鉗制：確保最大縮放+最大平移時，臉部仍完全在 viewport 內

        Args:
            subject_regions: 偵測結果列表（由 face_detection_service 產出）
            default_pan_amp_x: 預設水平平移振幅
            default_pan_amp_y: 預設垂直平移振幅
            zoom_amp: 縮放振幅（build_zoompan_expr 計算出的值）
            margin: 額外安全邊距（佔畫面比例）

        Returns:
            None（無臉部）或 dict:
            {
                "cx_offset": float,      # 水平中心偏移（-0.5 ~ 0.5）
                "cy_offset": float,      # 垂直中心偏移（-0.5 ~ 0.5）
                "safe_pan_amp_x": float,  # 安全水平振幅
                "safe_pan_amp_y": float,  # 安全垂直振幅
                "has_face": True,
            }
        """
        if not subject_regions:
            return None

        # 取信心最高的臉部
        faces = [r for r in subject_regions if r.get("type") == "face"]
        if not faces:
            return None

        best = faces[0]  # 已按 confidence 排序
        bounds = best["bounds"]
        fx = bounds["x"]
        fy = bounds["y"]
        fw = bounds["width"]
        fh = bounds["height"]

        # 臉部中心（0~1 正規化座標）
        face_cx = fx + fw / 2
        face_cy = fy + fh / 2

        # 中心偏移量（相對於影像中心 0.5）
        cx_offset = face_cx - 0.5
        cy_offset = face_cy - 0.5

        # 只保護五官核心區域（不含頭髮），換取更大動態範圍
        # 五官大約佔臉部框的 60%（去除額頭髮際線和下巴邊緣）
        face_half_x = fw / 2 * 0.6
        face_half_y = fh / 2 * 0.6

        # 安全振幅鉗制：
        # viewport 半寬 = 0.5 / z_max（z_max 時 viewport 最小）
        # 最大平移時，臉部邊緣必須在 viewport 內
        # max_safe_pan = viewport_half - face_half - margin - |offset|
        # 雙向縮放模式：base_zoom=1.15, z_max = base_zoom + amp/2
        base_zoom = 1.15
        z_max = base_zoom + zoom_amp / 2.0
        vp_half_x = 0.5 / z_max
        vp_half_y = 0.5 / z_max

        max_safe_x = vp_half_x - face_half_x - margin - abs(cx_offset)
        max_safe_y = vp_half_y - face_half_y - margin - abs(cy_offset)

        # 鉗制到最小值 0.01（保證最低限度的平移動感）
        safe_pan_amp_x = min(default_pan_amp_x, max(0.01, max_safe_x))
        safe_pan_amp_y = min(default_pan_amp_y, max(0.01, max_safe_y))

        # === Overscan 邊界保護：鉗制 offset 到安全範圍 ===
        # 在 z_min（zoom out 到最大 viewport）時，offset + pan + micro 不能超出圖片邊界
        # 安全上限 = 0.5 × (1 - 1/z_min) - safe_pan_amp - micro_amp
        # z_min = base_zoom - amp/2（雙向縮放的最小值）
        z_min = max(1.0, base_zoom - zoom_amp / 2.0)
        micro_amp = 0.002  # 與 ffmpeg_renderer.py 中的 micro_amp 一致
        max_offset_x = max(0.0, 0.5 * (1.0 - 1.0 / z_min) - safe_pan_amp_x - micro_amp)
        max_offset_y = max(0.0, 0.5 * (1.0 - 1.0 / z_min) - safe_pan_amp_y - micro_amp)

        original_cx = cx_offset
        original_cy = cy_offset
        cx_offset = max(-max_offset_x, min(max_offset_x, cx_offset))
        cy_offset = max(-max_offset_y, min(max_offset_y, cy_offset))

        offset_clamped = (abs(cx_offset - original_cx) > 0.001
                          or abs(cy_offset - original_cy) > 0.001)

        logger.info(
            f"臉部安全參數: offset=({cx_offset:.3f}, {cy_offset:.3f})"
            f"{' [鉗制]' if offset_clamped else ''}"
            f" ← 原始({original_cx:.3f}, {original_cy:.3f}), "
            f"pan_amp=({safe_pan_amp_x:.4f}, {safe_pan_amp_y:.4f}) "
            f"← 原始({default_pan_amp_x:.4f}, {default_pan_amp_y:.4f}), "
            f"z=[{z_min:.3f}, {z_max:.3f}], max_offset=({max_offset_x:.4f}, {max_offset_y:.4f})"
        )

        return {
            "cx_offset": cx_offset,
            "cy_offset": cy_offset,
            "safe_pan_amp_x": safe_pan_amp_x,
            "safe_pan_amp_y": safe_pan_amp_y,
            "has_face": True,
        }

    def generate_slideshow(
        self,
        images: List[Dict],
        audio_files: List[str],
        pairing_mode: str = "1:N",
    ) -> List[ImageSegment]:
        """
        生成幻燈片序列

        Args:
            images: 圖片列表 [{path, width, height, subject_regions}]
            audio_files: 音訊檔案列表
            pairing_mode: "1:N" 或 "N:N"

        Returns:
            ImageSegment列表
        """
        segments = []

        if pairing_mode == "1:N":
            # 1張圖片對多首音樂
            if not images or not audio_files:
                return segments

            image = images[0]

            # 分析所有音樂並獲取時長（避免重複載入）
            bpm_analyses = []
            for audio in audio_files:
                bpm_analysis = self.analyze_music(audio)
                bpm_analyses.append(bpm_analysis)

            # 計算總時長
            total_duration = sum(analysis.duration for analysis in bpm_analyses)

            # 使用第一首音樂的BPM進行效果生成
            bpm_analysis = bpm_analyses[0] if bpm_analyses else BPMAnalysis(bpm=120.0)

            segment = self.generate_continuous_effects(
                image_path=image["path"],
                duration=total_duration,
                bpm_analysis=bpm_analysis,
                subject_regions=image.get("subject_regions")
            )
            segments.append(segment)

        else:
            # N:N 配對
            min_count = min(len(images), len(audio_files))

            for i in range(min_count):
                image = images[i]
                audio = audio_files[i]

                # 分析這首音樂的BPM（包含時長）
                bpm_analysis = self.analyze_music(audio)

                segment = self.generate_continuous_effects(
                    image_path=image["path"],
                    duration=bpm_analysis.duration,
                    bpm_analysis=bpm_analysis,
                    subject_regions=image.get("subject_regions")
                )
                segments.append(segment)

        return segments

    def _get_audio_duration(self, audio_path: str) -> float:
        """取得音訊時長"""
        try:
            import librosa
            info = librosa.info(audio_path)
            return float(info.get("duration", 30.0))
        except Exception as e:
            logger.warning(f"Audio duration error for {audio_path}: {e}")
            return 30.0  # 默認30秒

    def generate_ffmpeg_filters(
        self,
        segment: ImageSegment,
        output_width: int = 1920,
        output_height: int = 1080,
    ) -> str:
        """
        生成 FFmpeg 濾鏡命令

        Args:
            segment: ImageSegment
            output_width: 輸出寬度
            output_height: 輸出高度

        Returns:
            FFmpeg filter complex 字串
        """
        # 防止除以零
        if segment.end_time <= 0:
            return ""

        filters = []

        # 遍歷每個效果片段
        for effect in segment.effects:
            # 計算該片段在整體中的時間比例
            if segment.end_time > 0:
                start_pct = effect.start_time / segment.end_time
                end_pct = effect.end_time / segment.end_time
            else:
                start_pct = 0
                end_pct = 1

            # 計算縮放
            scale = f"scale={output_width}:{output_height}"

            # 根據效果類型計算平移
            zoom = effect.start_zoom + (effect.end_zoom - effect.start_zoom) * 0.5

            # 生成 zoompan 濾鏡
            zoompan = (
                f"zoompan=z='{effect.start_zoom}+({effect.end_zoom}-{effect.start_zoom})*"
                f"((t-{effect.start_time})/{effect.end_time - effect.start_time})'"
                f":x='{effect.start_x*output_width}+({effect.end_x-effect.start_x})*output_width*"
                f"((t-{effect.start_time})/{effect.end_time - effect.start_time})'"
                f":y='{effect.start_y*output_height}+({effect.end_y-effect.start_y})*output_height*"
                f"((t-{effect.start_time})/{effect.end_time - effect.start_time})'"
                f":d=1:s={output_width}x{output_height}:fps=30"
            )

            filters.append(zoompan)

        # 淡入淡出
        fade_filter = (
            f"fade=t=in:st=0:d={segment.fade_in_duration},"
            f"fade=t=out:st={segment.end_time - segment.fade_out_duration}:d={segment.fade_out_duration}"
        )

        return ";".join(filters) + ";" + fade_filter if filters else fade_filter
