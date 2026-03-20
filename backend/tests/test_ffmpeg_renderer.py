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
        """BPM=200（clamped 至 1.5）時旋轉振幅仍在安全範圍"""
        _, _, _, rot_info = self.renderer.build_zoompan_expr(bpm=200.0, total_frames=900)
        amp = rot_info["rotation_amp_deg"]
        ratio = 1.5  # clamped
        assert 8.0 * ratio <= amp <= 15.0 * ratio

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
