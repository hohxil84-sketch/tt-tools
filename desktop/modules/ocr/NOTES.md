# NOTES.md - desktop-ocr

## 设计备注

OCR 桌面入口、文件选择、结果展示、调用 local-worker OCR。

## 选型记录

### OCR 引擎

已确定使用 RapidOCR (基于 ONNX Runtime, PaddleOCR v4 模型, Apache 2.0)，由 local-worker-ocr 提供。本模块不安装 OCR 模型，仅作为桌面端入口。

### 通信方式

桌面端通过 LocalRuntimeClient (desktop-shared) 与 Python 路由脚本 (ocr_router.py) 通信，使用 stdin/stdout JSON 协议。不用 WCF、gRPC 或 HTTP，避免引入额外服务依赖。

### 桌面技术栈

C# / .NET 8 / WPF，与整个 desktop 端保持一致。

### 不涉及的内容

- 本模块是本地免费功能，不需要云端 API 调用。
- 不需要 OpenAPI 契约变更。
- 不需要数据库表变更。
- 不需要云端权限检查。
