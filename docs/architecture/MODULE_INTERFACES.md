# MODULE_INTERFACES.md

本文件定义模块之间的调用边界。CC 开发模块时必须遵守，避免各模块互相乱调。

## 桌面端调用规则

桌面业务模块只能调用：

- `desktop/shared/auth`
- `desktop/shared/cloud-api`
- `desktop/shared/local-runtime`
- `desktop/shared/file-system`
- `desktop/shared/job-system`
- `desktop/shared/logging`
- `desktop/shared/settings`
- `desktop/shared/ui-components`

桌面业务模块不得：

- 直接调用第三方 AI API。
- 直接保存第三方 AI Key。
- 直接决定套餐权限、额度扣费、Provider 成本。
- 直接读取其他业务模块的内部实现。

## 本地 worker 调用规则

本地 worker 模块只能调用：

- `local-worker/shared/model-registry`
- `local-worker/shared/file-io`
- `local-worker/shared/errors`
- `local-worker/shared/logging`
- `local-worker/shared/runtime`

本地 worker 不得：

- 调用云端 Provider。
- 写入云端账本。
- 提交模型文件到 Git。
- 直接读取桌面端 UI 状态。

## 云端调用规则

云端业务模块只能通过公共层访问：

- `cloud/shared/auth`
- `cloud/shared/permissions`
- `cloud/shared/database`
- `cloud/shared/errors`
- `cloud/shared/request-id`
- `cloud/shared/logging`
- `cloud/modules/provider-runtime`
- `cloud/modules/credits-billing`

云端 AI 模块不得直接调用 OpenAI、DeepSeek 或其他 Provider，必须通过 `provider-runtime`。

## Provider Runtime 输出结构

Provider Runtime 对上层模块统一返回：

```json
{
  "provider": "deepseek",
  "model": "deepseek-chat",
  "status": "success",
  "text": "生成内容",
  "files": [],
  "usage": {
    "input_tokens": 120,
    "output_tokens": 80,
    "total_tokens": 200,
    "reasoning_tokens": 0,
    "cached_tokens": 0,
    "image_count": 0
  },
  "estimated_cost": 0.002,
  "raw_usage_json": {},
  "provider_request_id": "provider_req_xxx",
  "latency_ms": 1200
}
```

## 标准云端 AI 调用链

```text
API endpoint
  -> auth/device check
  -> permission check
  -> credits precheck
  -> provider-runtime
  -> provider-call-log
  -> credits charge
  -> usage event
  -> unified response
```

## 标准本地付费工具调用链

```text
desktop module
  -> cloud entitlement check
  -> local-worker module
  -> desktop job-system
  -> local usage event sync
```
