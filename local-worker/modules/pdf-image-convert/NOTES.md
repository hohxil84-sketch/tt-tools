# NOTES.md - local-worker-pdf-image-convert

## 设计备注

PDF/图片互转本地实现，支持单文件和后续批量扩展。

## 选型记录

### 核心库选型

| 方案 | 许可证 | 优点 | 缺点 | 结论 |
|------|--------|------|------|------|
| **PyMuPDF (fitz)** | AGPL 3.0 | 纯 Python，无需外部系统依赖；支持 PDF→Image 和 Image→PDF 双向；速度快；Windows 原生支持 | AGPL 许可证对闭源商用有要求（需商业授权） | ✅ **采用** |
| pdf2image | MIT | 纯 Python 包 | 依赖 poppler-utils 系统安装（Windows 下需额外安装二进制）；仅支持 PDF→Image | ❌ |
| pdfkit | MIT | 使用简单 | 依赖 wkhtmltopdf；不支持 PDF→Image | ❌ |
| ReportLab | BSD | 纯 Python PDF 生成 | 仅支持 Image→PDF；API 复杂 | ❌ |
| Pillow | HPND | 已在项目中广泛使用 | PDF 支持有限（仅读取单页、不支持写入多页 PDF） | 已采用，作为辅助 |

### 推荐方案

- **PDF 转图片**：PyMuPDF (fitz) — 将 PDF 每页通过缩放矩阵渲染为指定 DPI 的像素图，再通过 Pillow 编码为 PNG/JPEG。
- **图片转 PDF**：PyMuPDF (fitz) — 创建空白 PDF 文档，通过 `new_page` + `insert_image` 逐张插入图片。

### 许可证说明

PyMuPDF 使用 AGPL 3.0 许可证。如果 TT Tools 作为闭源商用产品分发，需要购买 PyMuPDF 的商业许可证。当前阶段为开发/内部测试，可使用 AGPL 版本。

### 系统要求

- 纯 CPU 运行，不依赖 GPU
- 不涉及 AI 模型
- Windows 10/11 原生支持
- Python 3.12+ 兼容

## 已安装依赖

- PyMuPDF 1.27.2.3 — PDF 渲染和创建核心引擎
- Pillow 12.2.0 — 图像编码/解码、色彩空间处理
- pytest 9.1.1 — 测试框架
