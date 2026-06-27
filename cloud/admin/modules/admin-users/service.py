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

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import AppError, ErrorCode
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

    # 查询分页数据
    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()

    # 构建响应 DTO
    items = [
        UserItem(
            id=row.id,
            account=row.account,
            display_name=row.display_name,
            role=row.role,
            status=row.status,
            plan_code=row.plan_code,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return UserListData(items=items, total=total, limit=limit, offset=offset)


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

    return UserDetail(
        id=user.id,
        account=user.account,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        plan_code=user.plan_code,
        created_at=user.created_at,
        updated_at=user.updated_at,
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

    return UserDetail(
        id=user.id,
        account=user.account,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        plan_code=user.plan_code,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def create_user(
    db: AsyncSession,
    account: str,
    password: str,
    display_name: Optional[str] = None,
    role: str = "user",
    plan_code: str = "free",
) -> UserDetail:
    """创建新用户（管理员手动创建）。

    Args:
        db: 数据库异步会话
        account: 登录账号
        password: 明文密码（将 bcrypt 哈希存储）
        display_name: 展示名称（可选）
        role: 用户角色（默认 user）
        plan_code: 套餐编码（默认 free）

    Returns:
        UserDetail 创建的用户信息

    Raises:
        AppError: 账号已存在时抛出 409
    """
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
        display_name=display_name,
        role=role,
        status="active",
        plan_code=plan_code,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.flush()

    return UserDetail(
        id=user.id,
        account=user.account,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        plan_code=user.plan_code,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def update_user(
    db: AsyncSession,
    user_id: str,
    display_name: Optional[str] = None,
    plan_code: Optional[str] = None,
    role: Optional[str] = None,
) -> UserDetail:
    """编辑用户信息（只更新传入的非 None 字段）。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        display_name: 新展示名称（可选）
        plan_code: 新套餐编码（可选）
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
    if plan_code is not None:
        user.plan_code = plan_code
    if role is not None:
        user.role = role

    user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()

    return UserDetail(
        id=user.id,
        account=user.account,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        plan_code=user.plan_code,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def delete_user(db: AsyncSession, user_id: str) -> dict:
    """删除用户（硬删除，同时清理关联设备）。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID

    Returns:
        {"deleted": True}

    Raises:
        AppError: 用户不存在时抛出 404
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

    # 删除关联设备
    await db.execute(
        select(Device).where(Device.user_id == user_id)
    )
    devices_result = await db.execute(
        select(Device).where(Device.user_id == user_id)
    )
    for device in devices_result.scalars().all():
        await db.delete(device)

    # 删除用户
    await db.delete(user)
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

    items = [
        DeviceItem(
            id=row.id,
            user_id=row.user_id,
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

    items = [
        DeviceItem(
            id=row.id,
            user_id=row.user_id,
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

    return DeviceDetail(
        id=device.id,
        user_id=device.user_id,
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

    return DeviceDetail(
        id=device.id,
        user_id=device.user_id,
        device_name=device.device_name,
        client_version=device.client_version,
        status=device.status,
        bound_at=device.bound_at,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


async def delete_device(db: AsyncSession, device_id: str) -> dict:
    """删除设备（硬删除）。

    Args:
        db: 数据库异步会话
        device_id: 设备 ID

    Returns:
        {"deleted": True}

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

    await db.delete(device)
    await db.flush()

    return {"deleted": True}


# ============================================================
# 管理员强制重置密码
# ============================================================


async def force_reset_password(db: AsyncSession, user_id: str) -> dict:
    """管理员强制重置用户密码。

    生成新随机密码、更新哈希、撤销该用户所有活跃会话。

    Args:
        db: 数据库异步会话
        user_id: 目标用户 ID

    Returns:
        {"new_password": "<新密码>", "message": "..."}
    """
    import secrets
    import bcrypt

    # 查询用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError(code="USER_NOT_FOUND", message="用户不存在", status_code=404)

    # 生成新随机密码
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

    return {
        "new_password": new_password,
        "message": "密码已重置，用户需使用新密码重新登录",
    }
