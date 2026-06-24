"""
admin-users：后台用户和设备管理。

本模块是后台管理系统的用户和设备管理模块，提供：
- 用户列表查询、详情查询、状态修改
- 设备列表查询、详情查询、状态修改
- 按用户查询其绑定设备列表

所有接口需要管理员权限（通过 cloud-shared require_admin 鉴权）。
SQLAlchemy ORM 模型对齐 cloud/DATABASE_SCHEMA.md 的 users / devices 表定义。
"""
