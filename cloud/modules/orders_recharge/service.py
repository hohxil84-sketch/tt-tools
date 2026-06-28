"""
cloud-orders-recharge 业务逻辑层。

提供订单创建、列表查询和支付确认的核心逻辑。

关键规则（硬约束）：
- 客户端不得提交 user_id、final_price、plan_code 等决策字段。
- 支付确认为 mock/dev 预留，不接入真实支付网关。
- 确认支付必须在同一数据库事务中完成：状态更新 + 额度发放/套餐切换。
- 重复确认幂等：使用数据库条件 UPDATE（WHERE status='pending'），rowcount=0 时返回已有结果。
- grant_credits() 调用时 source_id 设为 order.id，description 含 order_no，确保 ledger 可追溯。
- 金额全程用整数分，不做浮点运算。

跨模块导入说明：
credits-billing 目录使用中划线命名，无法用 Python 点号导入。
通过 importlib 按文件路径加载 credits-billing/service.py 获取 grant_credits 函数。
为避免 SQLAlchemy 重复注册表，credits-billing 的模型类预期已在 sys.modules
中以 "credits_billing_models" 为键缓存（由调用方/conftest 预先加载）。
"""
from __future__ import annotations

import importlib.util
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import ErrorCode, AppError

from models import Order
from schemas import OrderData, OrderListData


# ============================================================
# 跨模块导入：credits-billing 的 grant_credits 函数
# ============================================================

# 模块级缓存的 grant_credits 引用，首次调用 _load_grant_credits() 时设置
_grant_credits = None


def _get_grant_credits():
    """获取 grant_credits 函数引用（惰性加载）。

    通过 importlib 按文件路径加载 credits-billing/service.py。
    要求 sys.modules 中存在 "credits_billing_models" 键（由 conftest 预先加载），
    加载时会临时将 models 别名为 credits_billing_models 以避免重复注册 SQLAlchemy 表。
    """
    global _grant_credits
    if _grant_credits is not None:
        return _grant_credits

    _credits_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "credits-billing")
    )
    _service_path = os.path.join(_credits_dir, "service.py")

    # 临时将 credits-billing 目录加入 sys.path[0]
    _orig_path = list(sys.path)
    if _credits_dir in sys.path:
        sys.path.remove(_credits_dir)
    sys.path.insert(0, _credits_dir)

    # 保存当前 models 模块，临时替换为 credits_billing_models
    _saved_models = {}
    if "models" in sys.modules:
        _saved_models["models"] = sys.modules.pop("models")
    if "schemas" in sys.modules:
        _saved_models["schemas"] = sys.modules.pop("schemas")
    if "service" in sys.modules:
        _saved_models["service"] = sys.modules.pop("service")

    # 将 credits_billing_models 别名为 models，使 service.py 的 from models import ... 正确解析
    if "credits_billing_models" in sys.modules:
        sys.modules["models"] = sys.modules["credits_billing_models"]

    try:
        spec = importlib.util.spec_from_file_location(
            "credits_billing_service", _service_path
        )
        _mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_mod)
        _grant_credits = _mod.grant_credits
        return _grant_credits
    finally:
        # 恢复 sys.modules
        for _key in ("models", "schemas", "service"):
            sys.modules.pop(_key, None)
        for _key, _val in _saved_models.items():
            sys.modules[_key] = _val
        # 恢复 sys.path
        sys.path.clear()
        sys.path.extend(_orig_path)


# ============================================================
# 定价配置（从 DB 查询，替代硬编码）
# ============================================================


async def _get_product_pricing(
    db: AsyncSession, order_type: str, product_code: str
) -> tuple[int, Optional[int]]:
    """从 DB 查询产品定价（替代 PLAN_PRICES 和 CREDIT_PACKAGES 硬编码）。

    Args:
        db: 数据库异步会话
        order_type: plan / credits
        product_code: 产品编码

    Returns:
        (price_cents, credit_amount or None)

    Raises:
        AppError: 无效的产品编码
    """
    if order_type == "plan":
        result = await db.execute(
            text("SELECT price_cents FROM plans WHERE id = :pid AND status = 'active'"),
            {"pid": product_code},
        )
        row = result.fetchone()
        if row is None:
            raise AppError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"无效的套餐编码：{product_code}",
                status_code=400,
            )
        return row[0], None

    elif order_type == "credits":
        result = await db.execute(
            text(
                "SELECT credit_amount, price_cents FROM credit_packages "
                "WHERE product_code = :pc AND is_active = TRUE"
            ),
            {"pc": product_code},
        )
        row = result.fetchone()
        if row is None:
            raise AppError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"无效的额度包编码：{product_code}，可选的产品请通过 GET /products 查询",
                status_code=400,
            )
        return row[1], row[0]

    else:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"无效的订单类型：{order_type}，可选：plan / credits",
            status_code=400,
        )


# ============================================================
# 订单号生成
# ============================================================


def _generate_order_no() -> str:
    """生成唯一订单号，格式：ORD-YYYYMMDD-xxxxxxxx。"""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:8]
    return f"ORD-{date_part}-{random_part}"


# ============================================================
# 定价查询
# ============================================================


async def _get_price_and_credit_amount(
    db: AsyncSession, order_type: str, product_code: str
) -> tuple[int, Optional[int]]:
    """从 DB 查询定价（替代硬编码 PLAN_PRICES 和 CREDIT_PACKAGES）。

    Raises:
        AppError: 无效的 order_type 或 product_code
    """
    return await _get_product_pricing(db, order_type, product_code)


# ============================================================
# 订单创建
# ============================================================


async def create_order(
    db: AsyncSession,
    user_id: str,
    order_type: str,
    product_code: str,
    client_request_id: str,
) -> OrderData:
    """创建订单。服务端根据 order_type 和 product_code 查询定价表计算金额。"""
    amount_cents, credit_amount = await _get_price_and_credit_amount(db, order_type, product_code)
    order_no = _generate_order_no()

    now = datetime.now(timezone.utc)
    order = Order(
        user_id=user_id,
        order_no=order_no,
        order_type=order_type,
        product_code=product_code,
        amount_cents=amount_cents,
        credit_amount=credit_amount,
        currency="CNY",
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(order)
    await db.flush()

    return _to_order_data(order)


# ============================================================
# 订单查询
# ============================================================


async def list_orders(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    order_type: Optional[str] = None,
    status: Optional[str] = None,
) -> OrderListData:
    """查询当前用户的订单列表。只返回当前用户自己的订单。"""
    limit = min(limit, 100)

    conditions = [Order.user_id == user_id]
    if order_type:
        conditions.append(Order.order_type == order_type)
    if status:
        conditions.append(Order.status == status)

    count_result = await db.execute(
        select(func.count()).select_from(Order).where(and_(*conditions))
    )
    total = count_result.scalar()

    result = await db.execute(
        select(Order)
        .where(and_(*conditions))
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    orders = result.scalars().all()
    items = [_to_order_data(o) for o in orders]

    return OrderListData(items=items, total=total, limit=limit, offset=offset)


async def get_order_by_id(
    db: AsyncSession, order_id: str, user_id: str
) -> Optional[Order]:
    """按 ID 查询订单（带用户校验）。只返回属于当前用户的订单。"""
    result = await db.execute(
        select(Order).where(
            and_(Order.id == order_id, Order.user_id == user_id)
        )
    )
    return result.scalar_one_or_none()


# ============================================================
# 确认支付（mock/dev 预留，硬约束 #2、#3、#4、#8）
# ============================================================


async def confirm_order(
    db: AsyncSession,
    order_id: str,
    user_id: str,
) -> OrderData:
    """确认支付（mock/dev 预留）。

    硬约束：
    - #2 安全性：只允许确认当前用户自己的订单，不接真实支付
    - #3 原子性：状态更新 + grant_credits/plan_code 在同一事务
    - #4 幂等性：数据库条件 UPDATE WHERE status='pending'，rowcount=0 返回已有结果
    - #8 追溯性：source_id=order.id，description 含 order_no
    """
    # 1. 查询订单（带用户校验）
    order = await get_order_by_id(db, order_id, user_id)
    if order is None:
        raise AppError(code="ORDER_NOT_FOUND", message="订单不存在", status_code=404)

    # 2. 校验订单状态
    if order.status == "closed":
        raise AppError(
            code="ORDER_ALREADY_CLOSED", message="订单已关闭，无法确认支付", status_code=400
        )
    if order.status == "refunded":
        raise AppError(
            code="ORDER_ALREADY_REFUNDED", message="订单已退款，无法确认支付", status_code=400
        )

    # 3. 数据库层面条件更新（防并发双发）
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Order)
        .where(and_(Order.id == order_id, Order.status == "pending"))
        .values(status="paid", paid_at=now, updated_at=now)
    )

    if result.rowcount == 0:
        # 幂等：订单已不是 pending，返回已有结果
        await db.refresh(order)
        return _to_order_data(order)

    # 4. 在同一事务中执行对应业务操作
    if order.order_type == "credits" and order.credit_amount:
        grant_credits = _get_grant_credits()
        await grant_credits(
            db,
            user_id=user_id,
            amount=order.credit_amount,
            source_type="order",
            source_id=order.id,
            description=(
                f"充值订单 {order.order_no}：购买 {order.product_code}，"
                f"到账 {order.credit_amount} 额度"
            ),
        )

    elif order.order_type == "plan":
        await db.execute(
            text("UPDATE users SET plan_code = :plan_code, updated_at = :now WHERE id = :uid"),
            {"plan_code": order.product_code, "now": now, "uid": user_id},
        )

    # 5. 刷新订单状态
    await db.refresh(order)
    return _to_order_data(order)


async def cancel_order(
    db: AsyncSession,
    order_id: str,
) -> OrderData:
    """取消订单（管理员操作）。

    将 pending 状态的订单变更为 closed。已支付订单不可取消。

    Args:
        db: 数据库异步会话
        order_id: 订单 ID

    Returns:
        更新后的 OrderData

    Raises:
        AppError: 订单不存在、状态不允许取消
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise AppError(code="ORDER_NOT_FOUND", message="订单不存在", status_code=404)

    if order.status != "pending":
        raise AppError(
            code="ORDER_CANNOT_CANCEL",
            message=f"订单状态为 {order.status}，只有待支付订单可以取消",
            status_code=400,
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    order.status = "closed"
    order.updated_at = now
    await db.flush()
    await db.refresh(order)
    return _to_order_data(order)


async def refund_order(
    db: AsyncSession,
    order_id: str,
) -> OrderData:
    """退款订单（管理员操作）。

    将 paid 状态的订单变更为 refunded。
    对于 credits 类型订单，退还已充值的额度（调用 refund_credits）。
    对于 plan 类型订单，将用户套餐降级为 free。

    Args:
        db: 数据库异步会话
        order_id: 订单 ID

    Returns:
        更新后的 OrderData

    Raises:
        AppError: 订单不存在、状态不允许退款
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise AppError(code="ORDER_NOT_FOUND", message="订单不存在", status_code=404)

    if order.status == "refunded":
        raise AppError(
            code="ORDER_ALREADY_REFUNDED",
            message="订单已退款，不可重复操作",
            status_code=400,
        )

    if order.status != "paid":
        raise AppError(
            code="ORDER_CANNOT_REFUND",
            message=f"订单状态为 {order.status}，只有已支付订单可以退款",
            status_code=400,
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 根据订单类型执行退款逻辑
    if order.order_type == "credits" and order.credit_amount:
        # 退款 credits 订单：扣除已充值的额度
        _refund_credits = await _get_refund_credits()
        await _refund_credits(
            db,
            user_id=order.user_id,
            amount=order.credit_amount,
            source_id=order.id,
            description=f"订单 {order.order_no} 退款，扣除 {order.credit_amount} 额度",
        )

    elif order.order_type == "plan":
        # 退款 plan 订单：将用户套餐降级为 free
        await db.execute(
            text("UPDATE users SET plan_code = 'free', updated_at = :now WHERE id = :uid"),
            {"now": now, "uid": order.user_id},
        )

    # 更新订单状态
    order.status = "refunded"
    order.updated_at = now
    await db.flush()
    await db.refresh(order)
    return _to_order_data(order)


async def _get_refund_credits():
    """惰性加载 credits-billing 的 refund_credits 函数。"""
    import importlib.util, os
    _credits_billing_dir = os.path.join(
        os.path.dirname(__file__), "..", "credits-billing"
    )
    # 通过 sys.modules 查找已加载的 credits_billing
    import sys
    for _name in ("credits_billing_service", "service"):
        if _name in sys.modules:
            _mod = sys.modules[_name]
            if hasattr(_mod, "refund_credits"):
                return _mod.refund_credits
    # fallback: importlib 加载
    _svc_path = os.path.join(_credits_billing_dir, "service.py")
    _spec = importlib.util.spec_from_file_location("_credits_billing_refund_svc", _svc_path)
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        return _mod.refund_credits
    raise RuntimeError("Cannot load refund_credits from credits-billing")


# ============================================================
# 内部辅助
# ============================================================


def _to_order_data(order: Order) -> OrderData:
    """将 Order ORM 对象转为 OrderData DTO。"""
    return OrderData(
        id=order.id,
        order_no=order.order_no,
        order_type=order.order_type,
        product_code=order.product_code,
        amount_cents=order.amount_cents,
        credit_amount=order.credit_amount,
        currency=order.currency,
        status=order.status,
        paid_at=order.paid_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
