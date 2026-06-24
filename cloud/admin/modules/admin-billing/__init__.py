"""
admin-billing 后台套餐、订单、额度管理模块。

提供 11 个后台管理 API 端点，全部对齐 shared-contract/openapi/admin-billing.yaml：
套餐管理（5 个）：
- GET    /admin/plans              — 套餐列表
- GET    /admin/plans/{plan_id}    — 套餐详情
- POST   /admin/plans              — 创建套餐
- PATCH  /admin/plans/{plan_id}    — 更新套餐
- PATCH  /admin/plans/{plan_id}/status — 启用/停用套餐
订单管理（2 个）：
- GET    /admin/orders             — 全部订单列表
- GET    /admin/orders/{order_id}  — 订单详情
额度管理（4 个）：
- GET    /admin/credits/accounts   — 额度账户列表
- GET    /admin/credits/accounts/{account_id} — 额度账户详情
- GET    /admin/credits/ledger     — 全部额度流水
- POST   /admin/credits/adjust     — 手动调整额度

所有端点需要管理员权限（JWT role=admin），通过 cloud-shared 的 require_admin 实现鉴权。
"""
