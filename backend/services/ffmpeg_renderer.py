"""
FFmpeg Ken-Burns 渲染器

負責 FFmpeg 命令構建、BPM 驅動的 zoompan 表達式生成、
非同步執行與進度追蹤。
"""

import asyncio
import logging
import math
import os
import shutil
from typing import Callable, List, Optional, Tuple

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

    def build_zoompan_expr(self, bpm: float, total_frames: int) -> Tuple[str, str, str]:
        """
        根據 BPM 構建序列式 zoompan 表達式（半隨機方向）

        4 步子循環不斷重複：放大 → 平移出去 → 縮小 → 平移回中心
        每個子循環的平移方向由黃金角序列決定（半隨機、均勻分佈、不重複）。
        放大後必定先縮小才能再放大。每段正弦緩動 (ease-in-out)。
        段尾位置 = 段首位置，邏輯串連。

        黃金角 ≈ 137.5°，數學上保證：
        - 連續方向間隔最大化（永遠不會連續朝相似方向）
        - 均勻覆蓋 360° 所有方向（包含對角）
        - 確定性（相同 BPM + 時長 = 相同結果）

        Args:
            bpm: 音樂 BPM
            total_frames: 總幀數

        Returns:
            (z_expr, x_expr, y_expr) 三個 FFmpeg 表達式字串
        """
        if bpm <= 0:
            bpm = 120.0

        # 一小節 = 4 拍（4/4 拍號），時長 = 240 / BPM 秒
        bar_duration = 240.0 / bpm

        # 每個動作 = 2 小節（BPM 120 → 4秒, BPM 80 → 6秒, BPM 160 → 3秒）
        bars_per_action = 2
        action_frames = bars_per_action * bar_duration * self.fps
        # 子循環 = 4 個動作（放大→平移→縮小→回中心）
        sub_cycle_frames = 4 * action_frames

        # 縮放幅度根據 BPM 調整（柔和範圍，避免晃動感）
        if bpm < 80:
            zoom_amp = 0.15   # 慢歌：最大放大至 1.15x
        elif bpm < 140:
            zoom_amp = 0.20   # 中速：最大放大至 1.20x
        else:
            zoom_amp = 0.28   # 快歌：最大放大至 1.28x

        pan_amp_x = 0.05    # 水平幅度（畫面 5%，約 96px at 1920）
        pan_amp_y = 0.035   # 垂直幅度（畫面 3.5%，16:9 考量）

        # --- FFmpeg 子表達式 ---
        af = f"{action_frames:.1f}"
        scf = f"{sub_cycle_frames:.1f}"

        # qseg: 子循環內位置 (0=放大, 1=平移出, 2=平移回中心, 3=縮小)
        qseg = f"floor(mod(floor(on/{af}),4))"
        # sc: 子循環編號（決定本次平移方向）
        sc = f"floor(on/{scf})"
        # t: 段內進度 (0→1)，smootherstep 緩動
        # 6t⁵ - 15t⁴ + 10t³：邊界處速度和加速度皆為零，消除頓挫感
        tr = f"(mod(on,{af})/{af})"
        t = f"(6*pow({tr},5)-15*pow({tr},4)+10*pow({tr},3))"
        # alpha: 黃金角序列（每個子循環旋轉 137.5°）
        # 2.39996... rad ≈ 137.508° = 360° × (1 - 1/φ)
        alpha = f"({sc}*2.4)"

        # z: 縮放
        # 新順序：放大→平移出→平移回→縮小
        # 確保平移時 zoom 恆定（不會因 zoom 變化造成座標漂移）
        # 確保縮放時在中心（不會因 zoom=1.0 時偏移超出畫面）
        # qseg=0: 放大 1.0→1.0+amp
        # qseg=1: 保持放大（平移出去中）
        # qseg=2: 保持放大（平移回中心中）
        # qseg=3: 縮小 1.0+amp→1.0
        z_expr = (
            f"1.0+{zoom_amp}*("
            f"between({qseg},0,0)*{t}"
            f"+between({qseg},1,1)"
            f"+between({qseg},2,2)"
            f"+between({qseg},3,3)*(1-{t})"
            f")"
        )

        # x: 水平平移（方向由 cos(alpha) 決定）
        # qseg=0: 靜止在中心（放大中）
        # qseg=1: 中心 → cos(alpha)*A（平移出去）
        # qseg=2: cos(alpha)*A → 中心（平移回來）
        # qseg=3: 靜止在中心（縮小中）
        # trunc() 確保一致的整數截斷，消除捨入方向不一致的抖動
        x_expr = (
            f"trunc((iw-iw/zoom)/2+iw/zoom*{pan_amp_x}*cos({alpha})*("
            f"between({qseg},1,1)*{t}"
            f"+between({qseg},2,2)*(1-{t})"
            f"))"
        )

        # y: 垂直平移（方向由 sin(alpha) 決定）
        # 模式與 x 相同，sin(alpha) 控制垂直分量
        y_expr = (
            f"trunc((ih-ih/zoom)/2+ih/zoom*{pan_amp_y}*sin({alpha})*("
            f"between({qseg},1,1)*{t}"
            f"+between({qseg},2,2)*(1-{t})"
            f"))"
        )

        return z_expr, x_expr, y_expr

    def build_command(
        self,
        image_paths: List[str],
        audio_paths: List[str],
        output_path: str,
        bpm: float,
        total_duration: float,
        encoder: str = "libx264",
    ) -> List[str]:
        """
        構建完整的 FFmpeg 命令

        Args:
            image_paths: 圖片路徑列表
            audio_paths: 音訊路徑列表
            output_path: 輸出檔案路徑
            bpm: 音樂 BPM
            total_duration: 總時長（秒）
            encoder: 編碼器名稱

        Returns:
            FFmpeg 命令參數列表
        """
        total_frames = int(total_duration * self.fps)
        z_expr, x_expr, y_expr = self.build_zoompan_expr(bpm, total_frames)

        # 淡入淡出幀數（1 秒）
        fade_frames = self.fps
        fade_out_start = max(0, total_frames - fade_frames)

        # 構建 filter_complex
        # 超取樣倍率：先放大至 4x 解析度再做 zoompan，
        # 將整數捨入誤差從 1px 降至 0.25px（亞像素級，視覺不可見）
        # 參考：FFmpeg Trac #4298 — zoompan 整數捨入是已知的抖動根因
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

        # 音訊濾鏡
        if len(audio_paths) > 1:
            audio_inputs = "".join(f"[{i+1}:a]" for i in range(len(audio_paths)))
            audio_filter = f"{audio_inputs}concat=n={len(audio_paths)}:v=0:a=1[a]"
            filter_complex = f"{video_filter};{audio_filter}"
        elif len(audio_paths) == 1:
            audio_filter = f"[1:a]anull[a]"
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
