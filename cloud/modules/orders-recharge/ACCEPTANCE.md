# ACCEPTANCE.md - cloud-orders-recharge

## 验收状态

`READY_FOR_REVIEW`

## 验收清单

- [x] 模块目标已实现：订单创建、充值、支付预留。
- [x] 不包含禁止内容：无密钥、模型大文件、缓存、构建产物。
- [x] 测试记录已写入 PROGRESS.md（25 项全部通过）。
- [x] 新依赖和模型已登记：无新增外部依赖。
- [x] 代码关键逻辑有中文注释。
- [x] 硬约束全部满足：
  - [x] #1 目录命名：Python 代码在 orders_recharge/，文档在 orders-recharge/
  - [x] #2 安全性：确认支付仅允许当前用户自己的订单，标注 mock/dev 预留
  - [x] #3 事务原子性：状态更新 + grant_credits/plan_code 在同一事务
  - [x] #4 幂等性：DB 条件 UPDATE WHERE status='pending'，rowcount 检查
  - [x] #5 orders 表对齐：ORM 与 DATABASE_SCHEMA.md 逐列一致
  - [x] #6 负例测试：跨用户隔离、closed 拒绝、无效参数、决策字段忽略、幂等验证
  - [x] #7 金额用分：全程 amount_cents 整数，无浮点
  - [x] #8 ledger 追溯：source_id=order.id，description 含 order_no

## 涉及文件

### 新建
- shared-contract/openapi/orders-recharge.yaml
- cloud/modules/orders_recharge/ (全部 Python 代码)
- cloud/modules/orders-recharge/PROGRESS.md (更新)

### 修改
- cloud/DATABASE_SCHEMA.md
- shared-contract/API_INDEX.md
- cloud/app-shell/main.py

## 是否允许合并

是，待用户确认。
