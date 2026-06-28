"""
cloud-credits-billing 业务逻辑层。

提供套餐权限、额度账户、扣费、额度流水和本地付费功能权限检查的核心逻辑。
所有数据库操作通过 cloud-shared 公共层的异步会话完成。

关键规则：
- credit_ledger 只能由本模块写入（DATABASE_SCHEMA.md 写入边界）。
- 客户端不得提交 user_id、plan_id、permission_granted 等字段。
- 本地付费功能不消耗 AI 额度，不计入 credit_ledger。
- 免费套餐每日配额通过 usage_events 表统计。
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import ErrorCode, AppError
from cloud.shared.database import Base

from models import Plan, CreditAccount, CreditLedger, UsageEvent
from schemas import (
    CreditBalanceData,
    CreditLedgerItem,
    CreditLedgerListData,
    EntitlementCheckData,
)


# ============================================================
# 默认套餐数据（开发/测试用种子数据）
# ============================================================

# 免费套餐功能配置：本地免费功能全开，本地付费功能有每日限制，AI 功能关闭
_FREE_FEATURES = {
    "ocr_local": True,
    "remove_bg_local": True,
    "id_photo_local": True,
    "preflight_check_local": True,
    "format_convert_local": True,
    "resize_image_local_paid": {"daily_limit": 3},
    "pdf_image_convert_local_paid": {"daily_limit": 2},
    "ai_copy_cloud": False,
    "ai_render_cloud": False,
    "upscale_image_cloud": False,
    "vectorize_image_cloud": False,
    "ai_edit_image_cloud": False,
    "remove_bg_cloud": False,
    "ocr_cloud": False,
}

# 标准套餐功能配置：本地功能全开且无限制，AI 功能全开
_STANDARD_FEATURES = {
    "resize_image_local_paid": True,
    "pdf_image_convert_local_paid": True,
    "ai_copy_cloud": True,
    "ai_render_cloud": True,
    "upscale_image_cloud": True,
    "vectorize_image_cloud": True,
    "ai_edit_image_cloud": True,
    "remove_bg_cloud": True,
    "ocr_cloud": True,
}

# 专业套餐功能配置：同标准套餐，月赠额度更高
_PRO_FEATURES = {
    "resize_image_local_paid": True,
    "pdf_image_convert_local_paid": True,
    "ai_copy_cloud": True,
    "ai_render_cloud": True,
    "upscale_image_cloud": True,
    "vectorize_image_cloud": True,
    "ai_edit_image_cloud": True,
    "remove_bg_cloud": True,
    "ocr_cloud": True,
}

# 默认套餐定义
_DEFAULT_PLANS = [
    {"name": "免费套餐", "monthly_grant": 10, "plan_tier": "free", "price_cents": 0, "features": _FREE_FEATURES},
    {"name": "标准套餐", "monthly_grant": 500, "plan_tier": "standard", "price_cents": 2900, "features": _STANDARD_FEATURES},
    {"name": "专业套餐", "monthly_grant": 2000, "plan_tier": "pro", "price_cents": 9900, "features": _PRO_FEATURES},
]


# ============================================================
# 种子数据
# ============================================================


async def seed_plans(db: AsyncSession) -> List[Plan]:
    """初始化套餐种子数据。

    仅在 plans 表为空时插入默认套餐配置。
    该函数应在应用启动或测试初始化时调用。

    Args:
        db: 数据库异步会话

    Returns:
        已存在或新创建的 Plan 列表
    """
    # 检查是否已有数据
    result = await db.execute(select(func.count()).select_from(Plan))
    count = result.scalar()
    if count > 0:
        # 已有数据，返回全部套餐
        result = await db.execute(select(Plan))
        return list(result.scalars().all())

    # 插入默认套餐
    plans = []
    for p in _DEFAULT_PLANS:
        plan = Plan(
            name=p["name"],
            monthly_grant=p["monthly_grant"],
            plan_tier=p.get("plan_tier", ""),
            price_cents=p.get("price_cents", 0),
            enabled_features_json=p["features"],
            status="active",
        )
        db.add(plan)
        plans.append(plan)

    await db.flush()
    return plans


# ============================================================
# 额度账户管理
# ============================================================


async def get_or_create_credit_account(
    db: AsyncSession,
    user_id: str,
    plan_id: str = "",
) -> CreditAccount:
    """获取或创建用户的额度账户。

    如果用户已有额度账户则返回已有记录，否则创建新的额度账户。
    新账户自动获得当前周期的赠送额度。
    如果未提供 plan_id，则从 users 表中查询用户实际的套餐 ID。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        plan_id: 套餐 ID（UUID，可选，为空时从 users 表查询）

    Returns:
        CreditAccount ORM 对象

    Raises:
        AppError: 账户被冻结
    """
    result = await db.execute(
        select(CreditAccount).where(CreditAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()

    if account is not None:
        if account.status == "frozen":
            raise AppError(
                code=ErrorCode.PLAN_REQUIRED,
                message="账户已被冻结，请联系客服",
                status_code=403,
            )
        return account

    # 如果未指定 plan_id，从 users 表查询用户实际套餐 ID
    if not plan_id:
        from sqlalchemy import text
        user_result = await db.execute(
            text("SELECT plan_id FROM users WHERE id = :uid"),
            {"uid": user_id},
        )
        row = user_result.fetchone()
        if row is not None:
            plan_id = row[0] or ""
        else:
            plan_id = ""

    # 查询套餐信息以获取 monthly_grant
    monthly_grant = 0
    if plan_id:
        plan_result = await db.execute(
            select(Plan).where(Plan.id == plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        monthly_grant = plan.monthly_grant if plan else 0

    now = datetime.now(timezone.utc)
    # 计费周期：从创建日起算，满一个月（周年计费）
    import calendar as _cal
    period_start = now
    if now.month == 12:
        next_year, next_month = now.year + 1, 1
    else:
        next_year, next_month = now.year, now.month + 1
    last_day = _cal.monthrange(next_year, next_month)[1]
    period_end = now.replace(
        year=next_year, month=next_month,
        day=min(now.day, last_day),
        hour=0, minute=0, second=0, microsecond=0,
    )

    account = CreditAccount(
        user_id=user_id,
        plan_id=plan_id or None,
        balance=monthly_grant,  # 新账户获得初始赠送额度
        monthly_grant=monthly_grant,
        period_start=period_start,
        period_end=period_end,
        status="active",
    )
    db.add(account)
    await db.flush()

    # 记录初始赠送流水
    if monthly_grant > 0:
        await _create_ledger_entry(
            db,
            user_id=user_id,
            account_id=account.id,
            change_type="grant",
            amount=monthly_grant,
            balance_after=monthly_grant,
            source_type="system",
            description="新账户初始赠送额度",
        )

    return account


# ============================================================
# 额度余额查询
# ============================================================


async def get_credit_balance(
    db: AsyncSession,
    user_id: str,
) -> CreditBalanceData:
    """查询用户 AI 额度余额。

    先确保用户有额度账户（不存在则自动创建），再检查是否跨周期需要刷新赠送额度。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID

    Returns:
        CreditBalanceData（包含余额、套餐、周期等信息）
    """
    # 获取或创建额度账户
    account = await get_or_create_credit_account(db, user_id)

    # 检查是否需要跨周期刷新赠送额度
    account = await _maybe_refresh_monthly_grant(db, account)

    return CreditBalanceData(
        user_id=account.user_id,
        plan_id=account.plan_id,
        monthly_grant=account.monthly_grant,
        balance=account.balance,
        period_start=account.period_start,
        period_end=account.period_end,
        status=account.status,
        updated_at=account.updated_at,
    )


# ============================================================
# 额度流水查询
# ============================================================


async def list_credit_ledger(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    change_type: Optional[str] = None,
) -> CreditLedgerListData:
    """查询用户 AI 额度流水。

    支持按 change_type 筛选和分页，按 created_at 倒序排列。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        limit: 每页条数（默认 50，最大 100）
        offset: 偏移量
        change_type: 可选筛选条件（grant / consume / recharge / refund / adjust）

    Returns:
        CreditLedgerListData（包含 items、total、limit、offset）
    """
    # 限制最大条数
    limit = min(limit, 100)

    # 构建查询条件
    conditions = [CreditLedger.user_id == user_id]
    if change_type:
        conditions.append(CreditLedger.change_type == change_type)

    # 查询总数
    count_result = await db.execute(
        select(func.count()).select_from(CreditLedger).where(and_(*conditions))
    )
    total = count_result.scalar()

    # 查询分页数据
    result = await db.execute(
        select(CreditLedger)
        .where(and_(*conditions))
        .order_by(CreditLedger.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    entries = result.scalars().all()

    items = [
        CreditLedgerItem(
            id=e.id,
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

    return CreditLedgerListData(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ============================================================
# 本地付费功能权限检查
# ============================================================


async def check_entitlement(
    db: AsyncSession,
    user_id: str,
    plan_id: str,
    feature: str,
    operation: str,
    client_request_id: str,
) -> EntitlementCheckData:
    """检查本地付费功能套餐权限。

    权限规则（对齐 shared-contract/pricing-rules.md）：
    - free 套餐：可能有每日/每月免费使用次数限制。
    - standard / pro 套餐：通常无限制，allowed=true。
    - 账户冻结：allowed=false。

    免费套餐的每日配额通过 usage_events 表统计当天 entitlement_granted 事件数。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID（来自 JWT）
        plan_id: 当前套餐 ID（UUID，来自 JWT）
        feature: 功能码（如 resize_image_local_paid）
        operation: 操作类型（single / batch）
        client_request_id: 客户端请求 ID

    Returns:
        EntitlementCheckData（allowed、feature、plan_id、remaining_free_quota、reason）
    """
    # 0. 检查功能码是否全局启用
    fc_result = await db.execute(
        text("SELECT is_active FROM feature_codes WHERE code = :fcode"),
        {"fcode": feature},
    )
    fc_row = fc_result.fetchone()
    if fc_row is None or not fc_row[0]:
        return EntitlementCheckData(
            allowed=False,
            feature=feature,
            plan_id=plan_id,
            reason=f"该功能（{feature}）暂未开放",
        )

    # 1. 查询套餐信息
    plan_result = await db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.status == "active")
    )
    plan = plan_result.scalar_one_or_none()

    if plan is None:
        return EntitlementCheckData(
            allowed=False,
            feature=feature,
            plan_id=plan_id,
            reason="套餐不存在或已停用",
        )

    # 2. 检查账户状态
    account_result = await db.execute(
        select(CreditAccount).where(CreditAccount.user_id == user_id)
    )
    account = account_result.scalar_one_or_none()

    if account and account.status == "frozen":
        return EntitlementCheckData(
            allowed=False,
            feature=feature,
            plan_id=plan_id,
            reason="账户已被冻结，请联系客服",
        )

    # 3. 检查套餐是否支持该功能
    features = plan.enabled_features_json or {}
    feature_config = features.get(feature)

    if feature_config is None or feature_config is False:
        # 功能未在套餐中启用
        return EntitlementCheckData(
            allowed=False,
            feature=feature,
            plan_id=plan_id,
            reason=f"当前套餐不支持此功能：{feature}",
        )

    # 4. 免费套餐（plan_tier == 'free' 判定，替代 monthly_grant <= 10 硬编码）
    is_free_plan = (plan.plan_tier == "free")
    if is_free_plan and isinstance(feature_config, dict):
        daily_limit = feature_config.get("daily_limit", 0)
        if daily_limit > 0:
            # 统计今天已使用的次数
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            usage_result = await db.execute(
                select(func.count()).select_from(UsageEvent).where(
                    and_(
                        UsageEvent.user_id == user_id,
                        UsageEvent.feature == feature,
                        UsageEvent.event_type == "entitlement_granted",
                        UsageEvent.created_at >= today_start,
                    )
                )
            )
            today_used = usage_result.scalar()

            remaining = daily_limit - today_used
            if remaining <= 0:
                return EntitlementCheckData(
                    allowed=False,
                    feature=feature,
                    plan_id=plan_id,
                    remaining_free_quota=0,
                    reason="免费套餐当日使用次数已用完，请升级套餐",
                )

            # 记录本次授权事件（用于配额统计）
            _record_usage_event(
                db,
                user_id=user_id,
                feature=feature,
                event_type="entitlement_granted",
                request_id=client_request_id,
                metadata={"operation": operation, "remaining_after": remaining - 1},
            )
            await db.flush()

            return EntitlementCheckData(
                allowed=True,
                feature=feature,
                plan_id=plan_id,
                remaining_free_quota=remaining - 1,
            )

    # 5. 非免费套餐或免费套餐无限制功能：直接允许
    return EntitlementCheckData(
        allowed=True,
        feature=feature,
        plan_id=plan_id,
    )


# ============================================================
# 扣费操作（供 provider-runtime 等模块调用）
# ============================================================


async def consume_credits(
    db: AsyncSession,
    user_id: str,
    amount: int,
    source_type: str = "provider_call",
    source_id: Optional[str] = None,
    description: Optional[str] = None,
) -> CreditAccount:
    """扣减用户 AI 额度（原子操作，防并发超扣）。

    使用原子 UPDATE WHERE balance >= amount 确保不会超扣到负数。
    如果账户不存在则直接报错，不自动创建（防止无套餐用户免费获取额度）。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        amount: 扣费金额（正整数）
        source_type: 来源类型，默认 provider_call
        source_id: 来源 ID（如 provider_call_log.id）
        description: 中文说明

    Returns:
        更新后的 CreditAccount

    Raises:
        AppError: 额度不足或账户不存在
    """
    if amount <= 0:
        raise AppError(
            code=ErrorCode.BILLING_FAILED,
            message="扣费金额必须大于 0",
            status_code=400,
        )

    now = datetime.now(timezone.utc)

    # 原子扣费：UPDATE WHERE balance >= amount，通过 rowcount 判断结果
    result = await db.execute(
        text(
            "UPDATE credit_accounts SET balance = balance - :amt, updated_at = :now "
            "WHERE user_id = :uid AND status = 'active' AND balance >= :amt "
            "RETURNING id, balance"
        ),
        {"amt": amount, "now": now, "uid": user_id},
    )
    updated = result.fetchone()

    if updated is None:
        # 扣费失败：可能账户不存在、已冻结或余额不足
        check = await db.execute(
            select(CreditAccount).where(CreditAccount.user_id == user_id)
        )
        account = check.scalar_one_or_none()
        if account is None:
            raise AppError(
                code=ErrorCode.CREDITS_NOT_ENOUGH,
                message="未找到额度账户，请先分配套餐",
                status_code=402,
            )
        if account.status == "frozen":
            raise AppError(
                code=ErrorCode.PLAN_REQUIRED,
                message="账户已被冻结，请联系客服",
                status_code=403,
            )
        raise AppError(
            code=ErrorCode.CREDITS_NOT_ENOUGH,
            message=f"AI 额度不足（当前 {account.balance}，需要 {amount}），请充值后再试",
            status_code=402,
        )

    account_id, new_balance = updated[0], updated[1]

    # 写入流水（金额为负数）
    await _create_ledger_entry(
        db,
        user_id=user_id,
        account_id=account_id,
        change_type="consume",
        amount=-amount,
        balance_after=new_balance,
        source_type=source_type,
        source_id=source_id,
        description=description or f"AI 功能消耗 {amount} 额度",
    )

    await db.flush()
    # 重新查询返回最新账户
    result2 = await db.execute(
        select(CreditAccount).where(CreditAccount.id == account_id)
    )
    return result2.scalar_one()


async def grant_credits(
    db: AsyncSession,
    user_id: str,
    amount: int,
    source_type: str = "system",
    source_id: Optional[str] = None,
    description: Optional[str] = None,
) -> CreditAccount:
    """赠送/充值 AI 额度（原子操作）。

    若账户不存在则自动创建。正数 amount 直接累加到余额。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        amount: 赠送金额（正整数）
        source_type: 来源类型（system / order / admin）
        source_id: 来源 ID
        description: 中文说明

    Returns:
        更新后的 CreditAccount
    """
    if amount <= 0:
        raise AppError(
            code=ErrorCode.BILLING_FAILED,
            message="赠送金额必须大于 0",
            status_code=400,
        )

    account = await get_or_create_credit_account(db, user_id)

    # 原子累加余额
    now = datetime.now(timezone.utc)
    result = await db.execute(
        text(
            "UPDATE credit_accounts SET balance = balance + :amt, updated_at = :now "
            "WHERE id = :aid RETURNING balance"
        ),
        {"amt": amount, "now": now, "aid": account.id},
    )
    updated = result.fetchone()
    new_balance = updated[0] if updated else account.balance + amount

    # 根据来源类型决定 change_type
    change_type = "recharge" if source_type == "order" else "grant"

    await _create_ledger_entry(
        db,
        user_id=user_id,
        account_id=account.id,
        change_type=change_type,
        amount=amount,
        balance_after=new_balance,
        source_type=source_type,
        source_id=source_id,
        description=description or f"获得 {amount} 额度",
    )

    await db.flush()
    result2 = await db.execute(
        select(CreditAccount).where(CreditAccount.id == account.id)
    )
    return result2.scalar_one()


async def refund_credits(
    db: AsyncSession,
    user_id: str,
    amount: int,
    source_id: Optional[str] = None,
    description: Optional[str] = None,
) -> CreditAccount:
    """退款：扣除已充值的 AI 额度（原子操作）。

    写入 credit_ledger 流水，change_type 为 refund。
    不自动创建账户——退款仅针对已有账户。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        amount: 退款金额（正整数，从用户余额扣除）
        source_id: 来源订单 ID
        description: 中文说明

    Returns:
        更新后的 CreditAccount

    Raises:
        AppError: 额度不足或账户不存在
    """
    if amount <= 0:
        raise AppError(
            code=ErrorCode.BILLING_FAILED,
            message="退款金额必须大于 0",
            status_code=400,
        )

    now = datetime.now(timezone.utc)

    # 原子扣费
    result = await db.execute(
        text(
            "UPDATE credit_accounts SET balance = balance - :amt, updated_at = :now "
            "WHERE user_id = :uid AND status = 'active' AND balance >= :amt "
            "RETURNING id, balance"
        ),
        {"amt": amount, "now": now, "uid": user_id},
    )
    updated = result.fetchone()

    if updated is None:
        check = await db.execute(
            select(CreditAccount).where(CreditAccount.user_id == user_id)
        )
        account = check.scalar_one_or_none()
        if account is None:
            raise AppError(
                code=ErrorCode.BILLING_FAILED,
                message="用户没有额度账户，无法退款",
                status_code=400,
            )
        raise AppError(
            code=ErrorCode.BILLING_FAILED,
            message=f"用户余额不足，当前余额 {account.balance}，退款需要 {amount}",
            status_code=400,
        )

    account_id, new_balance = updated[0], updated[1]

    await _create_ledger_entry(
        db,
        user_id=user_id,
        account_id=account_id,
        change_type="refund",
        amount=-amount,
        balance_after=new_balance,
        source_type="admin",
        source_id=source_id,
        description=description or f"订单退款扣除 {amount} 额度",
    )

    await db.flush()
    result2 = await db.execute(
        select(CreditAccount).where(CreditAccount.id == account_id)
    )
    return result2.scalar_one()


# ============================================================
# 内部辅助函数
# ============================================================


async def _create_ledger_entry(
    db: AsyncSession,
    user_id: str,
    account_id: str,
    change_type: str,
    amount: int,
    balance_after: int,
    source_type: str,
    source_id: Optional[str] = None,
    description: Optional[str] = None,
) -> CreditLedger:
    """创建额度流水记录（内部函数）。

    所有额度变化必须通过此函数写入 credit_ledger。
    外部模块不得直接写入 credit_ledger。
    """
    entry = CreditLedger(
        user_id=user_id,
        account_id=account_id,
        change_type=change_type,
        amount=amount,
        balance_after=balance_after,
        source_type=source_type,
        source_id=source_id,
        description=description,
    )
    db.add(entry)
    return entry


def _record_usage_event(
    db: AsyncSession,
    user_id: str,
    feature: str,
    event_type: str,
    request_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> UsageEvent:
    """记录使用事件（内部函数）。

    用于免费套餐配额统计等场景。
    """
    event = UsageEvent(
        user_id=user_id,
        feature=feature,
        event_type=event_type,
        request_id=request_id,
        metadata_json=metadata or {},
    )
    db.add(event)
    return event


async def _maybe_refresh_monthly_grant(
    db: AsyncSession,
    account: CreditAccount,
) -> CreditAccount:
    """检查是否需要跨周期刷新。

    如果当前时间已超过 period_end，则推进计费周期，但不自动赠送额度。
    套餐到期后不续费——用户额度保持原样，余额不足即无法调用 AI。

    Args:
        db: 数据库异步会话
        account: 用户额度账户

    Returns:
        CreditAccount（可能已更新周期）
    """
    now = datetime.now(timezone.utc)
    period_end = account.period_end

    if period_end is None:
        # 没有周期信息，设置初始周期（周年计费）
        import calendar as _cal
        period_start = now
        if now.month == 12:
            next_year, next_month = now.year + 1, 1
        else:
            next_year, next_month = now.year, now.month + 1
        last_day = _cal.monthrange(next_year, next_month)[1]
        period_end_new = now.replace(
            year=next_year, month=next_month,
            day=min(now.day, last_day),
            hour=0, minute=0, second=0, microsecond=0,
        )
        account.period_start = period_start
        account.period_end = period_end_new
        await db.flush()
        return account

    # 兼容 SQLite 无时区存储
    if period_end.tzinfo is not None:
        period_end = period_end.replace(tzinfo=None)
    now_naive = now.replace(tzinfo=None)

    if now_naive < period_end:
        # 还在当前周期内
        return account

    # 跨周期：清零额度，推进周期（订阅制：当月额度当月用，到期清零）
    import calendar as _cal
    old_balance = account.balance
    new_period_start = period_end
    if period_end.month == 12:
        next_year, next_month = period_end.year + 1, 1
    else:
        next_year, next_month = period_end.year, period_end.month + 1
    last_day = _cal.monthrange(next_year, next_month)[1]
    new_period_end = period_end.replace(
        year=next_year, month=next_month,
        day=min(period_end.day, last_day),
    )

    account.period_start = new_period_start
    account.period_end = new_period_end
    account.balance = 0
    account.updated_at = now

    # 记录清零流水
    if old_balance > 0:
        await _create_ledger_entry(
            db,
            user_id=account.user_id,
            account_id=account.id,
            change_type="adjust",
            amount=-old_balance,
            balance_after=0,
            source_type="system",
            description=f"套餐周期到期，{old_balance} 额度清零",
        )

    await db.flush()
    return account


# ============================================================
# DB 驱动定价函数（替代所有代码硬编码）
# ============================================================


async def get_exchange_rate(db: AsyncSession) -> float:
    """获取 CNY → 点数的汇率。

    Args:
        db: 数据库异步会话

    Returns:
        汇率（默认 10，即 1 元 = 10 点）
    """
    result = await db.execute(
        text("SELECT value FROM system_config WHERE key = 'credits_exchange_rate'"),
    )
    row = result.fetchone()
    if row is None:
        return 10.0  # 兜底默认值
    return float(row[0])


async def get_model_pricing(
    db: AsyncSession, provider: str, model: str
) -> dict:
    """从 DB 查询某模型的定价。

    Args:
        db: 数据库异步会话
        provider: Provider 名称
        model: 模型名称

    Returns:
        dict，含 input_price、output_price（元/百万token）
    """
    result = await db.execute(
        text(
            "SELECT input_price, output_price FROM provider_model_pricing "
            "WHERE provider_name = :prov AND model_name = :model AND is_active = TRUE"
        ),
        {"prov": provider, "model": model},
    )
    row = result.fetchone()
    if row is not None:
        return {
            "input_price": float(row[0]),
            "output_price": float(row[1]),
        }
    # 兜底：查默认定价
    result = await db.execute(
        text(
            "SELECT input_price, output_price FROM provider_model_pricing "
            "WHERE provider_name = '__default__' AND is_active = TRUE"
        ),
    )
    row = result.fetchone()
    if row is not None:
        return {
            "input_price": float(row[0]),
            "output_price": float(row[1]),
        }
    # 最终兜底
    return {"input_price": 1.0, "output_price": 2.0}


async def get_feature_min_credits(db: AsyncSession, feature: str) -> int:
    """查询某功能的最小扣点数（起步扣点）。

    Args:
        db: 数据库异步会话
        feature: 功能码

    Returns:
        起步扣点（默认 1）
    """
    result = await db.execute(
        text("SELECT min_credits FROM feature_pricing WHERE feature_code = :fc"),
        {"fc": feature},
    )
    row = result.fetchone()
    return row[0] if row else 1


async def get_feature_default_max_tokens(db: AsyncSession, feature: str) -> int:
    """查询某功能的默认 max_tokens。

    Args:
        db: 数据库异步会话
        feature: 功能码

    Returns:
        max_tokens（默认 2048）
    """
    result = await db.execute(
        text("SELECT default_max_tokens FROM feature_pricing WHERE feature_code = :fc"),
        {"fc": feature},
    )
    row = result.fetchone()
    return row[0] if row else 2048


async def calculate_deduction(
    db: AsyncSession,
    feature: str,
    provider: str,
    model: str,
    usage,  # ProviderUsage
) -> int:
    """计算实际扣点数（核心公式）。

    从 DB 独立计算 CNY 成本 + 汇率换算，完全不依赖 cost.py 硬编码。

    公式：max(起步扣点, ceil(实际CNY成本 × 汇率))

    Args:
        db: 数据库异步会话
        feature: 功能码
        provider: Provider 名称
        model: 模型名称
        usage: ProviderUsage 结构（含 input_tokens、output_tokens、image_count）

    Returns:
        实际应扣点数（整数）
    """
    # 1. 查起步扣点
    min_credits = await get_feature_min_credits(db, feature)

    # 2. 查模型定价
    pricing = await get_model_pricing(db, provider, model)

    # 3. 计算实际 CNY 成本（token消耗 × 模型单价）
    input_cost = (usage.input_tokens / 1_000_000) * pricing["input_price"]
    output_cost = (usage.output_tokens / 1_000_000) * pricing["output_price"]
    actual_cost_cny = input_cost + output_cost

    # 4. 汇率换算
    rate = await get_exchange_rate(db)
    cost_credits = math.ceil(actual_cost_cny * rate)

    # 5. 取最大值
    return max(min_credits, cost_credits)


async def estimate_credits(
    db: AsyncSession,
    feature: str,
    capability: str,
    max_tokens: int,
    prompt_text: str,
    router=None,  # ProviderRouter 实例，用于路由选模型
) -> dict:
    """预估扣费 + 耗时（/estimate 端点用）。

    不调用 Provider，纯查 DB + 计算。路由确定 provider/model 后查定价表。

    Args:
        db: 数据库异步会话
        feature: 功能码
        capability: text / image_generation / image_edit
        max_tokens: 请求的 max_tokens
        prompt_text: 用户提示词（用于估算输入 token 数）
        router: ProviderRouter 实例（用于 resolve_route）

    Returns:
        dict:
        - min_credits: 起步扣点
        - estimated_max_credits: 预估最大扣点
        - provider: 路由到的 Provider 名称（可能为空）
        - model: 路由到的模型名称（可能为空）
        - balance: 当前余额（为 None 时表示未登录/无账户）
        - enough: 余额是否足够
        - estimated_latency: {p50_ms, p95_ms, display, sample_count}
    """
    result = {
        "min_credits": 0,
        "estimated_max_credits": 0,
        "provider": "",
        "model": "",
        "balance": 0,
        "enough": False,
        "estimated_latency": {
            "p50_ms": 0,
            "p95_ms": 0,
            "display": "暂无耗时数据",
            "sample_count": 0,
        },
    }

    # 1. 路由确定 provider + model
    if router is not None:
        try:
            from cloud.modules.provider_runtime.registry import resolve_route
            target = resolve_route(capability=capability, router=router)
            result["provider"] = target.provider
            result["model"] = target.model
        except Exception:
            pass  # 路由失败不阻塞预估

    provider = result["provider"]
    model_name = result["model"]

    # 2. 查起步扣点
    min_credits = await get_feature_min_credits(db, feature)
    result["min_credits"] = min_credits

    # 3. 查模型定价
    pricing = {"input_price": 1.0, "output_price": 2.0}  # 兜底
    if provider and model_name:
        pricing = await get_model_pricing(db, provider, model_name)

    # 4. 估算输入 token（中文字符数 × 1.2，英文约 0.75，取保守估算 1.2）
    estimated_input_tokens = max(1, int(len(prompt_text) * 1.2))

    # 5. 预估最大成本
    input_cost = (estimated_input_tokens / 1_000_000) * pricing["input_price"]
    output_cost = (max_tokens / 1_000_000) * pricing["output_price"]
    max_cost_cny = input_cost + output_cost

    # 6. 汇率换算
    rate = await get_exchange_rate(db)
    max_credits = math.ceil(max_cost_cny * rate)

    # 7. 预检查阈值
    threshold = max(min_credits, max_credits)
    result["estimated_max_credits"] = threshold

    # 8. 查耗时统计
    if provider and model_name:
        latency_result = await db.execute(
            text(
                "SELECT p50_latency_ms, p95_latency_ms, sample_count "
                "FROM provider_latency_stats "
                "WHERE provider_name = :pn AND model_name = :mn AND capability = :cap"
            ),
            {"pn": provider, "mn": model_name, "cap": capability},
        )
        row = latency_result.fetchone()
        if row is not None:
            p50, p95, count = row[0], row[1], row[2]
            result["estimated_latency"] = {
                "p50_ms": p50,
                "p95_ms": p95,
                "display": f"约 {p50 // 1000}-{p95 // 1000} 秒",
                "sample_count": count,
            }

    return result


async def estimate_with_balance(
    db: AsyncSession,
    user_id: str,
    feature: str,
    capability: str,
    max_tokens: int,
    prompt_text: str,
    router=None,
) -> dict:
    """预估扣费 + 耗时，并检查用户余额（完整版 /estimate）。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        feature: 功能码
        capability: 能力类型
        max_tokens: max_tokens
        prompt_text: 提示词
        router: ProviderRouter 实例

    Returns:
        同 estimate_credits，但 balance 和 enough 会填充真实值
    """
    result = await estimate_credits(
        db, feature, capability, max_tokens, prompt_text, router
    )

    # 查用户余额
    balance_result = await db.execute(
        text("SELECT balance FROM credit_accounts WHERE user_id = :uid AND status = 'active'"),
        {"uid": user_id},
    )
    row = balance_result.fetchone()
    balance = row[0] if row else 0
    result["balance"] = balance
    result["enough"] = balance >= result["estimated_max_credits"]

    return result


async def get_credit_package(
    db: AsyncSession, product_code: str
) -> Optional[dict]:
    """查询充值套餐。

    Args:
        db: 数据库异步会话
        product_code: 产品编码

    Returns:
        dict(credit_amount, price_cents, name) 或 None
    """
    result = await db.execute(
        text(
            "SELECT credit_amount, price_cents, name FROM credit_packages "
            "WHERE product_code = :pc AND is_active = TRUE"
        ),
        {"pc": product_code},
    )
    row = result.fetchone()
    if row is None:
        return None
    return {
        "credit_amount": row[0],
        "price_cents": row[1],
        "name": row[2],
    }


async def list_credit_packages(
    db: AsyncSession,
) -> list[dict]:
    """列出所有启用的充值套餐。

    Returns:
        套餐列表，按 sort_order 排序
    """
    result = await db.execute(
        text(
            "SELECT product_code, name, credit_amount, price_cents, sort_order "
            "FROM credit_packages WHERE is_active = TRUE ORDER BY sort_order ASC"
        ),
    )
    rows = result.all()
    return [
        {
            "product_code": row[0],
            "name": row[1],
            "credit_amount": row[2],
            "price_cents": row[3],
            "sort_order": row[4],
        }
        for row in rows
    ]


async def get_plan_price(db: AsyncSession, plan_id: str) -> Optional[int]:
    """查询套餐月费（分）。

    Args:
        db: 数据库异步会话
        plan_id: 套餐 ID

    Returns:
        价格（分），或 None
    """
    result = await db.execute(
        text("SELECT price_cents FROM plans WHERE id = :pid AND status = 'active'"),
        {"pid": plan_id},
    )
    row = result.fetchone()
    return row[0] if row else None
