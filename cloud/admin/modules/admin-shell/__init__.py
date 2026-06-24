"""
admin-shell：后台基础入口、导航、权限框架和基础布局。

本模块是后台管理系统的外壳，提供：
- 管理员鉴权守卫（基于 cloud-shared require_admin）
- 后台仪表盘概览
- 后台导航菜单结构
- 服务状态检查

后续后台模块（admin-users、admin-billing、admin-ops）在本模块基础上扩展。
"""
