# INSTALLED_DEPENDENCIES.md

| 名称 | 类型 | 版本 | 安装位置 | 下载/缓存位置 | 用途 | 首次引入模块 | 验证命令 | 状态 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| D:\localPath | local-root | 固定路径 | D:\localPath | D:\localPath | 所有下载、安装包、模型、工具缓存优先根目录 | project | Test-Path D:\localPath | planned | 首次安装依赖前创建 |
| .NET SDK | toolchain | 待确认 | system | D:\localPath\downloads 或 D:\localPath\tools | WPF 原生客户端 | desktop-app-shell | dotnet --version | planned | 首次开发桌面端前确认 |
| Python | toolchain | 3.11 优先 | system / D:\localPath\venvs | D:\localPath\downloads / D:\localPath\caches | local-worker 和 cloud | local-worker-shared / cloud-app-shell | python --version | planned | 不重复安装，确认后登记实际版本 |
| PostgreSQL | service | 待确认 | system / docker / remote | D:\localPath\downloads / D:\localPath\tools | 云端数据库 | cloud-shared | psql --version | planned | 云端开发前确认 |
| Redis | service | 待确认 | system / docker / remote | D:\localPath\downloads / D:\localPath\tools | 缓存、队列、限流预留 | cloud-shared | redis-cli --version | planned | 云端开发前确认 |
| GitHub CLI | toolchain | 待确认 | system | D:\localPath\downloads / D:\localPath\tools | 推送、PR、CI 查询 | project | gh --version | planned | 提交推送前确认 |
