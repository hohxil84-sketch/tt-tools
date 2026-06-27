"""
admin-export FastAPI 路由。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import (
    require_permission,
    TokenData, require_admin, get_request_id, get_db,
)

from service import (
    export_users_csv, export_orders_csv,
    export_credits_ledger_csv, export_provider_call_logs_csv,
)

router = APIRouter(tags=["Admin Export"])


@router.get("/admin/export/users")
async def admin_export_users(
    status: Optional[str] = Query(default=None, description="按状态筛选"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("export.read")),
    db: AsyncSession = Depends(get_db),
):
    """导出用户列表为 CSV。"""
    return await export_users_csv(db, status=status)


@router.get("/admin/export/orders")
async def admin_export_orders(
    status: Optional[str] = Query(default=None, description="按状态筛选"),
    order_type: Optional[str] = Query(default=None, description="按类型筛选"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("export.read")),
    db: AsyncSession = Depends(get_db),
):
    """导出订单列表为 CSV。"""
    return await export_orders_csv(db, status=status, order_type=order_type)


@router.get("/admin/export/credits-ledger")
async def admin_export_credits_ledger(
    user_id: Optional[str] = Query(default=None, description="按用户 ID 筛选"),
    change_type: Optional[str] = Query(default=None, description="按变化类型筛选"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("export.read")),
    db: AsyncSession = Depends(get_db),
):
    """导出额度流水为 CSV。"""
    return await export_credits_ledger_csv(db, user_id=user_id, change_type=change_type)


@router.get("/admin/export/provider-call-logs")
async def admin_export_provider_logs(
    feature: Optional[str] = Query(default=None, description="按功能码筛选"),
    provider: Optional[str] = Query(default=None, description="按 Provider 筛选"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("export.read")),
    db: AsyncSession = Depends(get_db),
):
    """导出 Provider 调用记录为 CSV。"""
    return await export_provider_call_logs_csv(db, feature=feature, provider=provider)
