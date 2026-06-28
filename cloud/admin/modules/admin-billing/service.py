"""
admin-billing 业务逻辑层。

提供后台套餐管理、订单管理和额度管理的核心逻辑：
- 套餐：列表、详情、创建、更新、状态切换
- 订单：跨用户列表查询、详情查询
- 额度：跨用户账户列表、账户详情、流水查询、手动调整

模型复用策略：
本模块不定义 ORM 模型，直接通过 importlib 加载已有模块的模型：
- Plan / CreditAccount / CreditLedger ← cloud/modules/credits-billing/models.py
- Order ← cloud/modules/orders_recharge/models.py
- User ← cloud/admin/modules/admin-users/models.py

调用方（conftest）需要预先将模型类注册到 sys.modules 的别名键下，
service.py 通过 _get_model() 惰性加载。

手动调整额度时：
- 正数 amount：调用 credits-billing 的 grant_credits()
- 负数 amount：调用 credits-billing 的 consume_credits()（取绝对值）
- source_type 统一为 "admin"，description 记录调整原因
"""
from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import ErrorCode, AppError
from cloud.shared.database import Base

from schemas import (
    PlanItem,
    PlanDetail,
    PlanListData,
    PlanOption,
    PlanOptionsData,
    AdminOrderItem,
    AdminOrderDetail,
    AdminOrderListData,
    AdminCreditAccountItem,
    AdminCreditAccountDetail,
    AdminCreditAccountListData,
    AdminCreditLedgerItem,
    AdminCreditLedgerListData,
)

# ============================================================
# 分页常量
# ============================================================

MAX_LIMIT = 100

# ============================================================
# 跨模块模型加载
# ============================================================

# 缓存的模型类和函数引用
_Plan = None
_CreditAccount = None
_CreditLedger = None
_Order = None
_User = None
_grant_credits = None
_consume_credits = None


def _get_project_root() -> str:
    """获取项目根目录的绝对路径。"""
    # 从当前文件向上：admin-billing → modules → admin → cloud → TT Tools
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )


def _find_model_class_in_modules(table_name: str, class_name: str):
    """在 sys.modules 中搜索已注册的 ORM 模型类。"""
    for mod in sys.modules.values():
        cls = getattr(mod, class_name, None)
        if cls is not None and getattr(cls, "__tablename__", "") == table_name:
            return cls
    return None


def _safe_load_model(table_name: str, class_name: str, alias: str,
                      module_dir_name: str):
    """安全加载跨模块 ORM 模型类，避免重复注册表。"""
    # 1) 从预期别名获取
    if alias in sys.modules:
        return getattr(sys.modules[alias], class_name)
    # 2) 表已在 Base.metadata 中注册 → 全局搜索
    if table_name in Base.metadata.tables:
        cls = _find_model_class_in_modules(table_name, class_name)
        if cls is not None:
            return cls
    # 3) 回退：importlib 文件加载
    mod = _import_model_file(module_dir_name, "models", alias)
    return getattr(mod, class_name)


def _load_module_models():
    """惰性加载所有跨模块模型类和函数引用。

    预期调用方（conftest）已将模型类注册到 sys.modules 的别名键下：
    - "credits_billing_models" → credits-billing 的 models 模块
    - "orders_recharge_models" → orders-recharge 的 models 模块
    - "admin_users_models" → admin-users 的 models 模块

    如果表已在 Base.metadata 中注册（被 app-shell 启动时加载），则从已注册元数据中获取类。
    """
    global _Plan, _CreditAccount, _CreditLedger, _Order, _User
    global _grant_credits, _consume_credits

    if _Plan is not None:
        return  # 已加载

    # 加载 credits-billing 模型（Plan / CreditAccount / CreditLedger）
    if "credits_billing_models" in sys.modules:
        cb_models = sys.modules["credits_billing_models"]
        _Plan = cb_models.Plan
        _CreditAccount = cb_models.CreditAccount
        _CreditLedger = cb_models.CreditLedger
    elif "plans" in Base.metadata.tables or "credit_accounts" in Base.metadata.tables:
        # 表已注册但别名不在 sys.modules → 全局搜索
        _Plan = _find_model_class_in_modules("plans", "Plan")
        _CreditAccount = _find_model_class_in_modules("credit_accounts", "CreditAccount")
        _CreditLedger = _find_model_class_in_modules("credit_ledger", "CreditLedger")
    else:
        _plan_tmp = _import_model_file("credits-billing", "models", "credits_billing_models")
        _Plan = _plan_tmp.Plan
        _CreditAccount = _plan_tmp.CreditAccount
        _CreditLedger = _plan_tmp.CreditLedger

    # 加载 credits-billing 服务函数
    _grant_credits, _consume_credits = _load_billing_functions()

    # 加载订单模型
    _Order = _safe_load_model("orders", "Order", "orders_recharge_models",
                               "orders_recharge")

    # 加载用户模型
    if "admin_users_models" in sys.modules:
        _User = sys.modules["admin_users_models"].UserAdmin


def _import_model_file(module_dir_name: str, module_file: str, alias: str):
    """通过 importlib 按文件路径加载模块。

    Args:
        module_dir_name: 模块目录名（如 credits-billing、orders_recharge）
        module_file: 文件名（如 models、service）
        alias: 在 sys.modules 中注册的别名

    Returns:
        加载的模块对象
    """
    root = _get_project_root()
    dir_path = os.path.join(root, "cloud", "modules", module_dir_name)
    file_path = os.path.join(dir_path, f"{module_file}.py")

    # 临时将目录加入 sys.path
    _orig_path = list(sys.path)
    if dir_path in sys.path:
        sys.path.remove(dir_path)
    sys.path.insert(0, dir_path)

    # 保存可能冲突的模块
    _saved = {}
    for _key in ("models", "service", "schemas", "router"):
        if _key in sys.modules:
            _saved[_key] = sys.modules.pop(_key)

    try:
        spec = importlib.util.spec_from_file_location(alias, file_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[alias] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        # 恢复 sys.modules
        for _key in ("models", "service", "schemas", "router"):
            sys.modules.pop(_key, None)
        for _key, _val in _saved.items():
            sys.modules[_key] = _val
        # 恢复 sys.path
        sys.path.clear()
        sys.path.extend(_orig_path)


def _load_billing_functions():
    """加载 credits-billing 的 grant_credits 和 consume_credits 函数。

    通过 importlib 加载 service.py，使用与 _import_model_file 相同的模式。
    """
    root = _get_project_root()
    dir_path = os.path.join(root, "cloud", "modules", "credits-billing")
    file_path = os.path.join(dir_path, "service.py")

    _orig_path = list(sys.path)
    if dir_path in sys.path:
        sys.path.remove(dir_path)
    sys.path.insert(0, dir_path)

    _saved = {}
    for _key in ("models", "service", "schemas", "router"):
        if _key in sys.modules:
            _saved[_key] = sys.modules.pop(_key)

    # 将 credits_billing_models 别名为 models，使 service.py 的 import 正确解析
    if "credits_billing_models" in sys.modules:
        sys.modules["models"] = sys.modules["credits_billing_models"]

    try:
        spec = importlib.util.spec_from_file_location(
            "credits_billing_service", file_path
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.grant_credits, mod.consume_credits
    finally:
        for _key in ("models", "service", "schemas", "router"):
            sys.modules.pop(_key, None)
        for _key, _val in _saved.items():
            sys.modules[_key] = _val
        sys.path.clear()
        sys.path.extend(_orig_path)


# ============================================================
# 套餐管理
# ============================================================


async def list_plans(db: AsyncSession) -> PlanListData:
    """查询所有套餐列表。

    Args:
        db: 数据库异步会话

    Returns:
        PlanListData 套餐列表
    """
    _load_module_models()

    result = await db.execute(
        select(_Plan).order_by(_Plan.created_at.desc())
    )
    plans = result.scalars().all()

    items = [
        PlanItem(
            id=p.id,
            name=p.name,
            monthly_grant=p.monthly_grant,
            expire_days=getattr(p, 'expire_days', 0) or 0,
            is_default=bool(getattr(p, 'is_default', False)),
            plan_tier=getattr(p, 'plan_tier', None) or None,
            enabled_features_json=getattr(p, 'enabled_features_json', None) or None,
            status=p.status,
            created_at=p.created_at,
        )
        for p in plans
    ]

    return PlanListData(items=items)


async def get_plan_detail(db: AsyncSession, plan_id: str) -> PlanDetail:
    """查询套餐详情。

    Args:
        db: 数据库异步会话
        plan_id: 套餐 ID（UUID）

    Returns:
        PlanDetail 套餐详细信息

    Raises:
        AppError: 套餐不存在时抛出 404
    """
    _load_module_models()

    result = await db.execute(select(_Plan).where(_Plan.id == plan_id))
    plan = result.scalar_one_or_none()

    if plan is None:
        raise AppError(
            code="PLAN_NOT_FOUND",
            message=f"套餐 {plan_id} 不存在",
            status_code=404,
        )

    return PlanDetail(
        id=plan.id,
        name=plan.name,
        monthly_grant=plan.monthly_grant,
        expire_days=getattr(plan, 'expire_days', 0) or 0,
        plan_tier=getattr(plan, 'plan_tier', None) or None,
        enabled_features_json=plan.enabled_features_json or {},
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


async def _validate_features(db: AsyncSession, features: dict) -> None:
    """校验功能开关中的功能码均为全局启用的功能码。

    Args:
        db: 数据库异步会话
        features: 功能开关 dict（如 {"ai_copy_cloud": true}）

    Raises:
        AppError: 存在未启用或未知的功能码
    """
    if not features:
        return
    fc_keys = list(features.keys())
    # 使用 IN 子句兼容 SQLite 和 PostgreSQL
    placeholders = ", ".join(f":fc{i}" for i in range(len(fc_keys)))
    params = {f"fc{i}": fc_keys[i] for i in range(len(fc_keys))}
    result = await db.execute(
        text(f"SELECT code, is_active FROM feature_codes WHERE code IN ({placeholders})"),
        params,
    )
    active_map = {row[0]: row[1] for row in result.all()}
    for code in fc_keys:
        if code not in active_map:
            raise AppError(
                code="FEATURE_NOT_FOUND",
                message=f"功能码 {code} 不存在于功能码表中",
                status_code=422,
            )
        if not active_map[code]:
            raise AppError(
                code="FEATURE_NOT_ACTIVE",
                message=f"功能码 {code} 已被全局关闭，不能加入套餐",
                status_code=422,
            )


async def create_plan(
    db: AsyncSession,
    name: str,
    monthly_grant: int = 0,
    expire_days: int = 0,
    is_default: bool = False,
    plan_tier: str = "standard",
    enabled_features_json: Optional[dict] = None,
) -> PlanDetail:
    """创建新套餐。

    使用套餐名称作为唯一标识。创建前检查同名 active 套餐是否已存在。
    功能开关中所有功能码必须在 feature_codes 表中且 is_active=true。

    Args:
        db: 数据库异步会话
        name: 套餐名称
        monthly_grant: 每周期赠送额度
        expire_days: 到期天数，0=永不过期
        enabled_features_json: 功能开关配置

    Returns:
        PlanDetail 创建的套餐信息

    Raises:
        AppError: 套餐名称已存在时抛出 409
        AppError: 功能码未启用或不存在时抛出 422
    """
    _load_module_models()

    # 校验功能码合法性
    if enabled_features_json:
        await _validate_features(db, enabled_features_json)

    # 检查同名 active 套餐是否已存在
    existing = await db.execute(
        select(_Plan).where(_Plan.name == name, _Plan.status == "active")
    )
    if existing.scalar_one_or_none() is not None:
        raise AppError(
            code="PLAN_NAME_EXISTS",
            message=f"套餐名称 {name} 已存在",
            status_code=409,
        )

    # 默认套餐互斥：新设为默认时清掉其他
    if is_default:
        await db.execute(
            text("UPDATE plans SET is_default = false WHERE is_default = true")
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    plan = _Plan(
        name=name,
        monthly_grant=monthly_grant,
        expire_days=expire_days,
        is_default=is_default,
        plan_tier=plan_tier,
        enabled_features_json=enabled_features_json or {},
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    await db.flush()

    return PlanDetail(
        id=plan.id,
        name=plan.name,
        monthly_grant=plan.monthly_grant,
        expire_days=getattr(plan, 'expire_days', 0) or 0,
        plan_tier=getattr(plan, 'plan_tier', None) or None,
        enabled_features_json=plan.enabled_features_json or {},
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


async def update_plan(
    db: AsyncSession,
    plan_id: str,
    name: Optional[str] = None,
    monthly_grant: Optional[int] = None,
    expire_days: Optional[int] = None,
    is_default: Optional[bool] = None,
    plan_tier: Optional[str] = None,
    enabled_features_json: Optional[dict] = None,
) -> PlanDetail:
    """更新套餐配置。

    只更新传入的非 None 字段。套餐编码不可修改。

    Args:
        db: 数据库异步会话
        plan_id: 套餐 ID
        name: 新名称（可选）
        monthly_grant: 新月赠额度（可选）
        enabled_features_json: 新功能配置（可选）

    Returns:
        PlanDetail 更新后的套餐信息

    Raises:
        AppError: 套餐不存在时抛出 404
    """
    _load_module_models()

    result = await db.execute(select(_Plan).where(_Plan.id == plan_id))
    plan = result.scalar_one_or_none()

    if plan is None:
        raise AppError(
            code="PLAN_NOT_FOUND",
            message=f"套餐 {plan_id} 不存在",
            status_code=404,
        )

    # 只更新传入的非 None 字段
    if name is not None:
        plan.name = name
    if monthly_grant is not None:
        plan.monthly_grant = monthly_grant
    if expire_days is not None:
        plan.expire_days = expire_days
    if is_default is not None:
        if is_default:
            await db.execute(text("UPDATE plans SET is_default = false WHERE is_default = true"))
        plan.is_default = is_default
    if plan_tier is not None:
        plan.plan_tier = plan_tier
    if enabled_features_json is not None:
        await _validate_features(db, enabled_features_json)
        plan.enabled_features_json = enabled_features_json

    plan.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()

    return PlanDetail(
        id=plan.id,
        name=plan.name,
        monthly_grant=plan.monthly_grant,
        expire_days=getattr(plan, 'expire_days', 0) or 0,
        plan_tier=getattr(plan, 'plan_tier', None) or None,
        enabled_features_json=plan.enabled_features_json or {},
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


async def update_plan_status(
    db: AsyncSession, plan_id: str, new_status: str
) -> PlanDetail:
    """启用/停用套餐。

    Args:
        db: 数据库异步会话
        plan_id: 套餐 ID
        new_status: 目标状态（active / disabled）

    Returns:
        PlanDetail 更新后的套餐信息

    Raises:
        AppError: 套餐不存在或状态值无效
    """
    _load_module_models()

    if new_status not in ("active", "disabled"):
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"无效的套餐状态：{new_status}，允许值：active / disabled",
            status_code=400,
        )

    result = await db.execute(select(_Plan).where(_Plan.id == plan_id))
    plan = result.scalar_one_or_none()

    if plan is None:
        raise AppError(
            code="PLAN_NOT_FOUND",
            message=f"套餐 {plan_id} 不存在",
            status_code=404,
        )

    plan.status = new_status
    plan.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()

    return PlanDetail(
        id=plan.id,
        name=plan.name,
        monthly_grant=plan.monthly_grant,
        expire_days=getattr(plan, 'expire_days', 0) or 0,
        plan_tier=getattr(plan, 'plan_tier', None) or None,
        enabled_features_json=plan.enabled_features_json or {},
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


async def list_plan_options(db: AsyncSession) -> PlanOptionsData:
    """查询套餐选项列表（供下拉框使用）。

    仅返回 active 状态的套餐，字段精简为 id/name。

    Args:
        db: 数据库异步会话

    Returns:
        PlanOptionsData 套餐选项列表
    """
    _load_module_models()

    result = await db.execute(
        select(_Plan.id, _Plan.name)
        .where(_Plan.status == "active")
        .order_by(_Plan.monthly_grant.asc())
    )
    rows = result.all()

    items = [
        PlanOption(id=row[0], name=row[1])
        for row in rows
    ]
    return PlanOptionsData(items=items)


# ============================================================
# 订单管理
# ============================================================


async def list_all_orders(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    user_id: Optional[str] = None,
    order_type: Optional[str] = None,
    status: Optional[str] = None,
    order: str = "desc",
) -> AdminOrderListData:
    """查询全部订单列表（管理员视角，跨用户）。

    支持按 user_id、order_type、status 多条件筛选和分页。
    关联 users 表获取用户账号信息。

    Args:
        db: 数据库异步会话
        limit: 每页条数
        offset: 偏移量
        user_id: 按用户 ID 筛选
        order_type: 按订单类型筛选
        status: 按订单状态筛选

    Returns:
        AdminOrderListData 订单列表及分页信息
    """
    _load_module_models()

    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)

    # 构建筛选条件
    conditions = []
    if user_id:
        conditions.append(_Order.user_id == user_id)
    if order_type:
        conditions.append(_Order.order_type == order_type)
    if status:
        conditions.append(_Order.status == status)

    # 查询总数
    count_query = select(func.count()).select_from(_Order)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 查询分页数据（按创建时间倒序）
    query = (
        select(_Order)
        .where(and_(*conditions) if conditions else True)
        .order_by(_Order.created_at.desc() if order == "desc" else _Order.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    orders = result.scalars().all()

    # 批量查询关联用户账号（避免 N+1 查询）
    user_ids = list({o.user_id for o in orders})
    user_map = await _get_user_account_map(db, user_ids)

    items = [
        AdminOrderItem(
            id=o.id,
            order_no=o.order_no,
            order_type=o.order_type,
            product_code=o.product_code,
            amount_cents=o.amount_cents,
            credit_amount=o.credit_amount,
            currency=o.currency,
            status=o.status,
            paid_at=o.paid_at,
            user_id=o.user_id,
            user_account=user_map.get(o.user_id),
            created_at=o.created_at,
            updated_at=o.updated_at,
        )
        for o in orders
    ]

    return AdminOrderListData(items=items, total=total, limit=limit, offset=offset)


async def get_admin_order_detail(db: AsyncSession, order_id: str) -> AdminOrderDetail:
    """查询订单详情（管理员视角，任意用户订单）。

    Args:
        db: 数据库异步会话
        order_id: 订单 ID（UUID）

    Returns:
        AdminOrderDetail 订单详情（含用户信息）

    Raises:
        AppError: 订单不存在时抛出 404
    """
    _load_module_models()

    result = await db.execute(select(_Order).where(_Order.id == order_id))
    order = result.scalar_one_or_none()

    if order is None:
        raise AppError(
            code="ORDER_NOT_FOUND",
            message=f"订单 {order_id} 不存在",
            status_code=404,
        )

    # 查询关联用户信息
    user_account = None
    user_display_name = None
    if _User is not None:
        user_result = await db.execute(
            select(_User.account, _User.display_name).where(_User.id == order.user_id)
        )
        user_row = user_result.one_or_none()
        if user_row:
            user_account = user_row[0]
            user_display_name = user_row[1]

    return AdminOrderDetail(
        id=order.id,
        order_no=order.order_no,
        order_type=order.order_type,
        product_code=order.product_code,
        amount_cents=order.amount_cents,
        credit_amount=order.credit_amount,
        currency=order.currency,
        status=order.status,
        paid_at=order.paid_at,
        user_id=order.user_id,
        user_account=user_account,
        user_display_name=user_display_name,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


# ============================================================
# 额度管理
# ============================================================


async def delete_plan(db: AsyncSession, plan_id: str) -> dict:
    """软删除套餐。

    将套餐状态设为 disabled，保留套餐记录及已有用户的关联。

    Args:
        db: 数据库异步会话
        plan_id: 套餐 ID

    Returns:
        {"deleted": True}

    Raises:
        AppError: 套餐不存在或已禁用时抛出 404
    """
    _load_module_models()

    result = await db.execute(select(_Plan).where(_Plan.id == plan_id))
    plan = result.scalar_one_or_none()

    if plan is None:
        raise AppError(
            code="PLAN_NOT_FOUND",
            message=f"套餐 {plan_id} 不存在",
            status_code=404,
        )

    if plan.status == "disabled":
        raise AppError(
            code="PLAN_ALREADY_DISABLED",
            message=f"套餐 {plan.name} 已被禁用",
            status_code=404,
        )

    plan.status = "disabled"
    await db.flush()

    return {"deleted": True}


async def list_credit_accounts(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    plan_id: Optional[str] = None,
    user_id: Optional[str] = None,
    order: str = "desc",
) -> AdminCreditAccountListData:
    """查询所有额度账户列表（管理员视角，跨用户）。

    支持按状态、套餐ID和用户ID筛选。关联 users 表获取用户账号。

    Args:
        db: 数据库异步会话
        limit: 每页条数
        offset: 偏移量
        status: 按账户状态筛选
        plan_id: 按套餐 ID 筛选
        user_id: 按用户 ID 筛选

    Returns:
        AdminCreditAccountListData 额度账户列表
    """
    _load_module_models()

    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)

    conditions = []
    if status:
        conditions.append(_CreditAccount.status == status)
    if plan_id:
        conditions.append(_CreditAccount.plan_id == plan_id)
    if user_id:
        conditions.append(_CreditAccount.user_id == user_id)

    # 查询总数
    count_query = select(func.count()).select_from(_CreditAccount)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 查询分页数据
    query = (
        select(_CreditAccount)
        .where(and_(*conditions) if conditions else True)
        .order_by(_CreditAccount.created_at.desc() if order == "desc" else _CreditAccount.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    accounts = result.scalars().all()

    # 批量查询关联用户账号
    user_ids = list({a.user_id for a in accounts})
    user_map = await _get_user_account_map(db, user_ids)

    # 批量查询套餐中文名（通过 plan_id 关联 plans 表）
    plan_ids = list({a.plan_id for a in accounts if a.plan_id})
    plan_name_map: dict[str, str] = {}
    if plan_ids and _Plan is not None:
        result = await db.execute(
            select(_Plan.id, _Plan.name).where(_Plan.id.in_(plan_ids))
        )
        rows = result.all()
        plan_name_map = {row[0]: row[1] for row in rows}

    items = [
        AdminCreditAccountItem(
            id=a.id,
            user_id=a.user_id,
            user_account=user_map.get(a.user_id),
            plan_id=a.plan_id,
            plan_name=plan_name_map.get(a.plan_id),
            balance=a.balance,
            monthly_grant=a.monthly_grant,
            status=a.status,
            period_start=a.period_start,
            period_end=a.period_end,
            updated_at=a.updated_at,
        )
        for a in accounts
    ]

    return AdminCreditAccountListData(items=items, total=total, limit=limit, offset=offset)


async def get_credit_account_detail(
    db: AsyncSession, account_id: str
) -> AdminCreditAccountDetail:
    """查询额度账户详情（管理员视角）。

    Args:
        db: 数据库异步会话
        account_id: 额度账户 ID（UUID）

    Returns:
        AdminCreditAccountDetail 账户详情（含用户信息）

    Raises:
        AppError: 账户不存在时抛出 404
    """
    _load_module_models()

    result = await db.execute(
        select(_CreditAccount).where(_CreditAccount.id == account_id)
    )
    account = result.scalar_one_or_none()

    if account is None:
        raise AppError(
            code="CREDIT_ACCOUNT_NOT_FOUND",
            message=f"额度账户 {account_id} 不存在",
            status_code=404,
        )

    # 查询关联用户信息
    user_account = None
    user_display_name = None
    if _User is not None:
        user_result = await db.execute(
            select(_User.account, _User.display_name).where(
                _User.id == account.user_id
            )
        )
        user_row = user_result.one_or_none()
        if user_row:
            user_account = user_row[0]
            user_display_name = user_row[1]

    # 查询套餐中文名
    plan_name = None
    if account.plan_id and _Plan is not None:
        result = await db.execute(
            select(_Plan.name).where(_Plan.id == account.plan_id)
        )
        row = result.one_or_none()
        if row:
            plan_name = row[0]

    return AdminCreditAccountDetail(
        id=account.id,
        user_id=account.user_id,
        user_account=user_account,
        user_display_name=user_display_name,
        plan_id=account.plan_id,
        plan_name=plan_name,
        balance=account.balance,
        monthly_grant=account.monthly_grant,
        status=account.status,
        period_start=account.period_start,
        period_end=account.period_end,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


async def list_all_credit_ledger(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    user_id: Optional[str] = None,
    change_type: Optional[str] = None,
    source_type: Optional[str] = None,
    order: str = "desc",
) -> AdminCreditLedgerListData:
    """查询全部额度流水（管理员视角，跨用户）。

    支持按 user_id、change_type、source_type 多条件筛选和分页。
    关联 users 表获取用户账号。

    Args:
        db: 数据库异步会话
        limit: 每页条数
        offset: 偏移量
        user_id: 按用户 ID 筛选
        change_type: 按变化类型筛选
        source_type: 按来源类型筛选

    Returns:
        AdminCreditLedgerListData 流水列表及分页信息
    """
    _load_module_models()

    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)

    conditions = []
    if user_id:
        conditions.append(_CreditLedger.user_id == user_id)
    if change_type:
        conditions.append(_CreditLedger.change_type == change_type)
    if source_type:
        conditions.append(_CreditLedger.source_type == source_type)

    # 查询总数
    count_query = select(func.count()).select_from(_CreditLedger)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 查询分页数据（按创建时间倒序）
    query = (
        select(_CreditLedger)
        .where(and_(*conditions) if conditions else True)
        .order_by(_CreditLedger.created_at.desc() if order == "desc" else _CreditLedger.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    entries = result.scalars().all()

    # 批量查询关联用户账号
    user_ids = list({e.user_id for e in entries})
    user_map = await _get_user_account_map(db, user_ids)

    items = [
        AdminCreditLedgerItem(
            id=e.id,
            user_id=e.user_id,
            user_account=user_map.get(e.user_id),
            account_id=e.account_id,
            change_type=e.change_type,
            amount=e.amount,
            balance_after=e.balance_after,
            source_type=e.source_type,
            source_id=e.source_id,
            description=e.description,
            created_at=e.created_at,
        )
        for e in entries
    ]

    return AdminCreditLedgerListData(items=items, total=total, limit=limit, offset=offset)


async def adjust_credits(
    db: AsyncSession,
    user_id: str,
    amount: int,
    description: Optional[str] = None,
) -> AdminCreditAccountDetail:
    """手动调整用户额度（管理员操作）。

    正数 amount 为赠送额度，负数 amount 为扣除额度。
    写入 credit_ledger 时 source_type 为 "admin"。

    Args:
        db: 数据库异步会话
        user_id: 目标用户 ID
        amount: 调整额度（正数为赠送，负数为扣除，不允许为 0）
        description: 调整原因说明

    Returns:
        AdminCreditAccountDetail 调整后的账户信息

    Raises:
        AppError: amount 为 0 时抛出 422，用户不存在时抛出 404
    """
    _load_module_models()

    if amount == 0:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="调整额度不能为 0",
            status_code=422,
        )

    # 确认用户存在
    user_result = await db.execute(
        select(_User).where(_User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise AppError(
            code="USER_NOT_FOUND",
            message=f"用户 {user_id} 不存在",
            status_code=404,
        )

    # 根据 amount 正负决定调用赠送还是扣费
    if amount > 0:
        # 赠送额度
        await _grant_credits(
            db,
            user_id=user_id,
            amount=amount,
            source_type="admin",
            description=description or f"管理员手动赠送 {amount} 额度",
        )
    else:
        # 扣除额度（consume_credits 要求正数金额）
        await _consume_credits(
            db,
            user_id=user_id,
            amount=abs(amount),
            source_type="admin",
            description=description or f"管理员手动扣除 {abs(amount)} 额度",
        )

    await db.flush()

    # 查询调整后的账户信息
    result = await db.execute(
        select(_CreditAccount).where(_CreditAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()

    return AdminCreditAccountDetail(
        id=account.id,
        user_id=account.user_id,
        user_account=user.account,
        user_display_name=user.display_name,
        plan_id=account.plan_id,
        plan_name=None,
        balance=account.balance,
        monthly_grant=account.monthly_grant,
        status=account.status,
        period_start=account.period_start,
        period_end=account.period_end,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


# ============================================================
# 内部辅助函数
# ============================================================


async def _get_user_account_map(
    db: AsyncSession, user_ids: list[str]
) -> dict[str, Optional[str]]:
    """批量查询用户 ID → 账号的映射，避免 N+1 查询。

    Args:
        db: 数据库异步会话
        user_ids: 用户 ID 列表

    Returns:
        dict: user_id → user_account 映射
    """
    if not user_ids or _User is None:
        return {}

    result = await db.execute(
        select(_User.id, _User.account).where(_User.id.in_(user_ids))
    )
    rows = result.all()
    return {row[0]: row[1] for row in rows}


async def _get_plan_name_map(
    db: AsyncSession, plan_ids: list[str]
) -> dict[str, Optional[str]]:
    """批量查询 plan_id → plan_name 映射。

    Args:
        db: 数据库异步会话
        plan_ids: plan_id 字符串列表

    Returns:
        dict: plan_id → plan_name 映射
    """
    if not plan_ids or _Plan is None:
        return {}

    result = await db.execute(
        select(_Plan.id, _Plan.name).where(_Plan.id.in_(plan_ids))
    )
    rows = result.all()
    return {row[0]: row[1] for row in rows}


# ============================================================
# 订单操作（取消 / 退款）
# ============================================================


async def cancel_admin_order(db: AsyncSession, order_id: str):
    """管理员取消订单。

    通过 importlib 加载 orders_recharge 的 cancel_order。
    """
    _cancel = await _get_order_function("cancel_order")
    return await _cancel(db, order_id)


async def refund_admin_order(db: AsyncSession, order_id: str):
    """管理员退款订单。

    通过 importlib 加载 orders_recharge 的 refund_order。
    """
    _refund = await _get_order_function("refund_order")
    return await _refund(db, order_id)


async def _get_order_function(func_name: str):
    """惰性加载 orders_recharge 的 service 函数。"""
    import importlib.util, os, sys

    # 尝试从 sys.modules 查找
    for _name in ("orders_recharge_service", "service"):
        if _name in sys.modules:
            _mod = sys.modules[_name]
            if hasattr(_mod, func_name):
                return getattr(_mod, func_name)

    # fallback: importlib 加载
    _order_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "modules", "orders_recharge"
    )
    _svc_path = os.path.join(_order_dir, "service.py")
    _spec = importlib.util.spec_from_file_location(
        f"_orders_{func_name}_svc", _svc_path
    )
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules[f"_orders_{func_name}_svc"] = _mod
        _spec.loader.exec_module(_mod)
        return getattr(_mod, func_name)
    raise RuntimeError(f"Cannot load {func_name} from orders_recharge")


# ============================================================
# 模型定价管理（provider_model_pricing 表 CRUD）
# ============================================================


async def list_model_pricing(
    db: AsyncSession,
    provider_id: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> list[dict]:
    """列出所有 Provider 模型定价（JOIN providers 获取名称）。"""
    from sqlalchemy import text as _t
    conditions = ["1=1"]
    params: dict = {}
    if provider_id:
        conditions.append("pmp.provider_id = :pid")
        params["pid"] = provider_id
    if is_active is not None:
        conditions.append("pmp.is_active = :ia")
        params["ia"] = is_active

    result = await db.execute(
        _t(
            f"SELECT pmp.id, p.name, pmp.model_name, pmp.input_price, pmp.output_price, "
            f"pmp.currency, pmp.is_active, pmp.created_at, pmp.updated_at, pmp.provider_id "
            f"FROM provider_model_pricing pmp "
            f"JOIN providers p ON pmp.provider_id = p.id "
            f"WHERE {' AND '.join(conditions)} "
            f"ORDER BY p.name, pmp.model_name"
        ),
        params,
    )
    rows = result.all()
    return [
        {
            "id": r[0], "provider_name": r[1], "model_name": r[2],
            "provider_id": r[9],
            "input_price": float(r[3]), "output_price": float(r[4]),
            "currency": r[5], "is_active": r[6],
            "created_at": r[7].isoformat() if r[7] else None,
            "updated_at": r[8].isoformat() if r[8] else None,
        }
        for r in rows
    ]


async def create_model_pricing(
    db: AsyncSession,
    provider_id: str,
    model_name: str,
    input_price: float,
    output_price: float,
    currency: str = "CNY",
    capability: str = "text",
) -> dict:
    """新增模型定价（关联 Provider UUID + capability）。"""
    import uuid as _uuid
    from sqlalchemy import text as _t
    now = datetime.now(timezone.utc)
    id_ = str(_uuid.uuid4())

    await db.execute(
        _t(
            "INSERT INTO provider_model_pricing "
            "(id, provider_id, model_name, capability, input_price, output_price, currency, created_at, updated_at) "
            "VALUES (:id, :pid, :mn, :cap, :ip, :op, :cur, :now, :now)"
        ),
        {"id": id_, "pid": provider_id, "mn": model_name, "cap": capability,
         "ip": input_price, "op": output_price, "cur": currency, "now": now},
    )
    await db.flush()
    # 查 provider name 返回
    result = await db.execute(_t("SELECT name FROM providers WHERE id = :pid"), {"pid": provider_id})
    row = result.fetchone()
    pname = row[0] if row else ""
    return {"id": id_, "provider_name": pname, "model_name": model_name}


async def update_model_pricing(
    db: AsyncSession, pricing_id: str, **kwargs,
) -> None:
    """更新模型定价（部分字段）。"""
    from sqlalchemy import text as _t
    updates = []
    params = {"id": pricing_id, "now": datetime.now(timezone.utc)}
    for field in ("input_price", "output_price", "currency", "is_active",
                  "provider_name", "model_name"):
        if field in kwargs:
            updates.append(f"{field} = :{field}")
            params[field] = kwargs[field]
    if not updates:
        return
    updates.append("updated_at = :now")
    await db.execute(
        _t(f"UPDATE provider_model_pricing SET {', '.join(updates)} WHERE id = :id"),
        params,
    )
    await db.flush()


# ============================================================
# 功能定价管理（feature_pricing 表 CRUD）
# ============================================================


async def list_feature_pricing(db: AsyncSession) -> list[dict]:
    """列出所有功能起步扣点。"""
    from sqlalchemy import text as _t
    result = await db.execute(
        _t(
            "SELECT fp.feature_code, fc.name, fp.min_credits, fp.default_max_tokens, fp.updated_at "
            "FROM feature_pricing fp LEFT JOIN feature_codes fc ON fp.feature_code = fc.code "
            "ORDER BY fp.feature_code"
        ),
    )
    rows = result.all()
    return [
        {
            "feature_code": r[0], "feature_name": r[1] or r[0],
            "min_credits": r[2], "default_max_tokens": r[3],
            "updated_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]


async def update_feature_pricing(
    db: AsyncSession, feature_code: str, min_credits: int,
    default_max_tokens: Optional[int] = None,
) -> None:
    """更新功能起步扣点。"""
    from sqlalchemy import text as _t
    now = datetime.now(timezone.utc)
    # UPSERT
    result = await db.execute(
        _t(
            "UPDATE feature_pricing SET min_credits = :mc, updated_at = :now "
            "WHERE feature_code = :fc"
        ),
        {"mc": min_credits, "now": now, "fc": feature_code},
    )
    if result.rowcount == 0:
        await db.execute(
            _t(
                "INSERT INTO feature_pricing (feature_code, min_credits, default_max_tokens, updated_at) "
                "VALUES (:fc, :mc, :dmt, :now)"
            ),
            {"fc": feature_code, "mc": min_credits,
             "dmt": default_max_tokens or 2048, "now": now},
        )
    elif default_max_tokens is not None:
        await db.execute(
            _t(
                "UPDATE feature_pricing SET default_max_tokens = :dmt "
                "WHERE feature_code = :fc"
            ),
            {"dmt": default_max_tokens, "fc": feature_code},
        )
    await db.flush()


# ============================================================
# 系统配置管理（system_config 表 CRUD）
# ============================================================


async def get_system_config(db: AsyncSession) -> dict:
    """获取所有系统配置。"""
    from sqlalchemy import text as _t
    result = await db.execute(
        _t("SELECT key, value, updated_at FROM system_config ORDER BY key"),
    )
    rows = result.all()
    return {
        r[0]: {"value": r[1], "updated_at": r[2].isoformat() if r[2] else None}
        for r in rows
    }


async def update_system_config(db: AsyncSession, key: str, value: str) -> None:
    """更新系统配置（UPSERT）。"""
    from sqlalchemy import text as _t
    now = datetime.now(timezone.utc)
    result = await db.execute(
        _t("UPDATE system_config SET value = :val, updated_at = :now WHERE key = :key"),
        {"val": value, "now": now, "key": key},
    )
    if result.rowcount == 0:
        await db.execute(
            _t("INSERT INTO system_config (key, value, updated_at) VALUES (:key, :val, :now)"),
            {"key": key, "val": value, "now": now},
        )
    await db.flush()


# ============================================================
# 充值套餐管理（credit_packages 表 CRUD）
# ============================================================


async def list_credit_packages_admin(db: AsyncSession) -> list[dict]:
    """列出所有充值套餐（含停用）。"""
    from sqlalchemy import text as _t
    result = await db.execute(
        _t(
            "SELECT id, product_code, name, credit_amount, price_cents, "
            "is_active, sort_order, created_at, updated_at "
            "FROM credit_packages ORDER BY sort_order"
        ),
    )
    rows = result.all()
    return [
        {
            "id": r[0], "product_code": r[1], "name": r[2],
            "credit_amount": r[3], "price_cents": r[4],
            "is_active": r[5], "sort_order": r[6],
            "created_at": r[7].isoformat() if r[7] else None,
            "updated_at": r[8].isoformat() if r[8] else None,
        }
        for r in rows
    ]


async def create_credit_package(
    db: AsyncSession,
    product_code: str, name: str,
    credit_amount: int, price_cents: int,
    sort_order: int = 0,
) -> dict:
    """新增充值套餐。"""
    import uuid as _uuid
    from sqlalchemy import text as _t
    now = datetime.now(timezone.utc)
    id_ = str(_uuid.uuid4())
    await db.execute(
        _t(
            "INSERT INTO credit_packages "
            "(id, product_code, name, credit_amount, price_cents, sort_order, created_at, updated_at) "
            "VALUES (:id, :pc, :nm, :ca, :pr, :so, :now, :now)"
        ),
        {"id": id_, "pc": product_code, "nm": name,
         "ca": credit_amount, "pr": price_cents, "so": sort_order, "now": now},
    )
    await db.flush()
    return {"id": id_, "product_code": product_code, "name": name}


async def update_credit_package(
    db: AsyncSession, package_id: str, **kwargs,
) -> None:
    """更新充值套餐。"""
    from sqlalchemy import text as _t
    updates = []
    params = {"id": package_id, "now": datetime.now(timezone.utc)}
    for field in ("product_code", "name", "credit_amount", "price_cents",
                  "is_active", "sort_order"):
        if field in kwargs:
            updates.append(f"{field} = :{field}")
            params[field] = kwargs[field]
    if not updates:
        return
    updates.append("updated_at = :now")
    await db.execute(
        _t(f"UPDATE credit_packages SET {', '.join(updates)} WHERE id = :id"),
        params,
    )
    await db.flush()
