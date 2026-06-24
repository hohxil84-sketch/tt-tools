# ACCEPTANCE.md - admin-users

## 验收状态

`PASSED`

## 验收清单

- [x] 模块目标已实现：后台用户和设备管理（查询、详情、状态修改）。
- [x] 不包含禁止内容：无密钥、模型大文件、缓存、构建产物。
- [x] 测试记录已写入 PROGRESS.md：50 项测试全部通过。
- [x] 新依赖和模型已登记：无新增依赖，无新增模型。
- [x] 代码关键逻辑有中文注释。
- [x] OpenAPI 契约已创建（admin-users.yaml）。
- [x] API_INDEX.md 已更新。
- [x] 接口响应格式符合 common.yaml ApiResponse 结构。
- [x] 管理员权限检查正常（require_admin 依赖）。
- [x] 数据库操作对齐 DATABASE_SCHEMA.md（users / devices 表）。
- [x] 模块仅修改允许范围内的文件。

## 是否允许合并

是。模块开发完成，测试通过，可合并到 dev/full-product。
