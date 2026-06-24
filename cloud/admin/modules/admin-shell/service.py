"""
admin-shell 业务逻辑层。

提供仪表盘统计、导航菜单生成和服务状态查询。
当前阶段为骨架实现：仪表盘统计返回占位值，后续 admin-users、
admin-billing、admin-ops 模块完成后接入真实数据。
"""
from __future__ import annotations

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
