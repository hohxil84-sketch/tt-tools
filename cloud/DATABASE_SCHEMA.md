# DATABASE_SCHEMA.md

本文件是云端数据库的初始权威设计。CC 开发云端模块、后台模块、计费模块、Provider 模块前必须阅读本文件。

## 设计原则

- 主键默认使用 UUID。
- 时间字段使用 UTC。
- 成本和金额字段使用 decimal 或整数分，不用浮点数做最终账务。
- 客户端不得直接写入账本、扣费结果、Provider 成本。
- Provider 原始 usage 可保存到服务端 JSON 字段，但不得返回给普通客户端。
- 敏感字段必须脱敏或哈希存储。

## users

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 用户 ID |
| account | varchar(255) | unique, not null | 登录账号 |
| password_hash | varchar(255) | not null | 密码哈希 |
| display_name | varchar(100) | nullable | 展示名称 |
| role | varchar(50) | not null default `user` | 用户角色 |
| status | varchar(50) | not null default `active` | active / blocked / deleted |
| plan_id | uuid | fk plans.id, nullable | 当前套餐 ID（UUID 外键） |
| profile_json | jsonb | nullable | 社会化资料：头像、昵称、性别、地区等 |
| created_at | timestamptz | not null | 创建时间 |
| updated_at | timestamptz | not null | 更新时间 |

索引：unique `account`，index `status`，index `plan_id`

## user_alipay_bindings

支付宝用户与本地用户绑定表。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 绑定 ID |
| user_id | uuid | fk users.id, not null | 本地用户 ID |
| alipay_user_id | varchar(64) | unique, not null | 支付宝 user_id |
| created_at | timestamptz | not null | 绑定时间 |

索引：unique `alipay_user_id`，index `user_id`

## devices

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 设备 ID |
| user_id | uuid | fk users.id, not null | 用户 ID |
| device_fingerprint_hash | varchar(255) | not null | 设备指纹哈希 |
| device_name | varchar(255) | nullable | 设备名称 |
| client_version | varchar(50) | nullable | 客户端版本 |
| status | varchar(50) | not null default `active` | active / blocked / removed |
| bound_at | timestamptz | not null | 绑定时间 |
| last_seen_at | timestamptz | nullable | 最近活跃时间 |
| created_at | timestamptz | not null | 创建时间 |
| updated_at | timestamptz | not null | 更新时间 |

索引：unique `(user_id, device_fingerprint_hash)`，index `user_id`，index `status`

## auth_sessions

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 会话 ID |
| user_id | uuid | fk users.id, not null | 用户 ID |
| device_id | uuid | fk devices.id, nullable | 设备 ID |
| refresh_token_hash | varchar(255) | unique, not null | refresh token 哈希 |
| status | varchar(50) | not null default `active` | active / revoked / expired |
| expires_at | timestamptz | not null | 过期时间 |
| created_at | timestamptz | not null | 创建时间 |
| revoked_at | timestamptz | nullable | 撤销时间 |

## plans

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 套餐 ID |
| name | varchar(100) | not null | 套餐名称 |
| monthly_grant | integer | not null default 0 | 每周期赠送 AI 额度 |
| enabled_features_json | jsonb | not null default `{}` | 功能开关 |
| expire_days | integer | not null default 0 | 到期天数，0=永不过期 |
| is_default | boolean | not null default false | 是否默认套餐（新用户自动获得） |
| plan_tier | varchar(20) | not null default '' | 套餐等级：free / standard / pro |
| price_cents | integer | not null default 0 | 套餐月费（分），如 2900=¥29 |
| status | varchar(50) | not null default `active` | active / disabled |
| created_at | timestamptz | not null | 创建时间 |
| updated_at | timestamptz | not null | 更新时间 |

## credit_accounts

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 账户 ID |
| user_id | uuid | unique, fk users.id, not null | 用户 ID |
| plan_id | uuid | fk plans.id, nullable | 当前套餐 ID（UUID 外键） |
| balance | integer | not null default 0 | 当前 AI 额度 |
| monthly_grant | integer | not null default 0 | 周期赠送额度 |
| period_start | timestamptz | nullable | 周期开始 |
| period_end | timestamptz | nullable | 周期结束 |
| status | varchar(50) | not null default `active` | active / frozen |
| created_at | timestamptz | not null | 创建时间 |
| updated_at | timestamptz | not null | 更新时间 |

## credit_ledger

所有额度变化必须写入本表。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 流水 ID |
| user_id | uuid | fk users.id, not null | 用户 ID |
| account_id | uuid | fk credit_accounts.id, not null | 额度账户 ID |
| change_type | varchar(50) | not null | grant / consume / recharge / refund / adjust |
| amount | integer | not null | 变化值，扣费为负数 |
| balance_after | integer | not null | 变化后余额 |
| source_type | varchar(50) | not null | provider_call / order / system / admin |
| source_id | uuid | nullable | 来源 ID |
| description | varchar(255) | nullable | 中文说明 |
| created_at | timestamptz | not null | 创建时间 |

索引：`user_id`、`account_id`、`created_at`、`(source_type, source_id)`

## provider_call_log

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 调用 ID |
| request_id | varchar(100) | unique, not null | 请求追踪 ID |
| user_id | uuid | fk users.id, not null | 用户 ID |
| device_id | uuid | fk devices.id, nullable | 设备 ID |
| feature | varchar(100) | nullable | 功能码（冗余缓存，过渡期保留） |
| feature_code_id | uuid | fk feature_codes.id, nullable | 功能码外键 ID |
| provider | varchar(100) | nullable | Provider 名称（冗余缓存，过渡期保留） |
| provider_id | uuid | fk providers.id, nullable | Provider 外键 ID |
| model | varchar(100) | not null | 模型名称 |
| status | varchar(50) | not null | success / failed / timeout |
| error_code | varchar(100) | nullable | 统一错误码 |
| input_tokens | integer | not null default 0 | 输入 token |
| output_tokens | integer | not null default 0 | 输出 token |
| total_tokens | integer | not null default 0 | 总 token |
| reasoning_tokens | integer | not null default 0 | 推理 token |
| cached_tokens | integer | not null default 0 | 缓存 token |
| image_count | integer | not null default 0 | 图片数量 |
| estimated_cost | decimal(18, 6) | not null default 0 | 估算成本（人民币） |
| credits_charged | integer | not null default 0 | 扣除额度 |
| estimated_credits_before | integer | nullable | 调用前预估扣点（用于预估 vs 实际对比） |
| estimated_latency_ms | integer | nullable | 调用前预估耗时（用于预估 vs 实际对比） |
| latency_ms | integer | nullable | 实际 Provider 延迟 |
| raw_usage_json | jsonb | nullable | 原始 usage，仅服务端使用 |
| raw_meta_json | jsonb | nullable | 脱敏元数据 |
| created_at | timestamptz | not null | 创建时间 |

索引：`user_id`、`feature`、`provider`、`status`、`created_at`

## usage_events

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 事件 ID |
| user_id | uuid | fk users.id, not null | 用户 ID |
| device_id | uuid | fk devices.id, nullable | 设备 ID |
| feature | varchar(100) | nullable | 功能码（冗余缓存，过渡期保留） |
| feature_code_id | uuid | fk feature_codes.id, nullable | 功能码外键 ID |
| event_type | varchar(100) | not null | local_start / local_success / cloud_success 等 |
| request_id | varchar(100) | nullable | 请求 ID |
| metadata_json | jsonb | not null default `{}` | 脱敏元数据 |
| created_at | timestamptz | not null | 创建时间 |

## orders

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 订单 ID |
| user_id | uuid | fk users.id, not null | 用户 ID |
| order_no | varchar(100) | unique, not null | 订单号 |
| order_type | varchar(50) | not null | plan / credits |
| product_code | varchar(100) | not null | 具体产品编码：standard / pro / credits_100 / credits_500 / credits_2000 |
| amount_cents | integer | not null | 金额，单位分 |
| credit_amount | integer | nullable | 充值额度数量（仅 order_type=credits 时有值） |
| currency | varchar(20) | not null default `CNY` | 币种 |
| status | varchar(50) | not null | pending / paid / closed / refunded |
| paid_at | timestamptz | nullable | 支付时间 |
| created_at | timestamptz | not null | 创建时间 |
| updated_at | timestamptz | not null | 更新时间 |

索引：unique `order_no`，index `user_id`，index `status`，index `created_at`

## files

仅云端任务需要上传文件时使用；本地免费任务默认不上传原文件。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 文件 ID |
| user_id | uuid | fk users.id, not null | 用户 ID |
| storage_key | varchar(500) | not null | 存储路径 |
| original_name | varchar(255) | nullable | 原始文件名 |
| mime_type | varchar(100) | not null | MIME |
| size_bytes | bigint | not null | 文件大小 |
| sha256 | varchar(64) | nullable | 文件 hash |
| width | integer | nullable | 图片宽度 |
| height | integer | nullable | 图片高度 |
| created_at | timestamptz | not null | 创建时间 |

## ai_tasks

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 任务 ID |
| user_id | uuid | fk users.id, not null | 用户 ID |
| device_id | uuid | fk devices.id, nullable | 设备 ID |
| feature | varchar(100) | nullable | 功能码（冗余缓存，过渡期保留） |
| feature_code_id | uuid | fk feature_codes.id, nullable | 功能码外键 ID |
| status | varchar(50) | not null | queued / running / succeeded / failed |
| input_json | jsonb | not null | 脱敏输入 |
| result_json | jsonb | nullable | 结果 |
| provider_call_id | uuid | fk provider_call_log.id, nullable | Provider 调用 ID |
| credits_charged | integer | not null default 0 | 扣除额度 |
| estimated_credits_before | integer | nullable | 创建任务时预估扣点 |
| estimated_latency_ms | integer | nullable | 创建任务时预估耗时 |
| error_code | varchar(100) | nullable | 错误码 |
| created_at | timestamptz | not null | 创建时间 |
| updated_at | timestamptz | not null | 更新时间 |

## risk_logs

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 风控日志 ID |
| user_id | uuid | fk users.id, nullable | 用户 ID |
| device_id | uuid | fk devices.id, nullable | 设备 ID |
| risk_type | varchar(100) | not null | 风险类型 |
| severity | varchar(50) | not null | low / medium / high |
| details_json | jsonb | not null default `{}` | 脱敏详情 |
| created_at | timestamptz | not null | 创建时间 |

## admin_audit_logs

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 审计日志 ID |
| admin_user_id | uuid | fk users.id, not null | 操作管理员 ID |
| admin_account | varchar(255) | not null | 操作管理员账号 |
| action | varchar(50) | not null | 操作类型：create / update / delete / status_change / adjust / refund / cancel / batch |
| target_type | varchar(50) | not null | 目标资源类型：user / device / order / plan / credits / feature_flag / provider |
| target_id | uuid | nullable | 目标资源 ID |
| summary | varchar(500) | not null | 操作摘要（中文） |
| details_json | jsonb | not null default `{}` | 操作详情（请求体、变更前后等） |
| ip_address | varchar(45) | nullable | 请求来源 IP |
| created_at | timestamptz | not null | 记录时间 |

索引：`admin_user_id`、`action`、`target_type`、`(target_type, target_id)`、`created_at`

## password_reset_tokens

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 令牌 ID |
| user_id | uuid | fk users.id, not null | 目标用户 ID |
| token_hash | varchar(255) | unique, not null | 重置令牌 SHA-256 哈希 |
| status | varchar(50) | not null default `active` | active / used / expired |
| expires_at | timestamptz | not null | 过期时间（默认 1 小时） |
| created_at | timestamptz | not null | 创建时间 |
| used_at | timestamptz | nullable | 使用时间 |

## providers

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | Provider ID |
| name | varchar(100) | unique, not null | Provider 名称 |
| provider_type | varchar(50) | not null | 见下方 Provider 类型说明 |
| api_key_encrypted | varchar(500) | nullable | 加密存储的 API Key |
| base_url | varchar(500) | **必填**（deepseek 除外） | API 基础 URL（如 https://api.openai.com/v1） |
| models_json | jsonb | nullable | 模型配置 JSON |
| is_enabled | boolean | not null default true | 是否启用 |
| priority | integer | not null default 0 | 优先级，数字越大越优先调用 |
| created_at | timestamptz | not null | 创建时间 |
| updated_at | timestamptz | not null | 更新时间 |

### Provider 类型说明

provider_type 决定使用哪个 Provider 类。未列出的类型自动回退到 `OpenAICompatibleProvider`（纯 DB 驱动）。

| provider_type | 类 | base_url 必填 | 说明 |
|---|---|---|---|
| `deepseek` | DeepSeekProvider | 否（默认 api.deepseek.com） | 向后兼容，OpenAI 兼容接口 |
| `doubao` | DoubaoProvider | 是 | 特殊：支持图片生成/编辑 |
| `openai_compatible` | OpenAICompatibleProvider | 是 | 通用 OpenAI 兼容类 |
| **其他任意值** | OpenAICompatibleProvider | 是 | `openai`、`gemini`、`groq` 等均可，自动回退 |

**新增 Provider 示例**（只需在后台填表，零代码改动）：

| name | provider_type | base_url |
|---|---|---|
| deepseek | deepseek | （可为空，自动用 api.deepseek.com） |
| openai | openai | https://api.openai.com/v1 |
| gemini | gemini | https://generativelanguage.googleapis.com/v1beta/openai |
| groq | groq | https://api.groq.com/openai/v1 |

## feature_codes

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 功能码 ID |
| code | varchar(100) | unique, not null | 功能码（如 ai_copy_cloud） |
| name | varchar(100) | not null | 功能名称 |
| category | varchar(50) | not null | local_free / local_paid / cloud_ai |
| description | text | nullable | 功能说明 |
| status | varchar(50) | not null default 'active' | active / disabled |
| is_active | boolean | not null default true | 是否启用 |
| created_at | timestamptz | not null | 创建时间 |

## provider_model_pricing

Provider 模型定价表，替代代码硬编码。运营后台可编辑，即时生效。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | |
| provider_id | uuid | fk providers.id, not null | 关联的 Provider |
| model_name | varchar(100) | not null | deepseek-chat / gpt-4o |
| input_price | decimal(18, 6) | not null | 输入单价（元/百万token） |
| output_price | decimal(18, 6) | not null | 输出单价（元/百万token） |
| currency | varchar(10) | not null default 'CNY' | |
| is_active | boolean | not null default true | |
| created_at | timestamptz | not null | |
| updated_at | timestamptz | not null | |

索引：UNIQUE `(provider_id, model_name)`

## ai_capability

AI 能力表，替代硬编码 capability 字符串。调度时按 code 匹配。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 能力 ID |
| code | varchar(64) | unique, not null | 能力编码（如 text、vision） |
| name | varchar(64) | not null | 能力名称（如"文本生成"） |
| description | text | nullable | 能力说明 |
| is_active | boolean | not null default true | 是否启用 |
| created_at | timestamptz | not null | 创建时间 |
| updated_at | timestamptz | not null | 更新时间 |

索引：unique `code`

## provider_model_capability

Provider 模型 ↔ 能力 多对多关联表。替代原 provider_model_pricing.capability 单值字段。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 关联 ID |
| provider_model_id | uuid | fk provider_model_pricing.id, not null | 模型定价 ID |
| capability_id | uuid | fk ai_capability.id, not null | 能力 ID |
| created_at | timestamptz | not null | 创建时间 |

索引：UNIQUE `(provider_model_id, capability_id)`，index `provider_model_id`，index `capability_id`

## feature_pricing

功能起步扣点表，替代代码硬编码。每个 AI 功能对应一条记录。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| feature_code | varchar(100) | pk, fk feature_codes.code | 功能码 |
| min_credits | integer | not null | 起步扣点（最少扣点数） |
| default_max_tokens | integer | not null default 2048 | 默认 max_tokens，用于预估计算 |
| updated_at | timestamptz | not null | |

## system_config

全局系统配置表，简单 KV 结构。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| key | varchar(100) | pk | 配置键，如 credits_exchange_rate |
| value | varchar(500) | not null | 配置值 |
| updated_at | timestamptz | not null | |

种子数据：`credits_exchange_rate = "10"`（1 CNY = 10 点）

## provider_latency_stats

Provider 耗时统计表，由 provider-log 模块异步更新。滑动窗口基于最近 1000 条成功调用。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | |
| provider_name | varchar(50) | not null | |
| model_name | varchar(100) | not null | |
| capability | varchar(50) | not null | text / image_generation / image_edit |
| p50_latency_ms | integer | not null | 中位数耗时（毫秒） |
| p95_latency_ms | integer | not null | 95分位耗时（毫秒） |
| sample_count | integer | not null | 样本数 |
| updated_at | timestamptz | not null | |

索引：UNIQUE `(provider_name, model_name, capability)`

## credit_packages

充值套餐表，替代 `orders_recharge/service.py` 硬编码。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | |
| product_code | varchar(50) | unique, not null | credits_100 / credits_500 / credits_2000 |
| name | varchar(100) | not null | "100点额度包" |
| credit_amount | integer | not null | 到账点数 |
| price_cents | integer | not null | 价格（分），如 1000=¥10 |
| is_active | boolean | not null default true | |
| sort_order | integer | not null default 0 | 排序 |
| created_at | timestamptz | not null | |
| updated_at | timestamptz | not null | |

## roles / permissions / 关联表

### roles

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 角色 ID |
| name | varchar(100) | not null | 角色名称 |
| code | varchar(100) | unique, not null | 角色编码 |
| description | text | nullable | 描述 |
| is_system | boolean | not null default false | 是否系统内置（不可删除） |
| is_active | boolean | not null default true | 是否启用（软删除标记） |
| created_at | timestamptz | not null | 创建时间 |

### permissions

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | uuid | pk | 权限 ID |
| code | varchar(100) | unique, not null | 权限编码（如 users.read） |
| name | varchar(100) | not null | 权限名称 |
| resource | varchar(50) | not null | 资源：users / orders / plans / credits / providers / features / roles / audit |
| action | varchar(50) | not null | 操作：read / create / update / delete / manage |
| description | text | nullable | 描述 |
| created_at | timestamptz | not null | 创建时间 |

### role_permissions（关联表）

| role_id | uuid | pk, fk roles.id |
| permission_id | uuid | pk, fk permissions.id |

### user_roles（关联表）

| user_id | uuid | pk, fk users.id |
| role_id | uuid | pk, fk roles.id |

## 写入边界


- `credit_ledger` 只能由云端计费服务写入。
- `provider_call_log` 只能由 Provider Runtime 或其封装服务写入。
- `usage_events` 由云端和本地同步服务按脱敏规则写入。
- `files` 只记录云端上传文件，本地文件路径不得直接上传为敏感数据。
- `raw_usage_json` 不返回给普通客户端。

