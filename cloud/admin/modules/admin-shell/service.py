"""
admin-shell 业务逻辑层。

提供仪表盘统计、导航菜单生成和服务状态查询。
当前阶段为骨架实现：仪表盘统计返回占位值，后续 admin-users、
admin-billing、admin-ops 模块完成后接入真实数据。
"""
from __future__ import annotations

import os
import time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from schemas import DashboardStats, MenuItem, MenuData, StatusData


# 服务启动时间（用于计算 uptime）
_SERVER_START_TIME: float = time.time()


# ============================================================
# 仪表盘统计
# ============================================================

async def get_dashboard_stats(db: Optional[AsyncSession] = None) -> DashboardStats:
    """获取后台仪表盘核心统计指标。

    当前为骨架实现：返回占位值 0。
    后续由 admin-users、admin-billing、admin-ops 模块接入真实数据库查询。

    Args:
        db: 数据库异步会话（预留，当前未使用）

    Returns:
        DashboardStats 统计指标
    """
    # 骨架实现：占位值，后续由对应后台模块注入真实查询
    # 预留 db 参数用于后续从 users、devices、orders 等表聚合统计
    _ = db  # 预留参数位

    return DashboardStats(
        users_total=0,
        orders_today=0,
        revenue_today_cents=0,
        active_devices=0,
        server_status="healthy",
    )


# ============================================================
# 导航菜单
# ============================================================

def get_menu() -> MenuData:
    """获取后台导航菜单结构。

    定义后台左侧导航栏的菜单项，前端根据此数据渲染导航。
    后续后台模块完成后，可在此追加新菜单项。

    Returns:
        MenuData 菜单结构数据
    """
    menu_items = [
        MenuItem(
            id="dashboard",
            title="首页仪表盘",
            icon="dashboard",
            path="/admin/dashboard",
        ),
        MenuItem(
            id="users",
            title="用户管理",
            icon="users",
            path="/admin/users",
        ),
        MenuItem(
            id="billing",
            title="计费管理",
            icon="billing",
            path="/admin/billing",
        ),
        MenuItem(
            id="ops",
            title="运维管理",
            icon="ops",
            path="/admin/ops",
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
