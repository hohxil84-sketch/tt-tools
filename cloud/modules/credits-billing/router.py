"""
cloud-credits-billing FastAPI 路由。

提供 3 个 API 端点，全部对齐 shared-contract/openapi/credits-billing.yaml：
- GET  /credits/balance     — 查询当前用户 AI 额度余额
- GET  /credits/ledger      — 查询当前用户 AI 额度流水
- POST /entitlements/check  — 检查本地付费功能套餐权限

统一响应格式和错误处理通过 cloud-shared 公共层实现。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
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

from schemas import EntitlementCheckRequest
from service import (
    get_credit_balance,
    list_credit_ledger,
    check_entitlement,
)

# 创建路由，prefix 在 app-shell 装配时指定
router = APIRouter(tags=["Credits / Billing"])


# ============================================================
# Credits 端点（需要 Bearer Token 鉴权）
# ============================================================


@router.get("/credits/balance")
async def credits_balance(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户 AI 额度余额。

    返回用户额度账户的套餐、余额、计费周期和状态信息。
    需要有效的 Bearer Token。
    对齐 credits-billing.yaml GET /credits/balance。
    """
    try:
        data = await get_credit_balance(db, user_id=current_user.user_id)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )


@router.get("/credits/ledger")
async def credits_ledger(
    limit: int = Query(default=50, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    change_type: Optional[str] = Query(
        default=None, description="筛选变化类型：grant / consume / recharge / refund / adjust"
    ),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户 AI 额度流水。

    支持按 change_type 筛选和分页，按创建时间倒序排列。
    需要有效的 Bearer Token。
    对齐 credits-billing.yaml GET /credits/ledger。
    """
    try:
        data = await list_credit_ledger(
            db,
            user_id=current_user.user_id,
            limit=limit,
            offset=offset,
            change_type=change_type,
        )
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )


# ============================================================
# Entitlement 端点（需要 Bearer Token 鉴权）
# ============================================================


@router.post("/entitlements/check")
async def entitlements_check(
    req: EntitlementCheckRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """检查本地付费功能套餐权限。

    桌面端在调用本地付费功能前，通过本接口检查当前用户套餐是否允许使用。
    权限检查不消耗 AI 额度，仅返回套餐权限结果。
    需要有效的 Bearer Token。
    对齐 credits-billing.yaml POST /entitlements/check。
    """
    try:
        data = await check_entitlement(
            db,
            user_id=current_user.user_id,
            plan_id=current_user.plan_id,
            feature=req.feature,
            operation=req.operation,
            client_request_id=req.client_request_id,
        )
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )
