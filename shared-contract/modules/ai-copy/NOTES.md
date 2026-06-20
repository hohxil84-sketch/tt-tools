# NOTES.md - contract-ai-copy

## 设计备注

云端文案生成 API 契约。

- 接口：POST `/api/v1/ai/copy/generate`
- 功能码：`ai_copy_cloud`（云端 AI 付费功能）
- 请求必填：scene、product_name、selling_points、tone、client_request_id
- 请求可选：target_audience、platform、extra_requirements
- 响应数据：feature（const: ai_copy_cloud）、text、variants、provider、model、estimated_cost、credits_charged、provider_call_id
- 客户端不得提交：provider、model、estimated_cost、credits_charged 等云端决定字段
- 调用链：API endpoint → auth/device check → permission check → credits precheck → provider-runtime → provider-call-log → credits charge → usage event → unified response

## 选型记录

无需选型。本模块为 shared-contract 接口契约模块，不涉及开源项目或模型。

## DTO 文件

- Python: `shared-contract/dto/python/ai_copy.py`
- C#: `shared-contract/dto/csharp/AiCopyDto.cs`
- 测试: `shared-contract/dto/python/test_ai_copy_dto.py`（44 项）
