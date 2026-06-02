# GIT_RULES.md

## 分支模型

- main：稳定版本。
- dev/full-product：全量开发集成主线。
- feature/contract-xxx：接口契约模块。
- feature/desktop-xxx：桌面端模块。
- feature/local-xxx：本地 worker 模块。
- feature/cloud-xxx：云端模块。
- feature/admin-xxx：后台模块。

## 开发前同步规则

- 每次开始新模块前，必须先确认工作区干净。
- 如果 git status 存在未提交改动，必须停止并说明，不得切分支、pull 或开发。
- 必须切换到 `dev/full-product`。
- 必须拉取 `origin/dev/full-product` 最新代码。
- 必须从最新 `dev/full-product` 创建当前模块 feature 分支。
- 如果当前模块 feature 分支已存在，必须确认该分支只属于当前模块，不得复用其他模块分支。

## 模块分支规则

- 一个模块一个分支。
- 一个模块一个本地目录或 worktree。
- 不允许同一分支混合开发多个模块。
- 不允许直接在 main 开发。

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

## 提交信息

提交信息必须使用中文，例如：

```
feat(ocr): 完成本地 OCR 基础识别流程

- 新增图片识别调用入口
- 新增识别结果展示结构
- 更新 OCR 模块进度和测试记录
```
