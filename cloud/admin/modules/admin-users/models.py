"""
admin-users SQLAlchemy ORM 模型。

为避免与 auth-device 模块的 User/Device 类在 SQLAlchemy Base 注册表中同名冲突，
本模块将类名重命名为 UserAdmin / DeviceAdmin，映射到相同的 users / devices 表。

对齐 cloud/DATABASE_SCHEMA.md。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cloud.shared import Base


def _utcnow() -> datetime:
    """返回当前 UTC 时间（不含时区信息，适合数据库存储）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ============================================================
# 用户模型（更名为 UserAdmin，避免与 auth-device 的 User 冲突）
# ============================================================


class UserAdmin(Base):
    """用户表模型，对齐 DATABASE_SCHEMA.md users 表。

    类名使用 UserAdmin 而非 User，避免与 auth-device/models.py 中的 User 类
    在 SQLAlchemy 声明式基类注册表中同名冲突。
    """

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    # 登录账号
    account: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    # 密码哈希（管理端不返回此字段）
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # 展示名称
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 用户角色：user / admin
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    # 用户状态：active / blocked / deleted
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    # 是否启用（软删除标记，统一列表过滤）
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 套餐外键 ID（→ plans.id）
    plan_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("plans.id"), nullable=True
    )
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    # 关联设备（一对多）
    devices: Mapped[list["DeviceAdmin"]] = relationship(
        "DeviceAdmin", back_populates="user", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<UserAdmin id={self.id} account={self.account} role={self.role}>"


# ============================================================
# 设备模型（更名为 DeviceAdmin，避免与 auth-device 的 Device 冲突）
# ============================================================


class DeviceAdmin(Base):
    """设备表模型，对齐 DATABASE_SCHEMA.md devices 表。

    类名使用 DeviceAdmin 而非 Device，避免与 auth-device/models.py 中的 Device 类
    在 SQLAlchemy 声明式基类注册表中同名冲突。
    """

    __tablename__ = "devices"
    __table_args__ = {"extend_existing": True}

    # 主键
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # 所属用户 ID（外键）
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    # 设备指纹哈希
    device_fingerprint_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    # 设备名称
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 客户端版本
    client_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 设备状态：active / blocked / removed
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    # 是否启用（软删除标记，统一列表过滤）
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 绑定时间
    bound_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    # 最近活跃时间
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    # 关联用户（多对一）
    user: Mapped["UserAdmin"] = relationship("UserAdmin", back_populates="devices")

    def __repr__(self) -> str:
        return f"<DeviceAdmin id={self.id} user_id={self.user_id} name={self.device_name}>"
