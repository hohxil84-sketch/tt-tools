"""
admin-shell 业务逻辑层。

提供仪表盘统计、导航菜单生成和服务状态查询。
仪表盘统计从数据库实时查询 users、devices、orders 表聚合数据。
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import DashboardStats, MenuItem, MenuData, StatusData


# 服务启动时间（用于计算 uptime）
_SERVER_START_TIME: float = time.time()


# ============================================================
# 仪表盘统计（从数据库实时查询）
# ============================================================

async def get_dashboard_stats(db: Optional[AsyncSession] = None) -> DashboardStats:
    """获取后台仪表盘核心统计指标。

    从数据库实时查询用户总数、今日订单数、今日收入、活跃设备数。
    如果 db 为 None（无数据库连接），返回占位值 0。

    Args:
        db: 数据库异步会话

    Returns:
        DashboardStats 统计指标
    """
    if db is None:
        return DashboardStats(
            users_total=0,
            orders_today=0,
            revenue_today_cents=0,
            active_devices=0,
            server_status="healthy",
        )

    # 查询用户总数
    users_result = await db.execute(text("SELECT COUNT(*) FROM users"))
    users_total = users_result.scalar_one()

    # 查询今日订单数和收入（UTC 今日 00:00:00 起）
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    orders_result = await db.execute(
        text(
            "SELECT COUNT(*), COALESCE(SUM(amount_cents), 0) "
            "FROM orders WHERE created_at >= :today_start"
        ),
        {"today_start": today_start},
    )
    orders_row = orders_result.one()
    orders_today = orders_row[0]
    revenue_today_cents = orders_row[1]

    # 查询活跃设备数
    devices_result = await db.execute(
        text("SELECT COUNT(*) FROM devices WHERE status = 'active'")
    )
    active_devices = devices_result.scalar_one()

    return DashboardStats(
        users_total=users_total,
        orders_today=orders_today,
        revenue_today_cents=revenue_today_cents,
        active_devices=active_devices,
        server_status="healthy",
    )


# ============================================================
# 导航菜单
# ============================================================

def get_menu(user_permissions: set | None = None) -> MenuData:
    """获取后台导航菜单结构，按用户权限过滤。

    每个菜单项声明 required_permission，服务端根据用户拥有的权限码
    自动过滤无权限的菜单项。父级菜单无子菜单时也会被隐藏。

    Args:
        user_permissions: 用户拥有的权限码集合，None 表示不过滤

    Returns:
        MenuData 菜单结构数据
    """

    def can_see(perm: str | None) -> bool:
        """检查是否能看到需要指定权限的菜单项。"""
        if user_permissions is None:
            return True  # 不过滤
        if perm is None:
            return True  # 无权限要求的菜单项所有人可见
        return perm in user_permissions

    # 所有菜单项定义（含权限要求）
    all_items: list[MenuItem] = [
        MenuItem(
            id="dashboard",
            title="仪表盘",
            icon="dashboard",
            path="/admin/dashboard",
            required_permission="dashboard.read",
        ),
        # 用户管理（统一入口：管理员 + 普通用户）
        MenuItem(
            id="users",
            title="用户管理",
            icon="users",
            path="/admin/users",
            children=[
                MenuItem(
                    id="system-users-list",
                    title="管理员",
                    icon="admin",
                    path="/admin/system-users",
                    required_permission="users.read",
                ),
                MenuItem(
                    id="client-users-list",
                    title="普通用户",
                    icon="user",
                    path="/admin/client-users",
                    required_permission="users.read",
                ),
            ],
        ),
        # 设备管理（独立顶级菜单）
        MenuItem(
            id="devices",
            title="设备管理",
            icon="devices",
            path="/admin/devices",
            children=[
                MenuItem(
                    id="devices-list",
                    title="设备列表",
                    icon="list",
                    path="/admin/devices",
                    required_permission="devices.read",
                ),
            ],
        ),
        MenuItem(
            id="billing",
            title="计费管理",
            icon="billing",
            path="/admin/billing",
            children=[
                MenuItem(
                    id="plans",
                    title="套餐管理",
                    icon="plan",
                    path="/admin/plans",
                    required_permission="plans.read",
                ),
                MenuItem(
                    id="orders",
                    title="订单管理",
                    icon="order",
                    path="/admin/orders",
                    required_permission="orders.read",
                ),
                MenuItem(
                    id="credits-accounts",
                    title="算力账户",
                    icon="credits",
                    path="/admin/credits/accounts",
                    required_permission="credits.read",
                ),
                MenuItem(
                    id="credits-ledger",
                    title="算力流水",
                    icon="ledger",
                    path="/admin/credits/ledger",
                    required_permission="credits.read",
                ),
                MenuItem(
                    id="model-pricing",
                    title="模型定价",
                    icon="dollar",
                    path="/admin/billing/model-pricing",
                    required_permission="plans.read",
                ),
            ],
        ),
        MenuItem(
            id="ops",
            title="运维管理",
            icon="ops",
            path="/admin/ops",
            children=[
                MenuItem(
                    id="provider-call-logs",
                    title="AI 调用日志",
                    icon="log",
                    path="/admin/provider-call-logs",
                    required_permission="ops.read",
                ),
                MenuItem(
                    id="cost-stats",
                    title="成本统计",
                    icon="cost",
                    path="/admin/cost-stats",
                    required_permission="ops.read",
                ),
                MenuItem(
                    id="risk-logs",
                    title="风控日志",
                    icon="risk",
                    path="/admin/risk-logs",
                    required_permission="ops.read",
                ),
            ],
        ),
        MenuItem(
            id="audit",
            title="安全审计",
            icon="audit",
            path="/admin/audit-logs",
            children=[
                MenuItem(
                    id="audit-logs",
                    title="审计日志",
                    icon="log",
                    path="/admin/audit-logs",
                    required_permission="audit.read",
                ),
                MenuItem(
                    id="roles",
                    title="角色权限",
                    icon="roles",
                    path="/admin/roles",
                    required_permission="roles.read",
                ),
            ],
        ),
        MenuItem(
            id="settings",
            title="系统设置",
            icon="settings",
            path="/admin/settings",
            children=[
                MenuItem(
                    id="providers",
                    title="Provider 管理",
                    icon="provider",
                    path="/admin/providers",
                    required_permission="providers.read",
                ),
                MenuItem(
                    id="feature-codes",
                    title="功能码管理",
                    icon="feature",
                    path="/admin/feature-codes",
                    required_permission="features.read",
                ),
            ],
        ),
    ]

    # 如果传入了权限集合，按权限过滤
    # 空集合表示用户无任何 RBAC 权限（admin 向后兼容），返回全部菜单
    if user_permissions is not None and len(user_permissions) > 0:
        filtered: list[MenuItem] = []
        for item in all_items:
            if item.children:
                # 过滤有权限的子菜单
                visible_children = [
                    c for c in item.children
                    if can_see(c.required_permission)
                ]
                if visible_children:
                    # 保留有可见子菜单的父菜单
                    filtered.append(MenuItem(
                        id=item.id,
                        title=item.title,
                        icon=item.icon,
                        path=item.path,
                        children=visible_children,
                        required_permission=item.required_permission,
                    ))
            else:
                if can_see(item.required_permission):
                    filtered.append(item)
        return MenuData(menu=filtered)

    return MenuData(menu=all_items)


# ============================================================
# 服务状态
# ============================================================

def get_status() -> StatusData:
    """获取服务运行状态。

    返回服务健康状态、版本号和运行时长。

    Returns:
        StatusData 服务状态数据
    """
    uptime = time.time() - _SERVER_START_TIME
    return StatusData(
        status="healthy",
        version="0.1.0",
        uptime_seconds=round(uptime, 1),
    )


# ============================================================
# 认证登录（直接实现 JWT 验证，通过 importlib 加载 User 模型）
# ============================================================

import hashlib  # noqa: E402
import secrets  # noqa: E402
from datetime import datetime, timezone, timedelta  # noqa: E402

import bcrypt  # noqa: E402
from jose import jwt  # noqa: E402
from sqlalchemy import text  # noqa: E402 — 用原始 SQL 避免 ORM 类冲突

from cloud.shared.config import shared_settings  # noqa: E402
from cloud.shared import AppError, ErrorCode  # noqa: E402

# 刷新令牌有效期（天）
_REFRESH_TOKEN_EXPIRE_DAYS = 7


def _verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码与 bcrypt 哈希。"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _hash_token(token: str) -> str:
    """对 refresh_token 做 SHA-256 哈希，用于安全存储。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _generate_refresh_token() -> str:
    """生成加密安全的随机 refresh_token。"""
    return secrets.token_urlsafe(64)


def _create_jwt(user_id: str, role: str) -> str:
    """创建 JWT access_token。"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=shared_settings.auth_access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, shared_settings.auth_secret_key,
                      algorithm=shared_settings.auth_algorithm)


async def login_admin(db, account: str, password: str, device_fingerprint: str = "admin-web",
                      device_name: str = None, client_version: str = None):
    """管理员登录。

    直接使用原始 SQL 查询 users 表，避免 ORM 类注册冲突。
    """
    # 原始 SQL 查询用户
    result = await db.execute(
        text("SELECT id, account, password_hash, display_name, role, status, plan_id "
             "FROM users WHERE account = :account"),
        {"account": account},
    )
    row = result.first()
    if row is None:
        raise AppError(code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                       message="账号或密码错误", status_code=401)
    # row 是 tuple，按 SELECT 字段顺序
    (user_id, user_account, password_hash, display_name,
     role, status, plan_id) = row

    if status == "blocked":
        raise AppError(code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                       message="账号已被封禁", status_code=403)

    if role != "admin":
        raise AppError(code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                       message="非管理员账号，无权登录后台管理系统", status_code=403)

    if not _verify_password(password, password_hash):
        raise AppError(code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                       message="账号或密码错误", status_code=401)

    access_token = _create_jwt(user_id=user_id, role=role)
    refresh_token = _generate_refresh_token()
    expires_in = shared_settings.auth_access_token_expire_minutes * 60

    # 将 refresh_token 哈希后写入 auth_sessions 表，使后续刷新/登出可用
    refresh_hash = _hash_token(refresh_token)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    refresh_expires = now_utc + timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS)
    import uuid
    session_id = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO auth_sessions (id, user_id, device_id, refresh_token_hash, "
             "status, expires_at, created_at) "
             "VALUES (:id, :user_id, :device_id, :token_hash, 'active', :expires_at, :created_at)"),
        {"id": session_id, "user_id": user_id, "device_id": None,
         "token_hash": refresh_hash, "expires_at": refresh_expires,
         "created_at": now_utc},
    )
    await db.flush()

    # 查询用户权限列表（RBAC）
    from cloud.shared.auth import get_user_permissions
    import asyncio
    user_permissions = await get_user_permissions(db, user_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": {
            "id": user_id,
            "account": user_account,
            "display_name": display_name,
            "plan_id": plan_id,
            "permissions": user_permissions,
        },
        "device": {
            "id": "",
            "status": "active",
            "is_new": True,
        },
    }


async def refresh_admin(db, refresh_token: str):
    """刷新管理员令牌（令牌轮换）。

    1. 校验 refresh_token 有效性
    2. 撤销旧会话
    3. 创建新会话（令牌轮换）
    4. 返回新的 token 对
    """
    refresh_hash = _hash_token(refresh_token)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    # 1. 查询并校验旧会话
    result = await db.execute(
        text("SELECT id, user_id, status, expires_at "
             "FROM auth_sessions WHERE refresh_token_hash = :token_hash"),
        {"token_hash": refresh_hash},
    )
    row = result.first()
    if row is None:
        raise AppError(code="AUTH_TOKEN_EXPIRED",
                       message="刷新令牌无效", status_code=401)

    session_id, user_id, status, expires_at = row

    if status == "revoked":
        raise AppError(code="AUTH_TOKEN_EXPIRED",
                       message="刷新令牌已被撤销，请重新登录", status_code=401)

    if status == "expired" or expires_at < now_utc:
        # 标记为过期
        if status != "expired":
            await db.execute(
                text("UPDATE auth_sessions SET status = 'expired' WHERE id = :id"),
                {"id": session_id},
            )
            await db.flush()
        raise AppError(code="AUTH_TOKEN_EXPIRED",
                       message="刷新令牌已过期，请重新登录", status_code=401)

    # 2. 撤销旧会话
    await db.execute(
        text("UPDATE auth_sessions SET status = 'revoked', revoked_at = :now "
             "WHERE id = :id"),
        {"id": session_id, "now": now_utc},
    )

    # 3. 查询用户当前角色（确保 JWT 载荷反映最新状态）
    user_result = await db.execute(
        text("SELECT role FROM users WHERE id = :user_id"),
        {"user_id": user_id},
    )
    user_row = user_result.first()
    user_role = user_row[0] if user_row else "admin"

    # 4. 创建新会话
    new_access_token = _create_jwt(user_id=user_id, role=user_role)
    new_refresh_token = _generate_refresh_token()
    new_refresh_hash = _hash_token(new_refresh_token)
    new_expires_in = shared_settings.auth_access_token_expire_minutes * 60
    refresh_expires = now_utc + timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS)
    import uuid
    new_session_id = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO auth_sessions (id, user_id, device_id, refresh_token_hash, "
             "status, expires_at, created_at) "
             "VALUES (:id, :user_id, :device_id, :token_hash, 'active', :expires_at, :created_at)"),
        {"id": new_session_id, "user_id": user_id, "device_id": None,
         "token_hash": new_refresh_hash, "expires_at": refresh_expires,
         "created_at": now_utc},
    )
    await db.flush()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": new_expires_in,
    }


async def logout_admin(db, refresh_token: str):
    """退出登录：撤销指定的 refresh_token。

    将 auth_sessions 中对应记录标记为 revoked。
    如果令牌不存在或已撤销，不报错（幂等操作）。
    """
    refresh_hash = _hash_token(refresh_token)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.execute(
        text("UPDATE auth_sessions SET status = 'revoked', revoked_at = :now "
             "WHERE refresh_token_hash = :token_hash AND status = 'active'"),
        {"token_hash": refresh_hash, "now": now_utc},
    )
    await db.flush()
    return {"logged_out": True}
