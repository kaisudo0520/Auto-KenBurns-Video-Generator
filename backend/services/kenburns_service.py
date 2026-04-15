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
        safe_gap: float = 0.025,
        base_zoom: float = 1.15,
    ) -> Optional[Dict]:
        """
        計算臉部安全參數（自適應 zoom_amp + 非對稱 pan bias）

        核心策略：
        1. 頭部估算：臉框外推 80% 頭部輪廓（含頭髮，寬 1.15×、高 1.4×）
        2. 自適應 zoom_amp：若頭部 + 2×safe_gap 無法塞進 z_max viewport，
           或 cy_offset 無可行解，縮小 zoom_amp 至可行上限
        3. 求 cx/cy offset 可行範圍，clamp 至最接近 raw 值
        4. 非對稱 pan bias：頭部靠上緣時壓縮正向 pan（viewport 往下 = 頭部朝上）
           解析解：a*(1-b) <= pos_budget, a*(1+b) <= neg_budget
                  a = (pos+neg)/2, b = (neg-pos)/(pos+neg)

        Args:
            subject_regions: 偵測結果（由 face_detection_service 產出）
            default_pan_amp_x / default_pan_amp_y: 預設平移振幅
            zoom_amp: 預估縮放振幅（通常 0.28×BPM比，作為上限輸入）
            margin: 歷史相容參數（不再使用，由 safe_gap 取代）
            safe_gap: 頭部與 viewport 邊緣的安全距離（圖片比例，預設 2.5%）
            base_zoom: Overscan 基礎縮放（需與 ffmpeg_renderer 一致）

        Returns:
            None（無臉部）或 dict，含：
            cx_offset, cy_offset, safe_pan_amp_x, safe_pan_amp_y,
            pan_bias_x, pan_bias_y, zoom_amp_cap, has_face
        """
        if not subject_regions:
            return None

        faces = [r for r in subject_regions if r.get("type") == "face"]
        if not faces:
            return None

        best = faces[0]
        bounds = best["bounds"]
        fx = bounds["x"]
        fy = bounds["y"]
        fw = bounds["width"]
        fh = bounds["height"]

        # === 頭部估算 ===
        face_cx = fx + fw / 2
        head_cy = (fy + fh / 2) - 0.2 * fh

        head_half_x = fw / 2 * 1.15 * 0.8
        head_half_y = fh / 2 * 1.40 * 0.8

        head_top = max(0.0, head_cy - head_half_y)
        head_bot = min(1.0, head_cy + head_half_y)
        head_left = max(0.0, face_cx - head_half_x)
        head_right = min(1.0, face_cx + head_half_x)

        cx_offset_raw = face_cx - 0.5
        cy_offset_raw = head_cy - 0.5

        # === 自適應 zoom_amp：迭代求可行 cap,同時保留 min_pan_budget ===
        # 可行且有感 pan 的約束（推導見設計筆記）：
        #   0.5*zoom_amp/(z_min*z_max) + min_pan*(1/z_min + 1/z_max) <= edge - safe_gap
        # LHS 第一項為 overscan 不均衡補償,第二項為左右兩側各自保留 min_pan 空間
        edge_y_budget = min(head_top, 1.0 - head_bot) - safe_gap
        edge_x_budget = min(head_left, 1.0 - head_right) - safe_gap
        min_pan_budget = 0.008   # 0.8% 圖片大小 = 約 8px@1080

        def _solve_zoom_cap(edge_budget: float) -> float:
            if edge_budget <= 0:
                return 0.0
            cap = zoom_amp
            for _ in range(15):
                zmn = max(1.0, base_zoom - cap / 2.0)
                zmx = base_zoom + cap / 2.0
                required = 0.5 * cap / (zmn * zmx) + min_pan_budget * (1.0 / zmn + 1.0 / zmx)
                if required <= edge_budget + 1e-9:
                    break
                # 依比例收縮（留 5% 餘裕避免來回跳）
                cap *= 0.95 * edge_budget / required
            return max(0.0, cap)

        zoom_cap_y = _solve_zoom_cap(edge_y_budget)
        zoom_cap_x = _solve_zoom_cap(edge_x_budget)
        zoom_amp_cap = max(0.0, min(zoom_amp, zoom_cap_x, zoom_cap_y))

        z_max = base_zoom + zoom_amp_cap / 2.0
        z_min = max(1.0, base_zoom - zoom_amp_cap / 2.0)

        half_over_zmax = 0.5 * (1.0 - 1.0 / z_max)
        half_over_zmin = 0.5 * (1.0 - 1.0 / z_min)
        half_vp_zmax = 0.5 * (1.0 + 1.0 / z_max)

        def _solve_axis(
            head_lo: float,
            head_hi: float,
            offset_raw: float,
            default_amp: float,
        ) -> Tuple[float, float, float]:
            """求解單軸 (offset, pan_amp, pan_bias)

            當 offset_raw 在可行範圍內 → 用 raw(最佳臉部居中)
            當 offset_raw 超出範圍 → 取平衡 offset(L_top = R_top 使 pan budget 最大)
            """
            cy_upper = min(head_lo - safe_gap - half_over_zmax, half_over_zmin)
            cy_lower = max(-half_over_zmin, head_hi + safe_gap - half_vp_zmax)

            if cy_upper < cy_lower:
                # 不可行：退回 black-border 限制內的 raw 鉗制,pan 幾乎為零
                fallback = max(-half_over_zmin, min(half_over_zmin, offset_raw))
                return (fallback, 0.0, 0.0)

            def _budget_at(c: float) -> Tuple[float, float]:
                """給定 offset c,回傳 (max_pos, max_neg) 合法 pan 振幅預算"""
                r_top = max(0.0, head_lo - safe_gap - c - half_over_zmax)
                l_bot_black = max(0.0, half_over_zmin - c)
                l_top = max(0.0, c + half_over_zmin)
                r_bot = max(0.0, half_vp_zmax + c - head_hi - safe_gap)
                pos = min(r_top * z_max, l_bot_black * z_min)
                neg = min(l_top * z_min, r_bot * z_max)
                return (max(0.0, pos), max(0.0, neg))

            # 候選 offset:raw、0、head-top/bot 平衡、中點
            candidates = [
                offset_raw,
                0.0,
                0.5 * (head_lo - safe_gap - half_over_zmax - half_over_zmin),
                0.5 * (head_hi + safe_gap + half_over_zmin - half_vp_zmax),
                0.5 * (cy_lower + cy_upper),
            ]
            best_offset = None
            best_score = -1.0
            for c in candidates:
                c_clamped = max(cy_lower, min(cy_upper, c))
                pos, neg = _budget_at(c_clamped)
                # 分數:雙向都有空間時強烈獎勵(×4 mineral),單向只拿 max*1
                # 這讓對稱 pan 勝過單邊 endpoint,避免無謂地進入 bias=±0.9 的極端區
                if pos > 1e-6 and neg > 1e-6:
                    score = 4.0 * min(pos, neg)
                else:
                    score = max(pos, neg)
                # 輕微獎勵接近 raw 的 offset (|Δ| 越小獎勵越多)
                score -= 0.005 * abs(c_clamped - offset_raw)
                if score > best_score:
                    best_score = score
                    best_offset = c_clamped

            offset = best_offset if best_offset is not None else max(
                cy_lower, min(cy_upper, offset_raw)
            )
            max_pos, max_neg = _budget_at(offset)

            total = max_pos + max_neg
            if total < 1e-6:
                return (offset, 0.0, 0.0)

            bias = (max_neg - max_pos) / total
            bias = max(-0.9, min(0.9, bias))

            a_lim_pos = max_pos / max(1e-6, 1.0 - bias) if max_pos > 0 else float("inf")
            a_lim_neg = max_neg / max(1e-6, 1.0 + bias) if max_neg > 0 else float("inf")
            a_max = min(a_lim_pos, a_lim_neg)

            # 不對 a_max 加人工下限 —— 保持嚴格幾何約束
            safe_amp = min(default_amp, max(0.0, a_max))
            return (offset, safe_amp, bias)

        cy_offset, safe_pan_amp_y, pan_bias_y = _solve_axis(
            head_top, head_bot, cy_offset_raw, default_pan_amp_y
        )
        cx_offset, safe_pan_amp_x, pan_bias_x = _solve_axis(
            head_left, head_right, cx_offset_raw, default_pan_amp_x
        )

        logger.info(
            f"臉部安全參數: offset=({cx_offset:+.4f}, {cy_offset:+.4f}), "
            f"pan_amp=({safe_pan_amp_x:.4f}, {safe_pan_amp_y:.4f}), "
            f"pan_bias=({pan_bias_x:+.3f}, {pan_bias_y:+.3f}), "
            f"zoom_cap={zoom_amp_cap:.4f}(原{zoom_amp:.4f}), "
            f"z=[{z_min:.3f},{z_max:.3f}], "
            f"head=[T={head_top:.3f} B={head_bot:.3f} L={head_left:.3f} R={head_right:.3f}]"
        )

        return {
            "cx_offset": cx_offset,
            "cy_offset": cy_offset,
            "safe_pan_amp_x": safe_pan_amp_x,
            "safe_pan_amp_y": safe_pan_amp_y,
            "pan_bias_x": pan_bias_x,
            "pan_bias_y": pan_bias_y,
            "zoom_amp_cap": zoom_amp_cap,
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
            duration = librosa.get_duration(path=audio_path)
            return float(duration)
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
