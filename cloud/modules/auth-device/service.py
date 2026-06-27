"""
cloud-auth-device 业务逻辑层。

提供登录、刷新、退出、设备绑定、设备状态查询的核心逻辑。
所有数据库操作通过 cloud-shared 公共层的异步会话完成。

密码使用 bcrypt 哈希，设备指纹和 refresh_token 使用 SHA-256 哈希存储，
对齐 cloud/DATABASE_SCHEMA.md 设计原则中的"敏感字段必须脱敏或哈希存储"。
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import (
    ErrorCode,
    AppError,
    create_access_token,
    shared_settings,
)

from models import User, Device, AuthSession, PasswordResetToken
from schemas import (
    LoginRequest,
    LoginData,
    UserInfo,
    DeviceInfo,
    TokenPair,
    RefreshData,
    LogoutData,
    CurrentDevice,
    BindDeviceRequest,
)

# 刷新令牌有效期（天）
_REFRESH_TOKEN_EXPIRE_DAYS = 7


# ============================================================
# 哈希工具函数
# ============================================================

def hash_fingerprint(fingerprint: str) -> str:
    """对设备指纹做 SHA-256 哈希。

    DATABASE_SCHEMA.md 要求 devices.device_fingerprint_hash 为哈希值，
    不得明文存储原始设备指纹。
    """
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def hash_token(token: str) -> str:
    """对 refresh_token 做 SHA-256 哈希，用于安全存储。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_refresh_token() -> str:
    """生成加密安全的随机 refresh_token（64 字节，URL-safe base64）。"""
    return secrets.token_urlsafe(64)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """验证明文密码与 bcrypt 哈希是否匹配。

    直接使用 bcrypt 库，避免 passlib 与 bcrypt 5.x 不兼容。
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def hash_password(plain_password: str) -> str:
    """对明文密码做 bcrypt 哈希。

    直接使用 bcrypt 库，避免 passlib 与 bcrypt 5.x 不兼容。
    """
    return bcrypt.hashpw(
        plain_password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


# ============================================================
# 用户查询
# ============================================================

async def _get_active_user(db: AsyncSession, account: str) -> User:
    """根据账号查询活跃用户，不存在或被封禁则抛出 AppError。

    Args:
        db: 数据库异步会话
        account: 登录账号

    Returns:
        查询到的 User ORM 对象

    Raises:
        AppError: 用户不存在或已被封禁/删除
    """
    result = await db.execute(
        select(User).where(User.account == account)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise AppError(
            code=ErrorCode.AUTH_INVALID_CREDENTIALS,
            message="账号或密码错误",
            status_code=401,
        )

    if user.status == "blocked":
        raise AppError(
            code=ErrorCode.AUTH_INVALID_CREDENTIALS,
            message="账号已被封禁，请联系客服",
            status_code=403,
        )

    if user.status == "deleted":
        raise AppError(
            code=ErrorCode.AUTH_INVALID_CREDENTIALS,
            message="账号已注销",
            status_code=401,
        )

    return user


# ============================================================
# 设备管理
# ============================================================

async def _get_or_create_device(
    db: AsyncSession,
    user_id: str,
    fingerprint: str,
    device_name: str | None,
    client_version: str | None,
) -> tuple[Device, bool]:
    """查询或创建设备记录。

    通过 (user_id, device_fingerprint_hash) 唯一约束查找已有设备。
    如果不存在则创建新记录，存在则更新 last_seen_at。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        fingerprint: 原始设备指纹
        device_name: 设备名称
        client_version: 客户端版本

    Returns:
        (Device, is_new) 元组
    """
    fp_hash = hash_fingerprint(fingerprint)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 查询已有设备（基于唯一约束）
    result = await db.execute(
        select(Device).where(
            Device.user_id == user_id,
            Device.device_fingerprint_hash == fp_hash,
        )
    )
    device = result.scalar_one_or_none()

    if device is not None:
        # 已有设备：更新最后活跃时间和名称/版本
        is_new = False
        device.last_seen_at = now
        if device_name:
            device.device_name = device_name
        if client_version:
            device.client_version = client_version
        device.updated_at = now
        await db.flush()
        return device, is_new

    # 新设备：创建记录
    is_new = True
    device = Device(
        user_id=user_id,
        device_fingerprint_hash=fp_hash,
        device_name=device_name,
        client_version=client_version,
        status="active",
        bound_at=now,
        last_seen_at=now,
    )
    db.add(device)
    await db.flush()
    return device, is_new


# ============================================================
# 会话管理
# ============================================================

async def _create_session(
    db: AsyncSession,
    user_id: str,
    device_id: str,
    role: str = "user",
    plan_code: str = "free",
) -> TokenPair:
    """创建认证会话：生成 access_token + refresh_token 对。

    access_token 使用 cloud-shared 的 JWT 签发。
    refresh_token 为加密随机字符串，哈希后存入 auth_sessions 表。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        device_id: 设备 ID
        role: 用户角色（用于 JWT 载荷）
        plan_code: 当前套餐编码（用于 JWT 载荷）

    Returns:
        TokenPair（access_token, refresh_token, token_type, expires_in）
    """
    # 生成 refresh_token 原文和哈希
    raw_refresh = generate_refresh_token()
    refresh_hash = hash_token(raw_refresh)

    # 签发 JWT access_token（委托 cloud-shared，携带用户真实 role 和 plan_code）
    access_token = create_access_token(
        user_id=user_id,
        device_id=device_id,
        role=role,
        plan_code=plan_code,
    )

    # 计算过期时间
    expires_in = shared_settings.auth_access_token_expire_minutes * 60
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    refresh_expires = now + timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS)

    # 写入 auth_sessions 表
    session = AuthSession(
        user_id=user_id,
        device_id=device_id,
        refresh_token_hash=refresh_hash,
        status="active",
        expires_at=refresh_expires,
    )
    db.add(session)
    await db.flush()

    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        expires_in=expires_in,
    )


async def _revoke_session(db: AsyncSession, refresh_token: str) -> None:
    """撤销刷新令牌对应的会话。

    将 auth_sessions 中对应记录标记为 revoked。
    如果令牌不存在或已撤销，不报错（幂等操作）。

    Args:
        db: 数据库异步会话
        refresh_token: 原始 refresh_token
    """
    refresh_hash = hash_token(refresh_token)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    result = await db.execute(
        select(AuthSession).where(
            AuthSession.refresh_token_hash == refresh_hash,
            AuthSession.status == "active",
        )
    )
    session = result.scalar_one_or_none()

    if session is not None:
        session.status = "revoked"
        session.revoked_at = now
        await db.flush()


async def _validate_and_get_session(
    db: AsyncSession, refresh_token: str
) -> AuthSession:
    """校验 refresh_token 并返回有效的会话记录。

    验证逻辑：
    1. 令牌哈希匹配
    2. 会话状态为 active
    3. 未过期

    Args:
        db: 数据库异步会话
        refresh_token: 原始 refresh_token

    Returns:
        有效的 AuthSession ORM 对象

    Raises:
        AppError: 令牌无效、已撤销或已过期
    """
    refresh_hash = hash_token(refresh_token)

    result = await db.execute(
        select(AuthSession).where(
            AuthSession.refresh_token_hash == refresh_hash
        )
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise AppError(
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="刷新令牌无效",
            status_code=401,
        )

    if session.status == "revoked":
        raise AppError(
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="刷新令牌已被撤销，请重新登录",
            status_code=401,
        )

    # 兼容 SQLite 无时区存储：将 aware datetime 转为 naive UTC 比较
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if session.status == "expired" or session.expires_at < now_utc:
        # 标记为过期
        if session.status != "expired":
            session.status = "expired"
            await db.flush()
        raise AppError(
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="刷新令牌已过期，请重新登录",
            status_code=401,
        )

    return session


# ============================================================
# 对外服务函数
# ============================================================


async def login(
    db: AsyncSession,
    req: LoginRequest,
) -> LoginData:
    """登录服务。

    流程：
    1. 验证账号密码
    2. 查询或创建设备记录
    3. 创建认证会话（access_token + refresh_token）
    4. 返回用户信息、设备信息和令牌对

    Args:
        db: 数据库异步会话
        req: 登录请求数据

    Returns:
        LoginData（含 user、device、token 信息）

    Raises:
        AppError: 账号不存在、密码错误、账号被封禁等
    """
    # 1. 查询用户并校验密码
    user = await _get_active_user(db, req.account)

    if not verify_password(req.password, user.password_hash):
        raise AppError(
            code=ErrorCode.AUTH_INVALID_CREDENTIALS,
            message="账号或密码错误",
            status_code=401,
        )

    # 2. 查询或创建设备
    device, is_new = await _get_or_create_device(
        db,
        user_id=user.id,
        fingerprint=req.device_fingerprint,
        device_name=req.device_name,
        client_version=req.client_version,
    )

    # 如果设备被封禁或移除，拒绝登录
    if device.status == "blocked":
        raise AppError(
            code=ErrorCode.DEVICE_NOT_BOUND,
            message="设备已被封禁",
            status_code=403,
        )
    if device.status == "removed":
        # 设备被移除后重新绑定
        device.status = "active"
        device.bound_at = datetime.now(timezone.utc).replace(tzinfo=None)
        is_new = True
        await db.flush()

    # 3. 创建会话（携带用户真实的 role 和 plan_code 进入 JWT 载荷）
    tokens = await _create_session(
        db,
        user_id=user.id,
        device_id=device.id,
        role=user.role,
        plan_code=user.plan_code,
    )

    # 4. 构造响应
    return LoginData(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user=UserInfo(
            id=user.id,
            account=user.account,
            display_name=user.display_name,
            plan_code=user.plan_code,
        ),
        device=DeviceInfo(
            id=device.id,
            status=device.status,
            is_new=is_new,
        ),
    )


async def refresh(
    db: AsyncSession,
    refresh_token: str,
) -> RefreshData:
    """刷新令牌服务。

    流程：
    1. 校验 refresh_token 有效性
    2. 撤销旧会话
    3. 创建新会话（令牌轮换）
    4. 更新设备 last_seen_at

    Args:
        db: 数据库异步会话
        refresh_token: 当前有效的 refresh_token

    Returns:
        RefreshData（新令牌对）

    Raises:
        AppError: 令牌无效、过期或已撤销
    """
    # 1. 校验旧令牌
    session = await _validate_and_get_session(db, refresh_token)

    # 2. 撤销旧会话
    old_refresh = refresh_token  # 保存引用
    await _revoke_session(db, old_refresh)

    # 3. 创建新会话（令牌轮换，需要获取用户真实 role 和 plan_code）
    # 查询用户信息用于 JWT 载荷
    user_result = await db.execute(
        select(User).where(User.id == session.user_id)
    )
    user = user_result.scalar_one_or_none()
    user_role = user.role if user else "user"
    user_plan = user.plan_code if user else "free"

    new_tokens = await _create_session(
        db,
        user_id=session.user_id,
        device_id=session.device_id or "",
        role=user_role,
        plan_code=user_plan,
    )

    # 4. 更新设备活跃时间
    if session.device_id:
        result = await db.execute(
            select(Device).where(Device.id == session.device_id)
        )
        device = result.scalar_one_or_none()
        if device is not None:
            device.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.flush()

    return RefreshData(
        access_token=new_tokens.access_token,
        refresh_token=new_tokens.refresh_token,
        token_type=new_tokens.token_type,
        expires_in=new_tokens.expires_in,
    )


async def logout(
    db: AsyncSession,
    refresh_token: str,
) -> LogoutData:
    """退出登录服务。

    撤销指定的 refresh_token，使对应会话失效。
    操作是幂等的——重复退出同一令牌不报错。

    Args:
        db: 数据库异步会话
        refresh_token: 要撤销的 refresh_token

    Returns:
        LogoutData
    """
    await _revoke_session(db, refresh_token)
    return LogoutData(logged_out=True)


async def get_current_device(
    db: AsyncSession,
    user_id: str,
    device_id: str,
) -> CurrentDevice:
    """获取当前设备详情。

    根据 JWT 中解析的 user_id 和 device_id 查询设备信息。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID（来自 JWT）
        device_id: 设备 ID（来自 JWT）

    Returns:
        CurrentDevice 设备详情

    Raises:
        AppError: 设备不存在或不属于该用户
    """
    result = await db.execute(
        select(Device).where(
            Device.id == device_id,
            Device.user_id == user_id,
        )
    )
    device = result.scalar_one_or_none()

    if device is None:
        raise AppError(
            code=ErrorCode.DEVICE_NOT_BOUND,
            message="设备未绑定或不属于当前用户",
            status_code=404,
        )

    return CurrentDevice(
        id=device.id,
        device_fingerprint=device.device_fingerprint_hash,
        device_name=device.device_name or "",
        status=device.status,
        bound_at=device.bound_at,
        last_seen_at=device.last_seen_at,
    )


async def bind_device(
    db: AsyncSession,
    user_id: str,
    req: BindDeviceRequest,
) -> DeviceInfo:
    """绑定当前设备到登录用户。

    如果设备已存在（同用户同指纹），返回已有记录；
    否则创建新设备记录。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID（来自 JWT）
        req: 设备绑定请求

    Returns:
        DeviceInfo（设备 ID、状态、是否新绑定）
    """
    device, is_new = await _get_or_create_device(
        db,
        user_id=user_id,
        fingerprint=req.device_fingerprint,
        device_name=req.device_name,
        client_version=req.client_version,
    )

    return DeviceInfo(
        id=device.id,
        status=device.status,
        is_new=is_new,
    )


# ============================================================
# 密码重置服务
# ============================================================

# 密码重置令牌有效期（小时）
_PASSWORD_RESET_EXPIRE_HOURS = 1


async def forgot_password(
    db: AsyncSession,
    account: str,
) -> tuple[str, str]:
    """忘记密码：生成重置令牌。

    1. 根据账号查找用户
    2. 生成加密随机重置令牌
    3. 哈希后存入 password_reset_tokens 表
    4. 返回原始令牌（开发阶段，生产应发邮件）

    Args:
        db: 数据库异步会话
        account: 用户登录账号

    Returns:
        (message, reset_token) 元组

    Raises:
        AppError: 用户不存在
    """
    user = await _get_active_user(db, account)

    # 生成重置令牌
    raw_token = generate_refresh_token()  # 复用安全随机生成
    token_hash = hash_token(raw_token)

    # 使该用户之前的未使用重置令牌失效
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.execute(
        text("UPDATE password_reset_tokens SET status = 'expired' "
             "WHERE user_id = :user_id AND status = 'active'"),
        {"user_id": user.id},
    )

    # 创建新重置令牌
    expires_at = now_utc + timedelta(hours=_PASSWORD_RESET_EXPIRE_HOURS)
    import uuid as _uuid
    reset_record = PasswordResetToken(
        id=str(_uuid.uuid4()),
        user_id=user.id,
        token_hash=token_hash,
        status="active",
        expires_at=expires_at,
    )
    db.add(reset_record)
    await db.flush()

    return (
        f"密码重置令牌已生成，有效期 {_PASSWORD_RESET_EXPIRE_HOURS} 小时",
        raw_token,
    )


async def reset_password(
    db: AsyncSession,
    reset_token: str,
    new_password: str,
) -> str:
    """重置密码：使用重置令牌设置新密码。

    1. 哈希令牌并查找有效记录
    2. 校验未过期、未使用
    3. 更新用户密码哈希
    4. 标记令牌为已使用
    5. 撤销该用户所有活跃会话

    Args:
        db: 数据库异步会话
        reset_token: 原始重置令牌
        new_password: 新密码明文

    Returns:
        成功消息

    Raises:
        AppError: 令牌无效、过期或已使用
    """
    from cloud.shared import ErrorCode as EC

    token_hash = hash_token(reset_token)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    # 查找有效令牌
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash
        )
    )
    reset_record = result.scalar_one_or_none()

    if reset_record is None:
        raise AppError(
            code=EC.AUTH_TOKEN_EXPIRED,
            message="密码重置链接无效",
            status_code=400,
        )

    if reset_record.status == "used":
        raise AppError(
            code=EC.AUTH_TOKEN_EXPIRED,
            message="密码重置链接已使用，请重新申请",
            status_code=400,
        )

    if reset_record.status == "expired" or reset_record.expires_at < now_utc:
        if reset_record.status != "expired":
            reset_record.status = "expired"
            await db.flush()
        raise AppError(
            code=EC.AUTH_TOKEN_EXPIRED,
            message="密码重置链接已过期，请重新申请",
            status_code=400,
        )

    # 更新密码
    new_hash = hash_password(new_password)
    await db.execute(
        text("UPDATE users SET password_hash = :pw, updated_at = :now WHERE id = :uid"),
        {"pw": new_hash, "now": now_utc, "uid": reset_record.user_id},
    )

    # 标记令牌已使用
    reset_record.status = "used"
    reset_record.used_at = now_utc

    # 撤销该用户所有活跃会话（强制重新登录）
    await db.execute(
        text("UPDATE auth_sessions SET status = 'revoked', revoked_at = :now "
             "WHERE user_id = :uid AND status = 'active'"),
        {"now": now_utc, "uid": reset_record.user_id},
    )
    await db.flush()

    return "密码已重置，请使用新密码重新登录"


async def change_password(
    db: AsyncSession,
    user_id: str,
    old_password: str,
    new_password: str,
) -> str:
    """已登录用户修改密码。

    1. 查询用户
    2. 验证旧密码
    3. 更新为新密码哈希
    4. 撤销其他会话（当前会话保留）

    Args:
        db: 数据库异步会话
        user_id: 当前用户 ID
        old_password: 旧密码
        new_password: 新密码

    Returns:
        成功消息

    Raises:
        AppError: 旧密码错误
    """
    from cloud.shared import ErrorCode as EC

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise AppError(
            code=EC.AUTH_INVALID_CREDENTIALS,
            message="用户不存在",
            status_code=404,
        )

    if not verify_password(old_password, user.password_hash):
        raise AppError(
            code=EC.AUTH_INVALID_CREDENTIALS,
            message="旧密码错误",
            status_code=400,
        )

    # 更新密码
    new_hash = hash_password(new_password)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    user.password_hash = new_hash
    user.updated_at = now_utc
    await db.flush()

    return "密码已修改"
