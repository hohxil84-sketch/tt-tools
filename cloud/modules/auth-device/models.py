"""
cloud-auth-device ORM 数据模型。

定义 users、devices、auth_sessions 三张表的 SQLAlchemy 模型。
表结构对齐 cloud/DATABASE_SCHEMA.md。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# cloud-shared 公共层 ORM 基类
from cloud.shared.database import Base


def _utcnow() -> datetime:
    """获取当前 UTC 时间（naive，避免 asyncpg aware/naive 混用报错）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_uuid() -> str:
    """生成 UUID 字符串（主键用）。"""
    return str(uuid.uuid4())


class User(Base):
    """用户表，对齐 cloud/DATABASE_SCHEMA.md users 表定义。"""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    # 主键
    id = Column(String(36), primary_key=True, default=_new_uuid)
    # 登录账号（唯一）
    account = Column(String(255), unique=True, nullable=False, index=True)
    # 密码哈希，使用 bcrypt
    password_hash = Column(String(255), nullable=False)
    # 展示名称
    display_name = Column(String(100), nullable=True)
    # 用户角色：user / admin
    role = Column(String(50), nullable=False, default="user")
    # 用户状态：active / blocked / deleted
    status = Column(String(50), nullable=False, default="active", index=True)
    # 当前套餐编码
    plan_code = Column(String(50), nullable=False, default="free", index=True)
    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # 关联关系
    devices = relationship("Device", back_populates="user", lazy="dynamic")
    auth_sessions = relationship("AuthSession", back_populates="user", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, account={self.account})>"


class Device(Base):
    """设备表，对齐 cloud/DATABASE_SCHEMA.md devices 表定义。

    唯一约束：(user_id, device_fingerprint_hash) 确保同一用户同一设备只绑定一次。
    """

    __tablename__ = "devices"

    # 主键
    id = Column(String(36), primary_key=True, default=_new_uuid)
    # 所属用户
    user_id = Column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    # 设备指纹哈希（SHA-256）
    device_fingerprint_hash = Column(String(255), nullable=False)
    # 设备名称（客户端上报）
    device_name = Column(String(255), nullable=True)
    # 客户端版本
    client_version = Column(String(50), nullable=True)
    # 设备状态：active / blocked / removed
    status = Column(String(50), nullable=False, default="active", index=True)
    # 绑定时间
    bound_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    # 最近活跃时间
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # 复合唯一约束：同一用户同一设备指纹只保留一条记录
    __table_args__ = (
        UniqueConstraint("user_id", "device_fingerprint_hash", name="uq_user_device"),
        Index("idx_device_user_id", "user_id"),
        Index("idx_device_status", "status"),
        {"extend_existing": True},
    )

    # 关联关系
    user = relationship("User", back_populates="devices")

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, user_id={self.user_id}, name={self.device_name})>"


class AuthSession(Base):
    """认证会话表，对齐 cloud/DATABASE_SCHEMA.md auth_sessions 表定义。

    每次登录/刷新生成一条记录，refresh_token 哈希后存储。
    """

    __tablename__ = "auth_sessions"

    # 主键
    id = Column(String(36), primary_key=True, default=_new_uuid)
    # 所属用户
    user_id = Column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    # 关联设备
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=True)
    # refresh_token 的 SHA-256 哈希
    refresh_token_hash = Column(
        String(255), unique=True, nullable=False, index=True
    )
    # 会话状态：active / revoked / expired
    status = Column(String(50), nullable=False, default="active")
    # 过期时间
    expires_at = Column(DateTime(timezone=True), nullable=False)
    # 创建时间
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    # 撤销时间
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # 关联关系
    user = relationship("User", back_populates="auth_sessions")

    def __repr__(self) -> str:
        return f"<AuthSession(id={self.id}, user_id={self.user_id}, status={self.status})>"
