"""
admin-audit ORM 模型。
"""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from cloud.shared.database import Base

def _new_uuid(): return str(uuid.uuid4())

class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    admin_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    admin_account: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"), index=True)

    __table_args__ = (
        Index("idx_audit_admin_user", "admin_user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_target", "target_type", "target_id"),
        Index("idx_audit_created", "created_at"),
    )
