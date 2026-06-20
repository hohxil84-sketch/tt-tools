# INSTALLED_DEPENDENCIES.md

| 名称 | 类型 | 版本 | 安装位置 | 下载/缓存位置 | 用途 | 首次引入模块 | 验证命令 | 状态 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| D:\localPath | local-root | 固定路径 | D:\localPath | D:\localPath | 所有下载、安装包、模型、工具缓存优先根目录 | project | Test-Path D:\localPath | created | 2026-06-03 已创建完整目录结构：downloads、tools、caches\nuget、venvs、models、logs |
| .NET SDK | toolchain | 8.0.421 | C:\Program Files\dotnet | D:\localPath\downloads | WPF 原生客户端开发和编译 | desktop-app-shell | dotnet --version | installed | 系统级安装，安装包已在 D:\localPath\downloads\dotnet-sdk-8.0.421-win-x64.exe，NuGet 缓存配置到 D:\localPath\caches\nuget |
| Python | toolchain | 3.11.9 | C:\Program Files\Python311 | D:\localPath\downloads | 云端和 local-worker 开发 | cloud-app-shell | python --version | installed | 2026-06-20 安装 Python 3.11.9（对齐 TOOLCHAIN.md 云端推荐），安装包在 D:\localPath\downloads\python-3.11.9-amd64.exe。pip 缓存自动使用 D:\localPath\caches\pip |
| Python venv (local-worker-shared) | virtualenv | — | D:\localPath\venvs\local-worker-shared | D:\localPath\venvs | local-worker-shared 模块隔离运行环境 | local-worker-shared | D:\localPath\venvs\local-worker-shared\Scripts\python.exe --version | planned | 2026-06-03 记录，待后续 local-worker 开发时重新确认 |
| Python venv (cloud) | virtualenv | — | D:\localPath\venvs\cloud-app-shell | D:\localPath\venvs | cloud 公共隔离运行环境（cloud-app-shell + cloud-shared 共用） | cloud-app-shell / cloud-shared | D:\localPath\venvs\cloud-app-shell\Scripts\python.exe --version | installed | 2026-06-20 创建，Python 3.11.9。2026-06-20 cloud-shared 追加 SQLAlchemy / asyncpg / python-jose / passlib / bcrypt / python-multipart / aiosqlite |
| FastAPI | pip | 0.138.0 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | 云端 API 框架 | cloud-app-shell | pip show fastapi | installed | 2026-06-20 |
| uvicorn | pip | 0.49.0 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | ASGI 开发/生产服务器 | cloud-app-shell | pip show uvicorn | installed | 2026-06-20，含 standard extras |
| pydantic-settings | pip | 2.14.2 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | 应用配置管理（环境变量映射） | cloud-app-shell | pip show pydantic-settings | installed | 2026-06-20 |
| httpx | pip | 0.28.1 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | 异步 HTTP 测试客户端 | cloud-app-shell | pip show httpx | installed | 2026-06-20，测试依赖 |
| pytest | pip | 9.1.1 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | Python 测试框架 | cloud-app-shell | pip show pytest | installed | 2026-06-20 |
| pytest-asyncio | pip | 1.4.0 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | pytest 异步测试支持 | cloud-app-shell | pip show pytest-asyncio | installed | 2026-06-20 |
| SQLAlchemy | pip | 2.0.51 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | 异步 ORM（含 asyncio 扩展） | cloud-shared | pip show sqlalchemy | installed | 2026-06-20 |
| asyncpg | pip | 0.31.0 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | PostgreSQL 异步驱动 | cloud-shared | pip show asyncpg | installed | 2026-06-20 |
| python-jose | pip | 3.5.0 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | JWT 编解码（含 cryptography） | cloud-shared | pip show python-jose | installed | 2026-06-20 |
| passlib | pip | 1.7.4 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | 密码哈希库 | cloud-shared | pip show passlib | installed | 2026-06-20 |
| bcrypt | pip | 5.0.0 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | bcrypt 哈希算法（passlib 依赖） | cloud-shared | pip show bcrypt | installed | 2026-06-20 |
| python-multipart | pip | 0.0.32 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | OAuth2 表单解析（FastAPI 鉴权依赖所需） | cloud-shared | pip show python-multipart | installed | 2026-06-20 |
| aiosqlite | pip | 0.22.1 | D:\localPath\venvs\cloud-app-shell | D:\localPath\caches\pip | SQLite 异步驱动（测试用） | cloud-shared | pip show aiosqlite | installed | 2026-06-20 |
| PostgreSQL | service | 待确认 | system / docker / remote | D:\localPath\downloads / D:\localPath\tools | 云端数据库 | cloud-shared | psql --version | planned | 云端开发前确认 |
| Redis | service | 待确认 | system / docker / remote | D:\localPath\downloads / D:\localPath\tools | 缓存、队列、限流预留 | cloud-shared | redis-cli --version | planned | 云端开发前确认 |
| GitHub CLI | toolchain | 2.93.0 | system (C:\Program Files\GitHub CLI\) | D:\localPath\downloads / D:\localPath\tools | 推送、PR、CI 查询 | project | gh --version | installed | 2026-06-03 确认已安装 gh 2.93.0 + git 2.54.0 |
| System.Security.Cryptography.ProtectedData | nuget | 8.0.0 | D:\localPath\caches\nuget | D:\localPath\caches\nuget | Windows DPAPI 加密存储令牌 | desktop-shared | dotnet list package | installed | 2026-06-03 引入，用于 TokenStorage 的 access_token / refresh_token 本地安全存储 |
| Spectral (Stoplight) | OpenAPI lint | 6.16.0 | npx 缓存 (D:\localPath\caches\npm) | D:\localPath\caches\npm | OpenAPI 3.1 规范校验 | contract-base-rules | npx @stoplight/spectral-cli lint | installed | 通过 npx 按需运行，npm 缓存指向 D:\localPath |
| Python venv (local-worker-ocr) | virtualenv | — | D:\localPath\venvs\local-worker-ocr | D:\localPath\venvs | local-worker-ocr 模块隔离运行环境 | local-worker-ocr | D:\localPath\venvs\local-worker-ocr\Scripts\python.exe --version | installed | 2026-06-20 创建，Python 3.12.10，安装 rapidocr-onnxruntime 及依赖 |
| rapidocr-onnxruntime | pip | 1.4.4 | D:\localPath\venvs\local-worker-ocr | D:\localPath\caches\pip | 本地 OCR 引擎（ONNX Runtime 推理） | local-worker-ocr | pip show rapidocr-onnxruntime | installed | 2026-06-20，基于 PaddleOCR v4 模型的轻量级 OCR，Apache 2.0 |
| onnxruntime | pip | 1.27.0 | D:\localPath\venvs\local-worker-ocr | D:\localPath\caches\pip | ONNX 模型推理运行时（rapidocr 依赖） | local-worker-ocr | pip show onnxruntime | installed | 2026-06-20，CPU 版本，rapidocr-onnxruntime 自动安装 |
| opencv-python | pip | 4.13.0.92 | D:\localPath\venvs\local-worker-ocr | D:\localPath\caches\pip | 图片读取和预处理（rapidocr 依赖） | local-worker-ocr | pip show opencv-python | installed | 2026-06-20，rapidocr-onnxruntime 自动安装 |
| numpy | pip | 2.4.6 | D:\localPath\venvs\local-worker-ocr | D:\localPath\caches\pip | 数值计算（rapidocr 依赖） | local-worker-ocr | pip show numpy | installed | 2026-06-20，rapidocr-onnxruntime 自动安装 |
| Pillow | pip | 12.2.0 | D:\localPath\venvs\local-worker-ocr | D:\localPath\caches\pip | 图片生成和处理（测试用 + rapidocr 依赖） | local-worker-ocr | pip show Pillow | installed | 2026-06-20，rapidocr-onnxruntime 自动安装 |
| pytest (local-worker-ocr) | pip | 9.1.1 | D:\localPath\venvs\local-worker-ocr | D:\localPath\caches\pip | Python 测试框架 | local-worker-ocr | pip show pytest | installed | 2026-06-20，用于 OCR 模块测试 |
| Python venv (local-worker-preflight-check) | virtualenv | — | D:\localPath\venvs\local-worker-preflight-check | D:\localPath\venvs | local-worker-preflight-check 模块隔离运行环境 | local-worker-preflight-check | D:\localPath\venvs\local-worker-preflight-check\Scripts\python.exe --version | installed | 2026-06-20 创建，Python 3.12.10 |
| Pillow (local-worker-preflight-check) | pip | 12.2.0 | D:\localPath\venvs\local-worker-preflight-check | D:\localPath\caches\pip | 图像元数据读取（印前检查核心依赖） | local-worker-preflight-check | pip show Pillow | installed | 2026-06-20，用于印前检查图像元数据读取 |
| pytest (local-worker-preflight-check) | pip | 9.1.1 | D:\localPath\venvs\local-worker-preflight-check | D:\localPath\caches\pip | Python 测试框架 | local-worker-preflight-check | pip show pytest | installed | 2026-06-20，用于印前检查模块测试 |
