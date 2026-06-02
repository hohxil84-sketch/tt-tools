# CLAUDE.md

本文件是 TT Tools 项目中 Claude Code 的最高优先级开发规则。

## 角色定义

你是 TT Tools 项目的执行开发代理。你的任务是根据用户指定的模块目录和该目录下的文档完成开发、自测、修复、提交和推送。

## 必读顺序

1. CLAUDE.md
2. README.md
3. CC_WORKFLOW.md
4. GIT_RULES.md
5. CODE_STYLE.md
6. shared-contract/API_INDEX.md
7. shared-contract/CONTRACT_TESTING.md
8. shared-contract/openapi/*.yaml
9. cloud/DATABASE_SCHEMA.md
10. docs/architecture/MODULE_INTERFACES.md
11. docs/development/CC_DEVELOPMENT_ORDER_AND_TERMS.md
12. environment/DEPENDENCY_RULES.md
13. environment/INSTALLED_DEPENDENCIES.md
14. environment/TOOLCHAIN.md
15. 用户指定模块目录下的全部文档。

## 硬规则

- 只开发用户明确指定的模块。
- 不得主动开发下一个模块。
- 不得跨模块修改，除非模块 TASK.md 明确允许。
- 涉及接口变更时，必须先修改 shared-contract 对应模块。
- 涉及接口名称、请求字段、响应字段时，必须先更新 shared-contract/API_INDEX.md。
- 涉及接口机器契约时，必须先更新 shared-contract/openapi/*.yaml。
- 涉及 DTO 时，必须以 shared-contract/openapi/*.yaml 为来源。
- 涉及接口联调时，必须按 shared-contract/CONTRACT_TESTING.md 执行契约测试。
- 涉及数据库表、字段、索引时，必须先更新 cloud/DATABASE_SCHEMA.md。
- 涉及模块调用关系时，必须先更新 docs/architecture/MODULE_INTERFACES.md。
- 新依赖必须登记到 environment/INSTALLED_DEPENDENCIES.md 和 environment/SETUP_HISTORY.md。
- 新模型必须登记到 environment/MODEL_REGISTRY.md。
- 下载依赖、安装包、模型、工具缓存或任何外部资源时，必须优先放到 D:\localPath，并在依赖台账中记录实际路径。
- 代码关键逻辑必须加中文注释。
- 提交、推送、合并记录必须写中文备注。
- 测试失败时必须先复现和定位根因，再做最小范围修复。
- 当前模块完成并推送后必须停止，等待用户指定下一模块。

## 禁止事项

- 禁止直接提交或推送 main。
- 禁止未测试就提交。
- 禁止提交 API Key、Token、密钥、真实账号信息。
- 禁止提交模型大文件、缓存、构建产物、临时文件。
- 禁止客户端保存第三方 AI API Key。
- 禁止客户端决定套餐权限、最终扣费、Provider 成本、模型选择。
- 禁止业务模块直接调用 OpenAI、DeepSeek 或其他第三方 AI，必须通过云端 provider-runtime。
- 禁止引入 Electron、Tauri、MAUI、Avalonia 等非本项目确认的桌面技术栈。
- 禁止未经说明把依赖、模型、安装包、缓存下载到系统盘、用户目录或模块目录。
