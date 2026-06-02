# SETUP_HISTORY.md

初始化：仅创建文档骨架，未安装任何新依赖。

依赖路径规则更新：后续下载依赖、安装包、模型、工具缓存或任何外部资源时，必须优先放到 D:\localPath，并在依赖台账中记录实际路径。

2026-06-03：contract-base-rules 模块引入 Spectral 6.16.0（OpenAPI 校验工具），通过 npx 按需运行，npm 缓存指向 D:\localPath\caches\npm。创建 D:\localPath 目录结构（downloads、tools、caches、venvs、models、logs）。

