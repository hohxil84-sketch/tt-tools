# ACCEPTANCE.md - cloud-ai-render

## 验收状态

`READY_FOR_REVIEW`

## 验收清单

- [x] 模块目标已实现：云端效果图生成业务模块，支持 Mock Provider 调用，实现任务创建和查询。
- [x] 不包含禁止内容：未引入未登记依赖，未提交密钥/模型/缓存/构建产物，未绕过 shared-contract 或公共层。
- [x] 测试记录已写入 PROGRESS.md：22 项测试全部通过。
- [x] 新依赖和模型已登记：无新增 pip 依赖，无需登记新模型（模型台账无变化）。
- [x] 代码关键逻辑有中文注释：schemas.py、service.py、router.py、models.py 均有中文注释。

## 实现要点

- 对齐 shared-contract/openapi/ai-render.yaml 定义的两个端点
- 遵循 MODULE_INTERFACES.md 标准云端 AI 调用链
- 通过 provider-runtime 的 MockProvider 调用，不直接调用第三方 AI
- 使用 raw SQL 进行跨模块数据访问，避免 ORM 模型冲突
- 实现权限检查、额度预检查、Provider 日志、额度扣费、任务追踪全链路
- Mock 模式下任务同步完成（创建后立即 succeeded + 返回 mock 结果文件）

## 是否允许合并

是。模块开发完成，测试通过，等待合并到 dev/full-product。
