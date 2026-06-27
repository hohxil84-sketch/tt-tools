"""
admin-audit 审计日志模块。

提供后台操作审计日志的记录和查询功能：
- 自动记录所有后台写操作（POST/PATCH/DELETE /api/v1/admin/*）
- GET /admin/audit-logs        — 查询审计日志列表（分页+筛选）
- GET /admin/audit-logs/{id}   — 查询审计日志详情

所有端点需要管理员权限（JWT role=admin），通过 cloud-shared 的
require_admin 依赖实现鉴权。

默认路由前缀：/api/v1/admin
"""
