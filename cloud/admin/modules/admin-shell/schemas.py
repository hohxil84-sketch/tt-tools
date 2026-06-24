"""
admin-shell Pydantic 请求/响应 DTO。

所有响应结构对齐 shared-contract/openapi/admin-shell.yaml。
字段命名使用 snake_case，通过 Pydantic 序列化为 JSON 时使用 snake_case。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 仪表盘统计
# ============================================================

class DashboardStats(BaseModel):
    """后台仪表盘核心统计指标，对齐 admin-shell.yaml DashboardStats。"""

    users_total: int = Field(..., description="系统总用户数")
    orders_today: int = Field(..., description="今日订单数")
    revenue_today_cents: int = Field(..., description="今日收入（单位：分）")
    active_devices: int = Field(..., description="当前活跃设备数")
    server_status: str = Field(..., description="服务健康状态：healthy / degraded / down")


# ============================================================
# 导航菜单
# ============================================================

class MenuItem(BaseModel):
    """后台导航菜单项，对齐 admin-shell.yaml MenuItem。

    支持嵌套子菜单：children 字段可包含子 MenuItem 列表。
    """

    id: str = Field(..., description="菜单项唯一标识")
    title: str = Field(..., description="菜单项中文标题")
    icon: str = Field(..., description="菜单项图标标识")
    path: str = Field(..., description="菜单项对应页面路径")
    children: Optional[list["MenuItem"]] = Field(
        default=None, description="子菜单项列表"
    )


class MenuData(BaseModel):
    """后台导航菜单数据，对齐 admin-shell.yaml MenuData。"""

    menu: list[MenuItem] = Field(..., description="顶级菜单项列表")


# ============================================================
# 服务状态
# ============================================================

class StatusData(BaseModel):
    """服务运行状态，对齐 admin-shell.yaml StatusData。"""

    status: str = Field(..., description="服务健康状态：healthy / degraded / down")
    version: str = Field(..., description="服务版本号")
    uptime_seconds: float = Field(..., description="服务运行时长（秒）")
