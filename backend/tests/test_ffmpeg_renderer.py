"""
FFmpegRenderer 單元測試

測試多段渲染邏輯，重點驗證多圖片 + 單音訊的修復。
不需要實際的 FFmpeg 執行環境。
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import importlib.util

# 直接載入模組，避免觸發 services/__init__.py
backend_dir = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location(
    "ffmpeg_renderer",
    backend_dir / "services" / "ffmpeg_renderer.py",
)
ffmpeg_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ffmpeg_module)

FFmpegRenderer = ffmpeg_module.FFmpegRenderer


class TestBuildCommandMultiSegment:
    """測試 build_command 多段模式觸發邏輯"""

    def setup_method(self):
        self.renderer = FFmpegRenderer(output_width=1920, output_height=1080, fps=30)
        self.img1 = "/tmp/img1.jpg"
        self.img2 = "/tmp/img2.jpg"
        self.img3 = "/tmp/img3.jpg"
        self.audio1 = "/tmp/audio1.mp3"
        self.audio2 = "/tmp/audio2.mp3"

    def test_single_image_single_audio_is_single_segment(self):
        """1 圖 + 1 音訊 → 單段模式（不呼叫 _build_multi_segment_command）"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1],
            audio_paths=[self.audio1],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=30.0,
            encoder="libx264",
            audio_durations=[30.0],
        )
        # 單段模式：只有 1 個 -i 圖片輸入（img1）
        img_inputs = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-i" and cmd[i + 1].endswith(".jpg")]
        assert len(img_inputs) == 1
        assert img_inputs[0] == self.img1

    def test_multi_image_single_audio_triggers_multi_segment(self):
        """多圖 + 1 音訊 → 多段模式，所有圖片都作為輸入"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2, self.img3],
            audio_paths=[self.audio1],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=30.0,
            encoder="libx264",
            audio_durations=[30.0],
        )
        # 多段模式：3 張圖片各自作為輸入
        img_inputs = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-i" and cmd[i + 1].endswith(".jpg")]
        assert len(img_inputs) == 3
        assert self.img1 in img_inputs
        assert self.img2 in img_inputs
        assert self.img3 in img_inputs

    def test_multi_image_single_audio_uses_all_images_in_filter(self):
        """多圖 + 1 音訊 → filter_complex 包含 [0:v], [1:v], [2:v] 三個影片輸入"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2],
            audio_paths=[self.audio1],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=20.0,
            encoder="libx264",
            audio_durations=[20.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        assert "[0:v]" in filter_complex
        assert "[1:v]" in filter_complex

    def test_multi_image_single_audio_segment_durations_evenly_split(self):
        """多圖 + 1 音訊 → 每段時長 = 音訊總長 / 圖片數

        30 秒音訊 / 3 圖 → 每段 10 秒 (300 幀)。
        BPM 120 hold = 240 幀 (但 min_motion = max(30, 300/3) = 100)
        motion = max(100, 300 - 240) = 100 → zoompan d=100
        hold_frames = 300 - 100 = 200 → tpad stop=200（整數幀）
        """
        total_audio = 30.0
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2, self.img3],
            audio_paths=[self.audio1],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=total_audio,
            encoder="libx264",
            audio_durations=[total_audio],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # zoompan d 為 motion_frames=100
        assert "d=100:" in filter_complex
        # trim/tpad 在每段存在，hold=200 幀（整數，不受浮點捨入影響）
        assert "trim=end_frame=100" in filter_complex
        assert "tpad=stop=200:stop_mode=clone" in filter_complex

    def test_multi_image_single_audio_xfade_video_segments(self):
        """多圖 + 1 音訊 → filter_complex 包含 xfade 交叉淡入淡出"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2],
            audio_paths=[self.audio1],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=20.0,
            encoder="libx264",
            audio_durations=[20.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # 應有 xfade 交叉淡入淡出（取代 concat，無黑畫面過渡）
        assert "xfade=transition=fade" in filter_complex

    def test_multi_image_single_audio_single_audio_input(self):
        """多圖 + 1 音訊 → FFmpeg 命令只有 1 個音訊 -i 輸入"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2],
            audio_paths=[self.audio1],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=20.0,
            encoder="libx264",
            audio_durations=[20.0],
        )
        audio_inputs = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-i" and cmd[i + 1].endswith(".mp3")]
        assert len(audio_inputs) == 1

    def test_multi_audio_multi_image_triggers_multi_segment(self):
        """多圖 + 多音訊 → 多段模式，段數 = 音訊數（音訊優先）"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2, self.img3],
            audio_paths=[self.audio1, self.audio2],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=40.0,
            encoder="libx264",
            audio_durations=[20.0, 20.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # 2 段 → xfade 交叉淡入淡出
        assert "xfade=transition=fade" in filter_complex
        # 2 首音訊 → acrossfade 交叉淡入淡出
        assert "acrossfade=" in filter_complex


class TestSingleImageMultiAudioSplit:
    """測試 1 張圖片 + 多首音訊的 split 分流修復"""

    def setup_method(self):
        self.renderer = FFmpegRenderer(output_width=1920, output_height=1080, fps=30)
        self.img1 = "/tmp/img1.jpg"
        self.img2 = "/tmp/img2.jpg"
        self.audio1 = "/tmp/audio1.mp3"
        self.audio2 = "/tmp/audio2.mp3"
        self.audio3 = "/tmp/audio3.mp3"

    def test_single_image_multi_audio_uses_split_filter(self):
        """1 圖 + 3 音訊 → filter_complex 包含 split=3 分流"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1],
            audio_paths=[self.audio1, self.audio2, self.audio3],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=90.0,
            encoder="libx264",
            audio_durations=[30.0, 30.0, 30.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # 應使用 split=3 分流，不是 [0:v][1:v][2:v]
        assert "split=3" in filter_complex
        assert "[img0]" in filter_complex
        assert "[img1]" in filter_complex
        assert "[img2]" in filter_complex

    def test_single_image_multi_audio_only_one_image_input(self):
        """1 圖 + 3 音訊 → FFmpeg 命令只有 1 個圖片 -i 輸入"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1],
            audio_paths=[self.audio1, self.audio2, self.audio3],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=90.0,
            encoder="libx264",
            audio_durations=[30.0, 30.0, 30.0],
        )
        img_inputs = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-i" and cmd[i + 1].endswith(".jpg")]
        # 只開啟一次圖片，避免多次開啟同一檔案的黑畫面問題
        assert len(img_inputs) == 1
        assert img_inputs[0] == self.img1

    def test_single_image_multi_audio_audio_input_index_correct(self):
        """1 圖 + 3 音訊 → 音訊輸入索引從 [1] 開始（圖片只佔 [0]）"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1],
            audio_paths=[self.audio1, self.audio2, self.audio3],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=90.0,
            encoder="libx264",
            audio_durations=[30.0, 30.0, 30.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # 音訊從 [1:a] 開始（[0] 是圖片）
        assert "[1:a]" in filter_complex
        assert "[2:a]" in filter_complex
        assert "[3:a]" in filter_complex
        # 不應有 [4:a]（只有 3 首音訊）
        assert "[4:a]" not in filter_complex

    def test_single_image_multi_audio_uses_img_refs_in_zoompan(self):
        """1 圖 + 2 音訊 → filter 使用 [img0][img1] 而非 [0:v][1:v]"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1],
            audio_paths=[self.audio1, self.audio2],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=60.0,
            encoder="libx264",
            audio_durations=[30.0, 30.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        assert "[img0]" in filter_complex
        assert "[img1]" in filter_complex
        # 不應有 [1:v]（第二個圖片輸入不存在）
        assert "[1:v]" not in filter_complex

    def test_different_images_no_split(self):
        """2 張不同圖 + 2 音訊 → 不用 split，各自獨立輸入"""
        img2 = "/tmp/img2.jpg"
        cmd = self.renderer.build_command(
            image_paths=[self.img1, img2],
            audio_paths=[self.audio1, self.audio2],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=60.0,
            encoder="libx264",
            audio_durations=[30.0, 30.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # 不同圖片 → 不用 split
        assert "split=" not in filter_complex
        assert "[0:v]" in filter_complex
        assert "[1:v]" in filter_complex

    def test_no_audio_multi_image_triggers_multi_segment(self):
        """多圖 + 無音訊 → 多段模式，無音訊映射"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2],
            audio_paths=[],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=10.0,
            encoder="libx264",
            audio_durations=None,
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        assert "[0:v]" in filter_complex
        assert "[1:v]" in filter_complex
        # 不應該有音訊映射
        assert "-map" in cmd
        map_idx = cmd.index("-map")
        assert cmd[map_idx + 1] == "[v]"
        # 確認沒有音訊編碼設定
        assert "-c:a" not in cmd


class TestBuildZoompanExpr:
    """測試 zoompan 表達式基本結構"""

    def setup_method(self):
        self.renderer = FFmpegRenderer(output_width=1920, output_height=1080, fps=30)

    def test_returns_four_values(self):
        """build_zoompan_expr 應回傳 4 個值（z, x, y, rotation_info）"""
        result = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        assert len(result) == 4
        z, x, y, rot_info = result
        assert isinstance(z, str)
        assert isinstance(x, str)
        assert isinstance(y, str)
        assert isinstance(rot_info, dict)

    def test_z_expr_uses_base_zoom(self):
        """縮放表達式應以 base_zoom (1.15) 開頭（雙向縮放基準點）"""
        z, _, _, _ = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        assert z.startswith("1.1500+")
        # 雙向縮放：表達式包含 -0.5 偏移
        assert "-0.5)" in z

    def test_x_expr_uses_ema(self):
        """x 表達式應使用 EMA 平滑（px+α×...）"""
        _, x, _, _ = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        assert x.startswith("px+")

    def test_y_expr_uses_ema(self):
        """y 表達式應使用 EMA 平滑（py+α×...）"""
        _, _, y, _ = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        assert y.startswith("py+")

    def test_invalid_bpm_defaults_to_120(self):
        """bpm <= 0 應 fallback 至 120"""
        z1, x1, y1, rot1 = self.renderer.build_zoompan_expr(bpm=0.0, total_frames=900)
        z2, x2, y2, rot2 = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        # 結構相同（振幅隨機，故不比較數值，只驗證表達式可正常生成）
        assert isinstance(z1, str)
        assert isinstance(x1, str)
        assert isinstance(y1, str)
        assert isinstance(rot1, dict)


class TestXfadeChainAndShortSegment:
    """測試 3+ 段 xfade 鏈式建構與極短段防護"""

    def setup_method(self):
        self.renderer = FFmpegRenderer(output_width=1920, output_height=1080, fps=30)
        self.img1 = "/tmp/img1.jpg"
        self.img2 = "/tmp/img2.jpg"
        self.img3 = "/tmp/img3.jpg"
        self.audio1 = "/tmp/audio1.mp3"
        self.audio2 = "/tmp/audio2.mp3"
        self.audio3 = "/tmp/audio3.mp3"

    def test_three_different_images_xfade_chain(self):
        """3 張不同圖 + 3 音訊 → 鏈式 xfade: [v0][v1]xfade→[vx0]; [vx0][v2]xfade→[v]"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2, self.img3],
            audio_paths=[self.audio1, self.audio2, self.audio3],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=90.0,
            encoder="libx264",
            audio_durations=[30.0, 30.0, 30.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # 應有鏈式 xfade
        assert "[v0][v1]xfade=transition=fade" in filter_complex
        assert "[vx0][v2]xfade=transition=fade" in filter_complex
        # 最後一個 xfade 的輸出應為 [v]
        assert "[v]" in filter_complex
        # 不應使用 split（3 張不同圖片）
        assert "split=" not in filter_complex

    def test_three_segments_audio_chain_acrossfade(self):
        """3 首音訊 → 鏈式 acrossfade"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2, self.img3],
            audio_paths=[self.audio1, self.audio2, self.audio3],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=90.0,
            encoder="libx264",
            audio_durations=[30.0, 30.0, 30.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # 應有鏈式 acrossfade
        assert "acrossfade=" in filter_complex
        assert "[ax0]" in filter_complex
        assert "[ax_merged]" in filter_complex

    def test_short_segment_auto_reduces_crossfade(self):
        """極短段（0.5s）→ crossfade 自動降低為 0.25s"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2],
            audio_paths=[self.audio1, self.audio2],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=30.5,
            encoder="libx264",
            audio_durations=[30.0, 0.5],
            crossfade_duration=1.0,
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # crossfade 應被降至 0.25s（0.5 × 0.5）
        assert "duration=0.25" in filter_complex

    def test_very_short_segment_fallback_concat(self):
        """極短段（0.1s）→ crossfade 降至 0，回退 concat 模式"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2],
            audio_paths=[self.audio1, self.audio2],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=30.1,
            encoder="libx264",
            audio_durations=[30.0, 0.1],
            crossfade_duration=1.0,
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # crossfade=0 → 應使用 concat 而非 xfade
        assert "concat=n=2:v=1:a=0" in filter_complex
        assert "xfade" not in filter_complex

    def test_very_short_segment_audio_fallback_concat(self):
        """極短段（0.1s）→ 音訊也回退 concat 模式"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2],
            audio_paths=[self.audio1, self.audio2],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=30.1,
            encoder="libx264",
            audio_durations=[30.0, 0.1],
            crossfade_duration=1.0,
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # 音訊也應使用 concat 而非 acrossfade
        assert "concat=n=2:v=0:a=1" in filter_complex
        assert "acrossfade" not in filter_complex

    def test_compute_effective_duration_static_method(self):
        """compute_effective_duration 靜態方法正確計算有效時長"""
        # 3 段 × 30s，crossfade=1.0 → 有效時長 = 90 - 2×1 = 88
        result = FFmpegRenderer.compute_effective_duration(
            [30.0, 30.0, 30.0], 1.0
        )
        assert result == 88.0

        # 1 段 → 無 xfade → 有效時長 = 原始時長
        result = FFmpegRenderer.compute_effective_duration([30.0], 1.0)
        assert result == 30.0

        # crossfade=0 → 有效時長 = 總時長
        result = FFmpegRenderer.compute_effective_duration(
            [10.0, 20.0], 0.0
        )
        assert result == 30.0


class TestRotationExpr:
    """測試旋轉表達式生成"""

    def setup_method(self):
        self.renderer = FFmpegRenderer(output_width=1920, output_height=1080, fps=30)

    def test_build_zoompan_expr_returns_four_values(self):
        """build_zoompan_expr 應回傳 4 個值（z, x, y, rotation_info）"""
        result = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        assert len(result) == 4

    def test_rotation_info_has_required_keys(self):
        """rotation_info 應包含 angle_expr, max_angle_deg, rotation_amp_deg"""
        _, _, _, rot_info = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        assert "angle_expr" in rot_info
        assert "max_angle_deg" in rot_info
        assert "rotation_amp_deg" in rot_info

    def test_rotation_angle_in_range(self):
        """rotation_amp_deg 應在 8~15° × clamped_ratio 範圍內"""
        # BPM=120 → ratio=120/160=0.75
        _, _, _, rot_info = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        amp = rot_info["rotation_amp_deg"]
        ratio = max(0.5, min(120.0 / 160.0, 1.5))
        assert 8.0 * ratio <= amp <= 15.0 * ratio

    def test_rotation_angle_in_range_high_bpm(self):
        """高 BPM 時旋轉振幅仍在 [8*ratio, 15*ratio] 安全範圍

        clamped_ratio = clamp(bpm/160, 0.5, 1.5)。
        BPM 240 對應 ratio = 1.5（觸發 clamp 上限），
        BPM 200 對應 ratio = 1.25（未觸發 clamp）。
        """
        for bpm in (200.0, 240.0, 320.0):
            _, _, _, rot_info = self.renderer.build_zoompan_expr(bpm=bpm, total_frames=900)
            amp = rot_info["rotation_amp_deg"]
            ratio = max(0.5, min(bpm / 160.0, 1.5))
            assert 8.0 * ratio <= amp <= 15.0 * ratio, (
                f"BPM={bpm}, ratio={ratio}, amp={amp} 超出範圍"
            )

    def test_rotation_expr_uses_sin(self):
        """angle_expr 應包含 sin 函數（正弦擺動）"""
        _, _, _, rot_info = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        assert "sin(" in rot_info["angle_expr"]

    def test_rotation_expr_uses_radians(self):
        """angle_expr 中的振幅應為弧度值（< 0.5 rad ≈ 28.6°）"""
        import re
        _, _, _, rot_info = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        # 表達式格式: "amp_rad*sin(...)"
        match = re.match(r"([\d.]+)\*sin", rot_info["angle_expr"])
        assert match is not None
        amp_rad = float(match.group(1))
        # 最大 15° × 1.5 = 22.5° ≈ 0.393 rad
        assert 0.0 < amp_rad < 0.5

    def test_build_rotation_expr_period(self):
        """旋轉週期應為 10/φ 小節（與 zoom 10 小節不可公約）"""
        import math
        phi = 1.618033988749895
        bpm = 120.0
        bar_duration = 240.0 / bpm
        expected_period_frames = (10.0 / phi) * bar_duration * 30  # fps=30

        # 驗證表達式中的頻率
        expr = self.renderer.build_rotation_expr(bpm, 10.0, cycle_offset=0)
        # 表達式格式: "amp*sin(freq*n+phase)"
        import re
        match = re.search(r"sin\(([\d.]+)\*n", expr)
        assert match is not None
        freq = float(match.group(1))
        actual_period = 2 * math.pi / freq
        assert abs(actual_period - expected_period_frames) < 1.0  # 容差 1 幀


class TestRotationBufferSize:
    """測試旋轉緩衝區尺寸計算"""

    def test_buffer_size_larger_than_crop(self):
        """緩衝區尺寸應大於裁切尺寸"""
        buf_w, buf_h, _, _ = FFmpegRenderer._compute_rotation_buffer_size(15.0)
        assert buf_w > 1920
        assert buf_h > 1080

    def test_buffer_size_16_9_ratio(self):
        """緩衝區應保持 16:9 比例"""
        buf_w, buf_h, _, _ = FFmpegRenderer._compute_rotation_buffer_size(15.0)
        assert buf_w / buf_h == 16 / 9

    def test_buffer_covers_rotation(self):
        """旋轉後的四個角落應完全在緩衝區內（無黑角）"""
        import math
        max_angle = 15.0
        buf_w, buf_h, crop_x, crop_y = FFmpegRenderer._compute_rotation_buffer_size(max_angle)
        theta = math.radians(max_angle)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        # 裁切區域半尺寸
        hw, hh = 1920 / 2, 1080 / 2
        # 四個角落旋轉後的座標檢查（相對中心）
        corners = [(hw, hh), (hw, -hh), (-hw, hh), (-hw, -hh)]
        for cx, cy in corners:
            # 旋轉後座標
            rx = abs(cx * cos_t + cy * sin_t)
            ry = abs(-cx * sin_t + cy * cos_t)
            assert rx <= buf_w / 2, f"角落 ({cx},{cy}) 旋轉後 x={rx} > buffer/2={buf_w/2}"
            assert ry <= buf_h / 2, f"角落 ({cx},{cy}) 旋轉後 y={ry} > buffer/2={buf_h/2}"

    def test_buffer_zero_angle(self):
        """0° 旋轉 → 緩衝區應僅略大於裁切尺寸（2% 安全邊距）"""
        buf_w, buf_h, _, _ = FFmpegRenderer._compute_rotation_buffer_size(0.0)
        # 0° 旋轉：need_w = 1920 * 1.02 = 1958.4 → k = ceil(1958.4/16) = 123
        # buf_w = 123*16 = 1968
        assert buf_w >= 1920
        assert buf_h >= 1080
        # 不應太大
        assert buf_w < 2100
        assert buf_h < 1200

    def test_crop_position_centers(self):
        """裁切位置應使裁切區域居中"""
        buf_w, buf_h, crop_x, crop_y = FFmpegRenderer._compute_rotation_buffer_size(10.0)
        # 裁切後的中心 = crop_x + 960 應等於 buf_w/2
        assert crop_x + 960 == buf_w // 2
        assert crop_y + 540 == buf_h // 2


class TestRotationInFilterChain:
    """測試旋轉濾鏡在完整濾鏡鏈中的整合"""

    def setup_method(self):
        self.renderer = FFmpegRenderer(output_width=1920, output_height=1080, fps=30)
        self.img1 = "/tmp/img1.jpg"
        self.img2 = "/tmp/img2.jpg"
        self.audio1 = "/tmp/audio1.mp3"
        self.audio2 = "/tmp/audio2.mp3"

    def test_single_segment_has_rotate_filter(self):
        """單段模式 filter_complex 應包含 rotate=a="""
        cmd = self.renderer.build_command(
            image_paths=[self.img1],
            audio_paths=[self.audio1],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=30.0,
            encoder="libx264",
            audio_durations=[30.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        assert "rotate=a=" in filter_complex

    def test_single_segment_has_crop_after_rotate(self):
        """單段模式應在 rotate 後有 crop=1920:1080: 裁切"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1],
            audio_paths=[self.audio1],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=30.0,
            encoder="libx264",
            audio_durations=[30.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # rotate 後應有 crop
        rotate_pos = filter_complex.index("rotate=a=")
        crop_pos = filter_complex.index("crop=1920:1080:")
        assert crop_pos > rotate_pos

    def test_single_segment_has_scale_before_rotate(self):
        """單段模式應在 rotate 前有 scale（放大到旋轉緩衝區）"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1],
            audio_paths=[self.audio1],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=30.0,
            encoder="libx264",
            audio_durations=[30.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # 應有兩次 scale：第一次 7680:4320（超取樣），第二次放大到旋轉緩衝區
        rotate_pos = filter_complex.index("rotate=a=")
        # 找到 rotate 之前最近的 scale（旋轉緩衝區放大）
        before_rotate = filter_complex[:rotate_pos]
        # 應至少有 2 個 scale
        assert before_rotate.count("scale=") >= 2

    def test_multi_segment_has_rotate_filter(self):
        """多段模式每段都應有 rotate=a="""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2],
            audio_paths=[self.audio1, self.audio2],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=60.0,
            encoder="libx264",
            audio_durations=[30.0, 30.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # 2 段 → 應有 2 個 rotate
        assert filter_complex.count("rotate=a=") == 2

    def test_multi_segment_has_crop_after_each_rotate(self):
        """多段模式每段 rotate 後都應有 crop"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2],
            audio_paths=[self.audio1, self.audio2],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=60.0,
            encoder="libx264",
            audio_durations=[30.0, 30.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        assert filter_complex.count("crop=1920:1080:") == 2

    def test_rotation_phase_differs_per_segment(self):
        """多段模式各段旋轉相位應不同（cycle_offset 不同）"""
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2],
            audio_paths=[self.audio1, self.audio2],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=60.0,
            encoder="libx264",
            audio_durations=[30.0, 30.0],
        )
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        # 提取所有 rotate 表達式
        import re
        rotate_exprs = re.findall(r"rotate=a='([^']+)'", filter_complex)
        assert len(rotate_exprs) == 2
        # 兩段的相位應不同
        assert rotate_exprs[0] != rotate_exprs[1]


class TestDetectEncoder:
    """測試 detect_encoder 編碼器偵測邏輯

    因測試檔案以 importlib 動態載入 ffmpeg_renderer 模組（未加入 sys.modules），
    故以 patch.object 直接替換模組內的 shutil / asyncio 屬性，
    而非使用 patch("ffmpeg_renderer.shutil.which") 字串路徑。
    """

    # ── 輔助常數 ──────────────────────────────────────────────────────────────
    # FFmpeg -encoders 輸出的典型片段
    _OUTPUT_H264_AND_HEVC = (
        " V..... h264_nvenc           NVIDIA NVENC H.264 encoder\n"
        " V..... hevc_nvenc           NVIDIA NVENC hevc encoder\n"
    )
    _OUTPUT_H264_ONLY = (
        " V..... h264_nvenc           NVIDIA NVENC H.264 encoder\n"
    )
    _OUTPUT_NO_NVENC = (
        " V..... libx264              libx264 H.264 / AVC / MPEG-4 AVC\n"
        " V..... libx265              libx265 H.265 / HEVC\n"
    )

    # ── 輔助方法：建立模擬子程序 ──────────────────────────────────────────────
    @staticmethod
    def _make_proc(stdout_text: str) -> MagicMock:
        """建立模擬 asyncio.subprocess.Process，communicate() 回傳指定的 stdout。"""
        proc = MagicMock()
        proc.communicate = AsyncMock(
            return_value=(stdout_text.encode("utf-8"), b"")
        )
        return proc

    @staticmethod
    def _run(coro):
        """在新 event loop 中執行協程，避免 loop already running 問題。"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    # ── 測試案例 ──────────────────────────────────────────────────────────────

    def test_detect_encoder_h264_nvenc_default(self):
        """prefer_hevc=False，FFmpeg 輸出包含 h264_nvenc → 回傳 "h264_nvenc"

        預設行為：H.264 NVENC 優先於 HEVC NVENC。
        """
        renderer = FFmpegRenderer()
        proc = self._make_proc(self._OUTPUT_H264_AND_HEVC)

        # 直接替換 ffmpeg_module 內的 shutil.which 與 asyncio.create_subprocess_exec
        with patch.object(ffmpeg_module.shutil, "which", return_value="/usr/bin/ffmpeg"), \
             patch.object(ffmpeg_module.asyncio, "create_subprocess_exec", return_value=proc):
            result = self._run(renderer.detect_encoder(prefer_hevc=False))

        assert result == "h264_nvenc"

    def test_detect_encoder_h265_nvenc_preferred(self):
        """prefer_hevc=True，FFmpeg 輸出包含 hevc_nvenc → 回傳 "h265_nvenc"

        HEVC 優先模式下，hevc_nvenc 應排在 h264_nvenc 之前被選取。
        """
        renderer = FFmpegRenderer()
        proc = self._make_proc(self._OUTPUT_H264_AND_HEVC)

        with patch.object(ffmpeg_module.shutil, "which", return_value="/usr/bin/ffmpeg"), \
             patch.object(ffmpeg_module.asyncio, "create_subprocess_exec", return_value=proc):
            result = self._run(renderer.detect_encoder(prefer_hevc=True))

        assert result == "h265_nvenc"

    def test_detect_encoder_prefer_hevc_fallback_h264(self):
        """prefer_hevc=True，FFmpeg 輸出只有 h264_nvenc（無 hevc_nvenc）→ 回傳 "h264_nvenc"

        hevc_nvenc 不存在時，應退而選用 h264_nvenc 而非直接 fallback 到軟體編碼器。
        """
        renderer = FFmpegRenderer()
        proc = self._make_proc(self._OUTPUT_H264_ONLY)

        with patch.object(ffmpeg_module.shutil, "which", return_value="/usr/bin/ffmpeg"), \
             patch.object(ffmpeg_module.asyncio, "create_subprocess_exec", return_value=proc):
            result = self._run(renderer.detect_encoder(prefer_hevc=True))

        assert result == "h264_nvenc"

    def test_detect_encoder_no_nvenc_fallback_libx264(self):
        """prefer_hevc=False，FFmpeg 輸出不含任何 NVENC → 回傳 "libx264"

        無硬體編碼器時，預設 fallback 為 libx264 軟體編碼器。
        """
        renderer = FFmpegRenderer()
        proc = self._make_proc(self._OUTPUT_NO_NVENC)

        with patch.object(ffmpeg_module.shutil, "which", return_value="/usr/bin/ffmpeg"), \
             patch.object(ffmpeg_module.asyncio, "create_subprocess_exec", return_value=proc):
            result = self._run(renderer.detect_encoder(prefer_hevc=False))

        assert result == "libx264"

    def test_detect_encoder_no_nvenc_fallback_libx265(self):
        """prefer_hevc=True，FFmpeg 輸出不含任何 NVENC → 回傳 "libx265"

        無硬體編碼器時，HEVC 優先模式的 fallback 為 libx265 軟體編碼器。
        """
        renderer = FFmpegRenderer()
        proc = self._make_proc(self._OUTPUT_NO_NVENC)

        with patch.object(ffmpeg_module.shutil, "which", return_value="/usr/bin/ffmpeg"), \
             patch.object(ffmpeg_module.asyncio, "create_subprocess_exec", return_value=proc):
            result = self._run(renderer.detect_encoder(prefer_hevc=True))

        assert result == "libx265"

    def test_detect_encoder_ffmpeg_not_found(self):
        """shutil.which("ffmpeg") 回傳 None → 拋出 RuntimeError

        系統未安裝 FFmpeg 時，應立即拋出明確的錯誤，而非靜默失敗。
        """
        import pytest
        renderer = FFmpegRenderer()

        with patch.object(ffmpeg_module.shutil, "which", return_value=None):
            with pytest.raises(RuntimeError, match="ffmpeg"):
                self._run(renderer.detect_encoder())

    def test_detect_encoder_subprocess_error(self):
        """subprocess 拋出異常 → fallback 到 "libx264"

        子程序啟動失敗（例如權限問題）時，應捕捉異常並使用軟體編碼器，
        而非讓整個渲染任務中斷。
        """
        renderer = FFmpegRenderer()

        with patch.object(ffmpeg_module.shutil, "which", return_value="/usr/bin/ffmpeg"), \
             patch.object(
                 ffmpeg_module.asyncio,
                 "create_subprocess_exec",
                 side_effect=OSError("無法啟動 FFmpeg 子程序"),
             ):
            result = self._run(renderer.detect_encoder(prefer_hevc=False))

        assert result == "libx264"


class TestComputeHoldFrames:
    """測試 BPM 同步 hold 幀數計算"""

    def test_bpm_120_yields_8s_hold(self):
        """BPM 120：16 拍 = 8s，未觸發 clamp"""
        assert FFmpegRenderer.compute_hold_frames(120.0, 30) == 240

    def test_bpm_160_yields_6s_hold(self):
        """BPM 160：16 拍 = 6s"""
        assert FFmpegRenderer.compute_hold_frames(160.0, 30) == 180

    def test_slow_bpm_clamped_to_max(self):
        """BPM 60：16 拍 = 16s → clamp 到 10s 上限"""
        assert FFmpegRenderer.compute_hold_frames(60.0, 30) == 300

    def test_fast_bpm_clamped_to_min(self):
        """BPM 200：16 拍 = 4.8s → clamp 到 5s 下限"""
        assert FFmpegRenderer.compute_hold_frames(200.0, 30) == 150

    def test_invalid_bpm_defaults_to_120(self):
        """BPM <= 0 自動回退 120"""
        assert FFmpegRenderer.compute_hold_frames(0, 30) == 240
        assert FFmpegRenderer.compute_hold_frames(-10, 30) == 240

    def test_custom_fps(self):
        """60fps：BPM 120 → 8s × 60 = 480 幀"""
        assert FFmpegRenderer.compute_hold_frames(120.0, 60) == 480

    def test_custom_hold_beats(self):
        """8 拍設定：BPM 120 → 4s（< min_sec 5s，clamp 到 5s）"""
        assert FFmpegRenderer.compute_hold_frames(120.0, 30, hold_beats=8) == 150


class TestSegmentHoldTpad:
    """測試段間 hold 以 trim+tpad=stop_mode=clone 硬凍結實作"""

    def test_zoompan_expressions_remain_clean(self):
        """表達式層不再包含 if/gt clamp（改由 filter chain 處理）"""
        r = FFmpegRenderer(fps=30)
        z, x, y, rot = r.build_zoompan_expr(120.0, 600)
        assert "if(gt(on," not in z
        assert "if(gt(on," not in x
        assert "if(gt(on," not in y
        assert "if(gt(n," not in rot["angle_expr"]

    def test_multi_segment_contains_trim_and_tpad(self):
        """多段模式應插入 trim=end_frame + tpad=stop=N:stop_mode=clone"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg", "/tmp/b.jpg"],
            audio_paths=["/tmp/a.mp3", "/tmp/b.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=40.0,
            audio_durations=[20.0, 20.0],
            bpms=[120.0, 120.0],
        )
        fc_idx = cmd.index("-filter_complex") + 1
        fc = cmd[fc_idx]
        # BPM 120: hold=240 frames (8s), seg=600 frames → motion=360
        assert "trim=end_frame=360" in fc
        assert "setpts=PTS-STARTPTS" in fc
        # 使用整數 stop=N（非浮點 stop_duration），避免幀數捨入漂移
        assert "tpad=stop=240:stop_mode=clone" in fc

    def test_tpad_uses_integer_stop_not_float_duration(self):
        """tpad 必須用整數 stop=N 而非浮點 stop_duration=X（防 regression）"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg", "/tmp/b.jpg"],
            audio_paths=["/tmp/a.mp3", "/tmp/b.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=40.0,
            audio_durations=[20.0, 20.0],
            bpms=[120.0, 120.0],
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert "stop_duration=" not in fc
        assert "tpad=stop=" in fc

    def test_ultra_short_segment_no_hold_no_double_comma(self):
        """極短段（seg < min_motion）→ hold_frames=0，過濾器鏈不可有 `,,` 雙逗號

        seg=2s=60 幀, BPM 120 hold_req=240, min_motion=max(30,20)=30
        motion=max(30, 60-240)=max(30,-180)=30, 但 hold_frames_req=240 > seg,
        所以 motion 會是 max(30, 60-240)=30 → hold=60-30=30.
        但若 seg 更短：seg=30 幀 (1s), min_motion=max(30,10)=30,
        motion=max(30, 30-240)=30, hold=30-30=0 → 觸發 hold_frames=0 路徑。
        """
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg", "/tmp/b.jpg"],
            audio_paths=["/tmp/a.mp3", "/tmp/b.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=2.0,
            audio_durations=[1.0, 1.0],
            bpms=[120.0, 120.0],
            crossfade_duration=0.1,
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        # hold=0 時不應有 trim/tpad
        assert "trim=end_frame" not in fc
        assert "tpad=" not in fc
        # 關鍵：不可有雙逗號（FFmpeg 會拒絕）
        assert ",," not in fc
        # zoompan d=motion_frames=30（整段都是運鏡）
        assert ":d=30:" in fc

    def test_multi_segment_zoompan_d_equals_motion_frames(self):
        """zoompan 的 d= 應為 motion_frames（非 seg_frames）"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg", "/tmp/b.jpg"],
            audio_paths=["/tmp/a.mp3", "/tmp/b.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=40.0,
            audio_durations=[20.0, 20.0],
            bpms=[120.0, 120.0],
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert ":d=360:" in fc   # motion 360 幀
        assert ":d=600:" not in fc  # 不再直接用 seg_frames

    def test_single_segment_no_tpad_when_intra_hold_disabled(self):
        """intra_hold=False 時單段維持純運鏡，不套 tpad"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg"],
            audio_paths=["/tmp/a.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=20.0,
            intra_hold=False,
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert "tpad" not in fc
        assert "trim=end_frame" not in fc

    def test_short_duration_below_threshold_no_intra_hold(self):
        """時長 < 20s 不觸發段內停頓（即使 intra_hold 預設 True）"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg"],
            audio_paths=["/tmp/a.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=15.0,
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert "tpad" not in fc
        assert "trim=end_frame" not in fc

    def test_short_segment_falls_back_to_min_motion(self):
        """極短段：motion 保留至少 1/3 段時長或 1 秒，hold 縮短

        seg=9s (270 幀), BPM 120 hold 需求=240 幀 → min_motion=max(30,90)=90
        motion=max(90, 270-240)=90 → hold=180 幀（整數，6s）
        """
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg", "/tmp/b.jpg"],
            audio_paths=["/tmp/a.mp3", "/tmp/b.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=18.0,
            audio_durations=[9.0, 9.0],
            bpms=[120.0, 120.0],
            crossfade_duration=0.5,
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert "trim=end_frame=90" in fc
        assert "tpad=stop=180:stop_mode=clone" in fc

    def test_build_zoompan_expr_no_motion_frames_param(self):
        """build_zoompan_expr 不再接受 motion_frames 參數（已移除）"""
        import inspect
        sig = inspect.signature(FFmpegRenderer.build_zoompan_expr)
        assert "motion_frames" not in sig.parameters


class TestIntraHoldExpansion:
    """測試 1 圖 + 1 音樂長曲自動切段為 pseudo-segments 的段內週期性停頓"""

    def test_long_audio_triggers_pseudo_segmentation(self):
        """3 分鐘音訊 → 自動拆成 9 個 pseudo-segments（180/20=9）"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg"],
            audio_paths=["/tmp/a.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=180.0,
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        # 多段路徑才有 tpad
        assert "tpad=stop=" in fc
        # 同圖多段用 split 分流
        assert "[0:v]split=9" in fc
        # 應產生 9 個 [vN] 輸出（0..8）
        for i in range(9):
            assert f"[v{i}]" in fc
        # concat 9 段（無 xfade）
        assert "concat=n=9" in fc

    def test_intra_hold_uses_concat_not_xfade(self):
        """段內 hold 為保留完整音訊，使用 concat 不 xfade"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg"],
            audio_paths=["/tmp/a.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=60.0,
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert "xfade=" not in fc
        assert "concat=" in fc

    def test_intra_hold_single_audio_afade_spans_full_duration(self):
        """單音訊仍以 afade 套在完整長度（不受 xfade 重疊縮減）"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg"],
            audio_paths=["/tmp/a.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=60.0,
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        # 音訊 afade_out 應以 effective_total=60 為基準，58.5 = 60 - 1.5
        assert "afade=t=out:st=58.50" in fc
        # -t 應為完整 60 秒
        t_idx = cmd.index("-t") + 1
        assert cmd[t_idx] == "60.00"

    def test_intra_hold_disabled_by_flag(self):
        """intra_hold=False 時保持原本單段行為"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg"],
            audio_paths=["/tmp/a.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=180.0,
            intra_hold=False,
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert "tpad" not in fc
        assert "split" not in fc
        assert "concat" not in fc

    def test_intra_hold_skipped_for_multi_image(self):
        """多圖模式不受 intra_hold 影響（走原本多段邏輯）"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg", "/tmp/b.jpg"],
            audio_paths=["/tmp/a.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=180.0,
            audio_durations=[180.0],
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        # 2 圖 → 2 段，保留 xfade 模式（不是 9 段 concat）
        assert "concat=n=9" not in fc
        assert "concat=n=2" not in fc  # 2 段用 xfade
        assert "xfade=" in fc

    def test_intra_hold_skipped_for_multi_audio(self):
        """多音訊模式不受 intra_hold 影響"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg"],
            audio_paths=["/tmp/a.mp3", "/tmp/b.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=180.0,
            audio_durations=[90.0, 90.0],
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        # 2 音訊 → 2 段（單圖走 split 分流）
        assert "[0:v]split=2" in fc
        assert "xfade=" in fc

    def test_pseudo_segment_count_rounding(self):
        """n_pseudo = max(2, round(total / 20))"""
        renderer = FFmpegRenderer(fps=30)
        # 30s → round(1.5)=2（banker's round），max(2,2)=2
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg"],
            audio_paths=["/tmp/a.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0, total_duration=30.0,
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert "[0:v]split=2" in fc
        # 60s → round(3.0)=3
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg"],
            audio_paths=["/tmp/a.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0, total_duration=60.0,
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert "[0:v]split=3" in fc


class TestContinuousMotion:
    """測試連續運動模式(共用 seed + 相位接續)確保 hold 後無視覺斷點"""

    def test_seeded_rng_produces_deterministic_amplitudes(self):
        """同一 seed 應產生相同振幅"""
        r = FFmpegRenderer(fps=30)
        z1, x1, y1, rot1 = r.build_zoompan_expr(120.0, 600, seed=42)
        z2, x2, y2, rot2 = r.build_zoompan_expr(120.0, 600, seed=42)
        assert z1 == z2
        assert x1 == x2
        assert y1 == y2
        assert rot1["rotation_amp_deg"] == rot2["rotation_amp_deg"]

    def test_different_seeds_produce_different_amplitudes(self):
        r = FFmpegRenderer(fps=30)
        z1, _, _, _ = r.build_zoompan_expr(120.0, 600, seed=1)
        z2, _, _, _ = r.build_zoompan_expr(120.0, 600, seed=2)
        assert z1 != z2

    def test_frame_phase_offset_shifts_on_variable(self):
        """frame_phase_offset > 0 時表達式應以 (on+offset) 取代 on"""
        r = FFmpegRenderer(fps=30)
        z, x, y, rot = r.build_zoompan_expr(
            120.0, 600, seed=42, frame_phase_offset=360
        )
        assert "(on+360)" in z
        assert "(on+360)" in x
        assert "(on+360)" in y
        assert "(n+360)" in rot["angle_expr"]

    def test_frame_phase_offset_zero_uses_bare_on(self):
        """frame_phase_offset=0 時表達式使用原本的 on / n"""
        r = FFmpegRenderer(fps=30)
        z, x, y, rot = r.build_zoompan_expr(120.0, 600, seed=42)
        assert "(on+" not in z
        assert "(on+" not in x
        assert "(on+" not in y
        assert "(n+" not in rot["angle_expr"]

    def test_intra_hold_triggers_continuous_motion(self):
        """1 圖 + 1 音樂長曲:每個 pseudo-segment 的 on 都被 offset 替換"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg"],
            audio_paths=["/tmp/a.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=60.0,
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        # BPM 120, seg=20s=600 幀, motion=360 幀 → 第 2 段 offset=360, 第 3 段=720
        assert "(on+360)" in fc
        assert "(on+720)" in fc
        assert "(n+360)" in fc
        assert "(n+720)" in fc

    def test_seeded_mode_skips_ema_smoothing(self):
        """連續運動模式（seed 已指定）應直接使用 target，不含 px/py EMA

        zoompan 的 px/py 每段 filter instance 重置為 0，使用
        `px + α*(target-px)` 會在段開頭 0.8s 內從 0 收斂到 target，
        破壞段間連續性。seeded 模式必須跳過 EMA。
        """
        r = FFmpegRenderer(fps=30)
        z, x, y, _ = r.build_zoompan_expr(120.0, 600, seed=42)
        assert "px+" not in x  # 無 EMA
        assert "py+" not in y  # 無 EMA
        # 正常模式仍使用 EMA
        z2, x2, y2, _ = r.build_zoompan_expr(120.0, 600)
        assert "px+" in x2
        assert "py+" in y2

    def test_multi_image_non_intra_hold_does_not_use_continuous_motion(self):
        """多圖模式(非 intra_hold)不啟用連續運動,每段各自不同軌跡"""
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg", "/tmp/b.jpg"],
            audio_paths=["/tmp/a.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=40.0,
            audio_durations=[40.0],
        )
        fc = cmd[cmd.index("-filter_complex") + 1]
        # 不使用 (on+offset) 格式(各段 cycle_offset 不同就夠了)
        assert "(on+" not in fc
        assert "(n+" not in fc


class TestBitrateSettings:
    """測試 8 Mbps 位元率上限"""

    def _build_single_cmd(self, encoder: str):
        renderer = FFmpegRenderer(fps=30)
        return renderer.build_command(
            image_paths=["/tmp/a.jpg"],
            audio_paths=["/tmp/a.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=10.0,
            encoder=encoder,
        )

    def test_h264_nvenc_has_vbr_bitrate_cap(self):
        cmd = self._build_single_cmd("h264_nvenc")
        assert "-rc" in cmd and cmd[cmd.index("-rc") + 1] == "vbr"
        assert "-b:v" in cmd and cmd[cmd.index("-b:v") + 1] == "8M"
        assert "-maxrate" in cmd and cmd[cmd.index("-maxrate") + 1] == "10M"
        assert "-bufsize" in cmd and cmd[cmd.index("-bufsize") + 1] == "16M"
        assert "-cq" not in cmd  # 改用位元率控制，不再使用 -cq

    def test_h265_nvenc_has_vbr_bitrate_cap(self):
        cmd = self._build_single_cmd("h265_nvenc")
        assert cmd[cmd.index("-rc") + 1] == "vbr"
        assert cmd[cmd.index("-b:v") + 1] == "8M"
        assert cmd[cmd.index("-maxrate") + 1] == "10M"
        assert cmd[cmd.index("-bufsize") + 1] == "16M"

    def test_libx264_has_crf_with_maxrate(self):
        cmd = self._build_single_cmd("libx264")
        assert "-crf" in cmd and cmd[cmd.index("-crf") + 1] == "20"
        assert cmd[cmd.index("-maxrate") + 1] == "10M"
        assert cmd[cmd.index("-bufsize") + 1] == "16M"

    def test_multi_segment_applies_bitrate_cap(self):
        renderer = FFmpegRenderer(fps=30)
        cmd = renderer.build_command(
            image_paths=["/tmp/a.jpg", "/tmp/b.jpg"],
            audio_paths=["/tmp/a.mp3", "/tmp/b.mp3"],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=40.0,
            encoder="h264_nvenc",
            audio_durations=[20.0, 20.0],
        )
        assert cmd[cmd.index("-b:v") + 1] == "8M"
        assert cmd[cmd.index("-maxrate") + 1] == "10M"
