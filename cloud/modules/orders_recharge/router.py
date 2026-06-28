"""
cloud-orders-recharge FastAPI 路由。

提供 3 个 API 端点，全部对齐 shared-contract/openapi/orders-recharge.yaml：
- POST /orders                 — 创建订单（套餐购买 / 额度充值）
- GET  /orders                 — 查询当前用户订单列表
- POST /orders/{order_id}/confirm — 确认支付（mock/dev 预留）

统一响应格式和错误处理通过 cloud-shared 公共层实现。
确认支付接口为开发/测试预留，生产前必须接支付回调验签。
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

from schemas import CreateOrderRequest
from service import (
    create_order,
    list_orders,
    confirm_order,
)

# 创建路由，prefix 在 app-shell 装配时指定
router = APIRouter(tags=["Orders / Recharge"])


# ============================================================
# Orders 端点（需要 Bearer Token 鉴权）
# ============================================================


@router.post("/orders")
async def create_order_endpoint(
    req: CreateOrderRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """创建订单（套餐购买 / 额度充值）。

    客户端只提交 order_type 和 product_code，金额由服务端定价表决定。
    客户端不得提交 user_id、final_price、plan_code 等决策字段。
    需要有效的 Bearer Token。
    对齐 orders-recharge.yaml POST /orders。
    """
    try:
        data = await create_order(
            db,
            user_id=current_user.user_id,
            order_type=req.order_type,
            product_code=req.product_code,
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


@router.get("/orders")
async def list_orders_endpoint(
    limit: int = Query(default=50, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    order_type: Optional[str] = Query(
        default=None, description="筛选订单类型：plan / credits"
    ),
    status: Optional[str] = Query(
        default=None, description="筛选订单状态：pending / paid / closed / refunded"
    ),
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户订单列表。

    只返回当前用户自己的订单，支持按 order_type 和 status 筛选和分页。
    需要有效的 Bearer Token。
    对齐 orders-recharge.yaml GET /orders。
    """
    try:
        data = await list_orders(
            db,
            user_id=current_user.user_id,
            limit=limit,
            offset=offset,
            order_type=order_type,
            status=status,
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


@router.post("/orders/{order_id}/confirm")
async def confirm_order_endpoint(
    order_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """确认支付（mock/dev 预留）。

    **注意：本接口为开发/测试预留，不接入真实支付网关。生产前必须接支付回调验签。**

    确认当前用户 pending 订单为 paid，并在同一事务中执行对应业务操作：
    - credits 订单：调用 credits-billing 发放额度
    - plan 订单：更新用户套餐

    接口幂等：重复确认同一订单不会重复发放额度或更新套餐。
    客户端不得提交支付金额、套餐编码等决策字段。
    对齐 orders-recharge.yaml POST /orders/{order_id}/confirm。
    """
    try:
        data = await confirm_order(
            db,
            order_id=order_id,
            user_id=current_user.user_id,
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
# 产品列表端点（供客户端展示可用充值/套餐选项）
# ============================================================


@router.get("/products")
async def list_products_endpoint(
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """获取可用产品列表（套餐 + 充值包）。不鉴权——任何人都可以浏览。"""
    try:
        from sqlalchemy import text as _text
        # 直接用 raw SQL 查 credit_packages，避免 importlib 跨模块冲突
        cp_result = await db.execute(
            _text("SELECT product_code, name, credit_amount, price_cents, sort_order "
                  "FROM credit_packages WHERE is_active = TRUE ORDER BY sort_order"),
        )
        credits_items = [
            {"product_code": r[0], "name": r[1], "credit_amount": r[2],
             "price_cents": r[3], "sort_order": r[4]}
            for r in cp_result.all()
        ]
        plans_result = await db.execute(
            _text("SELECT id, name, plan_tier, monthly_grant, price_cents FROM plans WHERE status = 'active' ORDER BY price_cents"),
        )
        plan_items = [
            {"plan_id": r[0], "name": r[1], "plan_tier": r[2],
             "monthly_grant": r[3], "price_cents": r[4]}
            for r in plans_result.all()
        ]
        return success_response({"plans": plan_items, "credit_packages": credits_items}, request_id)
    except AppError as e:
        return error_response(
            code=e.code, message=e.message,
            request_id=request_id, status_code=e.status_code, details=e.details,
        )
