"""
動漫臉部偵測服務

主要使用 dghs-imgutils（ONNX YOLO 模型）偵測動漫角色臉部，
支援正面與側臉。若 imgutils 不可用，fallback 至 lbpcascade_animeface。

回傳正規化座標（0~1），供 Ken-Burns 安全區計算使用。
偵測失敗時回傳空列表，不中斷渲染流程。
"""

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# === imgutils（主要偵測器）===
_imgutils_available: Optional[bool] = None


def _check_imgutils() -> bool:
    """檢查 imgutils 是否可用（懶載入，僅檢查一次）"""
    global _imgutils_available
    if _imgutils_available is not None:
        return _imgutils_available
    try:
        from imgutils.detect import detect_faces as _  # noqa: F401
        _imgutils_available = True
        logger.info("動漫臉部偵測: 使用 imgutils (ONNX YOLO)")
    except ImportError:
        _imgutils_available = False
        logger.info("imgutils 不可用，fallback 至 lbpcascade_animeface")
    return _imgutils_available


def _detect_with_imgutils(image_path: str) -> List[Dict]:
    """使用 imgutils YOLO 偵測動漫臉部"""
    from imgutils.detect import detect_faces

    results_raw = detect_faces(image_path)
    if not results_raw:
        return []

    # 取得圖片尺寸（用於正規化）
    import cv2
    img = cv2.imread(image_path)
    if img is None:
        return []
    img_h, img_w = img.shape[:2]
    if img_h == 0 or img_w == 0:
        return []

    results = []
    for bbox, label, conf in results_raw:
        x1, y1, x2, y2 = bbox
        # 轉換為正規化座標
        nx = x1 / img_w
        ny = y1 / img_h
        nw = (x2 - x1) / img_w
        nh = (y2 - y1) / img_h
        results.append({
            "type": "face",
            "bounds": {"x": nx, "y": ny, "width": nw, "height": nh},
            "confidence": round(float(conf), 3),
        })

    results.sort(key=lambda r: r["confidence"], reverse=True)
    return results


# === lbpcascade_animeface（fallback 偵測器）===
_cascade_classifier = None
_cascade_loaded = False
_CASCADE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "resources",
    "lbpcascade_animeface.xml",
)


def _get_cascade_classifier():
    """取得快取的 cascade 分類器"""
    global _cascade_classifier, _cascade_loaded
    if _cascade_loaded:
        return _cascade_classifier
    _cascade_loaded = True

    import cv2
    if not os.path.exists(_CASCADE_PATH):
        logger.warning(f"找不到 cascade 分類器: {_CASCADE_PATH}")
        return None

    cascade = cv2.CascadeClassifier(_CASCADE_PATH)
    if cascade.empty():
        return None

    _cascade_classifier = cascade
    logger.info("Fallback 分類器 lbpcascade_animeface 載入成功")
    return _cascade_classifier


def _detect_with_cascade(image_path: str) -> List[Dict]:
    """使用 lbpcascade_animeface 偵測（僅正面臉）"""
    import cv2

    classifier = _get_cascade_classifier()
    if classifier is None:
        return []

    img = cv2.imread(image_path)
    if img is None:
        return []

    img_h, img_w = img.shape[:2]
    if img_h == 0 or img_w == 0:
        return []

    # 縮放到 640px 寬（大圖偵測不穩定）
    if img_w > 800:
        scale = 640 / img_w
        det_img = cv2.resize(img, (640, int(img_h * scale)))
    else:
        det_img = img

    det_h, det_w = det_img.shape[:2]
    gray = cv2.cvtColor(det_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    min_face = max(24, int(min(det_w, det_h) * 0.05))

    # 兩輪偵測：先嚴格再寬鬆
    faces = classifier.detectMultiScale(
        gray, scaleFactor=1.05, minNeighbors=5, minSize=(min_face, min_face),
    )
    if len(faces) == 0:
        faces = classifier.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=3, minSize=(min_face, min_face),
        )

    results = []
    for (x, y, w, h) in faces:
        nx, ny = x / det_w, y / det_h
        nw, nh = w / det_w, h / det_h
        area_ratio = nw * nh
        confidence = min(1.0, area_ratio * 20)
        results.append({
            "type": "face",
            "bounds": {"x": nx, "y": ny, "width": nw, "height": nh},
            "confidence": round(confidence, 3),
        })

    results.sort(key=lambda r: r["confidence"], reverse=True)
    return results


# === 公開 API ===

def detect_anime_faces(image_path: str) -> List[Dict]:
    """
    偵測圖片中的動漫角色臉部

    優先使用 imgutils（ONNX YOLO，支援側臉），
    不可用時 fallback 至 lbpcascade_animeface（僅正面）。

    Args:
        image_path: 圖片檔案路徑

    Returns:
        偵測結果列表，每個元素格式：
        {
            "type": "face",
            "bounds": {"x": float, "y": float, "width": float, "height": float},
            "confidence": float
        }
        所有座標為 0~1 正規化值。偵測失敗回傳空列表。
    """
    try:
        if _check_imgutils():
            results = _detect_with_imgutils(image_path)
        else:
            results = _detect_with_cascade(image_path)

        if results:
            logger.info(
                f"偵測到 {len(results)} 個臉部: {os.path.basename(image_path)} "
                f"(最大: {results[0]['bounds']['width']:.1%} × {results[0]['bounds']['height']:.1%})"
            )
        else:
            logger.debug(f"未偵測到臉部: {os.path.basename(image_path)}")

        return results

    except Exception as e:
        logger.error(f"臉部偵測異常: {e}")
        return []
