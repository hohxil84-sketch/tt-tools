# INSTALLED_DEPENDENCIES.md

| 名称 | 类型 | 版本 | 安装位置 | 下载/缓存位置 | 用途 | 首次引入模块 | 验证命令 | 状态 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| D:\localPath | local-root | 固定路径 | D:\localPath | D:\localPath | 所有下载、安装包、模型、工具缓存优先根目录 | project | Test-Path D:\localPath | created | 2026-06-03 已创建完整目录结构：downloads、tools、caches\nuget、venvs、models、logs |
| .NET SDK | toolchain | 8.0.421 | C:\Program Files\dotnet | D:\localPath\downloads | WPF 原生客户端开发和编译 | desktop-app-shell | dotnet --version | installed | 系统级安装，安装包已在 D:\localPath\downloads\dotnet-sdk-8.0.421-win-x64.exe，NuGet 缓存配置到 D:\localPath\caches\nuget |
| Python | toolchain | 3.12.10 | D:\APPLICATION\Python312 | D:\localPath\downloads / D:\localPath\caches | local-worker 和 cloud | local-worker-shared / cloud-app-shell | python --version | installed | 系统已有 Python 3.12.10，向后兼容 3.11。虚拟环境已创建：D:\localPath\venvs\local-worker-shared |
| Python venv (local-worker-shared) | virtualenv | — | D:\localPath\venvs\local-worker-shared | D:\localPath\venvs | local-worker-shared 模块隔离运行环境 | local-worker-shared | D:\localPath\venvs\local-worker-shared\Scripts\python.exe --version | installed | 2026-06-03 创建，使用系统 Python 3.12.10，无额外 pip 依赖 |
| PostgreSQL | service | 待确认 | system / docker / remote | D:\localPath\downloads / D:\localPath\tools | 云端数据库 | cloud-shared | psql --version | planned | 云端开发前确认 |
| Redis | service | 待确认 | system / docker / remote | D:\localPath\downloads / D:\localPath\tools | 缓存、队列、限流预留 | cloud-shared | redis-cli --version | planned | 云端开发前确认 |
| GitHub CLI | toolchain | 2.93.0 | system (C:\Program Files\GitHub CLI\) | D:\localPath\downloads / D:\localPath\tools | 推送、PR、CI 查询 | project | gh --version | installed | 2026-06-03 确认已安装 gh 2.93.0 + git 2.54.0 |
