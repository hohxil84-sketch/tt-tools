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

Response `data`: `task_id`、`status`、`feature`、`result_files`、`provider`、`model`、`estimated_cost`、`credits_charged`、`provider_call_id`

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

## Orders / Recharge

### POST `/api/v1/orders`

创建订单（套餐购买 / 额度充值）。

Request:

```json
{
  "order_type": "credits",
  "product_code": "credits_100",
  "client_request_id": "req_client_xxx"
}
```

Response `data`:

```json
{
  "id": "uuid",
  "order_no": "ORD-20260621-a1b2c3d4",
  "order_type": "credits",
  "product_code": "credits_100",
  "amount_cents": 1000,
  "credit_amount": 100,
  "currency": "CNY",
  "status": "pending",
  "paid_at": null,
  "created_at": "2026-06-21T...",
  "updated_at": "2026-06-21T..."
}
```

客户端不得提交 `user_id`、`final_price`、`plan_code` 等决策字段。金额由服务端定价表决定。

### GET `/api/v1/orders`

查询当前用户订单列表。

Query: `limit`、`offset`、`order_type`、`status`

Response `data`: `items`、`total`、`limit`、`offset`

Item fields: `id`、`order_no`、`order_type`、`product_code`、`amount_cents`、`credit_amount`、`currency`、`status`、`paid_at`、`created_at`、`updated_at`

### POST `/api/v1/orders/{order_id}/confirm`

确认支付（**mock/dev 预留**，不接入真实支付网关，生产前必须接支付回调验签）。

确认当前用户 pending 订单为 paid，并执行对应业务：credits 订单发放额度，plan 订单更新套餐。接口幂等，重复确认不重复发放额度。

客户端不得提交支付金额、套餐编码、额度数量等决策字段。

Response `data`: 同 OrderData，status 变为 `paid`。

## Admin

后台接口统一使用 `/api/v1/admin/*` 前缀。后台模块开发前必须先补充对应契约，且必须经过管理员权限检查。

所有后台接口要求 `Authorization: Bearer <admin_access_token>`，且 JWT 中 role 字段为 `admin`。

### Admin Shell — 后台基础入口

### GET `/api/v1/admin/dashboard`

返回后台仪表盘核心统计指标。

Response `data`:

```json
{
  "users_total": 150,
  "orders_today": 12,
  "revenue_today_cents": 35000,
  "active_devices": 89,
  "server_status": "healthy"
}
```

字段说明：
- `users_total`：系统总用户数
- `orders_today`：今日订单数
- `revenue_today_cents`：今日收入（单位：分）
- `active_devices`：当前活跃设备数
- `server_status`：服务健康状态（healthy / degraded / down）

### GET `/api/v1/admin/menu`

返回后台左侧导航菜单结构。

Response `data`:

```json
{
  "menu": [
    {
      "id": "dashboard",
      "title": "首页仪表盘",
      "icon": "dashboard",
      "path": "/admin/dashboard",
      "children": null
    },
    {
      "id": "users",
      "title": "用户管理",
      "icon": "users",
      "path": "/admin/users",
      "children": null
    },
    {
      "id": "billing",
      "title": "计费管理",
      "icon": "billing",
      "path": "/admin/billing",
      "children": null
    },
    {
      "id": "ops",
      "title": "运维管理",
      "icon": "ops",
      "path": "/admin/ops",
      "children": null
    }
  ]
}
```

MenuItem 字段说明：
- `id`：菜单项唯一标识
- `title`：菜单项中文标题
- `icon`：图标标识
- `path`：对应页面路径
- `children`：子菜单项列表（可选）

### GET `/api/v1/admin/status`

返回服务运行状态。

Response `data`:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 3600.0
}
```
