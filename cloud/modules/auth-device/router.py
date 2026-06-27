"""
cloud-auth-device FastAPI 路由。

提供 5 个 API 端点，全部对齐 shared-contract/openapi/auth-device.yaml：
- POST /auth/login       — 登录
- POST /auth/refresh     — 刷新令牌
- POST /auth/logout      — 退出登录
- GET  /devices/current  — 获取当前设备
- POST /devices/bind     — 绑定设备

统一响应格式和错误处理通过 cloud-shared 公共层实现。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import (
    get_db,
    get_request_id,
    require_auth,
    success_response,
    error_response,
    AppError,
    TokenData,
)

from schemas import (
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
    BindDeviceRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
)
from service import (
    login, refresh, logout, get_current_device, bind_device,
    forgot_password, reset_password, change_password,
)

# 创建路由，prefix 在 app-shell 装配时指定
router = APIRouter(tags=["Auth / Device"])


# ============================================================
# Auth 端点
# ============================================================


@router.post("/auth/login")
async def auth_login(
    req: LoginRequest,
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """登录接口。

    使用账号、密码和设备指纹登录。
    成功返回 access_token、refresh_token、用户信息和设备绑定状态。
    对齐 auth-device.yaml POST /auth/login。
    """
    try:
        data = await login(db, req)
        return success_response(data.model_dump(), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )


@router.post("/auth/refresh")
async def auth_refresh(
    req: RefreshRequest,
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """刷新令牌接口。

    使用有效的 refresh_token 换取新的令牌对。
    旧 refresh_token 立即失效（令牌轮换）。
    对齐 auth-device.yaml POST /auth/refresh。
    """
    try:
        data = await refresh(db, req.refresh_token)
        return success_response(data.model_dump(), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )


@router.post("/auth/logout")
async def auth_logout(
    req: LogoutRequest,
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """退出登录接口。

    撤销指定的 refresh_token，使当前会话失效。
    操作是幂等的。
    对齐 auth-device.yaml POST /auth/logout。
    """
    try:
        data = await logout(db, req.refresh_token)
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
# 密码重置端点
# ============================================================


@router.post("/auth/password/forgot")
async def auth_forgot_password(
    req: ForgotPasswordRequest,
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """忘记密码接口。

    根据账号生成密码重置令牌。开发阶段直接返回令牌，
    生产环境应改为发送邮件。
    """
    try:
        message, reset_token = await forgot_password(db, req.account)
        return success_response(
            {"message": message, "reset_token": reset_token},
            request_id,
        )
    except AppError as e:
        return error_response(
            code=e.code, message=e.message,
            request_id=request_id, status_code=e.status_code, details=e.details,
        )


@router.post("/auth/password/reset")
async def auth_reset_password(
    req: ResetPasswordRequest,
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """重置密码接口。

    使用重置令牌设置新密码。成功后所有旧会话被撤销。
    """
    try:
        message = await reset_password(db, req.reset_token, req.new_password)
        return success_response({"message": message}, request_id)
    except AppError as e:
        return error_response(
            code=e.code, message=e.message,
            request_id=request_id, status_code=e.status_code, details=e.details,
        )


@router.post("/auth/password/change")
async def auth_change_password(
    req: ChangePasswordRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """修改密码接口（需登录）。

    验证旧密码后更新为新密码。
    """
    try:
        message = await change_password(
            db, current_user.user_id, req.old_password, req.new_password,
        )
        return success_response({"message": message}, request_id)
    except AppError as e:
        return error_response(
            code=e.code, message=e.message,
            request_id=request_id, status_code=e.status_code, details=e.details,
        )


# ============================================================
# Device 端点（需要 Bearer Token 鉴权）
# ============================================================


@router.get("/devices/current")
async def devices_current(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """获取当前设备详情。

    根据 JWT 中的 user_id 和 device_id 返回设备信息。
    需要有效的 Bearer Token。
    对齐 auth-device.yaml GET /devices/current。
    """
    try:
        device_id = current_user.device_id
        if not device_id:
            # JWT 中无 device_id（例如管理员操作），返回错误
            from cloud.shared import ErrorCode
            return error_response(
                code=ErrorCode.DEVICE_NOT_BOUND,
                message="当前会话未关联设备",
                request_id=request_id,
                status_code=404,
            )

        data = await get_current_device(
            db,
            user_id=current_user.user_id,
            device_id=device_id,
        )
        return success_response(data.model_dump(), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )


@router.post("/devices/bind")
async def devices_bind(
    req: BindDeviceRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """绑定当前设备。

    将设备与已登录用户关联。重复绑定同一设备返回已有记录。
    需要有效的 Bearer Token。
    对齐 auth-device.yaml POST /devices/bind。
    """
    try:
        data = await bind_device(db, user_id=current_user.user_id, req=req)
        return success_response(data.model_dump(), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )
