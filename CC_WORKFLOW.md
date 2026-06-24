# CC_WORKFLOW.md

## 开发前同步规则

- 每次开始新模块前，必须先确认工作区干净。
- 如果 git status 存在未提交改动，必须停止并说明，不得切分支、pull 或开发。
- 必须切换到 `dev/full-product`。
- 必须拉取 `origin/dev/full-product` 最新代码。
- 必须从最新 `dev/full-product` 创建当前模块 feature 分支。
- 如果当前模块 feature 分支已存在，必须确认该分支只属于当前模块，不得复用其他模块分支。

## 标准工作流

用户会指定一个模块目录，例如：按 desktop/modules/ocr/TASK.md 开发 OCR 模块。

每次开发新模块前，必须切回 `dev/full-product` 并拉取 `origin/dev/full-product` 最新代码。

CC 必须执行：

1. 阅读根目录规则文档。
2. 阅读 shared-contract/API_INDEX.md、shared-contract/CONTRACT_TESTING.md、shared-contract/openapi/*.yaml、cloud/DATABASE_SCHEMA.md、docs/architecture/MODULE_INTERFACES.md。
3. 阅读模块目录下所有执行文档。
4. 检查全局依赖台账，不重复安装已登记依赖。
5. 确认或创建模块分支。
6. 只在允许目录内开发。
7. 开发完成后运行模块测试。
8. 测试失败必须先定位根因，再修复。
9. 修复后重新运行失败测试和模块完整测试。
10. 更新模块 PROGRESS.md、ACCEPTANCE.md。
11. 提交、推送，并写中文备注。
12. 停止开发，等待用户指定下一个模块。

如果模块需要新增接口、字段、DTO、数据库表或模块调用关系，必须先更新对应权威规格文档，再写代码。涉及接口联调时，必须先让 mock API 和桌面端 API client 对齐 OpenAPI。

## Bug 修复工作流

后续出现的 bug 修复必须按模块归属处理，不得直接在 `dev/full-product` 或 `main` 上修改。

1. 先确认 bug 归属模块，例如 `desktop/modules/auth-device`、`cloud/app-shell`、`cloud/modules/ai-copy` 或 `shared-contract/openapi/...`。
2. 从最新 `dev/full-product` 创建修复分支，分支命名使用 `fix/<模块名>-<问题简述>`，例如 `fix/cloud-app-shell-router-registration` 或 `fix/desktop-settings-server-url`。
3. 只修改修复该 bug 必需的文件；不得把无关重构、新功能或其他模块改动混入同一修复分支。
4. 如果修复涉及接口字段、OpenAPI、DTO、数据库结构或模块调用关系，必须先更新对应权威规格文档，再修改实现代码。
5. 修复前应尽量复现问题并定位根因；修复后必须重新运行失败用例、受影响模块完整测试，涉及接口时还要运行相关契约或客户端测试。
6. 修复完成并自测通过后，必须停止并等待用户测试；只有用户明确确认测试通过后，才能提交和推送修复分支。
7. 更新对应模块 `PROGRESS.md` 的 Bug 记录或测试记录，写明 bug 现象、根因、修复点、测试命令、测试结果和分支名；提交哈希必须在用户确认通过并完成提交后补充。
8. 提交信息必须使用中文，并使用 `fix(<模块名>): <修复说明>` 格式。
9. 修复分支必须在用户测试通过后推送到 origin；是否合并到 `dev/full-product` 由用户确认。

影响当前联调、当前可运行版本、主流程或已合并模块稳定性的 bug，用户测试通过并确认后应合并到 `dev/full-product`。实验性修复、未验收修复或范围不清的修复，不得提交或推送，必须等待用户确认测试通过。

## 提交和推送前规则

- 提交前必须确认当前分支是当前模块 feature 分支，不是 main，也不是 `dev/full-product`。
- 提交前必须确认 git status 只包含当前模块允许范围内的改动。
- 提交前必须确认测试通过。
- Bug 修复提交和推送前，必须确认用户已明确测试通过。
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
