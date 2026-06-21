"""
cloud-orders-recharge ORM 数据模型。

定义 orders 表的 SQLAlchemy 模型，对齐 cloud/DATABASE_SCHEMA.md orders 表定义。
表字段、类型、约束逐列一致。
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
    Index,
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


class Order(Base):
    """订单表，对齐 cloud/DATABASE_SCHEMA.md orders 表定义。

    存储订单信息，包含订单号、类型、产品编码、金额、状态等。
    金额字段统一使用整数分（amount_cents），不做浮点运算。

    order_type: plan（套餐购买）/ credits（额度充值）
    product_code: 具体产品编码（standard / pro / credits_100 / credits_500 / credits_2000）
    status: pending → paid（确认支付）/ closed（取消）/ refunded（退款）
    """

    __tablename__ = "orders"

    # 主键
    id = Column(String(36), primary_key=True, default=_new_uuid)
    # 用户 ID
    user_id = Column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    # 订单号（唯一，服务端生成：ORD-YYYYMMDD-xxxxxxxx）
    order_no = Column(String(100), unique=True, nullable=False)
    # 订单类型：plan / credits
    order_type = Column(String(50), nullable=False)
    # 具体产品编码
    product_code = Column(String(100), nullable=False)
    # 订单金额（单位：分）
    amount_cents = Column(Integer, nullable=False)
    # 充值额度数量（仅 order_type=credits 时有值）
    credit_amount = Column(Integer, nullable=True)
    # 币种
    currency = Column(String(20), nullable=False, default="CNY")
    # 订单状态：pending / paid / closed / refunded
    status = Column(String(50), nullable=False, default="pending")
    # 支付时间
    paid_at = Column(DateTime(timezone=True), nullable=True)
    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # 复合索引
    __table_args__ = (
        Index("idx_orders_user_id", "user_id"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Order(id={self.id}, order_no={self.order_no}, "
            f"order_type={self.order_type}, status={self.status}, "
            f"amount_cents={self.amount_cents})>"
        )
