"""
admin-providers AI Provider 配置管理模块。

提供后台 Provider 配置 CRUD：
- GET    /admin/providers           — Provider 列表
- POST   /admin/providers           — 新增 Provider
- GET    /admin/providers/{id}      — Provider 详情
- PATCH  /admin/providers/{id}      — 更新 Provider
- DELETE /admin/providers/{id}      — 删除 Provider

所有端点需要管理员权限。
"""
