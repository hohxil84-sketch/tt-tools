# TT Tools

TT Tools 是面向快印/图文店的纯原生 Windows 工作助手。

## 顶层目录

- desktop/：C# / .NET 8 / WPF 原生桌面端。
- local-worker/：Python / ONNX / OpenCV 本地处理引擎。
- cloud/：FastAPI 云端、后台、Provider 公共调用层。
- shared-contract/：OpenAPI、DTO、错误码、功能码、计费规则。
- environment/：全局工具链、依赖台账、模型台账。
- official-website/：官网占位，当前阶段不开发。

## 开发方式

- 一个模块一个目录。
- 一个模块一个分支。
- 用户指定哪个模块，CC 只开发哪个模块。
- 模块完成后必须测试、记录中文进度、提交、推送，并等待用户指定下一模块。
- 新依赖必须登记到全局依赖表。
- 下载依赖、安装包、模型、工具缓存或任何外部资源时，必须优先放到 D:\localPath。
- 代码关键逻辑必须写中文注释。

## 权威规格文档

- 接口名称、请求字段、响应字段：shared-contract/API_INDEX.md
- 机器可校验 OpenAPI 契约：shared-contract/openapi/*.yaml
- 契约测试规则：shared-contract/CONTRACT_TESTING.md
- DTO 规则：shared-contract/dto/README.md
- 数据库表结构、字段、索引：cloud/DATABASE_SCHEMA.md
- 模块调用边界：docs/architecture/MODULE_INTERFACES.md
- 两台 CC 开发顺序和术语：docs/development/CC_DEVELOPMENT_ORDER_AND_TERMS.md
- 功能码：shared-contract/feature-codes.md
- 计费规则：shared-contract/pricing-rules.md

模块目录下的文档用于执行单个模块，以上文档用于保证全局一致性。发生冲突时，先更新权威规格文档，再更新模块文档。
