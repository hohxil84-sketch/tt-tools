# MODEL_REGISTRY.md

| 模型 | 功能 | 来源 | 版本 | 存放位置 | 大小 | 是否提交 Git | 下载方式 | 许可证 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| ch_PP-OCRv4_det_infer.onnx | OCR 文字检测 | RapidOCR/PaddleOCR | v4 | rapidocr_onnxruntime/models/（site-packages 内，随 pip 包安装） | ~4.5 MB | 否 | pip install rapidocr-onnxruntime | Apache 2.0 | active |
| ch_ppocr_mobile_v2.0_cls_infer.onnx | OCR 文字方向分类 | RapidOCR/PaddleOCR | v2.0 | rapidocr_onnxruntime/models/（site-packages 内，随 pip 包安装） | ~0.6 MB | 否 | pip install rapidocr-onnxruntime | Apache 2.0 | active |
| ch_PP-OCRv4_rec_infer.onnx | OCR 文字识别 | RapidOCR/PaddleOCR | v4 | rapidocr_onnxruntime/models/（site-packages 内，随 pip 包安装） | ~10.4 MB | 否 | pip install rapidocr-onnxruntime | Apache 2.0 | active |
| 待定 | 抠图 | 待选型 | 待定 | 待定 | 待定 | 否 | 待定 | 待确认 | active |
| u2net.onnx | 智能抠图 | rembg / U²-Net | v0.0.0 | %USERPROFILE%\\.u2net\\u2net.onnx | ~168 MB | 否 | 手动下载 → rembg 自动加载 | MIT | active |
| u2netp.onnx | 智能抠图（轻量） | rembg / U²-Net | v0.0.0 | %USERPROFILE%\\.u2net\\u2netp.onnx | ~4.4 MB | 否 | 手动下载 → rembg 自动加载 | MIT | active |

## 存放规则

模型文件必须优先存放在 D:\localPath\models 下，并登记实际路径、来源、版本和许可证。模型文件不得提交 Git。

