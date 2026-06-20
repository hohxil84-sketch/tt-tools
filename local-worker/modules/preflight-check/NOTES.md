# NOTES.md - local-worker-preflight-check

## 设计备注

印前检查本地实现，检查尺寸、DPI、文件类型、透明通道、低清风险等基础项。

纯本地执行，不依赖 GPU，不涉及 AI 模型，不使用 OpenCV——仅使用 Pillow 读取图像元数据。

## 选型记录

### 图像读取库

| 候选方案 | 版本 | 许可证 | 优点 | 缺点 | 是否采用 |
|---|---|---|---|---|---|
| Pillow | 12.2.0 | Historical Permission Notice and Disclaimer (HPND) | 轻量、Python 原生、读取元数据（DPI/模式/尺寸）方便、已随 local-worker-ocr 安装 | 不处理 CMYK 细节转换 | ✅ 采用 |
| OpenCV | 4.13.0 | Apache 2.0 | 功能强大、支持格式多 | 依赖较重、对元数据（DPI）支持不如 Pillow 直观、本模块不需要像素级处理 | ❌ |
| PyMuPDF | — | AGPL / 商业 | PDF 处理能力 | 本模块当前不处理 PDF、AGPL 许可证限制 | ❌（预留） |

### 推荐方案

**Pillow**（HPND 许可证）。纯 Python 图像库，读取 JPEG/PNG/TIFF 等格式的元数据（DPI、颜色模式、Alpha 通道）最为方便。已在 local-worker-ocr 模块中安装（12.2.0），本模块独立 venv 复用相同版本。

### 无需 GPU / 模型

本模块仅为图像元数据规则检查，不涉及 ML 推理或像素级处理，无需 GPU 支持，无需注册模型。
