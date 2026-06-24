# ACCEPTANCE.md - desktop-ai-copy-client

## 验收状态

`READY_FOR_REVIEW`

## 验收清单

- [x] 模块目标已实现：云端文案生成桌面入口，调用 ai-copy 契约并展示扣费和结果。
- [x] 不包含禁止内容：不调用第三方 AI API、不保存 API Key、不决定套餐权限和扣费。
- [x] 测试记录已写入 PROGRESS.md：28 个单元测试全部通过。
- [x] 新依赖和模型已登记：模块无新增依赖，复用 DesktopShared 已有能力。
- [x] 代码关键逻辑有中文注释。

## 模块实现概要

- **AiCopyViewModel**：管理文案生成完整流程，包括参数配置、场景/语气/平台预设、卖点管理、CloudApiClient 调用、结果展示和历史记录。
- **AiCopyView**：WPF UserControl，左右分栏布局（输入表单 / 结果+历史），支持动态主题。
- **DesktopAiCopyClient.Tests**：28 个 xUnit 测试，覆盖 ViewModel 全部核心逻辑。

## 技术笔记

- 本模块为纯云端 AI 模块，不依赖 local-worker（无 Python router）。
- 所有 AI 调用经过 CloudApiClient → 云端 provider-runtime，符合项目架构规则。
- 客户端不提交 provider、model、estimated_cost、credits_charged 等决策字段。
- DTO 严格对应 shared-contract/openapi/ai-copy.yaml 和 shared-contract/API_INDEX.md。

## 是否允许合并

是。核心功能已实现，测试全部通过。
