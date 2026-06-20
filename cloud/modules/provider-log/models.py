"""
cloud-provider-log ORM 数据模型。

定义 provider_call_log 表的 SQLAlchemy 模型。
表结构对齐 cloud/DATABASE_SCHEMA.md provider_call_log 表定义。

写入边界（DATABASE_SCHEMA.md）：
    provider_call_log 只能由 Provider Runtime 或其封装服务写入。
    本模块提供写入函数供 provider-runtime / AI 模块调用。
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
    Numeric,
    JSON,  # 兼容 PostgreSQL JSONB 和 SQLite TEXT
)

# cloud-shared 公共层 ORM 基类
from cloud.shared.database import Base


def _utcnow() -> datetime:
    """获取当前 UTC 时间。"""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    """生成 UUID 字符串（主键用）。"""
    return str(uuid.uuid4())


class ProviderCallLog(Base):
    """Provider 调用日志表，对齐 cloud/DATABASE_SCHEMA.md provider_call_log 表定义。

    记录每次 AI Provider 调用的核心信息。
    不得返回完整 prompt、API Key、Token、原图等隐私内容给客户端。

    字段说明：
    - id: 调用日志唯一 UUID
    - request_id: 请求追踪 ID（unique），用于全链路追踪
    - user_id: 用户 ID（FK users.id）
    - device_id: 设备 ID（FK devices.id，可选）
    - feature: 功能码（如 ai_copy_cloud、ai_render_cloud）
    - provider: Provider 名称（如 openai、deepseek）
    - model: 模型名称（如 gpt-4o、deepseek-chat）
    - status: 调用状态（success / failed / timeout）
    - error_code: 失败时的统一错误码，成功时为 null
    - input_tokens / output_tokens / total_tokens: token 用量统计
    - reasoning_tokens / cached_tokens: 推理和缓存 token（仅服务端使用）
    - image_count: 处理的图片数量
    - estimated_cost: 估算成本（人民币，仅供参考）
    - credits_charged: 实际扣除的 AI 额度
    - latency_ms: 调用延迟（毫秒）
    - raw_usage_json: Provider 原始 usage JSON（仅服务端使用，不返回客户端）
    - raw_meta_json: 脱敏元数据（仅服务端使用）
    - created_at: 调用发生时间（UTC）
    """

    __tablename__ = "provider_call_log"

    # 主键
    id = Column(String(36), primary_key=True, default=_new_uuid)

    # 请求追踪 ID（唯一，用于全链路追踪）
    request_id = Column(String(100), unique=True, nullable=False)

    # 用户 ID
    user_id = Column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )

    # 设备 ID（可选）
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=True)

    # 功能码
    feature = Column(String(100), nullable=False)

    # Provider 名称
    provider = Column(String(100), nullable=False)

    # 模型名称
    model = Column(String(100), nullable=False)

    # 调用状态：success / failed / timeout
    status = Column(String(50), nullable=False)

    # 统一错误码（成功时为 null）
    error_code = Column(String(100), nullable=True)

    # -- Token 用量统计 --
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    reasoning_tokens = Column(Integer, nullable=False, default=0)
    cached_tokens = Column(Integer, nullable=False, default=0)

    # 图片数量
    image_count = Column(Integer, nullable=False, default=0)

    # 估算成本（使用 Numeric 避免浮点精度问题）
    estimated_cost = Column(Numeric(18, 6), nullable=False, default=0)

    # 扣除额度
    credits_charged = Column(Integer, nullable=False, default=0)

    # 调用延迟（毫秒）
    latency_ms = Column(Integer, nullable=True)

    # Provider 原始 usage JSON（仅服务端使用，不返回客户端）
    raw_usage_json = Column(JSON, nullable=True)

    # 脱敏元数据
    raw_meta_json = Column(JSON, nullable=True)

    # 创建时间（UTC）
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # 索引：对齐 DATABASE_SCHEMA.md 定义的 user_id、feature、provider、status、created_at
    __table_args__ = (
        Index("idx_pcl_request_id", "request_id"),
        Index("idx_pcl_user_id", "user_id"),
        Index("idx_pcl_feature", "feature"),
        Index("idx_pcl_provider", "provider"),
        Index("idx_pcl_status", "status"),
        Index("idx_pcl_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProviderCallLog(id={self.id}, feature={self.feature}, "
            f"provider={self.provider}, status={self.status})>"
        )
