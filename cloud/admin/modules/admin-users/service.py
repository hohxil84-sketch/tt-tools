"""
admin-users 业务逻辑层。

提供用户和设备管理的数据库查询和修改操作：
- 用户列表查询（分页、状态筛选、搜索）
- 用户详情查询
- 用户状态修改
- 用户设备列表查询
- 设备列表查询（分页、状态筛选）
- 设备详情查询
- 设备状态修改

所有操作通过 SQLAlchemy 异步会话执行，对齐 cloud/DATABASE_SCHEMA.md。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import AppError, ErrorCode
from cloud.shared.database import Base
from models import UserAdmin as User, DeviceAdmin as Device
from schemas import (
    UserItem,
    UserDetail,
    UserListData,
    DeviceItem,
    DeviceDetail,
    DeviceListData,
    CreateUserRequest,
    UpdateUserRequest,
)

# bcrypt 密码哈希
import bcrypt

# 允许的用户状态值
VALID_USER_STATUSES = {"active", "blocked", "deleted"}

# ============================================================
# 跨模块模型加载（Plan 模型，用于 plan_id → plan_name 查询）
# ============================================================

_Plan = None  # 惰性加载缓存


def _find_plan_in_modules():
    """在 sys.modules 中搜索已注册的 Plan ORM 模型类（避免重复注册表）。"""
    import sys as _sys
    for mod in _sys.modules.values():
        cls = getattr(mod, "Plan", None)
        if cls is not None and getattr(cls, "__tablename__", "") == "plans":
            return cls
    return None


async def _load_plan_model():
    """惰性加载 Plan 模型（从 credits-billing 模块）。

    优先顺序：
    1. sys.modules 别名查找
    2. Base.metadata 已注册 → 全局搜索
    3. importlib 文件加载
    """
    global _Plan
    if _Plan is not None:
        return _Plan

    import sys as _sys
    from cloud.shared.database import Base

    # 1) 从预期别名获取
    if "credits_billing_models" in _sys.modules:
        _Plan = _sys.modules["credits_billing_models"].Plan
        return _Plan

    # 2) 表已在 Base.metadata 中注册（app-shell 启动时已加载）
    if "plans" in Base.metadata.tables:
        _Plan = _find_plan_in_modules()
        if _Plan is not None:
            return _Plan

    # 3) 回退：importlib 文件加载
    import importlib.util as _iu
    import os as _os

    _root = _os.path.abspath(
        _os.path.join(_os.path.dirname(__file__), "..", "..", "..", "..")
    )
    _dir_path = _os.path.join(_root, "cloud", "modules", "credits-billing")
    _file_path = _os.path.join(_dir_path, "models.py")

    _orig_path = list(_sys.path)
    if _dir_path in _sys.path:
        _sys.path.remove(_dir_path)
    _sys.path.insert(0, _dir_path)

    _saved = {}
    for _k in ("models", "service", "schemas", "router"):
        if _k in _sys.modules:
            _saved[_k] = _sys.modules.pop(_k)

    try:
        _spec = _iu.spec_from_file_location("credits_billing_models", _file_path)
        _mod = _iu.module_from_spec(_spec)
        _sys.modules["credits_billing_models"] = _mod
        _spec.loader.exec_module(_mod)
        _Plan = _mod.Plan
    finally:
        for _k in ("models", "service", "schemas", "router"):
            _sys.modules.pop(_k, None)
        for _k, _v in _saved.items():
            _sys.modules[_k] = _v
        _sys.path.clear()
        _sys.path.extend(_orig_path)

    return _Plan


async def _get_plan_info_map(
    db: AsyncSession, plan_ids: list[str] = None
) -> dict[str, tuple[str, str]]:
    """批量查询套餐信息映射，按 plan_id 查询。

    返回 dict: plan_id → (plan_id, plan_name) 映射。

    Args:
        db: 数据库异步会话
        plan_ids: plan_id (UUID) 字符串列表

    Returns:
        dict: plan_id → (plan_id, plan_name) 映射
    """
    try:
        Plan = await _load_plan_model()
    except Exception:
        return {}

    if plan_ids:
        valid_ids = [pid for pid in plan_ids if pid]
        if valid_ids:
            result = await db.execute(
                select(Plan.id, Plan.name).where(Plan.id.in_(valid_ids))
            )
            rows = result.all()
            return {row[0]: (row[0], row[1]) for row in rows}  # plan_id → (plan_id, plan_name)

    return {}


# ============================================================
# 批量聚合查询辅助函数（用于用户列表增强字段）
# ============================================================


async def _batch_credit_balances(
    db: AsyncSession, user_ids: list[str]
) -> dict[str, int]:
    """批量查询用户额度余额（credit_accounts 表，与 users 1:1）。"""
    if not user_ids:
        return {}
    try:
        ca = Base.metadata.tables["credit_accounts"]
        result = await db.execute(
            select(ca.c.user_id, ca.c.balance).where(ca.c.user_id.in_(user_ids))
        )
        return {row[0]: row[1] for row in result.all()}
    except Exception:
        return {}


async def _batch_device_counts(
    db: AsyncSession, user_ids: list[str]
) -> dict[str, int]:
    """批量查询用户绑定设备数（devices 表 COUNT）。"""
    if not user_ids:
        return {}
    try:
        dev = Base.metadata.tables["devices"]
        result = await db.execute(
            select(dev.c.user_id, func.count().label("cnt"))
            .where(dev.c.user_id.in_(user_ids))
            .group_by(dev.c.user_id)
        )
        return {row[0]: row[1] for row in result.all()}
    except Exception:
        return {}


async def _batch_last_logins(
    db: AsyncSession, user_ids: list[str]
) -> dict[str, datetime]:
    """批量查询用户最后登录时间（auth_sessions 表 MAX(created_at)）。"""
    if not user_ids:
        return {}
    try:
        sess = Base.metadata.tables["auth_sessions"]
        result = await db.execute(
            select(sess.c.user_id, func.max(sess.c.created_at).label("last_login"))
            .where(sess.c.user_id.in_(user_ids))
            .group_by(sess.c.user_id)
        )
        return {row[0]: row[1] for row in result.all()}
    except Exception:
        return {}


async def _batch_role_names(
    db: AsyncSession, user_ids: list[str]
) -> dict[str, str]:
    """批量查询用户 RBAC 角色名称（user_roles JOIN roles，逗号拼接）。

    使用 PostgreSQL 兼容的 string_agg 聚合函数（替代 MySQL/SQLite 的 group_concat）。
    """
    if not user_ids:
        return {}
    try:
        ur = Base.metadata.tables.get("user_roles")
        r = Base.metadata.tables.get("roles")
        if ur is None or r is None:
            import logging; logging.getLogger("admin-users").warning(
                "user_roles 或 roles 表未注册，无法查询 RBAC 角色名称"
            )
            return {}
        # string_agg 是 PostgreSQL 聚合函数，SQLite 3.44+ 也支持
        # 仅统计启用中的角色，已停用角色不显示
        result = await db.execute(
            select(ur.c.user_id, func.string_agg(r.c.name, ', ').label("role_names"))
            .join(r, (r.c.id == ur.c.role_id) & (r.c.is_active == True))
            .where(ur.c.user_id.in_(user_ids))
            .group_by(ur.c.user_id)
        )
        return {row[0]: row[1] for row in result.all()}
    except Exception:
        import logging; logging.getLogger("admin-users").warning(
            "_batch_role_names 查询失败", exc_info=True
        )
        return {}


async def _batch_monthly_usages(
    db: AsyncSession, user_ids: list[str]
) -> dict[str, int]:
    """批量查询用户本月消费额度（credit_ledger 表，当月 consume 类型 SUM(ABS(amount))）。"""
    if not user_ids:
        return {}
    try:
        cl = Base.metadata.tables["credit_ledger"]
        # 当月第一天 00:00:00 UTC
        month_start = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        result = await db.execute(
            select(
                cl.c.user_id,
                func.coalesce(func.sum(func.abs(cl.c.amount)), 0).label("total"),
            )
            .where(cl.c.user_id.in_(user_ids))
            .where(cl.c.change_type == "consume")
            .where(cl.c.created_at >= month_start)
            .group_by(cl.c.user_id)
        )
        return {row[0]: row[1] for row in result.all()}
    except Exception:
        return {}


async def _batch_audit_counts(
    db: AsyncSession, user_ids: list[str]
) -> dict[str, int]:
    """批量查询系统用户操作审计次数（admin_audit_logs 表 COUNT）。"""
    if not user_ids:
        return {}
    try:
        aal = Base.metadata.tables["admin_audit_logs"]
        result = await db.execute(
            select(aal.c.admin_user_id, func.count().label("cnt"))
            .where(aal.c.admin_user_id.in_(user_ids))
            .group_by(aal.c.admin_user_id)
        )
        return {row[0]: row[1] for row in result.all()}
    except Exception:
        return {}


async def _batch_period_ends(
    db: AsyncSession, user_ids: list[str]
) -> dict[str, datetime]:
    """批量查询用户套餐周期结束时间（credit_accounts 表 period_end）。"""
    if not user_ids:
        return {}
    try:
        ca = Base.metadata.tables.get("credit_accounts")
        if ca is None:
            import logging; logging.getLogger("admin-users").warning("credit_accounts 表未注册，period_end 无法查询")
            return {}
        result = await db.execute(
            select(ca.c.user_id, ca.c.period_end).where(ca.c.user_id.in_(user_ids))
        )
        return {row[0]: row[1] for row in result.all()}
    except Exception:
        import logging; logging.getLogger("admin-users").warning("_batch_period_ends 查询失败", exc_info=True)
        return {}


async def _sync_credit_account(
    db: AsyncSession, user_id: str, plan_id: str
) -> None:
    """同步额度账户：用户分配套餐后，确保 credit_accounts 行存在且 plan_id / monthly_grant 一致。

    若账户不存在则创建并赠送初始额度（= 套餐 monthly_grant）；
    若已存在且 plan_id 有变化则更新 plan_id 和 monthly_grant。
    所有异常均静默吞掉，不影响用户 CRUD 主流程。
    """
    # 1) 表存在性检查
    try:
        ca = Base.metadata.tables["credit_accounts"]
        cl = Base.metadata.tables["credit_ledger"]
        pl = Base.metadata.tables["plans"]
    except KeyError:
        return  # 相关表未注册，跳过

    # 2) 所有数据库操作包裹在 broad except 中，任何失败都不影响用户 CRUD
    try:
        # 查询套餐 monthly_grant 和 expire_days
        plan_monthly_grant = 0
        plan_expire_days = 0
        if plan_id:
            plan_result = await db.execute(
                select(pl.c.monthly_grant, pl.c.expire_days).where(pl.c.id == plan_id)
            )
            plan_row = plan_result.fetchone()
            if plan_row:
                plan_monthly_grant = plan_row[0] or 0
                plan_expire_days = plan_row[1] or 0

        # 检查额度账户是否存在
        result = await db.execute(
            select(ca).where(ca.c.user_id == user_id)
        )
        existing = result.fetchone()

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if existing is None:
            # === 创建新额度账户 ===
            account_id = str(uuid.uuid4())
            period_start = now
            # 到期时间：按 expire_days 计算，0 = 永不过期（100年后）
            if plan_expire_days > 0:
                from datetime import timedelta
                period_end = now + timedelta(days=plan_expire_days)
            else:
                period_end = now.replace(year=now.year + 100)

            await db.execute(
                ca.insert().values(
                    id=account_id,
                    user_id=user_id,
                    plan_id=plan_id or None,
                    balance=plan_monthly_grant,
                    monthly_grant=plan_monthly_grant,
                    period_start=period_start,
                    period_end=period_end,
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
            # 记录初始赠送流水
            if plan_monthly_grant > 0:
                await db.execute(
                    cl.insert().values(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        account_id=account_id,
                        change_type="grant",
                        amount=plan_monthly_grant,
                        balance_after=plan_monthly_grant,
                        source_type="system",
                        description="管理员分配套餐，初始赠送额度",
                        created_at=now,
                    )
                )
            await db.flush()
        else:
            # === 已存在：同步 plan_id / monthly_grant，若套餐变更则重置余额和周期 ===
            old_plan_id = getattr(existing, "plan_id", None)
            if old_plan_id != plan_id:
                # 套餐变更：余额重置为新套餐 monthly_grant，周期根据 expire_days 重置
                new_period_start = now
                if plan_expire_days > 0:
                    from datetime import timedelta as _td
                    new_period_end = now + _td(days=plan_expire_days)
                else:
                    new_period_end = now.replace(year=now.year + 100)
                old_balance = getattr(existing, "balance", 0)
                await db.execute(
                    ca.update()
                    .where(ca.c.user_id == user_id)
                    .values(
                        plan_id=plan_id or None,
                        monthly_grant=plan_monthly_grant,
                        balance=plan_monthly_grant,
                        period_start=new_period_start,
                        period_end=new_period_end,
                        updated_at=now,
                    )
                )
                # 记录套餐变更流水
                await db.execute(
                    cl.insert().values(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        account_id=getattr(existing, "id", ""),
                        change_type="adjust",
                        amount=plan_monthly_grant - old_balance,
                        balance_after=plan_monthly_grant,
                        source_type="system",
                        description=f"更换套餐，余额重置为 {plan_monthly_grant}（原余额 {old_balance}）",
                        created_at=now,
                    )
                )
                await db.flush()
    except Exception:
        # 额度账户同步失败不应阻塞用户创建/编辑主流程
        pass


# 允许的设备状态值
VALID_DEVICE_STATUSES = {"active", "blocked", "removed"}
# 分页最大条数
MAX_LIMIT = 100


# ============================================================
# 用户管理
# ============================================================


async def list_users(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    search: Optional[str] = None,
    role: Optional[str] = None,
    order: str = "desc",
) -> UserListData:
    """查询用户列表，支持分页、状态筛选、角色筛选和账号/名称模糊搜索。

    Args:
        db: 数据库异步会话
        limit: 每页条数（1-100）
        offset: 偏移量
        status: 按状态筛选（active / blocked / deleted）
        search: 按账号或展示名称模糊搜索
        role: 按角色筛选（admin / user）

    Returns:
        UserListData 用户列表及分页信息
    """
    # 角色值校验
    VALID_ROLES = {"admin", "user"}
    # 参数规范化
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)

    # 构建基础查询（排除 password_hash 字段，不返回给客户端）
    query = select(User).options(
        # 使用 load_only 只加载需要的列，排除 password_hash
    )

    # 角色筛选
    if role is not None:
        if role not in VALID_ROLES:
            raise AppError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"无效的用户角色：{role}，允许值：{', '.join(sorted(VALID_ROLES))}",
                status_code=400,
            )
        query = query.where(User.role == role)

    # 状态筛选
    if status is not None:
        if status not in VALID_USER_STATUSES:
            raise AppError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"无效的用户状态：{status}，允许值：{', '.join(sorted(VALID_USER_STATUSES))}",
                status_code=400,
            )
        query = query.where(User.status == status)

    # 模糊搜索（账号或展示名称）
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        query = query.where(
            (User.account.ilike(search_term))
            | (User.display_name.ilike(search_term))
        )

    # 查询总数
    count_query = select(func.count()).select_from(User)
    if role is not None:
        count_query = count_query.where(User.role == role)
    if status is not None:
        count_query = count_query.where(User.status == status)
    if search and search.strip():
        count_query = count_query.where(
            (User.account.ilike(search_term))
            | (User.display_name.ilike(search_term))
        )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 查询分页数据（按创建时间排序，默认倒序）
    query = query.order_by(
        User.created_at.desc() if order == "desc" else User.created_at.asc()
    ).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()

    # 批量查询套餐信息（按 plan_id）
    plan_ids = list({row.plan_id for row in rows if row.plan_id})
    plan_map = await _get_plan_info_map(db, plan_ids=plan_ids) if plan_ids else {}

    # === 批量聚合查询（增强字段） ===
    user_ids = [row.id for row in rows]
    credit_map = await _batch_credit_balances(db, user_ids)
    device_map = await _batch_device_counts(db, user_ids)
    login_map = await _batch_last_logins(db, user_ids)
    role_map = await _batch_role_names(db, user_ids)
    usage_map = await _batch_monthly_usages(db, user_ids)
    audit_map = await _batch_audit_counts(db, user_ids)
    period_end_map = await _batch_period_ends(db, user_ids)

    # 构建响应 DTO
    items = []
    for row in rows:
        pid, pname = None, None
        if row.plan_id and row.plan_id in plan_map:
            pid, pname = plan_map[row.plan_id]

        items.append(UserItem(
            id=row.id,
            account=row.account,
            display_name=row.display_name,
            role=row.role,
            status=row.status,
            plan_id=pid or row.plan_id,
            plan_name=pname,
            created_at=row.created_at,
            # === 新增聚合字段 ===
            updated_at=row.updated_at if hasattr(row, 'updated_at') and row.updated_at else None,
            last_login_at=login_map.get(row.id),
            device_count=device_map.get(row.id, 0),
            credit_balance=credit_map.get(row.id),
            role_names=role_map.get(row.id),
            monthly_usage=usage_map.get(row.id, 0),
            audit_count=audit_map.get(row.id, 0),
            period_end=period_end_map.get(row.id),
        ))

    return UserListData(items=items, total=total, limit=limit, offset=offset)


async def _build_user_detail(
    db: AsyncSession,
    user_id: str,
    account: str,
    display_name: Optional[str],
    role: str,
    status: str,
    created_at: datetime,
    updated_at: datetime,
    plan_id: Optional[str] = None,
    # === 新增聚合字段（可选，单用户查询时批量填充） ===
    last_login_at: Optional[datetime] = None,
    device_count: int = 0,
    credit_balance: Optional[int] = None,
    role_names: Optional[str] = None,
    monthly_usage: int = 0,
    audit_count: int = 0,
    period_end: Optional[datetime] = None,
) -> UserDetail:
    """统一构建 UserDetail，自动查询 plan_name。

    按 plan_id 查 plans 表获取套餐名称。
    聚合字段由调用方通过批量查询填充后传入。
    """
    pid, pname = None, None
    if plan_id:
        plan_map = await _get_plan_info_map(db, plan_ids=[plan_id])
        if plan_id in plan_map:
            pid, pname = plan_map[plan_id]

    return UserDetail(
        id=user_id,
        account=account,
        display_name=display_name,
        role=role,
        status=status,
        plan_id=pid or plan_id,
        plan_name=pname,
        created_at=created_at,
        updated_at=updated_at,
        # === 新增聚合字段 ===
        last_login_at=last_login_at,
        device_count=device_count,
        credit_balance=credit_balance,
        role_names=role_names,
        monthly_usage=monthly_usage,
        audit_count=audit_count,
        period_end=period_end,
    )


async def get_user_detail(db: AsyncSession, user_id: str) -> UserDetail:
    """查询用户详情。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID（UUID）

    Returns:
        UserDetail 用户详细信息

    Raises:
        AppError: 用户不存在时抛出 404
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AppError(
            code="USER_NOT_FOUND",
            message=f"用户 {user_id} 不存在",
            status_code=404,
        )

    # === 单用户批量聚合查询 ===
    uid_list = [user.id]
    credit_map = await _batch_credit_balances(db, uid_list)
    device_map = await _batch_device_counts(db, uid_list)
    login_map = await _batch_last_logins(db, uid_list)
    role_map = await _batch_role_names(db, uid_list)
    usage_map = await _batch_monthly_usages(db, uid_list)
    audit_map = await _batch_audit_counts(db, uid_list)
    period_end_map = await _batch_period_ends(db, uid_list)

    return await _build_user_detail(
        db, user.id, user.account, user.display_name,
        user.role, user.status,
        user.created_at, user.updated_at,
        plan_id=getattr(user, 'plan_id', None),
        last_login_at=login_map.get(user.id),
        device_count=device_map.get(user.id, 0),
        credit_balance=credit_map.get(user.id),
        role_names=role_map.get(user.id),
        monthly_usage=usage_map.get(user.id, 0),
        audit_count=audit_map.get(user.id, 0),
        period_end=period_end_map.get(user.id),
    )


async def update_user_status(
    db: AsyncSession, user_id: str, new_status: str
) -> UserDetail:
    """修改用户状态。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID（UUID）
        new_status: 目标状态（active / blocked / deleted）

    Returns:
        UserDetail 更新后的用户信息

    Raises:
        AppError: 用户不存在或状态值无效
    """
    # 校验状态值
    if new_status not in VALID_USER_STATUSES:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"无效的用户状态：{new_status}，允许值：{', '.join(sorted(VALID_USER_STATUSES))}",
            status_code=400,
        )

    # 查询用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AppError(
            code="USER_NOT_FOUND",
            message=f"用户 {user_id} 不存在",
            status_code=404,
        )

    # 更新状态和时间
    user.status = new_status
    user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()

    return await _build_user_detail(
        db, user.id, user.account, user.display_name,
        user.role, user.status,
        user.created_at, user.updated_at,
        plan_id=getattr(user, 'plan_id', None),
    )


async def create_user(
    db: AsyncSession,
    account: str,
    password: str,
    display_name: str,
    role: str = "user",
    plan_id: Optional[str] = None,
    role_ids: Optional[list[str]] = None,
) -> UserDetail:
    """创建新用户（管理员手动创建）。

    创建规则：
    - display_name 必填
    - 套餐（plan_id）必选（管理员和普通用户都必须选择）
    - role=admin 时必须分配 RBAC 角色（role_ids）

    Args:
        db: 数据库异步会话
        account: 登录账号
        password: 明文密码（将 bcrypt 哈希存储）
        display_name: 展示名称（必填）
        role: 用户角色（默认 user）
        plan_id: 套餐 ID（UUID），必选
        role_ids: RBAC 角色 ID 列表，管理员必选

    Returns:
        UserDetail 创建的用户信息

    Raises:
        AppError: 账号已存在、校验失败等
    """
    # === 校验 ===
    if not display_name or not display_name.strip():
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="展示名称不能为空",
            status_code=422,
        )

    if not plan_id:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="必须选择套餐",
            status_code=422,
        )

    if role == "admin" and (not role_ids or len(role_ids) == 0):
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="管理员必须分配至少一个角色",
            status_code=422,
        )

    # 检查账号是否已存在
    existing = await db.execute(select(User).where(User.account == account))
    if existing.scalar_one_or_none() is not None:
        raise AppError(
            code="ACCOUNT_EXISTS",
            message=f"账号 {account} 已存在",
            status_code=409,
        )

    # 密码哈希
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user = User(
        account=account,
        password_hash=password_hash,
        display_name=display_name.strip(),
        role=role,
        status="active",
        plan_id=plan_id,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.flush()

    # 用户创建时若指定了套餐，同步创建额度账户并赠送初始额度
    if plan_id:
        await _sync_credit_account(db, user.id, plan_id)

    # 创建管理员时分配 RBAC 角色
    if role_ids:
        await _assign_roles_to_user(db, user.id, role_ids)

    return await _build_user_detail(
        db, user.id, user.account, user.display_name,
        user.role, user.status,
        user.created_at, user.updated_at,
        plan_id=getattr(user, 'plan_id', None),
    )


async def _assign_roles_to_user(
    db: AsyncSession, user_id: str, role_ids: list[str]
) -> None:
    """内部函数：为用户分配 RBAC 角色。

    使用 raw SQL 写入 user_roles 表，避免跨模块 ORM 冲突。
    """
    for rid in role_ids:
        await db.execute(
            text(
                "INSERT INTO user_roles (user_id, role_id) "
                "VALUES (:uid, :rid)"
            ),
            {"uid": user_id, "rid": rid},
        )


async def update_user(
    db: AsyncSession,
    user_id: str,
    display_name: Optional[str] = None,
    plan_id: Optional[str] = None,
    role: Optional[str] = None,
) -> UserDetail:
    """编辑用户信息（只更新传入的非 None 字段）。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        display_name: 新展示名称（可选）
        plan_id: 套餐 ID（UUID）
        role: 新角色（可选）

    Returns:
        UserDetail 更新后的用户信息

    Raises:
        AppError: 用户不存在时抛出 404
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AppError(
            code="USER_NOT_FOUND",
            message=f"用户 {user_id} 不存在",
            status_code=404,
        )

    if display_name is not None:
        user.display_name = display_name
    if plan_id is not None:
        user.plan_id = plan_id
        # 套餐变更时同步额度账户（创建或更新 plan_id / monthly_grant）
        await _sync_credit_account(db, user_id, plan_id)
    if role is not None:
        user.role = role

    user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()

    return await _build_user_detail(
        db, user.id, user.account, user.display_name,
        user.role, user.status,
        user.created_at, user.updated_at,
        plan_id=getattr(user, 'plan_id', None),
    )


async def delete_user(db: AsyncSession, user_id: str) -> dict:
    """软删除用户。

    将用户状态设为 deleted，关联设备状态设为 removed，清除登录会话。
    保留所有关联数据（订单、额度、审计日志等），不做硬删除。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID

    Returns:
        {"deleted": True}

    Raises:
        AppError: 用户不存在或已删除时抛出 404
    """
    # 查询用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AppError(
            code="USER_NOT_FOUND",
            message=f"用户 {user_id} 不存在",
            status_code=404,
        )

    if user.status == "deleted":
        raise AppError(
            code="USER_ALREADY_DELETED",
            message=f"用户 {user_id} 已被删除",
            status_code=404,
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 软删除用户
    user.status = "deleted"
    user.updated_at = now

    # 软删除关联设备
    await db.execute(
        text("UPDATE devices SET status = 'removed', updated_at = :now WHERE user_id = :uid AND status != 'removed'"),
        {"uid": user_id, "now": now},
    )

    # 清除登录会话（强制下线）
    await db.execute(
        text("DELETE FROM auth_sessions WHERE user_id = :uid"),
        {"uid": user_id},
    )

    await db.flush()
    return {"deleted": True}


async def list_user_devices(
    db: AsyncSession,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
) -> DeviceListData:
    """查询指定用户的设备列表。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID（UUID）
        limit: 每页条数
        offset: 偏移量

    Returns:
        DeviceListData 设备列表及分页信息

    Raises:
        AppError: 用户不存在时抛出 404
    """
    # 先确认用户存在
    user_result = await db.execute(select(User.id).where(User.id == user_id))
    if user_result.scalar_one_or_none() is None:
        raise AppError(
            code="USER_NOT_FOUND",
            message=f"用户 {user_id} 不存在",
            status_code=404,
        )

    # 参数规范化
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)

    # 查询总数
    count_query = select(func.count()).select_from(Device).where(
        Device.user_id == user_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 查询分页数据
    query = (
        select(Device)
        .where(Device.user_id == user_id)
        .order_by(Device.bound_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    # 批量查询关联用户账号
    user_ids = list({row.user_id for row in rows})
    user_map = await _batch_user_info(db, user_ids)

    items = [
        DeviceItem(
            id=row.id,
            user_id=row.user_id,
            user_account=user_map.get(row.user_id, (None, None))[0],
            user_display_name=user_map.get(row.user_id, (None, None))[1],
            device_name=row.device_name,
            client_version=row.client_version,
            status=row.status,
            bound_at=row.bound_at,
            last_seen_at=row.last_seen_at,
        )
        for row in rows
    ]

    return DeviceListData(items=items, total=total, limit=limit, offset=offset)


# ============================================================
# 设备管理
# ============================================================


async def _batch_user_info(
    db: AsyncSession, user_ids: list[str]
) -> dict[str, tuple[Optional[str], Optional[str]]]:
    """批量查询 user_id → (account, display_name) 映射。"""
    if not user_ids:
        return {}
    result = await db.execute(
        select(User.id, User.account, User.display_name).where(User.id.in_(user_ids))
    )
    rows = result.all()
    return {row[0]: (row[1], row[2]) for row in rows}


async def list_devices(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
) -> DeviceListData:
    """查询所有设备列表，支持分页和状态筛选。

    Args:
        db: 数据库异步会话
        limit: 每页条数（1-100）
        offset: 偏移量
        status: 按状态筛选（active / blocked / removed）

    Returns:
        DeviceListData 设备列表及分页信息
    """
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)

    # 构建查询
    query = select(Device)

    # 状态筛选
    if status is not None:
        if status not in VALID_DEVICE_STATUSES:
            raise AppError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"无效的设备状态：{status}，允许值：{', '.join(sorted(VALID_DEVICE_STATUSES))}",
                status_code=400,
            )
        query = query.where(Device.status == status)

    # 查询总数
    count_query = select(func.count()).select_from(Device)
    if status is not None:
        count_query = count_query.where(Device.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 查询分页数据
    query = query.order_by(Device.bound_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()

    # 批量查询关联用户账号
    user_ids = list({row.user_id for row in rows})
    user_map = await _batch_user_info(db, user_ids)

    items = [
        DeviceItem(
            id=row.id,
            user_id=row.user_id,
            user_account=user_map.get(row.user_id, (None, None))[0],
            user_display_name=user_map.get(row.user_id, (None, None))[1],
            device_name=row.device_name,
            client_version=row.client_version,
            status=row.status,
            bound_at=row.bound_at,
            last_seen_at=row.last_seen_at,
        )
        for row in rows
    ]

    return DeviceListData(items=items, total=total, limit=limit, offset=offset)


async def get_device_detail(db: AsyncSession, device_id: str) -> DeviceDetail:
    """查询设备详情。

    Args:
        db: 数据库异步会话
        device_id: 设备 ID（UUID）

    Returns:
        DeviceDetail 设备详细信息

    Raises:
        AppError: 设备不存在时抛出 404
    """
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if device is None:
        raise AppError(
            code="DEVICE_NOT_FOUND",
            message=f"设备 {device_id} 不存在",
            status_code=404,
        )

    # 查询关联用户信息
    user_map = await _batch_user_info(db, [device.user_id])

    return DeviceDetail(
        id=device.id,
        user_id=device.user_id,
        user_account=user_map.get(device.user_id, (None, None))[0],
        user_display_name=user_map.get(device.user_id, (None, None))[1],
        device_name=device.device_name,
        client_version=device.client_version,
        status=device.status,
        bound_at=device.bound_at,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


async def update_device_status(
    db: AsyncSession, device_id: str, new_status: str
) -> DeviceDetail:
    """修改设备状态。

    Args:
        db: 数据库异步会话
        device_id: 设备 ID（UUID）
        new_status: 目标状态（active / blocked / removed）

    Returns:
        DeviceDetail 更新后的设备信息

    Raises:
        AppError: 设备不存在或状态值无效
    """
    # 校验状态值
    if new_status not in VALID_DEVICE_STATUSES:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"无效的设备状态：{new_status}，允许值：{', '.join(sorted(VALID_DEVICE_STATUSES))}",
            status_code=400,
        )

    # 查询设备
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if device is None:
        raise AppError(
            code="DEVICE_NOT_FOUND",
            message=f"设备 {device_id} 不存在",
            status_code=404,
        )

    # 更新状态和时间
    device.status = new_status
    device.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()

    user_map = await _batch_user_info(db, [device.user_id])
    return DeviceDetail(
        id=device.id,
        user_id=device.user_id,
        user_account=user_map.get(device.user_id, (None, None))[0],
        user_display_name=user_map.get(device.user_id, (None, None))[1],
        device_name=device.device_name,
        client_version=device.client_version,
        status=device.status,
        bound_at=device.bound_at,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


async def delete_device(db: AsyncSession, device_id: str) -> dict:
    """软删除设备。

    将设备状态设为 removed，保留设备记录。

    Args:
        db: 数据库异步会话
        device_id: 设备 ID

    Returns:
        {"deleted": True}

    Raises:
        AppError: 设备不存在或已移除时抛出 404
    """
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if device is None:
        raise AppError(
            code="DEVICE_NOT_FOUND",
            message=f"设备 {device_id} 不存在",
            status_code=404,
        )

    if device.status == "removed":
        raise AppError(
            code="DEVICE_ALREADY_REMOVED",
            message=f"设备 {device_id} 已被移除",
            status_code=404,
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    device.status = "removed"
    device.updated_at = now
    await db.flush()

    return {"deleted": True}


# ============================================================
# 管理员强制重置密码
# ============================================================


async def force_reset_password(
    db: AsyncSession, user_id: str, new_password: str | None = None
) -> dict:
    """管理员强制重置用户密码。

    如果传入 new_password 则使用管理员指定的密码，
    否则生成随机密码（向后兼容）。

    Args:
        db: 数据库异步会话
        user_id: 目标用户 ID
        new_password: 管理员指定的新密码（可选，不传则随机生成）

    Returns:
        {"message": "..."} 或 {"new_password": "<随机密码>", "message": "..."}
    """
    import secrets
    import bcrypt

    # 查询用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError(code="USER_NOT_FOUND", message="用户不存在", status_code=404)

    # 使用管理员指定密码或生成随机密码
    if new_password is None:
        new_password = secrets.token_urlsafe(12)

    # 哈希新密码
    password_hash = bcrypt.hashpw(
        new_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    # 更新密码
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user.password_hash = password_hash
    user.updated_at = now

    # 撤销该用户所有活跃会话
    from sqlalchemy import text
    await db.execute(
        text("UPDATE auth_sessions SET status = 'revoked', revoked_at = :now "
             "WHERE user_id = :uid AND status = 'active'"),
        {"now": now, "uid": user_id},
    )
    await db.flush()

    # 不返回明文密码（安全考虑），只返回成功提示
    return {
        "message": "密码已重置成功，用户需使用新密码重新登录",
    }
