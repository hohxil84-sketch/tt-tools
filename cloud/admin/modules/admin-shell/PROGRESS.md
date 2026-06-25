# PROGRESS.md - admin-shell

## 当前状态

`DEVELOPMENT_DONE`

## 分支

`feature/admin-web-backend`（原 `feature/admin-shell` 已完成，本轮在此基础上增强）

## 本轮新增/修改（2026-06-25）

- **dashboard 接入真实数据库查询**：从 users/devices/orders 表实时聚合统计，不再是占位值 0
- **menu 扩展为完整导航**：增加 4 个顶级菜单项 + 子菜单（用户管理→用户列表+设备管理，计费管理→套餐+订单+额度账户+额度流水，运维管理→AI调用日志+成本统计+风控日志+功能开关）
- **router.py**：dashboard 端点接入 get_db 依赖
- **测试更新**：conftest 覆盖 get_db 为 None（返回占位值），更新菜单测试断言匹配新标题

## 已完成

- 已创建模块文档骨架。
- 已创建 `shared-contract/openapi/admin-shell.yaml` OpenAPI 契约（3 个端点）。
- 已更新 `shared-contract/API_INDEX.md` 后台接口部分。
- 已实现模块代码：
  - `__init__.py` — 模块入口和说明
  - `schemas.py` — Pydantic DTO（DashboardStats / MenuItem / MenuData / StatusData）
  - `service.py` — 业务逻辑（仪表盘真实查询 / 完整菜单定义 / 状态查询 / 认证登录）
  - `router.py` — FastAPI 路由（3 个后台端点 + 3 个认证端点，均使用 require_admin 鉴权）
- 已编写测试：14 项全部通过
- admin-web 前端已创建在 `cloud/admin/modules/admin-web/`

## 未完成

- 仪表盘真实数据依赖 admin-users / admin-billing / admin-ops 后续注入。
- 路由注册到 cloud-app-shell main.py 待用户确认后完成。

## 测试记录

日期：2026-06-25
测试命令：`pytest cloud/admin/modules/admin-shell/tests/ -v`
结果：14 passed, 0 failed, 0 errors

日期：2026-06-25（全量 admin 测试）
测试命令：`pytest cloud/admin/modules/admin-users/tests/ cloud/admin/modules/admin-billing/tests/ cloud/admin/modules/admin-ops/tests/ -v`
结果：admin-users 50 passed, admin-billing 67 passed, admin-ops 48 passed, 全部 0 failed
总计：179 passed, 0 failed, 0 errors
中文备注：全部后台 API 端点（4 个模块共 28 个端点）的权限校验、业务逻辑、分页、筛选均通过。

## Bug 记录

暂无。

## 提交记录

暂无。

## 下一步

待用户确认后提交、推送当前模块分支。
