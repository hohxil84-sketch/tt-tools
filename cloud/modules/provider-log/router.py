"""
cloud-provider-log FastAPI 路由。

提供 1 个 API 端点，全部对齐 shared-contract/openapi/provider-log.yaml：
- GET /provider-call-logs — 查询当前用户 Provider 调用日志

统一响应格式和错误处理通过 cloud-shared 公共层实现。

安全规则：
    - 不得返回 raw_usage_json、raw_meta_json 等仅服务端字段。
    - 不得返回完整 prompt、API Key、Token、原图等隐私内容。
    - 只查询当前登录用户自己的调用日志（由 JWT user_id 限定）。
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

from service import list_provider_call_logs

# 创建路由，prefix 在 app-shell 装配时指定
router = APIRouter(tags=["Provider Log"])


# ============================================================
# Provider 调用日志查询（需要 Bearer Token 鉴权）
# ============================================================


@router.get("/provider-call-logs")
async def provider_call_logs(
    limit: int = Query(
        default=50, ge=1, le=100, description="每页返回的日志条数，最大 100"
    ),
    offset: int = Query(
        default=0, ge=0, description="分页偏移量，默认从第 0 条开始"
    ),
    feature: Optional[str] = Query(
        default=None, description="按功能码筛选（如 ai_copy_cloud、ai_render_cloud）"
    ),
    status: Optional[str] = Query(
        default=None, description="按调用状态筛选：success / failed / timeout"
    ),
    provider: Optional[str] = Query(
        default=None, description="按 Provider 名称筛选（如 openai、deepseek）"
    ),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户 Provider 调用日志。

    查询当前登录用户的 Provider（AI 服务）调用日志。
    支持按功能码、调用状态、Provider 名称筛选，支持分页。
    返回字段不包含完整 prompt、API Key、Token、原图等隐私内容。

    需要有效的 Bearer Token。
    对齐 provider-log.yaml GET /provider-call-logs。
    """
    try:
        data = await list_provider_call_logs(
            db,
            user_id=current_user.user_id,
            limit=limit,
            offset=offset,
            feature=feature,
            status=status,
            provider=provider,
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
