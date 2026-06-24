# SETUP_HISTORY.md

初始化：仅创建文档骨架，未安装任何新依赖。

依赖路径规则更新：后续下载依赖、安装包、模型、工具缓存或任何外部资源时，必须优先放到 D:\localPath，并在依赖台账中记录实际路径。

2026-06-03：
- D:\localPath 目录结构创建完毕（downloads、tools、caches\nuget、venvs、models、logs）。
- .NET SDK 8.0.421 安装到 C:\Program Files\dotnet（系统级安装），安装包存放在 D:\localPath\downloads\dotnet-sdk-8.0.421-win-x64.exe。
- NuGet 全局包缓存配置到 D:\localPath\caches\nuget（通过 desktop/app-shell/TTShell/nuget.config）。
- 首次引入模块：desktop/app-shell。
- WPF 主程序外壳项目创建并编译通过（0 错误 0 警告）。

2026-06-03（local-worker-shared）：
- 创建 Python 虚拟环境 D:\localPath\venvs\local-worker-shared（系统 Python 3.12.10）。
- 首次引入模块：local-worker/shared。
- 确认 GitHub CLI 2.93.0 + Git 2.54.0 可用。
- 本地 worker 公共层 5 个子模块创建完毕（errors、runtime、model_registry、file_io、logging）。
- 40 项单元测试全部通过，0 失败 0 警告。

2026-06-03（desktop-shared）：
- 创建桌面端公共层类库项目 DesktopShared（TTShared，net8.0-windows WPF Library）。
- 引入 NuGet 包 System.Security.Cryptography.ProtectedData 8.0.0 到 D:\localPath\caches\nuget。
- 首次引入模块：desktop/shared。
- 8 个子模块创建完毕：Auth、CloudApi、LocalRuntime、FileSystem、JobSystem、Logging、Settings、UI。
- 59 项单元测试全部通过，0 失败 0 警告。

2026-06-03（contract-base-rules）：
- 引入 Spectral 6.16.0（OpenAPI 校验工具），通过 npx 按需运行，npm 缓存指向 D:\localPath\caches\npm。

2026-06-20（cloud-app-shell）：
- 发现系统无可用 Python（原台账登记 D:\APPLICATION\Python312 不存在）。
- 下载 Python 3.11.9 安装包到 D:\localPath\downloads\python-3.11.9-amd64.exe。
- 安装 Python 3.11.9 到 C:\Program Files\Python311（系统级安装，对齐 TOOLCHAIN.md 云端推荐版本）。
- 创建 Python 虚拟环境 D:\localPath\venvs\cloud-app-shell。
- 安装 pip 依赖：fastapi 0.138.0、uvicorn 0.49.0、pydantic-settings 2.14.2、httpx 0.28.1、pytest 9.1.1、pytest-asyncio 1.4.0。
- 首次引入模块：cloud/app-shell。
- cloud-app-shell 模块 5 个源文件创建完毕（config.py、middleware.py、health.py、main.py、requirements.txt）。
- 4 个测试文件创建完毕（conftest.py、test_config.py、test_health.py、test_middleware.py）。
- 23 项单元测试全部通过，0 失败 0 警告。

2026-06-20（cloud-shared）：
- 在 D:\localPath\venvs\cloud-app-shell 追加安装依赖：sqlalchemy 2.0.51、asyncpg 0.31.0、python-jose 3.5.0、passlib 1.7.4、bcrypt 5.0.0、python-multipart 0.0.32、aiosqlite 0.22.1。
- 该 venv 更新为 cloud 公共 venv（cloud-app-shell + cloud-shared 共用）。
- 首次引入模块：cloud/shared。
- cloud-shared 模块 8 个源文件创建完毕（config.py、database.py、errors.py、request_id.py、logging_config.py、auth.py、permissions.py、__init__.py）。
- 6 个测试文件创建完毕（__init__.py、conftest.py、test_errors.py、test_request_id.py、test_auth.py、test_database.py、test_permissions.py）。
- 47 项单元测试全部通过，0 失败 0 警告。

2026-06-20（local-worker-ocr）：
- 使用系统 Python 3.12.10 创建虚拟环境 D:\localPath\venvs\local-worker-ocr。
- 安装 pip 依赖：rapidocr-onnxruntime 1.4.4（含 onnxruntime 1.27.0、opencv-python 4.13.0.92、numpy 2.4.6、Pillow 12.2.0 等依赖）、pytest 9.1.1。
- 首次引入模块：local-worker/modules/ocr。
- OCR 选型：RapidOCR（基于 ONNX Runtime，PaddleOCR v4 模型，Apache 2.0）。
- OCR 模块 4 个源文件创建完毕（__init__.py、engine.py、results.py）、测试文件（__init__.py、test_ocr.py）。
- 29 项单元测试全部通过，0 失败 0 警告（含 Python 版本检查、引擎初始化、文件/数组/bytes 识别、输入校验、结果结构、批量识别、上下文管理器、GPU 检测、便捷函数、置信度过滤）。

2026-06-20（local-worker-preflight-check）：
- 使用系统 Python 3.12.10 创建虚拟环境 D:\localPath\venvs\local-worker-preflight-check。
- 安装 pip 依赖：Pillow 12.2.0、pytest 9.1.1。
- 首次引入模块：local-worker/modules/preflight-check。
- 技术选型：Pillow（HPND 许可证），用于图像元数据读取（DPI/颜色模式/Alpha 通道/尺寸），不依赖 OpenCV/GPU/ML 模型。
- 印前检查模块 4 个源文件创建完毕（__init__.py、checker.py、report.py）、测试文件（__init__.py、test_preflight.py）。
- 29 项单元测试全部通过，0 失败 0 警告（含格式检查、尺寸检查、DPI 检查、颜色模式检查、透明通道检查、低清风险检查、文件大小检查、错误处理、报告结构、枚举验证、阈值验证）。

2026-06-20（local-worker-id-photo）：
- 使用系统 Python 3.12.10 创建虚拟环境 D:\localPath\venvs\local-worker-id-photo。
- 安装 pip 依赖：opencv-python 4.13.0.92（含 numpy 2.4.6）、Pillow 12.2.0、pytest 9.1.1。
- 首次引入模块：local-worker/modules/id-photo。
- 技术选型：OpenCV（Apache 2.0 许可证），用于颜色距离背景检测、GrabCut 分割、形态学处理、Alpha 混合；不依赖额外 ML 模型，所有算法纯图像处理，支持 CPU-only 运行。
- 证件照换底色模块 3 个源文件创建完毕（__init__.py、specifications.py、processor.py）、测试文件（__init__.py、test_id_photo.py）。
- 58 项单元测试全部通过，0 失败 0 警告（含规格/底色查询、背景检测、颜色遮罩/GrabCut 遮罩、背景替换、规格缩放、完整流程、文件 I/O、错误处理、元数据、输出合理性）。

2026-06-21（local-worker-remove-bg）：
- 使用系统 Python 3.12.10 创建虚拟环境 D:\localPath\venvs\local-worker-remove-bg。
- 安装 pip 依赖：rembg[cpu] 2.0.76（含 onnxruntime 1.27.0）、opencv-python 4.13.0.92、Pillow 12.2.0、numpy 2.4.6、pytest 9.1.1。
- 首次引入模块：local-worker/modules/remove-bg。
- 技术选型：rembg（MIT 许可证），基于 ONNX Runtime + u2net 模型族，无需 PyTorch/GPU，支持 CPU-only 运行。
- 模型 u2net.onnx（168MB）、u2netp.onnx（4.4MB）手动下载到 %USERPROFILE%\.u2net\（rembg 默认缓存目录）。
- 智能抠图模块 2 个源文件创建完毕（__init__.py、processor.py）、测试文件（__init__.py、test_remove_bg.py）。
- 32 项单元测试全部通过，0 失败 0 警告（含 Python/依赖检查、模块导入、模型列表、模型缓存、背景去除、文件路径 API、纯色合成、输入校验、多模型、仅遮罩、RGBA 输入、复杂场景、Alpha Matting）。

2026-06-21（local-worker-resize-image）：
- 使用系统 Python 3.12.10 创建虚拟环境 D:\localPath\venvs\local-worker-resize-image。
- 安装 pip 依赖：Pillow 12.2.0、pytest 9.1.1。
- 首次引入模块：local-worker/modules/resize-image。
- 技术选型：Pillow（HPND 许可证），纯本地图像处理，不依赖 GPU/ML 模型。
- 图片改尺寸模块 3 个源文件创建完毕（__init__.py、specifications.py、processor.py）、测试文件（__init__.py、test_resize_image.py）。
- 110 项单元测试全部通过，0 失败 0 警告（含模块导入/常量校验/参数校验/7种缩放模式/6种重采样滤镜/格式转换/预设尺寸/输入方式/文件输出/DPI处理/边缘情况/性能/便捷方法）。

2026-06-24（local-worker-pdf-image-convert）：
- 使用系统 Python 3.12.10 创建虚拟环境 D:\localPath\venvs\local-worker-pdf-image-convert。
- 安装 pip 依赖：PyMuPDF 1.27.2.3、Pillow 12.2.0、pytest 9.1.1。
- 首次引入模块：local-worker/modules/pdf-image-convert。
- 技术选型：PyMuPDF (fitz)（AGPL 3.0 许可证），纯 Python，无需外部系统依赖，支持 PDF↔图片双向转换；Pillow（HPND 许可证）作为辅助，用于图像编码和色彩空间处理。
- PDF/图片互转模块 3 个源文件创建完毕（__init__.py、specifications.py、processor.py）、测试文件（__init__.py、test_pdf_image_convert.py）。
- 60 项单元测试全部通过，0 失败 0 警告（含模块导入/常量校验/参数校验/PDF转图片/图片转PDF/主入口路由/查询方法/边界情况/结果结构/初始化）。
