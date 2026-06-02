# SETUP_HISTORY.md

初始化：仅创建文档骨架，未安装任何新依赖。

依赖路径规则更新：后续下载依赖、安装包、模型、工具缓存或任何外部资源时，必须优先放到 D:\localPath，并在依赖台账中记录实际路径。

2026-06-03：
- D:\localPath 目录结构创建完毕（downloads、tools、caches\nuget、venvs、models、logs）。
- .NET SDK 8.0.421 安装到 C:\Program Files\dotnet（系统级安装），安装包存放在 D:\localPath\downloads\dotnet-sdk-8.0.421-win-x64.exe。
- NuGet 全局包缓存配置到 D:\localPath\caches\nuget（通过 desktop/app-shell/TTShell/nuget.config）。
- 首次引入模块：desktop/app-shell。
- WPF 主程序外壳项目创建并编译通过（0 错误 0 警告）。
