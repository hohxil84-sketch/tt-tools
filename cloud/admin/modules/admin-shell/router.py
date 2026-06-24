"""
admin-shell FastAPI 路由。

提供 3 个后台管理 API 端点，全部对齐 shared-contract/openapi/admin-shell.yaml：
- GET /admin/dashboard  — 仪表盘概览
- GET /admin/menu       — 导航菜单
- GET /admin/status     — 服务状态

所有端点需要管理员权限（JWT role=admin），通过 cloud-shared 的
require_admin 依赖实现鉴权。

路由 prefix="/api/v1/admin" 由 cloud-app-shell main.py 在注册时指定。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from cloud.shared import (
    TokenData,
    require_admin,
    get_request_id,
    success_response,
    error_response,
    AppError,
)

from service import get_dashboard_stats, get_menu, get_status

# 创建路由，prefix="/api/v1/admin" 在 app-shell 装配时指定
router = APIRouter(tags=["Admin Shell"])


# ============================================================
# 仪表盘端点
# ============================================================

@router.get("/admin/dashboard")
async def admin_dashboard(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
):
    """后台仪表盘概览。

    返回核心统计指标：用户总数、今日订单数、今日收入、活跃设备数、
    服务健康状态。需要管理员权限。

    对齐 admin-shell.yaml GET /admin/dashboard。
    """
    try:
        # 调用服务层获取统计数据（db 参数预留，后续接入真实查询）
        data = await get_dashboard_stats(db=None)
        return success_response(data.model_dump(), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )


# ============================================================
# 导航菜单端点
# ============================================================

@router.get("/admin/menu")
async def admin_menu(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
):
    """后台导航菜单。

    返回后台左侧导航栏的菜单结构，前端根据此数据渲染导航。
    需要管理员权限。

    对齐 admin-shell.yaml GET /admin/menu。
    """
    try:
        data = get_menu()
        return success_response(data.model_dump(), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )


# ============================================================
# 服务状态端点
# ============================================================

@router.get("/admin/status")
async def admin_status(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
):
    """服务状态检查。

    返回当前服务的健康状态、版本号和运行时长。
    需要管理员权限。

    对齐 admin-shell.yaml GET /admin/status。
    """
    try:
        data = get_status()
        return success_response(data.model_dump(), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )
