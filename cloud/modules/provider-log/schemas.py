"""
cloud-provider-log Pydantic 请求/响应 DTO。

所有响应结构对齐 shared-contract/openapi/provider-log.yaml。
字段命名使用 snake_case，通过 Pydantic 序列化输出（mode="json" 时自动转为 camelCase
需在 model_config 中设置 alias_generator）。

规则：
    - 不得返回 raw_usage_json、raw_meta_json、reasoning_tokens、cached_tokens、image_count
      等仅服务端使用的字段。
    - 不得返回完整 prompt、API Key、Token、原图等隐私内容。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ============================================================
# Provider 调用日志写入请求（内部使用，非 API 端点直接暴露）
# ============================================================


class WriteProviderCallLogRequest(BaseModel):
    """Provider 调用日志写入请求（内部 DTO）。

    由 provider-runtime 或上层 AI 模块在调用完成后构造，
    调用本模块 service 层的 write_provider_call_log() 写入数据库。

    字段映射自 provider-runtime 的 ProviderResult 结构。
    """

    request_id: str = Field(..., description="云端请求追踪 ID")
    feature: str = Field(..., description="功能码，如 ai_copy_cloud")
    provider: str = Field(..., description="Provider 名称，如 deepseek、openai")
    model: str = Field(..., description="模型名称，如 deepseek-chat、gpt-4o")
    status: str = Field(..., description="调用状态：success / failed / timeout")
    error_code: Optional[str] = Field(default=None, description="失败时的统一错误码")
    input_tokens: int = Field(default=0, description="输入 token 数")
    output_tokens: int = Field(default=0, description="输出 token 数")
    total_tokens: int = Field(default=0, description="总 token 数")
    reasoning_tokens: int = Field(default=0, description="推理 token 数（仅服务端）")
    cached_tokens: int = Field(default=0, description="缓存命中 token 数（仅服务端）")
    image_count: int = Field(default=0, description="处理的图片数量（仅服务端）")
    estimated_cost: float = Field(default=0.0, description="估算成本（人民币）")
    credits_charged: int = Field(default=0, description="扣除的 AI 额度")
    latency_ms: Optional[int] = Field(default=None, description="调用延迟（毫秒）")
    raw_usage_json: Optional[dict] = Field(
        default=None, description="Provider 原始 usage JSON（仅服务端）"
    )
    raw_meta_json: Optional[dict] = Field(
        default=None, description="脱敏元数据（仅服务端）"
    )


# ============================================================
# 响应 DTO（对齐 OpenAPI provider-log.yaml）
# ============================================================


class ProviderCallLogItem(BaseModel):
    """Provider 调用日志条目，对齐 provider-log.yaml #/components/schemas/ProviderCallLogItem。

    仅返回客户端可见字段，不包含：
    - raw_usage_json（Provider 原始 usage）
    - raw_meta_json（脱敏元数据）
    - reasoning_tokens（推理 token）
    - cached_tokens（缓存 token）
    - image_count（图片数量）
    - 完整 prompt、API Key、Token、原图
    """

    id: str = Field(..., description="调用日志唯一 ID（UUID）")
    request_id: str = Field(..., description="请求追踪 ID")
    feature: str = Field(..., description="功能码")
    provider: str = Field(..., description="AI Provider 名称")
    model: str = Field(..., description="使用的模型名称")
    status: str = Field(..., description="调用状态：success / failed / timeout")
    error_code: Optional[str] = Field(default=None, description="失败时的统一错误码")
    input_tokens: int = Field(..., description="输入 token 数量")
    output_tokens: int = Field(..., description="输出 token 数量")
    total_tokens: int = Field(..., description="总 token 数量")
    estimated_cost: float = Field(..., description="估算成本（人民币，仅供参考）")
    credits_charged: int = Field(..., description="实际扣除的 AI 额度")
    latency_ms: Optional[int] = Field(default=None, description="调用延迟（毫秒）")
    created_at: datetime = Field(..., description="调用发生时间（UTC）")


class ProviderCallLogListData(BaseModel):
    """Provider 调用日志分页列表数据，对齐 provider-log.yaml #/components/schemas/ProviderCallLogListData。"""

    items: List[ProviderCallLogItem] = Field(
        default_factory=list, description="当前页的调用日志条目列表"
    )
    total: int = Field(..., description="符合条件的总记录数")
    limit: int = Field(..., description="当前每页条数")
    offset: int = Field(..., description="当前偏移量")
