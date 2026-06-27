"""
admin-batch FastAPI 路由。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import (
    require_permission,
    TokenData, require_admin, get_request_id,
    success_response, error_response, AppError, get_db,
)

from schemas import BatchStatusRequest, BatchAdjustRequest, BatchIdsRequest
from service import batch_update_user_status, batch_adjust_credits, batch_cancel_orders

router = APIRouter(tags=["Admin Batch"])


@router.post("/admin/users/batch/status")
async def admin_batch_user_status(
    body: BatchStatusRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("batch.manage")),
    db: AsyncSession = Depends(get_db),
):
    """批量修改用户状态。"""
    try:
        data = await batch_update_user_status(db, body)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(content=error_response(
            code=e.code, message=e.message, request_id=request_id, details=e.details,
        ), status_code=e.status_code)


@router.post("/admin/credits/batch/adjust")
async def admin_batch_adjust_credits(
    body: BatchAdjustRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("batch.manage")),
    db: AsyncSession = Depends(get_db),
):
    """批量调整额度。"""
    try:
        data = await batch_adjust_credits(db, body)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(content=error_response(
            code=e.code, message=e.message, request_id=request_id, details=e.details,
        ), status_code=e.status_code)


@router.post("/admin/orders/batch/cancel")
async def admin_batch_cancel_orders(
    body: BatchIdsRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("batch.manage")),
    db: AsyncSession = Depends(get_db),
):
    """批量取消订单。"""
    try:
        data = await batch_cancel_orders(db, body.ids)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(content=error_response(
            code=e.code, message=e.message, request_id=request_id, details=e.details,
        ), status_code=e.status_code)
