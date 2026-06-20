# NOTES.md - local-worker-ocr

## 设计备注

OCR 本地识别实现，候选 RapidOCR/PaddleOCR/Tesseract 需开发前选型并记录。

## 选型记录

### 候选方案

| 方案 | 引擎 | 推理 | 安装 | 中文精度 | 模型大小 | 许可证 |
|---|---|---|---|---|---|---|
| RapidOCR | ONNX Runtime | CPU/DirectML/CUDA | pip install rapidocr-onnxruntime | 高（PaddleOCR v4 模型） | ~15.5 MB | Apache 2.0 |
| PaddleOCR | PaddlePaddle | CPU/CUDA | pip install paddlepaddle + paddleocr | 最高 | ~200 MB+ | Apache 2.0 |
| Tesseract | Tesseract | CPU | 系统安装 tesseract-ocr | 低（需额外中文训练数据） | ~15 MB (chi_sim) | Apache 2.0 |

### 推荐方案：RapidOCR

**选中版本**：rapidocr-onnxruntime 1.4.4

**选型理由**：

1. **ONNX 原生**：基于 ONNX Runtime 推理，与项目 TOOLCHAIN.md 中 ONNX 技术栈一致，无需额外推理框架。
2. **轻量级**：三个模型文件总计 ~15.5 MB，pip 安装即用，无需系统级依赖。
3. **中文精度高**：使用 PaddleOCR v4 的检测和识别模型（ch_PP-OCRv4），中文印刷体识别准确率高。
4. **多后端支持**：CPU (ONNX Runtime)、DirectML (Windows GPU)、CUDA 均可选，默认 CPU 推理。
5. **pip 安装**：`pip install rapidocr-onnxruntime`，无需额外下载模型或配置环境。
6. **开源友好**：Apache 2.0 许可证，适合商业项目使用。

**模型详情**：

| 模型文件 | 功能 | 大小 |
|---|---|---|
| ch_PP-OCRv4_det_infer.onnx | 文字区域检测 | ~4.5 MB |
| ch_ppocr_mobile_v2.0_cls_infer.onnx | 文字方向分类（180° 旋转矫正） | ~0.6 MB |
| ch_PP-OCRv4_rec_infer.onnx | 文字内容识别 | ~10.4 MB |

模型随 rapidocr-onnxruntime 包安装，存放在 site-packages 下的 rapidocr_onnxruntime/models/ 目录。

**未选择方案的原因**：

- **PaddleOCR**：PaddlePaddle 框架安装体积大（~1GB），对图文店客户端过于臃肿；ONNX 转换版本（即 RapidOCR）已能满足需求。
- **Tesseract**：需要系统级安装 Tesseract OCR 引擎（Windows 下需额外配置），中文识别精度不如 PaddleOCR 模型，不适合以中文为主的图文店场景。

**GPU 加速**：

- 当前机器 GPU 检测：待首次运行后补充。
- CPU 推理在主流通用 PC 上对单张印刷品图片识别在 1-3 秒内完成，性能可接受。
- 可选 DirectML 加速（需 onnxruntime-directml 包），后续可根据需要启用。
