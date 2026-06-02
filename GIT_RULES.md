# GIT_RULES.md

## 分支模型

- main：稳定版本。
- dev/full-product：全量开发集成主线。
- eature/contract-xxx：接口契约模块。
- eature/desktop-xxx：桌面端模块。
- eature/local-xxx：本地 worker 模块。
- eature/cloud-xxx：云端模块。
- eature/admin-xxx：后台模块。

## 规则

- 每次开发新模块前，必须切回 `dev/full-product` 并拉取 `origin/dev/full-product` 最新代码。
- 一个模块一个分支。
- 一个模块一个本地目录或 worktree。
- 不允许同一分支混合开发多个模块。
- 不允许直接在 main 开发。
- 模块完成后合并到 dev/full-product。

## 提交信息

提交信息必须使用中文，例如：

`	ext
feat(ocr): 完成本地 OCR 基础识别流程

- 新增图片识别调用入口
- 新增识别结果展示结构
- 更新 OCR 模块进度和测试记录
`
"@;
  "CODE_STYLE.md" = @"
# CODE_STYLE.md

## 中文注释

必须加中文注释的位置：权限判断、扣费逻辑、Provider 路由、本地模型加载、任务状态流转、错误处理、文件导出规则、兼容性处理、幂等、重试、超时、安全相关逻辑。

不需要注释的位置：简单变量赋值、简单 getter/setter、明显 UI 绑定、重复样板代码。

## 桌面端

- 使用 C# / .NET 8 / WPF。
- 桌面端不得保存第三方 AI API Key。
- 桌面端不得决定套餐权限和最终扣费。

## 本地 worker

- 优先使用项目虚拟环境。
- 模型文件不得提交 Git。
- 必须支持 CPU fallback，除非模块文档明确要求 GPU。

## 云端

- 所有 AI 调用必须通过 provider-runtime。
- 所有收费功能必须经过权限检查、额度检查、调用日志和扣费记录。
