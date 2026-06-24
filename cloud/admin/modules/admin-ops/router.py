"""
admin-ops FastAPI 路由。

提供 7 个后台运维管理 API 端点，全部对齐 shared-contract/openapi/admin-ops.yaml：

Provider 调用日志：
- GET    /admin/provider-call-logs         — 全部调用日志列表
- GET    /admin/provider-call-logs/{log_id} — 调用日志详情

成本统计：
- GET    /admin/cost-stats                 — 成本/用量聚合统计

风控日志：
- GET    /admin/risk-logs                  — 风控日志列表
- GET    /admin/risk-logs/{log_id}         — 风控日志详情

功能开关：
- GET    /admin/feature-flags              — 查询功能开关配置
- PATCH  /admin/plans/{plan_id}/features   — 更新套餐功能开关

所有端点需要管理员权限（通过 cloud-shared require_admin 鉴权）。
路由 prefix="/api/v1" 由 cloud-app-shell main.py 在注册时指定。
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

from schemas import (
    UpdateFeatureFlagsRequest,
)
from service import (
    list_provider_call_logs,
    get_provider_call_log_detail,
    get_cost_stats,
    list_risk_logs,
    get_risk_log_detail,
    get_feature_flags,
    update_feature_flags,
)

# 创建路由，prefix 在 app-shell 装配时指定
router = APIRouter(tags=["Admin Ops"])


# ============================================================
# Provider 调用日志端点
# ============================================================


@router.get("/admin/provider-call-logs")
async def admin_list_provider_call_logs(
    limit: int = Query(default=20, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    user_id: str | None = Query(default=None, description="按用户 ID 筛选"),
    feature: str | None = Query(default=None, description="按功能码筛选"),
    provider: str | None = Query(default=None, description="按 Provider 名称筛选"),
    status: str | None = Query(default=None, description="按调用状态筛选"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询全部 Provider 调用日志。

    管理员可查看所有用户的调用日志，支持多条件筛选和分页。
    不返回 raw_usage_json 等隐私字段。需要管理员权限。

    对齐 admin-ops.yaml GET /admin/provider-call-logs。
    """
    try:
        data = await list_provider_call_logs(
            db=db,
            limit=limit,
            offset=offset,
            user_id=user_id,
            feature=feature,
            provider=provider,
            status=status,
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


@router.get("/admin/provider-call-logs/{log_id}")
async def admin_get_provider_call_log_detail(
    log_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询 Provider 调用日志详情。

    返回单条调用记录的详细信息（含用户账号和展示名称）。
    需要管理员权限。

    对齐 admin-ops.yaml GET /admin/provider-call-logs/{log_id}。
    """
    try:
        data = await get_provider_call_log_detail(db=db, log_id=log_id)
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
# 成本统计端点
# ============================================================


@router.get("/admin/cost-stats")
async def admin_cost_stats(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询成本/用量聚合统计。

    返回 Provider 调用的全局聚合统计和按功能码、Provider 的细分统计。
    需要管理员权限。

    对齐 admin-ops.yaml GET /admin/cost-stats。
    """
    try:
        data = await get_cost_stats(db=db)
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
# 风控日志端点
# ============================================================


@router.get("/admin/risk-logs")
async def admin_list_risk_logs(
    limit: int = Query(default=20, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    user_id: str | None = Query(default=None, description="按用户 ID 筛选"),
    risk_type: str | None = Query(default=None, description="按风险类型筛选"),
    severity: str | None = Query(default=None, description="按严重程度筛选"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询风控日志列表。

    返回系统中的风控日志，支持多条件筛选和分页。需要管理员权限。

    对齐 admin-ops.yaml GET /admin/risk-logs。
    """
    try:
        data = await list_risk_logs(
            db=db,
            limit=limit,
            offset=offset,
            user_id=user_id,
            risk_type=risk_type,
            severity=severity,
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


@router.get("/admin/risk-logs/{log_id}")
async def admin_get_risk_log_detail(
    log_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询风控日志详情。

    返回单条风控日志的详细信息（含脱敏详情和用户信息）。需要管理员权限。

    对齐 admin-ops.yaml GET /admin/risk-logs/{log_id}。
    """
    try:
        data = await get_risk_log_detail(db=db, log_id=log_id)
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
# 功能开关端点
# ============================================================


@router.get("/admin/feature-flags")
async def admin_get_feature_flags(
    plan_code: str | None = Query(default=None, description="按套餐编码筛选"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询功能开关配置。

    返回各套餐的功能开关配置，可按 plan_code 筛选。需要管理员权限。

    对齐 admin-ops.yaml GET /admin/feature-flags。
    """
    try:
        data = await get_feature_flags(db=db, plan_code=plan_code)
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


@router.patch("/admin/plans/{plan_id}/features")
async def admin_update_plan_features(
    plan_id: str,
    body: UpdateFeatureFlagsRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新套餐功能开关。

    合并更新指定套餐的功能开关配置（只更新传入的 key）。
    需要管理员权限。

    对齐 admin-ops.yaml PATCH /admin/plans/{plan_id}/features。
    """
    try:
        data = await update_feature_flags(
            db=db,
            plan_id=plan_id,
            enabled_features_json=body.enabled_features_json,
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
