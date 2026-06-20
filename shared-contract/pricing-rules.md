# 计费规则

## 免费本地功能

本地执行，不消耗云端 AI 额度，无需套餐权限。

## 本地付费功能

本地执行但需要登录和套餐权限。权限检查通过 `/api/v1/entitlements/check` 接口完成。

权限规则：
- free 套餐：可能有每日/每月免费使用次数限制，由 `remaining_free_quota` 返回剩余配额。
- standard / pro 套餐：通常无限制，`allowed=true`。
- 未登录或套餐无效：`allowed=false`，`reason` 返回具体拒绝原因。

本地付费功能不消耗 AI 额度，不计入 credit_ledger。

## 云端 AI 付费功能

云端执行，需要权限、额度预检查、Provider 调用、成本估算、扣费、日志。

详见 `shared-contract/openapi/credits-billing.yaml`。

