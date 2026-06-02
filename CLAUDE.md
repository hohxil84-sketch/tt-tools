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

## 开发前 Git 流程

每次开发新模块前，必须切回 `dev/full-product` 并拉取 `origin/dev/full-product` 最新代码。

1. 切回 `dev/full-product` 分支。
2. 拉取最新 `origin/dev/full-product`。
3. 从最新 `dev/full-product` 创建当前模块分支。
4. 开始开发当前模块。

## 开发前同步规则

- 每次开始新模块前，必须先确认工作区干净。
- 如果 git status 存在未提交改动，必须停止并说明，不得切分支、pull 或开发。
- 必须切换到 `dev/full-product`。
- 必须拉取 `origin/dev/full-product` 最新代码。
- 必须从最新 `dev/full-product` 创建当前模块 feature 分支。
- 如果当前模块 feature 分支已存在，必须确认该分支只属于当前模块，不得复用其他模块分支。

## 提交和推送前规则

- 提交前必须确认当前分支是当前模块 feature 分支，不是 main，也不是 `dev/full-product`。
- 提交前必须确认 git status 只包含当前模块允许范围内的改动。
- 提交前必须确认测试通过。
- 提交信息必须使用中文。
- 推送当前 feature 分支前，如果远程已有同名分支，必须先拉取远程同名分支最新内容。
- 如果拉取后有冲突，必须停止并说明，不得强行解决。
- 禁止强推。
- 推送完成后必须在模块 PROGRESS.md 中记录分支名、提交哈希、测试结果和中文说明。

## 合并到 dev/full-product 前规则

- 合并前必须确认当前模块 feature 分支已推送到 origin。
- 必须记录当前模块分支名和提交哈希。
- 必须切换到 `dev/full-product`。
- 必须拉取 `origin/dev/full-product` 最新代码。
- 再将当前模块 feature 分支合并到 `dev/full-product`。
- 如果合并冲突，必须停止并说明，不得强行解决。
- 合并后必须运行必要测试。
- 合并后必须更新全局 PROGRESS.md。
- 推送 `dev/full-product` 前，必须再次拉取 `origin/dev/full-product`。
- 如果再次拉取后出现冲突或远程有新提交，必须停止并说明。
- 禁止强推。
- 禁止合并 main。
- 禁止直接推送 main。

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
- D:\localPath 是下载、缓存、模型、安装包、临时文件的存放目录，不是所有软件的强制安装目录。
- 对必须系统级安装的软件（如 .NET SDK），安装包必须下载到 D:\localPath\downloads，实际安装位置可以使用系统默认，安装原因和实际路径必须写入 environment/INSTALLED_DEPENDENCIES.md，安装动作必须写入 environment/SETUP_HISTORY.md。
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
