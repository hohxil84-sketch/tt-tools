"""
admin-billing ORM 模型。

定义 ai_capability、provider_model_capability 表，对齐 cloud/DATABASE_SCHEMA.md。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text,
    ForeignKey, UniqueConstraint, text,
)
from cloud.shared.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AiCapability(Base):
    """AI 能力表（替代硬编码 capability 字符串）。

    每个能力有唯一 code，调度时按 code 匹配。
    """

    __tablename__ = "ai_capability"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    code = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:
        return f"<AiCapability {self.code}>"


class ProviderModelCapability(Base):
    """Provider 模型 ↔ 能力 多对多关联表。

    替代原 provider_model_pricing.capability 单值字段。
    调度时通过此表匹配 capability。
    """

    __tablename__ = "provider_model_capability"
    __table_args__ = (
        UniqueConstraint("provider_model_id", "capability_id", name="uq_pmc_model_cap"),
    )

    id = Column(String(36), primary_key=True, default=_new_uuid)
    provider_model_id = Column(
        String(36),
        ForeignKey("provider_model_pricing.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    capability_id = Column(
        String(36),
        ForeignKey("ai_capability.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    def __repr__(self) -> str:
        return f"<ProviderModelCapability model={self.provider_model_id} cap={self.capability_id}>"
