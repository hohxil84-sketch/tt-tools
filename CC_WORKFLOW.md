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
