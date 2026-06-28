# PROGRESS.md - admin-users

## 当前状态

`FIX_IN_PROGRESS`

## 分支

`fix/admin-users-role-period-plan-ui`

## 已完成

- 创建 shared-contract/openapi/admin-users.yaml OpenAPI 契约（7 个接口）
- 更新 shared-contract/API_INDEX.md（Admin Users 接口文档）
- 实现 7 个后台管理 API 端点：
  - GET /admin/users — 用户列表（分页、状态筛选、搜索）
  - GET /admin/users/{user_id} — 用户详情
  - PATCH /admin/users/{user_id}/status — 修改用户状态
  - GET /admin/users/{user_id}/devices — 用户设备列表
  - GET /admin/devices — 设备列表（分页、状态筛选）
  - GET /admin/devices/{device_id} — 设备详情
  - PATCH /admin/devices/{device_id}/status — 修改设备状态
- 创建 SQLAlchemy ORM 模型（User / Device），对齐 DATABASE_SCHEMA.md
- 实现业务逻辑层（分页、筛选、搜索、状态管理）
- 在 cloud/app-shell/main.py 注册 admin-shell 和 admin-users 路由
- 关键代码均有中文注释
- 50 项单元测试全部通过，0 失败 0 警告
- 无新增依赖，无新增模型

## 未完成

- 无

## 测试记录

日期：2026-06-29
测试命令：pytest cloud/admin/modules/admin-users/tests/ -v
结果：50 passed, 0 failed
失败原因：无
中文备注：全部 50 项测试通过。

## Bug 记录

### 2026-06-29

| 问题 | 根因 | 修复 | 测试结果 |
|---|---|---|---|
| RBAC 角色全显示"超级管理员" | `func.group_concat` 不兼容 PostgreSQL | 改为 `func.string_agg` | 50 passed |
| 全部用户视图无到期时间列 | Users.tsx 只在 isClient 视图渲染该列 | 全部用户视图增加「到期时间」列 | 构建通过 |
| 操作按钮溢出屏幕 | 4-5 个 ActBtn 占 21-27% 列宽 | 改为 ⋮ 紧凑下拉菜单（50px） | 构建通过 |
| 删除用户报外键冲突 | 漏清 user_alipay_bindings | 改为软删除 status='deleted' | 50 passed |
| 创管时不选套餐 | 校验仅对普通用户要求 | 创建管理员也必选套餐 | 50 passed |

## 提交记录

- 2026-06-29：`52daefe` fix: 修复角色显示/到期时间/按钮溢出 + 全模块软删除改造 + 数据库对齐
- 2026-06-24：`1b1cc71` feat(admin-users): complete admin users and devices management module
- 2026-06-24：`4d922ea` docs: update admin-users PROGRESS.md with commit hash

## 下一步

等待用户确认，合并 fix/admin-users-role-period-plan-ui 到 dev/full-product。
