# API_INDEX.md

本文件是桌面端和云端通信的权威接口清单。CC 开发任何涉及云端通信的模块前，必须先阅读本文件。

机器可校验契约位于 `shared-contract/openapi/*.yaml`。如果本文件和 OpenAPI 不一致，以 OpenAPI 为准，并立即同步修正文档。

## 全局规则

- API 版本前缀：`/api/v1`
- 认证方式：`Authorization: Bearer <access_token>`
- 统一响应：`success / data / error / request_id`

客户端不得提交最终决策字段：`user_id`、`device_id`、`role`、`plan_code`、`provider`、`model`、`estimated_cost`、`credits_charged`、`permission_granted`、`final_price`。

## Auth / Device

### POST `/api/v1/auth/login`

Request:

```json
{
  "account": "user@example.com",
  "password": "password",
  "device_fingerprint": "device_hash",
  "device_name": "DESKTOP-01",
  "client_version": "0.1.0"
}
```

Response `data`:

```json
{
  "access_token": "short_lived_token",
  "refresh_token": "refresh_token",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid",
    "account": "user@example.com",
    "display_name": "图文店用户",
    "plan_code": "standard"
  },
  "device": {
    "id": "uuid",
    "status": "active",
    "is_new": false
  }
}
```

### POST `/api/v1/auth/refresh`

Request: `refresh_token`

Response `data`: `access_token`、`refresh_token`、`token_type`、`expires_in`

### POST `/api/v1/auth/logout`

Request: `refresh_token`

Response `data`: `logged_out`

### GET `/api/v1/devices/current`

Response `data`: `id`、`device_fingerprint`、`device_name`、`status`、`bound_at`、`last_seen_at`

### POST `/api/v1/devices/bind`

Request: `device_fingerprint`、`device_name`、`client_version`

Response `data`: `id`、`status`、`is_new`

## Credits / Billing

### GET `/api/v1/credits/balance`

Response `data`: `user_id`、`plan_code`、`monthly_grant`、`balance`、`period_start`、`period_end`、`status`、`updated_at`

### GET `/api/v1/credits/ledger`

Query: `limit`、`offset`、`change_type`

Response `data`: `items`、`total`、`limit`、`offset`

Ledger item fields: `id`、`change_type`、`amount`、`balance_after`、`source_type`、`source_id`、`description`、`created_at`

### POST `/api/v1/entitlements/check`

用途：本地付费功能调用前，桌面端向云端检查套餐权限。

Request:

```json
{
  "feature": "resize_image_local_paid",
  "operation": "single",
  "client_request_id": "local_req_xxx"
}
```

Response `data`:

```json
{
  "allowed": true,
  "feature": "resize_image_local_paid",
  "plan_code": "standard",
  "remaining_free_quota": null,
  "reason": null
}
```

## Local Paid Tools

本地付费功能权限校验。桌面端在调用本地付费功能前，通过本接口检查套餐权限。

### POST `/api/v1/entitlements/check`

本地付费工具套餐权限检查。本接口与 Credits / Billing 中 `/entitlements/check` 为同一接口，从本地付费工具视角描述权限校验契约。

用途：本地付费功能调用前，桌面端向云端检查套餐权限。

Request:

```json
{
  "feature": "resize_image_local_paid",
  "operation": "single",
  "client_request_id": "local_req_xxx"
}
```

Response `data`:

```json
{
  "allowed": true,
  "feature": "resize_image_local_paid",
  "plan_code": "standard",
  "remaining_free_quota": null,
  "reason": null
}
```

免费套餐额度用完时的响应示例：

```json
{
  "allowed": false,
  "feature": "resize_image_local_paid",
  "plan_code": "free",
  "remaining_free_quota": 0,
  "reason": "免费套餐当日使用次数已用完，请升级套餐"
}
```

本地付费功能码见 `shared-contract/feature-codes.md`。权限规则见 `shared-contract/pricing-rules.md`。

## AI Copy

### POST `/api/v1/ai/copy/generate`

Request:

```json
{
  "scene": "poster",
  "product_name": "快印宣传单",
  "selling_points": ["当天取件", "高清印刷"],
  "target_audience": "附近商户",
  "tone": "direct",
  "platform": "offline_poster",
  "extra_requirements": "突出开业活动",
  "client_request_id": "req_client_xxx"
}
```

Response `data`:

```json
{
  "feature": "ai_copy_cloud",
  "text": "开业大促，高清快印，当天取件！",
  "variants": ["开业印刷不用等，高清宣传单当天取。"],
  "provider": "deepseek",
  "model": "deepseek-chat",
  "estimated_cost": 0.002,
  "credits_charged": 1,
  "provider_call_id": "uuid"
}
```

## AI Render

### POST `/api/v1/ai/render/tasks`

Request: `scene_type`、`prompt`、`input_file_ids`、`style`、`size`、`client_request_id`

Response `data`: `task_id`、`status`、`feature`、`estimated_credits`

### GET `/api/v1/ai/render/tasks/{task_id}`

Response `data`: `task_id`、`status`、`result_files`、`provider`、`model`、`estimated_cost`、`credits_charged`、`provider_call_id`

## AI Image Tools

### POST `/api/v1/ai/image-tools/tasks`

Request: `feature`、`input_file_ids`、`options`、`client_request_id`

Response `data`: `task_id`、`status`、`feature`、`estimated_credits`

### GET `/api/v1/ai/image-tools/tasks/{task_id}`

Response `data`: 同云端 AI 任务查询结构。

## Provider Log

### GET `/api/v1/provider-call-logs`

Query: `limit`、`offset`、`feature`、`status`、`provider`

Response `data`: `items`、`total`、`limit`、`offset`

Item fields: `id`、`request_id`、`feature`、`provider`、`model`、`status`、`error_code`、`input_tokens`、`output_tokens`、`total_tokens`、`estimated_cost`、`credits_charged`、`latency_ms`、`created_at`

不得返回完整 prompt、原图、API Key、Token、完整隐私内容。

## Admin

后台接口统一使用 `/api/v1/admin/*` 前缀。后台模块开发前必须先补充对应契约，且必须经过管理员权限检查。
