# TODO

## 臉部偵測服務（`backend/services/face_detection_service.py`）潛在問題

2026-09-05 排查「側臉未被偵測」時確認的三個問題。當時真正的原因是後端跑在缺少 `imgutils` 的 Anaconda 環境
（已由 `start.bat` 一鍵啟動器解決），以下三點不影響目前的正常流程，但會讓偵測在特定情況下靜默失效。

1. **`cv2.imread` 讀不到非 ASCII 路徑**（第 46 行與第 110 行）
   Windows 的 OpenCV 無法開啟含中日文的路徑。imgutils 已偵測到臉，服務層取圖片尺寸時卻回傳空列表。
   目前 quick-render 存 uuid 檔名所以沒踩到；`UPLOAD_DIR` 設在非 ASCII 目錄就會壞。
   修法：改用 PIL 取尺寸，或 `cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)`。

2. **多臉時只依信心度選臉**（`KenBurnsService.compute_face_safe_params` 取 `faces[0]`）
   鏡面反射圖實測主角 0.837 vs 倒影 0.821，只差 0.016，容易選錯。
   修法：以臉框面積為主、信心度為輔（主角通常是畫面中最大的臉）。

3. **退回 cascade 偵測器時只記 `info` log**（`_check_imgutils`）
   imgutils 不可用時靜默退回只認正面臉的 `lbpcascade_animeface`，使用者無從得知。
   修法：升為 `warning`，並在渲染進度或 API 回應中標示「使用降級偵測器」。

處理時依專案慣例先寫失敗測試再修。
