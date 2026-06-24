"""
admin-ops SQLAlchemy ORM 模型。

定义 risk_logs 表的 SQLAlchemy 模型。
表结构对齐 cloud/DATABASE_SCHEMA.md risk_logs 表定义。

ProviderCallLog、Plan、User 模型通过跨模块 importlib 加载使用，
不在本模块中重复定义。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

# cloud-shared 公共层 ORM 基类
from cloud.shared.database import Base


def _utcnow() -> datetime:
    """获取当前 UTC 时间（不含时区信息，兼容数据库存储）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_uuid() -> str:
    """生成 UUID 字符串（主键用）。"""
    return str(uuid.uuid4())


class RiskLog(Base):
    """风控日志表，对齐 cloud/DATABASE_SCHEMA.md risk_logs 表定义。

    记录系统中触发的风控事件，包括风险类型、严重程度和脱敏详情。

    字段说明：
    - id: 风控日志唯一 UUID
    - user_id: 用户 ID（FK users.id，可选，匿名事件可为空）
    - device_id: 设备 ID（FK devices.id，可选）
    - risk_type: 风险类型（如 suspicious_login / rate_limit / abnormal_usage）
    - severity: 严重程度（low / medium / high）
    - details_json: 脱敏详情（JSON 对象，不包含敏感原始数据）
    - created_at: 记录时间（UTC）
    """

    __tablename__ = "risk_logs"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),  # UUID 字符串（兼容 SQLite/PostgreSQL）
        primary_key=True,
        default=_new_uuid,
    )

    # 用户 ID（可选，匿名事件可为空）
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )

    # 设备 ID（可选）
    device_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("devices.id"), nullable=True
    )

    # 风险类型（如 suspicious_login / rate_limit / abnormal_usage）
    risk_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # 严重程度：low / medium / high
    severity: Mapped[str] = mapped_column(String(50), nullable=False)

    # 脱敏详情（JSON 对象）
    details_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )

    # 创建时间（UTC）
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )

    # 索引：对齐 DATABASE_SCHEMA.md
    __table_args__ = (
        Index("idx_risk_logs_user_id", "user_id"),
        Index("idx_risk_logs_risk_type", "risk_type"),
        Index("idx_risk_logs_severity", "severity"),
        Index("idx_risk_logs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<RiskLog(id={self.id}, risk_type={self.risk_type}, "
            f"severity={self.severity})>"
        )
