"""
admin-audit FastAPI 路由。

提供 2 个审计日志查询端点：
- GET /admin/audit-logs        — 查询审计日志列表
- GET /admin/audit-logs/{id}   — 查询审计日志详情

所有端点需要管理员权限（JWT role=admin）。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import (
    require_permission,
    TokenData,
    require_admin,
    get_request_id,
    success_response,
    error_response,
    AppError,
    get_db,
)

from service import list_audit_logs, get_audit_log_detail

router = APIRouter(tags=["Admin Audit"])


@router.get("/admin/audit-logs")
async def admin_list_audit_logs(
    limit: int = Query(default=20, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    admin_user_id: Optional[str] = Query(default=None, description="按操作管理员 ID 筛选"),
    action: Optional[str] = Query(default=None, description="按操作类型筛选"),
    target_type: Optional[str] = Query(default=None, description="按目标资源类型筛选"),
    target_id: Optional[str] = Query(default=None, description="按目标资源 ID 筛选"),
    order: str = Query(default="desc", description="排序方向：desc（倒序）/ asc（正序）"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("audit.read")),
    db: AsyncSession = Depends(get_db),
):
    """查询审计日志列表。

    支持分页和多条件筛选（操作人、操作类型、目标类型、目标 ID）。
    需要管理员权限。
    """
    try:
        data = await list_audit_logs(
            db=db,
            limit=limit,
            offset=offset,
            admin_user_id=admin_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            order=order,
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


@router.get("/admin/audit-logs/{log_id}")
async def admin_get_audit_log_detail(
    log_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("audit.read")),
    db: AsyncSession = Depends(get_db),
):
    """查询审计日志详情。

    返回单条审计日志的完整信息，包括操作详情 JSON。
    需要管理员权限。
    """
    try:
        data = await get_audit_log_detail(db=db, log_id=log_id)
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
