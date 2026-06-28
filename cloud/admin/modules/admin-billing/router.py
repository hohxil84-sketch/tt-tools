"""
admin-billing FastAPI 路由。

提供 11 个后台管理 API 端点，全部对齐 shared-contract/openapi/admin-billing.yaml：
套餐管理：
- GET    /admin/plans              — 套餐列表
- GET    /admin/plans/{plan_id}    — 套餐详情
- POST   /admin/plans              — 创建套餐
- PATCH  /admin/plans/{plan_id}    — 更新套餐
- PATCH  /admin/plans/{plan_id}/status — 启用/停用套餐
订单管理：
- GET    /admin/orders             — 全部订单列表
- GET    /admin/orders/{order_id}  — 订单详情
额度管理：
- GET    /admin/credits/accounts   — 额度账户列表
- GET    /admin/credits/accounts/{account_id} — 额度账户详情
- GET    /admin/credits/ledger     — 全部额度流水
- POST   /admin/credits/adjust     — 手动调整额度

所有端点需要管理员权限（通过 cloud-shared require_admin 鉴权）。
路由 prefix="/api/v1/admin" 由 cloud-app-shell main.py 在注册时指定。
"""
from __future__ import annotations

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

from schemas import (
    CreatePlanRequest,
    UpdatePlanRequest,
    UpdatePlanStatusRequest,
    AdjustCreditsRequest,
)
from service import (
    list_plans,
    get_plan_detail,
    list_plan_options,
    create_plan,
    update_plan,
    update_plan_status,
    delete_plan,
    list_all_orders,
    get_admin_order_detail,
    cancel_admin_order,
    refund_admin_order,
    list_credit_accounts,
    get_credit_account_detail,
    list_all_credit_ledger,
    adjust_credits,
    # 新增定价管理
    list_model_pricing,
    create_model_pricing,
    update_model_pricing,
    list_feature_pricing,
    update_feature_pricing,
    get_system_config,
    update_system_config,
    list_credit_packages_admin,
    create_credit_package,
    update_credit_package,
)

# 创建路由，prefix="/api/v1/admin" 在 app-shell 装配时指定
router = APIRouter(tags=["Admin Billing"])


# ============================================================
# 套餐管理端点
# ============================================================


@router.get("/admin/plans")
async def admin_list_plans(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.read")),
    db: AsyncSession = Depends(get_db),
):
    """查询套餐列表。

    返回所有套餐的列表，包括编码、名称、月赠额度、状态。
    需要管理员权限。

    对齐 admin-billing.yaml GET /admin/plans。
    """
    try:
        data = await list_plans(db=db)
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


@router.get("/admin/plans/options")
async def admin_list_plan_options(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.read")),
    db: AsyncSession = Depends(get_db),
):
    """查询套餐选项列表。

    返回 active 套餐的 {id, name} 精简列表，供前端下拉框使用。
    需要管理员权限。
    注意：此路由必须在 /admin/plans/{plan_id} 之前注册，否则 "options" 会被当作 plan_id 参数匹配。

    对齐 admin-billing.yaml GET /admin/plans/options。
    """
    try:
        data = await list_plan_options(db=db)
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


@router.get("/admin/plans/{plan_id}")
async def admin_get_plan_detail(
    plan_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.read")),
    db: AsyncSession = Depends(get_db),
):
    """查询套餐详情。

    根据套餐 ID 返回套餐的完整配置信息。需要管理员权限。

    对齐 admin-billing.yaml GET /admin/plans/{plan_id}。
    """
    try:
        data = await get_plan_detail(db=db, plan_id=plan_id)
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


@router.post("/admin/plans")
async def admin_create_plan(
    body: CreatePlanRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.manage")),
    db: AsyncSession = Depends(get_db),
):
    """创建新套餐。

    创建一个新的套餐配置，编码必须唯一。需要管理员权限。

    对齐 admin-billing.yaml POST /admin/plans。
    """
    try:
        data = await create_plan(
            db=db,
            name=body.name,
            monthly_grant=body.monthly_grant,
            expire_days=body.expire_days,
            is_default=body.is_default,
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


@router.patch("/admin/plans/{plan_id}")
async def admin_update_plan(
    plan_id: str,
    body: UpdatePlanRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.manage")),
    db: AsyncSession = Depends(get_db),
):
    """更新套餐配置。

    更新指定套餐的名称、月赠额度或功能开关。套餐编码不可修改。需要管理员权限。

    对齐 admin-billing.yaml PATCH /admin/plans/{plan_id}。
    """
    try:
        data = await update_plan(
            db=db,
            plan_id=plan_id,
            name=body.name,
            monthly_grant=body.monthly_grant,
            expire_days=body.expire_days,
            is_default=body.is_default,
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


@router.patch("/admin/plans/{plan_id}/status")
async def admin_update_plan_status(
    plan_id: str,
    body: UpdatePlanStatusRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.manage")),
    db: AsyncSession = Depends(get_db),
):
    """启用/停用套餐。

    修改指定套餐的状态（active / disabled）。需要管理员权限。

    对齐 admin-billing.yaml PATCH /admin/plans/{plan_id}/status。
    """
    try:
        data = await update_plan_status(db=db, plan_id=plan_id, new_status=body.status)
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
# 订单管理端点
# ============================================================


@router.delete("/admin/plans/{plan_id}")
async def admin_delete_plan(
    plan_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.manage")),
    db: AsyncSession = Depends(get_db),
):
    """删除套餐。

    硬删除套餐。如有关联用户则拒绝。需要管理员权限。

    对齐 admin-billing.yaml DELETE /admin/plans/{plan_id}。
    """
    try:
        data = await delete_plan(db=db, plan_id=plan_id)
        return success_response(data, request_id)
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


@router.get("/admin/orders")
async def admin_list_orders(
    limit: int = Query(default=20, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    user_id: str | None = Query(default=None, description="按用户 ID 筛选"),
    order_type: str | None = Query(default=None, description="按订单类型筛选"),
    status: str | None = Query(default=None, description="按订单状态筛选"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("orders.read")),
    db: AsyncSession = Depends(get_db),
):
    """查询全部订单列表。

    管理员可查看所有用户的订单，支持多条件筛选和分页。需要管理员权限。

    对齐 admin-billing.yaml GET /admin/orders。
    """
    try:
        data = await list_all_orders(
            db=db,
            limit=limit,
            offset=offset,
            user_id=user_id,
            order_type=order_type,
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


@router.get("/admin/orders/{order_id}")
async def admin_get_order_detail(
    order_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("orders.read")),
    db: AsyncSession = Depends(get_db),
):
    """查询订单详情。

    管理员可查看任意用户订单的详细信息（含用户账号和展示名称）。需要管理员权限。

    对齐 admin-billing.yaml GET /admin/orders/{order_id}。
    """
    try:
        data = await get_admin_order_detail(db=db, order_id=order_id)
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


@router.post("/admin/orders/{order_id}/cancel")
async def admin_cancel_order(
    order_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("orders.cancel")),
    db: AsyncSession = Depends(get_db),
):
    """取消订单。

    将 pending 状态的订单变更为 closed。需要管理员权限。
    """
    try:
        data = await cancel_admin_order(db=db, order_id=order_id)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(
                code=e.code, message=e.message,
                request_id=request_id, details=e.details,
            ),
            status_code=e.status_code,
        )


@router.post("/admin/orders/{order_id}/refund")
async def admin_refund_order(
    order_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("orders.refund")),
    db: AsyncSession = Depends(get_db),
):
    """退款订单。

    将 paid 状态的订单变更为 refunded，并退还/扣除对应资源。
    credits 类型退额度，plan 类型降级套餐。需要管理员权限。
    """
    try:
        data = await refund_admin_order(db=db, order_id=order_id)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(
                code=e.code, message=e.message,
                request_id=request_id, details=e.details,
            ),
            status_code=e.status_code,
        )


# ============================================================
# 额度管理端点
# ============================================================


@router.get("/admin/credits/accounts")
async def admin_list_credit_accounts(
    limit: int = Query(default=20, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    status: str | None = Query(default=None, description="按账户状态筛选"),
    plan_id: str | None = Query(default=None, description="按套餐 ID 筛选"),
    user_id: str | None = Query(default=None, description="按用户 ID 筛选"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("credits.read")),
    db: AsyncSession = Depends(get_db),
):
    """查询额度账户列表。

    管理员可查看所有用户的额度账户，支持状态和用户 ID 筛选。需要管理员权限。

    对齐 admin-billing.yaml GET /admin/credits/accounts。
    """
    try:
        data = await list_credit_accounts(
            db=db,
            limit=limit,
            offset=offset,
            status=status,
            plan_id=plan_id,
            user_id=user_id,
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


@router.get("/admin/credits/accounts/{account_id}")
async def admin_get_credit_account_detail(
    account_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("credits.read")),
    db: AsyncSession = Depends(get_db),
):
    """查询额度账户详情。

    返回指定额度账户的详细信息（含关联用户信息）。需要管理员权限。

    对齐 admin-billing.yaml GET /admin/credits/accounts/{account_id}。
    """
    try:
        data = await get_credit_account_detail(db=db, account_id=account_id)
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


@router.get("/admin/credits/ledger")
async def admin_list_credit_ledger(
    limit: int = Query(default=20, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    user_id: str | None = Query(default=None, description="按用户 ID 筛选"),
    change_type: str | None = Query(default=None, description="按变化类型筛选"),
    source_type: str | None = Query(default=None, description="按来源类型筛选"),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("credits.read")),
    db: AsyncSession = Depends(get_db),
):
    """查询全部额度流水。

    管理员可查看所有用户的额度流水，支持多条件筛选和分页。需要管理员权限。

    对齐 admin-billing.yaml GET /admin/credits/ledger。
    """
    try:
        data = await list_all_credit_ledger(
            db=db,
            limit=limit,
            offset=offset,
            user_id=user_id,
            change_type=change_type,
            source_type=source_type,
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


@router.post("/admin/credits/adjust")
async def admin_adjust_credits(
    body: AdjustCreditsRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("credits.adjust")),
    db: AsyncSession = Depends(get_db),
):
    """手动调整额度。

    管理员手动为用户赠送或扣除 AI 额度。操作写入 credit_ledger。
    需要管理员权限。

    对齐 admin-billing.yaml POST /admin/credits/adjust。
    """
    try:
        data = await adjust_credits(
            db=db,
            user_id=body.user_id,
            amount=body.amount,
            description=body.description,
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
# 模型定价管理端点
# ============================================================


@router.get("/admin/billing/model-pricing")
async def admin_list_model_pricing(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.read")),
    db: AsyncSession = Depends(get_db),
):
    """列出所有 Provider 模型定价。"""
    try:
        items = await list_model_pricing(db)
        return success_response({"items": items}, request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details),
            status_code=e.status_code,
        )


@router.post("/admin/billing/model-pricing")
async def admin_create_model_pricing(
    body: dict,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.write")),
    db: AsyncSession = Depends(get_db),
):
    """新增模型定价。"""
    try:
        data = await create_model_pricing(
            db,
            provider_name=body["provider_name"],
            model_name=body["model_name"],
            input_price=float(body["input_price"]),
            output_price=float(body["output_price"]),
            currency=body.get("currency", "CNY"),
        )
        return success_response(data, request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details),
            status_code=e.status_code,
        )


@router.put("/admin/billing/model-pricing/{pricing_id}")
async def admin_update_model_pricing(
    pricing_id: str,
    body: dict,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.write")),
    db: AsyncSession = Depends(get_db),
):
    """更新模型定价。"""
    try:
        await update_model_pricing(db, pricing_id, **body)
        return success_response({"id": pricing_id}, request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details),
            status_code=e.status_code,
        )


# ============================================================
# 功能定价管理端点
# ============================================================


@router.get("/admin/billing/feature-pricing")
async def admin_list_feature_pricing(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.read")),
    db: AsyncSession = Depends(get_db),
):
    """列出所有功能起步扣点。"""
    try:
        items = await list_feature_pricing(db)
        return success_response({"items": items}, request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details),
            status_code=e.status_code,
        )


@router.put("/admin/billing/feature-pricing/{feature_code}")
async def admin_update_feature_pricing(
    feature_code: str,
    body: dict,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.write")),
    db: AsyncSession = Depends(get_db),
):
    """更新功能起步扣点。"""
    try:
        await update_feature_pricing(
            db, feature_code,
            min_credits=int(body["min_credits"]),
            default_max_tokens=body.get("default_max_tokens"),
        )
        return success_response({"feature_code": feature_code}, request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details),
            status_code=e.status_code,
        )


# ============================================================
# 系统配置管理端点
# ============================================================


@router.get("/admin/billing/system-config")
async def admin_get_system_config(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.read")),
    db: AsyncSession = Depends(get_db),
):
    """获取系统配置。"""
    try:
        data = await get_system_config(db)
        return success_response(data, request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details),
            status_code=e.status_code,
        )


@router.put("/admin/billing/system-config/{key}")
async def admin_update_system_config(
    key: str,
    body: dict,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.write")),
    db: AsyncSession = Depends(get_db),
):
    """更新系统配置。"""
    try:
        await update_system_config(db, key, str(body["value"]))
        return success_response({"key": key}, request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details),
            status_code=e.status_code,
        )


# ============================================================
# 充值套餐管理端点
# ============================================================


@router.get("/admin/billing/credit-packages")
async def admin_list_credit_packages(
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.read")),
    db: AsyncSession = Depends(get_db),
):
    """列出所有充值套餐。"""
    try:
        items = await list_credit_packages_admin(db)
        return success_response({"items": items}, request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details),
            status_code=e.status_code,
        )


@router.post("/admin/billing/credit-packages")
async def admin_create_credit_package(
    body: dict,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.write")),
    db: AsyncSession = Depends(get_db),
):
    """新增充值套餐。"""
    try:
        data = await create_credit_package(
            db,
            product_code=body["product_code"],
            name=body["name"],
            credit_amount=int(body["credit_amount"]),
            price_cents=int(body["price_cents"]),
            sort_order=body.get("sort_order", 0),
        )
        return success_response(data, request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details),
            status_code=e.status_code,
        )


@router.put("/admin/billing/credit-packages/{package_id}")
async def admin_update_credit_package(
    package_id: str,
    body: dict,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_permission("plans.write")),
    db: AsyncSession = Depends(get_db),
):
    """更新充值套餐。"""
    try:
        await update_credit_package(db, package_id, **body)
        return success_response({"id": package_id}, request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details),
            status_code=e.status_code,
        )
