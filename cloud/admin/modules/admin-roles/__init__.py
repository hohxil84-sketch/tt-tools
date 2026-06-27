"""
admin-roles RBAC 权限管理模块。

提供角色和权限的 CRUD 管理：
Roles:     GET/POST /admin/roles, GET/PATCH/DELETE /admin/roles/{id}
Permissions: GET /admin/permissions
Role-Permission 关联: POST/DELETE /admin/roles/{id}/permissions
User-Role 关联: GET/POST/DELETE /admin/users/{id}/roles
"""
