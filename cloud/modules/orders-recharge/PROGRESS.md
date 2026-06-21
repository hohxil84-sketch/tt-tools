# PROGRESS.md - cloud-orders-recharge

## 当前状态

`DEVELOPMENT_COMPLETE`

## 分支

`feature/cloud-orders-recharge`

## 已完成

- 创建模块文档骨架。
- 更新 DATABASE_SCHEMA.md：orders 表新增 product_code 和 credit_amount 字段。
- 创建 shared-contract/openapi/orders-recharge.yaml（3 个端点契约）。
- 更新 shared-contract/API_INDEX.md：新增 Orders / Recharge 章节。
- 实现 models.py：Order ORM 模型（对齐 orders 表，amount_cents 用整数分）。
- 实现 schemas.py：CreateOrderRequest / OrderData / OrderListData DTO。
- 实现 service.py：
  - 服务端定价表（PLAN_PRICES + CREDIT_PACKAGES，全程整数分）。
  - create_order：创建订单，金额由服务端决定。
  - list_orders：按用户隔离的订单列表查询（分页+筛选）。
  - confirm_order：mock/dev 支付确认（事务原子性 + DB 条件更新幂等 + grant_credits 追溯）。
  - 跨模块调用 credits-billing 通过 importlib 懒加载。
- 实现 router.py：3 个 API 端点（明确标注 mock/dev 预留）。
- 注册路由到 cloud/app-shell/main.py。
- 完成测试：25 项全部通过。

## 测试记录

| 日期 | 测试命令 | 结果 | 备注 |
|------|---------|------|------|
| 2026-06-21 | D:\localPath\venvs\cloud-app-shell\Scripts\python.exe -m pytest cloud/modules/orders_recharge/tests/ -v | 25 passed | 全部通过 |

测试覆盖：
- 正例：创建 credits/plan 订单、列表查询（分页/筛选）、确认支付（credits 充值 + plan 切换）、完整流程
- 负例：未认证拒绝、跨用户隔离、closed 拒绝、无效参数拒绝、决策字段忽略、重复确认幂等（ledger 不重复写入）
- 结构测试：OpenAPI-DTO 字段一致性、amount_cents 整数检验、错误响应格式
- 硬约束验证：#2 安全性、#3 事务原子性、#4 幂等性、#6 跨用户隔离、#7 金额用分、#8 ledger 追溯

## Bug 记录

暂无。

## 提交记录

暂无（待提交）。

## 下一步

等待用户确认后提交并推送。
