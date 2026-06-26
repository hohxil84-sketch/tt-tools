# PROGRESS.md - cloud-ai-render

## 当前状态

`DEVELOPED`

## 分支

`feature/cloud-ai-render`

## 已完成

- 已创建模块文档骨架。
- 已创建 schemas.py：Pydantic DTO，对齐 shared-contract/openapi/ai-render.yaml。
  - CreateAiRenderTaskRequest（创建任务请求）
  - CreatedTaskData（创建任务响应数据）
  - AiRenderTaskData（查询任务响应数据）
  - ResultFile（结果文件信息）
  - RenderContext（服务层内部上下文）
- 已创建 models.py：AiTask ORM 模型，对齐 DATABASE_SCHEMA.md ai_tasks 表定义。
- 已创建 service.py：核心业务逻辑，实现标准云端 AI 调用链。
  - 套餐权限检查（_check_feature_permission）
  - 额度预检查（_check_credits_balance）
  - 任务记录创建和更新（_create_task_record / _update_task_result）
  - Provider Runtime 调用（通过 MockProvider + ProviderRouter）
  - Provider 调用日志写入（_insert_provider_log）
  - 额度扣费（_consume_credits）
  - Mock 效果图结果文件生成（_build_mock_result_files）
  - 任务查询（query_render_task），含跨用户隔离
- 已创建 router.py：2 个 API 端点。
  - POST /ai/render/tasks（创建效果图生成任务）
  - GET /ai/render/tasks/{task_id}（查询任务状态和结果）
- 已创建 __init__.py：模块文档。
- 已在 cloud/app-shell/main.py 注册路由。
- 已创建完整测试套件（22 项测试）。

## 测试记录

日期：2026-06-21
测试命令：python -m pytest tests/ -v
结果：22 passed, 0 failed
失败原因：无
中文备注：全部 22 项测试通过，覆盖成功场景、权限检查、额度检查、鉴权检查、请求校验、响应结构校验、任务查询、跨用户隔离、扣费验证、日志验证、幂等验证。

## 测试覆盖详情

- test_create_render_task_success_standard：标准用户成功创建任务
- test_create_render_task_success_pro：专业用户成功创建任务
- test_create_render_task_minimal_request：最小必填字段请求
- test_create_render_task_different_scenes：不同场景类型（interior_design / product_showcase / poster_design）
- test_create_render_task_with_optional_fields：带全部可选字段
- test_query_task_after_creation：创建后查询任务状态和结果
- test_query_task_response_structure_matches_openapi：查询响应对齐 OpenAPI
- test_free_user_permission_denied：免费用户权限拒绝
- test_low_balance_rejected：额度不足拒绝
- test_unauthenticated_create_rejected：未登录创建被拒绝（401）
- test_unauthenticated_query_rejected：未登录查询被拒绝（401）
- test_invalid_token_rejected：无效 Token 被拒绝（401）
- test_missing_required_fields：缺少必填字段返回 422
- test_empty_input_file_ids：空输入文件列表仍可创建
- test_query_task_not_found：任务不存在返回错误
- test_query_task_cross_user_isolation：跨用户任务隔离
- test_credits_are_consumed：扣费验证（余额减少 2）
- test_provider_call_log_written：Provider 调用日志写入验证
- test_credit_ledger_entry_created：额度流水写入验证
- test_ai_tasks_record_created：任务记录写入验证
- test_different_client_request_ids_independent：不同请求独立任务 ID
- test_create_response_structure_matches_openapi：创建响应对齐 OpenAPI

## 新增文件

- cloud/modules/ai-render/__init__.py
- cloud/modules/ai-render/schemas.py
- cloud/modules/ai-render/models.py
- cloud/modules/ai-render/service.py
- cloud/modules/ai-render/router.py
- cloud/modules/ai-render/tests/__init__.py
- cloud/modules/ai-render/tests/conftest.py
- cloud/modules/ai-render/tests/test_ai_render.py

## 修改文件

- cloud/app-shell/main.py（注册 ai-render 路由）

## 新增依赖

无。全部使用已有依赖（FastAPI、SQLAlchemy、pydantic 等，已在 cloud-app-shell venv 中）。

## Bug 记录

### 2026-06-26：路由错位 + 真实图片生成路由

- **分支**：`fix/ai-render-client-multi-fix`
- **提交**：31b5bc6
- **现象**：
  1. 效果图生成报 `[unknown] 未知错误`
  2. 返回的 Mock 图片 URL 打不开
  3. 真实图片生成 Provider 未被调用
- **根因**：
  1. main.py 注册 ai-render 路由前缺少 sys.modules 清理，导入到 provider-log 的 router
  2. Mock URL 指向假域名 `mock-cdn.tt-tools.com`
  3. `_call_provider` 硬编码 MockProvider()，未走真实路由
- **修复**：
  1. main.py 补充 sys.modules 清理（3行）
  2. Mock URL 改为 null
  3. `_call_provider` 改用 `create_default_router()` + `call_by_route(IMAGE_GENERATION, CHEAP)`，失败回退 Mock
  4. 新增 `_normalize_result_files()` 透传 Provider 真实文件
  5. `_PR_CONFLICT_NAMES` 扩展 registry/config/deepseek/doubao/http_utils
- **测试**：22 项测试全部通过

## 提交记录

- 1b1e218: feat(cloud-ai-render): 完成云端效果图生成模块开发，22项测试全部通过

## 下一步

等待用户确认后提交推送，或等待用户指定下一模块。
