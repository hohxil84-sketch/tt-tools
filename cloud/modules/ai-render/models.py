"""
cloud-ai-render ORM 模型。

定义 ai_tasks 表的 SQLAlchemy ORM 模型，对齐 cloud/DATABASE_SCHEMA.md。
所有业务数据访问通过 raw SQL 执行（对齐 ai-copy 模式），
ORM 模型仅用于 DDL 建表和类型参考。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from cloud.shared.database import Base


def _new_uuid() -> str:
    """生成 UUID 主键。"""
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    """获取当前 UTC 时间。"""
    return datetime.now(timezone.utc)


class AiTask(Base):
    """AI 任务表 ORM 模型，对齐 DATABASE_SCHEMA.md ai_tasks。"""

    __tablename__ = "ai_tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid,
        comment="任务 ID"
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False,
        comment="用户 ID"
    )
    device_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("devices.id"), nullable=True,
        comment="设备 ID"
    )
    feature: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="功能码"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="queued / running / succeeded / failed"
    )
    input_json: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="脱敏输入（JSON 字符串）"
    )
    result_json: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="结果（JSON 字符串）"
    )
    provider_call_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("provider_call_log.id"), nullable=True,
        comment="Provider 调用 ID"
    )
    credits_charged: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="扣除额度"
    )
    error_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="错误码"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
        comment="更新时间"
    )
