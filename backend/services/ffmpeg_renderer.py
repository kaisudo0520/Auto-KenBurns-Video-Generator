"""
FFmpeg Ken-Burns 渲染器

負責 FFmpeg 命令構建、BPM 驅動的 zoompan 表達式生成、
非同步執行與進度追蹤。
"""

import asyncio
import logging
import math
import os
import random
import shutil
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FFmpegRenderer:
    """FFmpeg Ken-Burns 渲染器"""

    def __init__(self, output_width: int = 1920, output_height: int = 1080, fps: int = 30):
        self.output_width = output_width
        self.output_height = output_height
        self.fps = fps
        self._process: Optional[asyncio.subprocess.Process] = None

    async def detect_encoder(self) -> str:
        """偵測可用的 H.264 編碼器，優先使用 NVENC"""
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            raise RuntimeError("找不到 ffmpeg，請確認已安裝並加入 PATH")

        # 嘗試 NVENC
        try:
            proc = await asyncio.create_subprocess_exec(
                ffmpeg_path, "-hide_banner", "-encoders",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode("utf-8", errors="replace")
            if "h264_nvenc" in output:
                logger.info("偵測到 NVENC 硬體編碼器")
                return "h264_nvenc"
        except Exception as e:
            logger.warning(f"偵測 NVENC 失敗: {e}")

        logger.info("使用 libx264 軟體編碼器")
        return "libx264"

    def build_zoompan_expr(
        self, bpm: float, total_frames: int, cycle_offset: int = 0,
        face_params: Optional[Dict] = None,
    ) -> Tuple[str, str, str]:
        """
        根據 BPM 構建 XYZ 三軸統一運動的 zoompan 表達式

        設計理念（統一 3D 攝影機模型）：
        - XYZ 三軸同時驅動，形成 3D Lissajous 軌跡
        - 各軸振幅在範圍內隨機取值 → 每次渲染獨特
        - 某軸振幅接近 0 時自然退化為雙軸或單軸運動
        - 多頻黃金比例正弦疊加，軌跡永不重複

        === Z 軸（縮放/深度） ===
        慢速餘弦 + smootherstep 包絡：
        - 週期 = 16 小節，振幅隨機 [0.04, 0.25] × BPM比率
        - 自然的放大→持續→縮小→靜止 波形

        === XY 軸（水平/垂直平移） ===
        3 層黃金比例頻率正弦疊加：
        - 基頻 = 4 小節，權重 60% / 30% / 10%
        - 振幅隨機 X:[0.005, 0.055] Y:[0.003, 0.038] × BPM比率
        - X 用 sin、Y 用 cos → 橢圓軌跡

        === 微動 ===
        固定低頻正弦（~0.2% 畫面振幅），模擬攝影機呼吸

        === 抖動消除 ===
        1. EMA 時間平滑（α=0.12）：一階 IIR 低通濾波
        2. 4x 超取樣 + Lanczos：捨入誤差降至 0.25px

        === 臉部保護 ===
        平移振幅鉗制到安全範圍：min(random_amp, safe_amp)

        Args:
            bpm: 音樂 BPM
            total_frames: 總幀數
            cycle_offset: 相位偏移量（多段渲染時確保方向連續性）
            face_params: 臉部安全參數（由 compute_face_safe_params 產出），None 表示無臉部偵測

        Returns:
            (z_expr, x_expr, y_expr) 三個 FFmpeg 表達式字串
        """
        if bpm <= 0:
            bpm = 120.0

        # BPM 速度比率（以 160 為基準）
        bpm_ratio = bpm / 160.0
        clamped_ratio = max(0.5, min(bpm_ratio, 1.5))

        # 一小節 = 4 拍，時長 = 240 / BPM 秒
        bar_duration = 240.0 / bpm

        # === Z 軸（縮放）參數 ===
        # 週期 = 16 小節（慢速呼吸感）
        zoom_period_frames = 16 * bar_duration * self.fps
        # 振幅隨機：每次渲染獨特的縮放強度
        zoom_amp = random.uniform(0.04, 0.25) * clamped_ratio

        # === XY 軸（平移）參數 ===
        # 基頻週期 = 4 小節
        pan_period_frames = 4 * bar_duration * self.fps
        phi = 1.618033988749895  # 黃金比例

        # 振幅隨機：每次渲染獨特的平移強度
        pan_amp_x = random.uniform(0.005, 0.055) * clamped_ratio   # 水平
        pan_amp_y = random.uniform(0.003, 0.038) * clamped_ratio   # 垂直（16:9）

        # === 臉部保護：鉗制平移振幅到安全範圍 ===
        cx_offset = 0.0
        cy_offset = 0.0
        if face_params:
            cx_offset = face_params["cx_offset"]
            cy_offset = face_params["cy_offset"]
            pan_amp_x = min(pan_amp_x, face_params["safe_pan_amp_x"])
            pan_amp_y = min(pan_amp_y, face_params["safe_pan_amp_y"])
            logger.debug(
                f"臉部保護啟用: offset=({cx_offset:.3f}, {cy_offset:.3f}), "
                f"clamped_amp=({pan_amp_x:.4f}, {pan_amp_y:.4f})"
            )

        # === 微動參數 ===
        micro_amp = 0.002  # 畫面 0.2%（1920px → ±4px）

        # === EMA 時間平滑（消除幀間抖動）===
        # 利用 FFmpeg zoompan 的 px/py（前幀座標）實現一階 IIR 低通濾波
        # alpha = 0.12: 時間常數 ≈ 8 幀（0.27s@30fps），90% 收斂 ≈ 18 幀（0.6s）
        # - 保留低頻主運動（基頻衰減 <3%、二次頻 <7%）
        # - 消除 trunc() 階梯跳躍、pan_mod 速度突變等幀間不連續
        ema_alpha = 0.12

        # === 相位偏移（多段連續性）===
        # cycle_offset × 黃金角(2.4 rad) 確保每段方向不重複
        phase_base = cycle_offset * 2.4

        logger.debug(
            f"zoompan XYZ 參數: BPM={bpm:.0f}, ratio={bpm_ratio:.2f}, "
            f"Z_amp={zoom_amp:.3f}, X_amp={pan_amp_x:.4f}, Y_amp={pan_amp_y:.4f}, "
            f"zoom_period={zoom_period_frames/self.fps:.1f}s, "
            f"pan_period={pan_period_frames/self.fps:.1f}s"
        )

        # === FFmpeg 表達式構建 ===

        # --- 縮放頻率 ---
        zf = 2 * math.pi / zoom_period_frames

        # --- 平移頻率（3 層黃金比例）---
        f1 = 2 * math.pi / pan_period_frames       # 基頻
        f2 = f1 * phi                               # ×φ
        f3 = f1 * phi * phi                         # ×φ²

        # --- 相位 ---
        p1 = phase_base
        p2 = phase_base + 2.4     # 黃金角偏移
        p3 = phase_base + 4.8     # 2 × 黃金角偏移

        # --- 微動頻率（固定、互質）---
        mf_x = 0.013   # 週期 ≈ 16s at 30fps
        mf_y = 0.019   # 週期 ≈ 11s at 30fps
        mp_x = phase_base * 0.7   # 微動相位
        mp_y = phase_base * 1.3

        # --- z: 縮放表達式 ---
        # (1 - cos(ω·on + φ)) / 2 → 0→1→0 的平滑鐘形包絡
        # smootherstep 壓扁過渡區：~35% 時間在 <10% zoom（純平移）
        tz = f"((1-cos({zf:.8f}*on+{p1:.4f}))/2)"
        zs = f"(6*pow({tz},5)-15*pow({tz},4)+10*pow({tz},3))"
        z_expr = f"1.0+{zoom_amp:.4f}*{zs}"

        # --- x: 水平平移表達式 ---
        # 3 層 sin 疊加（60% + 30% + 10%）+ 微動
        # XYZ 三軸統一模型：不再使用 pan_mod 抑制，三軸自由同時運動
        # EMA 時間平滑：px + α×(target - px)
        x_pan = (
            f"0.6*sin({f1:.8f}*on+{p1:.4f})"
            f"+0.3*sin({f2:.8f}*on+{p2:.4f})"
            f"+0.1*sin({f3:.8f}*on+{p3:.4f})"
        )
        x_offset_term = f"+iw*{cx_offset:.6f}" if abs(cx_offset) > 0.001 else ""
        x_target = (
            f"(iw-iw/zoom)/2"
            f"{x_offset_term}"
            f"+iw/zoom*({pan_amp_x:.4f}*({x_pan})"
            f"+{micro_amp}*sin({mf_x}*on+{mp_x:.4f}))"
        )
        x_expr = f"px+{ema_alpha}*({x_target}-px)"

        # --- y: 垂直平移表達式 ---
        # 用 cos 而非 sin → X/Y 構成橢圓軌跡（非直線往復）
        y_pan = (
            f"0.6*cos({f1:.8f}*on+{p1:.4f})"
            f"+0.3*cos({f2:.8f}*on+{p2:.4f})"
            f"+0.1*cos({f3:.8f}*on+{p3:.4f})"
        )
        y_offset_term = f"+ih*{cy_offset:.6f}" if abs(cy_offset) > 0.001 else ""
        y_target = (
            f"(ih-ih/zoom)/2"
            f"{y_offset_term}"
            f"+ih/zoom*({pan_amp_y:.4f}*({y_pan})"
            f"+{micro_amp}*sin({mf_y}*on+{mp_y:.4f}))"
        )
        y_expr = f"py+{ema_alpha}*({y_target}-py)"

        return z_expr, x_expr, y_expr

    def build_command(
        self,
        image_paths: List[str],
        audio_paths: List[str],
        output_path: str,
        bpm: float,
        total_duration: float,
        encoder: str = "libx264",
        audio_durations: Optional[List[float]] = None,
        crossfade_duration: float = 1.0,
        bpms: Optional[List[float]] = None,
        face_params_list: Optional[List[Optional[Dict]]] = None,
    ) -> List[str]:
        """
        構建完整的 FFmpeg 命令

        單段模式：1 張圖片 + 0~1 首音訊
        多段模式：N 首音訊各配 1 張圖片，段間 xfade/acrossfade 交叉淡入淡出

        Args:
            image_paths: 圖片路徑列表
            audio_paths: 音訊路徑列表
            output_path: 輸出檔案路徑
            bpm: 音樂 BPM（單段模式使用）
            total_duration: 總時長（秒）
            encoder: 編碼器名稱
            audio_durations: 每首音訊的個別時長（多段模式必填）
            crossfade_duration: 段間交叉淡入淡出時長（秒）
            bpms: 每首音訊的個別 BPM（多段模式，動態調整效果速度）
            face_params_list: 每張圖片的臉部安全參數（與 image_paths 對應）

        Returns:
            FFmpeg 命令參數列表
        """
        # 多段模式：多張圖片 OR 多首音訊
        is_multi_audio = len(audio_paths) > 1 and audio_durations and len(audio_durations) == len(audio_paths)
        is_multi_image = len(image_paths) > 1
        if is_multi_audio or is_multi_image:
            # 計算每段時長
            if is_multi_audio:
                # 多首音訊：每首音訊一段，段數 = 音訊數
                seg_durations = audio_durations
            elif audio_durations:
                # 單首音訊 + 多張圖片：均分音訊時長，段數 = 圖片數
                seg_durations = [audio_durations[0] / len(image_paths)] * len(image_paths)
            else:
                # 無音訊 + 多張圖片：均分總時長，段數 = 圖片數
                seg_durations = [total_duration / len(image_paths)] * len(image_paths)
            return self._build_multi_segment_command(
                image_paths, audio_paths, output_path, bpm,
                seg_durations, encoder, crossfade_duration, bpms,
                face_params_list,
            )

        # === 單段模式（原始邏輯） ===
        total_frames = int(total_duration * self.fps)
        # 取第一張圖片的 face_params（單段模式只有 1 張圖片）
        fp = face_params_list[0] if face_params_list else None
        z_expr, x_expr, y_expr = self.build_zoompan_expr(bpm, total_frames, face_params=fp)

        # 影片淡入淡出幀數（1 秒）
        fade_frames = self.fps
        fade_out_start = max(0, total_frames - fade_frames)

        # 超取樣倍率：先放大至 4x 解析度再做 zoompan，
        # 將整數捨入誤差從 1px 降至 0.25px（亞像素級，視覺不可見）
        oversample = 4
        os_w = self.output_width * oversample
        os_h = self.output_height * oversample

        # 影片濾鏡
        video_filter = (
            f"[0:v]format=yuv420p,"
            f"scale={os_w}:{os_h}:flags=lanczos,"
            f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}'"
            f":d={total_frames}:s={self.output_width}x{self.output_height}:fps={self.fps},"
            f"fade=in:0:{fade_frames},fade=out:{fade_out_start}:{fade_frames}[v]"
        )

        # 音訊濾鏡（加入淡入淡出）
        audio_fade_dur = 1.5
        if len(audio_paths) > 1:
            audio_inputs = "".join(f"[{i+1}:a]" for i in range(len(audio_paths)))
            fade_out_t = max(0, total_duration - audio_fade_dur)
            audio_filter = (
                f"{audio_inputs}concat=n={len(audio_paths)}:v=0:a=1,"
                f"afade=t=in:st=0:d={audio_fade_dur},"
                f"afade=t=out:st={fade_out_t:.2f}:d={audio_fade_dur}[a]"
            )
            filter_complex = f"{video_filter};{audio_filter}"
        elif len(audio_paths) == 1:
            fade_out_t = max(0, total_duration - audio_fade_dur)
            audio_filter = (
                f"[1:a]afade=t=in:st=0:d={audio_fade_dur},"
                f"afade=t=out:st={fade_out_t:.2f}:d={audio_fade_dur}[a]"
            )
            filter_complex = f"{video_filter};{audio_filter}"
        else:
            filter_complex = video_filter

        # 構建命令
        cmd = [shutil.which("ffmpeg") or "ffmpeg", "-y"]

        # 輸入：圖片（循環）
        cmd.extend(["-loop", "1", "-i", image_paths[0]])

        # 輸入：音訊
        for audio_path in audio_paths:
            cmd.extend(["-i", audio_path])

        # 濾鏡
        cmd.extend(["-filter_complex", filter_complex])

        # 輸出映射
        cmd.extend(["-map", "[v]"])
        if audio_paths:
            cmd.extend(["-map", "[a]"])

        # 編碼設定
        cmd.extend(["-c:v", encoder])
        if encoder == "h264_nvenc":
            cmd.extend(["-preset", "medium", "-rc", "vbr", "-cq", "18"])
        else:
            cmd.extend(["-preset", "medium", "-crf", "18"])

        if audio_paths:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])

        # 時長限制
        cmd.extend(["-t", f"{total_duration:.2f}"])

        # 進度回報
        cmd.extend(["-progress", "pipe:1"])

        # 輸出路徑
        cmd.append(output_path)

        return cmd

    def _build_multi_segment_command(
        self,
        image_paths: List[str],
        audio_paths: List[str],
        output_path: str,
        bpm: float,
        audio_durations: List[float],
        encoder: str = "libx264",
        crossfade_duration: float = 1.0,
        bpms: Optional[List[float]] = None,
        face_params_list: Optional[List[Optional[Dict]]] = None,
    ) -> List[str]:
        """
        構建多段 FFmpeg 命令：每首音訊配一張圖片，段間淡入淡出

        圖片循環分配：若圖片數 < 音訊數，圖片會循環使用。
        每段影片/音訊各自加上淡入淡出，再用 concat 串接。
        每段使用各自的 BPM 動態調整效果速度。
        """
        # 段數由 audio_durations 決定（多圖時 = 圖片數，多音訊時 = 音訊數）
        n_segments = len(audio_durations)
        n_audio = len(audio_paths)

        # 超取樣設定
        oversample = 4
        os_w = self.output_width * oversample
        os_h = self.output_height * oversample

        # 段間淡入淡出幀數（影片 1 秒、音訊 1 秒）
        fade_frames = self.fps
        audio_fade_dur = 1.0

        # 每段 BPM（若未提供，全部使用同一個 bpm）
        seg_bpms = bpms if bpms and len(bpms) == n_segments else [bpm] * n_segments

        # 分配圖片（循環）
        segment_images = [image_paths[i % len(image_paths)] for i in range(n_segments)]

        # 判斷是否所有段都使用同一張圖片
        # 若是，只需一個 -loop 1 -i 輸入，再用 split 分流給各段
        # 避免多次開啟同一檔案導致後段出現黑畫面的 FFmpeg 問題
        all_same_image = len(set(segment_images)) == 1

        filter_parts: List[str] = []

        # 若同一張圖片多段使用，先用 split 分流
        if all_same_image and n_segments > 1:
            img_labels = "".join(f"[img{i}]" for i in range(n_segments))
            filter_parts.append(f"[0:v]split={n_segments}{img_labels}")

        # --- 每段影片：獨立 zoompan（各自 BPM） ---
        cumulative_cycles = 0

        for i in range(n_segments):
            seg_bpm = seg_bpms[i]
            seg_frames = int(audio_durations[i] * self.fps)
            # 取對應圖片的 face_params（循環分配，與 segment_images 一致）
            seg_fp = None
            fp_list = face_params_list or []
            if fp_list:
                img_idx = i % len(image_paths)
                if img_idx < len(fp_list):
                    seg_fp = fp_list[img_idx]
            z_expr, x_expr, y_expr = self.build_zoompan_expr(
                seg_bpm, seg_frames, cycle_offset=cumulative_cycles,
                face_params=seg_fp,
            )
            # 每段加入個別淡入淡出
            seg_fade_out_start = max(0, seg_frames - fade_frames)
            # 同一圖片用 split 分流的輸入標籤，否則直接用輸入索引
            input_ref = f"[img{i}]" if all_same_image else f"[{i}:v]"
            filter_parts.append(
                f"{input_ref}format=yuv420p,"
                f"scale={os_w}:{os_h}:flags=lanczos,"
                f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}'"
                f":d={seg_frames}:s={self.output_width}x{self.output_height}:fps={self.fps},"
                f"fade=in:0:{fade_frames},fade=out:{seg_fade_out_start}:{fade_frames}[v{i}]"
            )
            # 累計循環數量，確保下段相位不重複
            seg_bar_dur = 240.0 / max(seg_bpm, 1.0)
            seg_zoom_period = 16 * seg_bar_dur * self.fps
            cumulative_cycles += max(1, int(seg_frames / seg_zoom_period)) + 1

        # --- 影片串接 (concat) ---
        if n_segments == 1:
            filter_parts.append("[v0]null[v]")
        else:
            v_inputs = "".join(f"[v{i}]" for i in range(n_segments))
            filter_parts.append(
                f"{v_inputs}concat=n={n_segments}:v=1:a=0[v]"
            )

        # --- 音訊處理（首尾淡入淡出）---
        # 同一張圖片用 split → 只有 1 個圖片輸入；不同圖片 → n_segments 個圖片輸入
        n_image_inputs = 1 if all_same_image else n_segments
        audio_input_offset = n_image_inputs  # 音訊輸入索引從圖片輸入數量之後開始
        audio_fade_dur = 1.5  # 整體首尾淡入淡出時長
        effective_audio = sum(audio_durations)

        if n_audio == 1:
            # 單首音訊 + 多張圖片：直接套用淡入淡出，橫跨整個影片
            aidx = audio_input_offset
            fade_out_t = max(0.0, effective_audio - audio_fade_dur)
            filter_parts.append(
                f"[{aidx}:a]afade=t=in:st=0:d={audio_fade_dur},"
                f"afade=t=out:st={fade_out_t:.2f}:d={audio_fade_dur}[a]"
            )
        else:
            # 多首音訊：直接串接（段間無淡入淡出），整體首尾淡入淡出
            a_inputs = "".join(f"[{audio_input_offset + i}:a]" for i in range(n_audio))
            fade_out_t = max(0.0, effective_audio - audio_fade_dur)
            filter_parts.append(
                f"{a_inputs}concat=n={n_audio}:v=0:a=1,"
                f"afade=t=in:st=0:d={audio_fade_dur},"
                f"afade=t=out:st={fade_out_t:.2f}:d={audio_fade_dur}[a]"
            )

        filter_complex = ";".join(filter_parts)

        # --- 構建命令 ---
        cmd = [shutil.which("ffmpeg") or "ffmpeg", "-y"]

        # 輸入：圖片
        if all_same_image:
            # 同一張圖片：只需一個輸入，filter 內用 split 分流
            cmd.extend(["-loop", "1", "-i", segment_images[0]])
        else:
            # 不同圖片（或部分不同）：各段各自獨立輸入
            for img_path in segment_images:
                cmd.extend(["-loop", "1", "-i", img_path])

        # 輸入：音訊
        for audio_path in audio_paths:
            cmd.extend(["-i", audio_path])

        # 濾鏡
        cmd.extend(["-filter_complex", filter_complex])

        # 輸出映射
        cmd.extend(["-map", "[v]"])
        if n_audio > 0:
            cmd.extend(["-map", "[a]"])

        # 編碼設定
        cmd.extend(["-c:v", encoder])
        if encoder == "h264_nvenc":
            cmd.extend(["-preset", "medium", "-rc", "vbr", "-cq", "18"])
        else:
            cmd.extend(["-preset", "medium", "-crf", "18"])

        if n_audio > 0:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])

        # 時長限制（各段總和，無交叉縮減）
        effective_total = sum(audio_durations)
        cmd.extend(["-t", f"{effective_total:.2f}"])

        # 進度回報
        cmd.extend(["-progress", "pipe:1"])

        # 輸出路徑
        cmd.append(output_path)

        logger.info(
            f"多段渲染: {n_segments} 段, 有效時長={effective_total:.1f}s"
        )

        return cmd

    async def execute(
        self,
        cmd: List[str],
        total_duration: float,
        progress_callback: Optional[Callable] = None,
        cancel_check: Optional[Callable] = None,
    ) -> bool:
        """
        非同步執行 FFmpeg 命令並追蹤進度

        Args:
            cmd: FFmpeg 命令參數列表
            total_duration: 總時長（用於計算進度百分比）
            progress_callback: 進度回調 async def callback(progress_pct, current_time)
            cancel_check: 取消檢查 def check() -> bool

        Returns:
            True 如果成功完成，False 如果被取消或失敗
        """
        logger.info(f"執行 FFmpeg: {' '.join(cmd[:6])}...")
        logger.debug(f"完整命令: {' '.join(cmd)}")

        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        last_progress = 0
        cancel_check_counter = 0

        try:
            while True:
                if self._process.stdout is None:
                    break

                line = await asyncio.wait_for(
                    self._process.stdout.readline(),
                    timeout=30.0,
                )

                if not line:
                    break

                text = line.decode("utf-8", errors="replace").strip()

                # 解析 out_time_us
                if text.startswith("out_time_us="):
                    try:
                        time_us = int(text.split("=")[1])
                        current_time = time_us / 1_000_000.0
                        if total_duration > 0:
                            progress_pct = min(99, int(current_time / total_duration * 100))
                            if progress_pct > last_progress and progress_callback:
                                await progress_callback(progress_pct, current_time)
                                last_progress = progress_pct
                    except (ValueError, IndexError):
                        pass

                # 完成標記
                if text == "progress=end":
                    break

                # 定期檢查取消（每 10 行檢查一次）
                cancel_check_counter += 1
                if cancel_check_counter >= 10:
                    cancel_check_counter = 0
                    if cancel_check and cancel_check():
                        logger.info("偵測到取消請求，終止 FFmpeg")
                        self.terminate()
                        return False

        except asyncio.TimeoutError:
            logger.warning("FFmpeg 進度讀取超時")
        except Exception as e:
            logger.error(f"FFmpeg 進度追蹤異常: {e}")

        # 等待進程結束
        await self._process.wait()
        returncode = self._process.returncode

        if returncode != 0:
            stderr = await self._process.stderr.read() if self._process.stderr else b""
            stderr_text = stderr.decode("utf-8", errors="replace")
            # 被終止的情況（取消）
            if returncode in (-9, -15, 1) and cancel_check and cancel_check():
                logger.info("FFmpeg 已被取消終止")
                return False
            logger.error(f"FFmpeg 失敗 (code={returncode}): {stderr_text[-500:]}")
            raise RuntimeError(f"FFmpeg 渲染失敗 (code={returncode}): {stderr_text[-200:]}")

        logger.info("FFmpeg 渲染完成")
        return True

    def terminate(self):
        """終止 FFmpeg 進程"""
        if self._process and self._process.returncode is None:
            try:
                self._process.terminate()
                logger.info("已發送終止信號給 FFmpeg")
            except ProcessLookupError:
                pass
