"""
admin-users FastAPI 路由。

提供 7 个后台管理 API 端点，全部对齐 shared-contract/openapi/admin-users.yaml：
用户管理：
- GET    /admin/users                      — 用户列表
- GET    /admin/users/{user_id}            — 用户详情
- PATCH  /admin/users/{user_id}/status     — 修改用户状态
- GET    /admin/users/{user_id}/devices    — 用户的设备列表
设备管理：
- GET    /admin/devices                    — 设备列表
- GET    /admin/devices/{device_id}        — 设备详情
- PATCH  /admin/devices/{device_id}/status — 修改设备状态

所有端点需要管理员权限（通过 cloud-shared require_admin 鉴权）。
路由 prefix="/api/v1/admin" 由 cloud-app-shell main.py 在注册时指定。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import (
    TokenData,
    require_admin,
    get_request_id,
    success_response,
    error_response,
    AppError,
    get_db,
)

from schemas import UpdateUserStatusRequest, UpdateDeviceStatusRequest
from service import (
    list_users,
    get_user_detail,
    update_user_status,
    list_user_devices,
    list_devices,
    get_device_detail,
    update_device_status,
)

# 创建路由，prefix="/api/v1/admin" 在 app-shell 装配时指定
router = APIRouter(tags=["Admin Users"])


# ============================================================
# 用户管理端点
# ============================================================


@router.get("/admin/users")
async def admin_list_users(
    limit: int = Query(default=20, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    status: str | None = Query(default=None, description="按状态筛选"),
    search: str | None = Query(default=None, description="按账号或名称搜索"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询用户列表。

    支持分页、状态筛选和账号/名称模糊搜索。需要管理员权限。

    对齐 admin-users.yaml GET /admin/users。
    """
    try:
        data = await list_users(
            db=db,
            limit=limit,
            offset=offset,
            status=status,
            search=search,
        )
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(
                code=e.code,
                message=e.message,
                request_id=request_id,
                details=e.details,
            ),
            status_code=e.status_code,
        )


@router.get("/admin/users/{user_id}")
async def admin_get_user(
    user_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询用户详情。

    根据用户 ID 返回用户的详细信息。需要管理员权限。

    对齐 admin-users.yaml GET /admin/users/{user_id}。
    """
    try:
        data = await get_user_detail(db=db, user_id=user_id)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(
                code=e.code,
                message=e.message,
                request_id=request_id,
                details=e.details,
            ),
            status_code=e.status_code,
        )


@router.patch("/admin/users/{user_id}/status")
async def admin_update_user_status(
    user_id: str,
    body: UpdateUserStatusRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """修改用户状态。

    将指定用户的状态修改为目标状态（active / blocked / deleted）。需要管理员权限。

    对齐 admin-users.yaml PATCH /admin/users/{user_id}/status。
    """
    try:
        data = await update_user_status(
            db=db, user_id=user_id, new_status=body.status
        )
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(
                code=e.code,
                message=e.message,
                request_id=request_id,
                details=e.details,
            ),
            status_code=e.status_code,
        )


@router.get("/admin/users/{user_id}/devices")
async def admin_list_user_devices(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询用户的设备列表。

    返回指定用户的所有绑定设备。需要管理员权限。

    对齐 admin-users.yaml GET /admin/users/{user_id}/devices。
    """
    try:
        data = await list_user_devices(
            db=db, user_id=user_id, limit=limit, offset=offset
        )
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(
                code=e.code,
                message=e.message,
                request_id=request_id,
                details=e.details,
            ),
            status_code=e.status_code,
        )


# ============================================================
# 设备管理端点
# ============================================================


@router.get("/admin/devices")
async def admin_list_devices(
    limit: int = Query(default=20, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    status: str | None = Query(default=None, description="按状态筛选"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询所有设备列表。

    支持分页和状态筛选。需要管理员权限。

    对齐 admin-users.yaml GET /admin/devices。
    """
    try:
        data = await list_devices(
            db=db, limit=limit, offset=offset, status=status
        )
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(
                code=e.code,
                message=e.message,
                request_id=request_id,
                details=e.details,
            ),
            status_code=e.status_code,
        )


@router.get("/admin/devices/{device_id}")
async def admin_get_device(
    device_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询设备详情。

    根据设备 ID 返回设备的详细信息。需要管理员权限。

    对齐 admin-users.yaml GET /admin/devices/{device_id}。
    """
    try:
        data = await get_device_detail(db=db, device_id=device_id)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(
                code=e.code,
                message=e.message,
                request_id=request_id,
                details=e.details,
            ),
            status_code=e.status_code,
        )


@router.patch("/admin/devices/{device_id}/status")
async def admin_update_device_status(
    device_id: str,
    body: UpdateDeviceStatusRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """修改设备状态。

    将指定设备的状态修改为目标状态（active / blocked / removed）。需要管理员权限。

    对齐 admin-users.yaml PATCH /admin/devices/{device_id}/status。
    """
    try:
        data = await update_device_status(
            db=db, device_id=device_id, new_status=body.status
        )
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(
                code=e.code,
                message=e.message,
                request_id=request_id,
                details=e.details,
            ),
            status_code=e.status_code,
        )
