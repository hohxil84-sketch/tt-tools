"""
cloud-credits-billing ORM 数据模型。

定义 plans、credit_accounts、credit_ledger、usage_events 四张表的 SQLAlchemy 模型。
表结构对齐 cloud/DATABASE_SCHEMA.md。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    JSON,  # 使用通用 JSON 类型，兼容 PostgreSQL (JSONB) 和 SQLite (TEXT)
)
from sqlalchemy.orm import relationship

# cloud-shared 公共层 ORM 基类
from cloud.shared.database import Base


def _utcnow() -> datetime:
    """获取当前 UTC 时间。"""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    """生成 UUID 字符串（主键用）。"""
    return str(uuid.uuid4())


class Plan(Base):
    """套餐表，对齐 cloud/DATABASE_SCHEMA.md plans 表定义。

    存储套餐编码、名称、月赠额度和功能开关配置。
    enabled_features_json 为 JSON 字段，key 为功能码，value 为 bool 或 {"daily_limit": N}。
    """

    __tablename__ = "plans"

    # 主键
    id = Column(String(36), primary_key=True, default=_new_uuid)
    # 套餐名称（中文）
    name = Column(String(100), nullable=False)
    # 每周期赠送 AI 额度
    monthly_grant = Column(Integer, nullable=False, default=0)
    # 功能开关（JSON）：{"feature_code": true | {"daily_limit": N}}
    enabled_features_json = Column(JSON, nullable=False, default=dict)
    # 套餐状态：active / disabled
    status = Column(String(50), nullable=False, default="active")
    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:
        return f"<Plan(id={self.id}, name={self.name})>"


class CreditAccount(Base):
    """额度账户表，对齐 cloud/DATABASE_SCHEMA.md credit_accounts 表定义。

    每个用户只有一条额度账户记录（user_id 唯一约束）。
    存储当前套餐、余额、周期赠送信息。
    """

    __tablename__ = "credit_accounts"

    # 主键
    id = Column(String(36), primary_key=True, default=_new_uuid)
    # 用户 ID（唯一，一个用户一个额度账户）
    user_id = Column(
        String(36), ForeignKey("users.id"), unique=True, nullable=False, index=True
    )
    # 套餐外键 ID（→ plans.id）
    plan_id = Column(
        String(36), ForeignKey("plans.id"), nullable=True, index=True
    )
    # 当前 AI 额度余额（单位：次/点数，整数）
    balance = Column(Integer, nullable=False, default=0)
    # 周期赠送额度
    monthly_grant = Column(Integer, nullable=False, default=0)
    # 当前计费周期开始
    period_start = Column(DateTime(timezone=True), nullable=True)
    # 当前计费周期结束
    period_end = Column(DateTime(timezone=True), nullable=True)
    # 账户状态：active / frozen
    status = Column(String(50), nullable=False, default="active")
    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # 关联关系（User 模型在 auth-device 模块中，不在此定义反向关系）
    ledger_entries = relationship("CreditLedger", back_populates="account", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<CreditAccount(id={self.id}, user_id={self.user_id}, balance={self.balance})>"


class CreditLedger(Base):
    """额度流水表，对齐 cloud/DATABASE_SCHEMA.md credit_ledger 表定义。

    所有额度变化必须写入本表。
    change_type: grant（赠送）/ consume（消费）/ recharge（充值）/ refund（退款）/ adjust（调整）
    amount: 变化值，扣费为负数
    balance_after: 变化后余额
    """

    __tablename__ = "credit_ledger"

    # 主键
    id = Column(String(36), primary_key=True, default=_new_uuid)
    # 用户 ID
    user_id = Column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    # 额度账户 ID
    account_id = Column(
        String(36), ForeignKey("credit_accounts.id"), nullable=False, index=True
    )
    # 变化类型：grant / consume / recharge / refund / adjust
    change_type = Column(String(50), nullable=False)
    # 变化值（扣费为负数）
    amount = Column(Integer, nullable=False)
    # 变化后余额
    balance_after = Column(Integer, nullable=False)
    # 来源类型：provider_call / order / system / admin
    source_type = Column(String(50), nullable=False)
    # 来源 ID（可选）
    source_id = Column(String(36), nullable=True)
    # 中文说明
    description = Column(String(255), nullable=True)
    # 创建时间
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # 复合索引：(source_type, source_id)
    __table_args__ = (
        Index("idx_ledger_user_id", "user_id"),
        Index("idx_ledger_account_id", "account_id"),
        Index("idx_ledger_created_at", "created_at"),
        Index("idx_ledger_source", "source_type", "source_id"),
    )

    # 关联关系
    account = relationship("CreditAccount", back_populates="ledger_entries")

    def __repr__(self) -> str:
        return f"<CreditLedger(id={self.id}, change_type={self.change_type}, amount={self.amount})>"


class UsageEvent(Base):
    """使用事件表，对齐 cloud/DATABASE_SCHEMA.md usage_events 表定义。

    记录本地功能使用事件，用于免费套餐配额统计等。
    event_type: local_start / local_success / cloud_success / entitlement_granted
    """

    __tablename__ = "usage_events"

    # 主键
    id = Column(String(36), primary_key=True, default=_new_uuid)
    # 用户 ID
    user_id = Column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    # 设备 ID（可选）
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=True)
    # 功能码（字符串冗余缓存，过渡期保留，新代码优先使用 feature_code_id）
    feature = Column(String(100), nullable=True)
    # 功能码外键 ID（→ feature_codes.id）
    feature_code_id = Column(
        String(36), ForeignKey("feature_codes.id"), nullable=True, index=True
    )
    # 事件类型
    event_type = Column(String(100), nullable=False)
    # 请求 ID（可选）
    request_id = Column(String(100), nullable=True)
    # 脱敏元数据
    metadata_json = Column(JSON, nullable=False, default=dict)
    # 创建时间
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # 索引
    __table_args__ = (
        Index("idx_usage_events_user_id", "user_id"),
        Index("idx_usage_events_feature", "feature"),
        Index("idx_usage_events_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<UsageEvent(id={self.id}, feature={self.feature}, event_type={self.event_type})>"
