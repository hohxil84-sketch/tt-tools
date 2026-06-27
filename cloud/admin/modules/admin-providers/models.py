"""
admin-providers ORM 模型。
"""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column
from cloud.shared.database import Base

def _new_uuid(): return str(uuid.uuid4())


class Provider(Base):
    """AI Provider 配置表。"""
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(String(500), nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    models_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
