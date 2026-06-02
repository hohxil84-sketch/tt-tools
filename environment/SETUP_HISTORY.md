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
