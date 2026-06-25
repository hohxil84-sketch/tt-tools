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
    ).strftime("%Y-%m-%d %H:%M:%S")

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

def get_menu() -> MenuData:
    """获取后台导航菜单结构。

    定义后台左侧导航栏的详细菜单项，前端根据此数据渲染导航。
    包含仪表盘、用户管理、设备管理、套餐管理、订单管理、额度管理、
    AI 调用日志、成本统计、风控日志、功能开关等所有后台功能入口。

    Returns:
        MenuData 菜单结构数据
    """
    menu_items = [
        MenuItem(
            id="dashboard",
            title="仪表盘",
            icon="dashboard",
            path="/admin/dashboard",
        ),
        MenuItem(
            id="users",
            title="用户管理",
            icon="users",
            path="/admin/users",
            children=[
                MenuItem(
                    id="users-list",
                    title="用户列表",
                    icon="list",
                    path="/admin/users",
                ),
                MenuItem(
                    id="devices-list",
                    title="设备管理",
                    icon="devices",
                    path="/admin/devices",
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
                ),
                MenuItem(
                    id="orders",
                    title="订单管理",
                    icon="order",
                    path="/admin/orders",
                ),
                MenuItem(
                    id="credits-accounts",
                    title="额度账户",
                    icon="credits",
                    path="/admin/credits/accounts",
                ),
                MenuItem(
                    id="credits-ledger",
                    title="额度流水",
                    icon="ledger",
                    path="/admin/credits/ledger",
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
                ),
                MenuItem(
                    id="cost-stats",
                    title="成本统计",
                    icon="cost",
                    path="/admin/cost-stats",
                ),
                MenuItem(
                    id="risk-logs",
                    title="风控日志",
                    icon="risk",
                    path="/admin/risk-logs",
                ),
                MenuItem(
                    id="feature-flags",
                    title="功能开关",
                    icon="feature",
                    path="/admin/feature-flags",
                ),
            ],
        ),
    ]
    return MenuData(menu=menu_items)


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

import secrets  # noqa: E402
from datetime import datetime, timezone, timedelta  # noqa: E402

import bcrypt  # noqa: E402
from jose import jwt  # noqa: E402
from sqlalchemy import text  # noqa: E402 — 用原始 SQL 避免 ORM 类冲突

from cloud.shared.config import shared_settings  # noqa: E402
from cloud.shared import AppError, ErrorCode  # noqa: E402


def _verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码与 bcrypt 哈希。"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _create_jwt(user_id: str, role: str, plan_code: str) -> str:
    """创建 JWT access_token。"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "plan_code": plan_code,
        "iat": now,
        "exp": now + timedelta(minutes=shared_settings.auth_access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, shared_settings.auth_secret_key,
                      algorithm=shared_settings.auth_algorithm)


async def login_admin(db, account: str, password: str, device_fingerprint: str,
                      device_name: str = None, client_version: str = None):
    """管理员登录。

    直接使用原始 SQL 查询 users 表，避免 ORM 类注册冲突。
    """
    # 原始 SQL 查询用户
    result = await db.execute(
        text("SELECT id, account, password_hash, display_name, role, status, plan_code "
             "FROM users WHERE account = :account"),
        {"account": account},
    )
    row = result.first()
    if row is None:
        raise AppError(code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                       message="账号或密码错误", status_code=401)
    # row 是 tuple，按 SELECT 字段顺序
    (user_id, user_account, password_hash, display_name,
     role, status, plan_code) = row

    if status == "blocked":
        raise AppError(code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                       message="账号已被封禁", status_code=403)

    if not _verify_password(password, password_hash):
        raise AppError(code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                       message="账号或密码错误", status_code=401)

    access_token = _create_jwt(user_id=user_id, role=role,
                               plan_code=plan_code or "free")
    refresh_token = secrets.token_urlsafe(64)
    expires_in = shared_settings.auth_access_token_expire_minutes * 60

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": {
            "id": user_id,
            "account": user_account,
            "display_name": display_name,
            "plan_code": plan_code or "free",
        },
        "device": {
            "id": "",
            "status": "active",
            "is_new": True,
        },
    }


async def refresh_admin(db, refresh_token: str):
    """刷新令牌（暂未实现）。"""
    raise AppError(code="NOT_IMPLEMENTED",
                   message="令牌刷新功能暂未实现，请重新登录", status_code=501)


async def logout_admin(db, refresh_token: str):
    """退出登录（无服务端状态，客户端丢弃 token 即可）。"""
    return {"success": True}
