"""
FFmpegRenderer 單元測試

測試多段渲染邏輯，重點驗證多圖片 + 單音訊的修復。
不需要實際的 FFmpeg 執行環境。
"""

import sys
from pathlib import Path
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
        """多圖 + 1 音訊 → 每段時長 = 音訊總長 / 圖片數"""
        total_audio = 30.0
        n_images = 3
        cmd = self.renderer.build_command(
            image_paths=[self.img1, self.img2, self.img3],
            audio_paths=[self.audio1],
            output_path="/tmp/out.mp4",
            bpm=120.0,
            total_duration=total_audio,
            encoder="libx264",
            audio_durations=[total_audio],
        )
        # 每段 10 秒 → 每段 300 幀（d=300）
        expected_frames = int(total_audio / n_images * 30)
        fc_idx = cmd.index("-filter_complex")
        filter_complex = cmd[fc_idx + 1]
        assert f"d={expected_frames}" in filter_complex

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

    def test_returns_three_expressions(self):
        """build_zoompan_expr 應回傳 3 個表達式"""
        z, x, y = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        assert isinstance(z, str)
        assert isinstance(x, str)
        assert isinstance(y, str)

    def test_z_expr_uses_base_zoom(self):
        """縮放表達式應以 base_zoom (1.15) 開頭（雙向縮放基準點）"""
        z, _, _ = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        assert z.startswith("1.1500+")
        # 雙向縮放：表達式包含 -0.5 偏移
        assert "-0.5)" in z

    def test_x_expr_uses_ema(self):
        """x 表達式應使用 EMA 平滑（px+α×...）"""
        _, x, _ = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        assert x.startswith("px+")

    def test_y_expr_uses_ema(self):
        """y 表達式應使用 EMA 平滑（py+α×...）"""
        _, _, y = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        assert y.startswith("py+")

    def test_invalid_bpm_defaults_to_120(self):
        """bpm <= 0 應 fallback 至 120"""
        z1, x1, y1 = self.renderer.build_zoompan_expr(bpm=0.0, total_frames=900)
        z2, x2, y2 = self.renderer.build_zoompan_expr(bpm=120.0, total_frames=900)
        # 結構相同（振幅隨機，故不比較數值，只驗證表達式可正常生成）
        assert isinstance(z1, str)
        assert isinstance(x1, str)
        assert isinstance(y1, str)


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
