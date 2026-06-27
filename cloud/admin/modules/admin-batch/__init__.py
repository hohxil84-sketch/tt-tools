"""
admin-batch 批量操作模块。

提供后台管理批量操作接口：
- POST /admin/users/batch/status     — 批量修改用户状态
- POST /admin/credits/batch/adjust   — 批量调整额度
- POST /admin/orders/batch/cancel    — 批量取消订单

所有端点需要管理员权限。
"""
