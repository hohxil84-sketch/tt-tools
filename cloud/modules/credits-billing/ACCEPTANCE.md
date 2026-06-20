# ACCEPTANCE.md - cloud-credits-billing

## 验收状态

`READY_FOR_REVIEW`

## 验收清单

- [x] 模块目标已实现（套餐权限、额度账户、扣费、额度流水、本地付费功能权限检查）。
- [x] 不包含禁止内容（无密钥、模型大文件、缓存、构建产物）。
- [x] 测试记录已写入 PROGRESS.md（30 项测试全部通过）。
- [x] 无新增依赖（复用已有 cloud-shared 依赖）。
- [x] 无新增模型。
- [x] 代码关键逻辑有中文注释。
- [x] 3 个 API 端点对齐 shared-contract/openapi/credits-billing.yaml。
- [x] 数据库表模型对齐 cloud/DATABASE_SCHEMA.md。
- [x] 写入边界正确：credit_ledger 只由本模块写入。

## 是否允许合并

待用户确认后合并。
