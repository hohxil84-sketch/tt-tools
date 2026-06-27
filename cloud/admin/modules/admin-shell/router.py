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
from fastapi.responses import JSONResponse

from cloud.shared import (
    TokenData,
    require_admin,
    require_permission,
    get_user_permissions,
    get_request_id,
    success_response,
    error_response,
    AppError,
)

from service import get_dashboard_stats, get_menu, get_status, login_admin, refresh_admin, logout_admin
from fastapi import Request as FastAPIRequest  # noqa: E402 — 用于认证端点的原始请求体
from cloud.shared.database import get_db  # noqa: E402 — 认证端点需要数据库会话

# 创建路由，prefix="/api/v1/admin" 在 app-shell 装配时指定
router = APIRouter(tags=["Admin Shell"])


# ============================================================
# 仪表盘端点
# ============================================================

@router.get("/dashboard")
async def admin_dashboard(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("dashboard.read")),
    db=Depends(get_db),
):
    """后台仪表盘概览。

    返回核心统计指标：用户总数、今日订单数、今日收入、活跃设备数、
    服务健康状态。需要管理员权限。

    对齐 admin-shell.yaml GET /admin/dashboard。
    """
    try:
        # 调用服务层获取统计数据（从数据库实时查询）
        data = await get_dashboard_stats(db=db)
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

@router.get("/menu")
async def admin_menu(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("dashboard.read")),
    db=Depends(get_db),
):
    """后台导航菜单。

    返回后台左侧导航栏的菜单结构，前端根据此数据渲染导航。
    需要管理员权限。菜单项按当前用户 RBAC 权限自动过滤。

    对齐 admin-shell.yaml GET /admin/menu。
    """
    try:
        # 查询用户权限码，传入 get_menu 进行菜单过滤
        user_permissions = await get_user_permissions(db, current_user.user_id)
        data = get_menu(user_permissions=set(user_permissions))
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

@router.get("/status")
async def admin_status(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("dashboard.read")),
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


# ============================================================
# 认证端点（登录 / 刷新 / 退出，无需管理员权限）
# ============================================================

@router.post("/auth/login")
async def auth_login(
    request: FastAPIRequest,
    request_id: str = Depends(get_request_id),
    db=Depends(get_db),
):
    """管理员登录，返回 JWT access_token 和 refresh_token。"""
    try:
        body = await request.json()
        data = await login_admin(
            db,
            account=body["account"],
            password=body["password"],
            device_fingerprint=body.get("device_fingerprint", "admin-web"),
            device_name=body.get("device_name"),
            client_version=body.get("client_version"),
        )
        return success_response(data, request_id)
    except AppError as e:
        return error_response(code=e.code, message=e.message,
                              request_id=request_id, status_code=e.status_code)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None,
                     "error": {"code": "UNKNOWN_ERROR", "message": str(e)},
                     "request_id": request_id},
        )


@router.post("/auth/refresh")
async def auth_refresh(
    request: FastAPIRequest,
    request_id: str = Depends(get_request_id),
    db=Depends(get_db),
):
    """刷新令牌，返回新的 token 对。"""
    try:
        body = await request.json()
        data = await refresh_admin(db, refresh_token=body["refresh_token"])
        return success_response(data, request_id)
    except AppError as e:
        return error_response(code=e.code, message=e.message,
                              request_id=request_id, status_code=e.status_code)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None,
                     "error": {"code": "UNKNOWN_ERROR", "message": str(e)},
                     "request_id": request_id},
        )


@router.post("/auth/logout")
async def auth_logout(
    request: FastAPIRequest,
    request_id: str = Depends(get_request_id),
    db=Depends(get_db),
):
    """退出登录，撤销 refresh_token。"""
    try:
        body = await request.json()
        data = await logout_admin(db, refresh_token=body["refresh_token"])
        return success_response(data, request_id)
    except AppError as e:
        return error_response(code=e.code, message=e.message,
                              request_id=request_id, status_code=e.status_code)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None,
                     "error": {"code": "UNKNOWN_ERROR", "message": str(e)},
                     "request_id": request_id},
        )
