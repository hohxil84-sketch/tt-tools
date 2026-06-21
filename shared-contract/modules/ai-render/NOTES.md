# NOTES.md - contract-ai-render

## 设计备注

云端效果图生成 API 契约。

- 接口：POST `/api/v1/ai/render/tasks`（创建任务）、GET `/api/v1/ai/render/tasks/{task_id}`（查询任务）
- 功能码：`ai_render_cloud`（云端 AI 付费功能）
- 创建任务请求必填：scene_type、prompt、input_file_ids、client_request_id
- 创建任务请求可选：style、size
- 创建任务响应数据：task_id、status、feature（const: ai_render_cloud）、estimated_credits
- 查询任务响应数据：task_id、status、feature（const: ai_render_cloud）、result_files、provider、model、estimated_cost、credits_charged、provider_call_id
- 客户端不得提交：user_id、device_id、role、plan_code、provider、model、estimated_cost、credits_charged 等云端决定字段
- 调用链：API endpoint → auth/device check → permission check → credits precheck → provider-runtime → provider-call-log → credits charge → usage event → unified response
- status 枚举：queued（排队中）、running（处理中）、succeeded（成功）、failed（失败）
- result_files 在 succeeded 时包含生成的效果图文件列表，其他状态为空数组

## 选型记录

无需选型。本模块为 shared-contract 接口契约模块，不涉及开源项目或模型。

## DTO 文件

- OpenAPI: `shared-contract/openapi/ai-render.yaml` v0.1.0（Spectral 校验 0 errors）
- Python: `shared-contract/dto/python/ai_render.py`
- C#: `shared-contract/dto/csharp/AiRenderDto.cs`
- 测试: `shared-contract/dto/python/test_ai_render_dto.py`（81 项）

