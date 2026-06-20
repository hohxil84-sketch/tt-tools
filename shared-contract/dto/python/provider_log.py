"""
provider_log DTO — Provider 调用日志查询。

来源：shared-contract/openapi/provider-log.yaml v0.1.0
生成方式：手写，以 OpenAPI 为唯一来源。

不得返回完整 prompt、原图、API Key、Token、完整隐私内容。
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 通用结构
# ============================================================


class ErrorDetail(BaseModel):
    """统一错误详情结构，与 common.yaml 保持一致"""
    code: str = Field(..., description="统一错误码")
    message: str = Field(..., description="人类可读的错误描述（中文）")
    details: Optional[dict] = Field(None, description="可选补充信息")


# ============================================================
# Provider 调用日志条目
# ============================================================


class ProviderCallLogItem(BaseModel):
    """
    Provider 调用日志条目，记录单次 AI Provider 调用的核心信息。
    不得包含完整 prompt、原图、API Key、Token、完整隐私内容。
    """
    id: str = Field(..., description="调用日志唯一 ID（UUID）")
    request_id: str = Field(..., description="请求追踪 ID，用于全链路追踪")
    feature: str = Field(
        ...,
        description="功能码（如 ai_copy_cloud、ai_render_cloud、ai_image_tools_cloud）",
    )
    provider: str = Field(
        ...,
        description="AI Provider 名称（如 openai、deepseek、qwen）",
    )
    model: str = Field(
        ...,
        description="使用的模型名称（如 gpt-4o、deepseek-chat）",
    )
    status: str = Field(
        ...,
        description="调用状态（success / failed / timeout）",
    )
    error_code: Optional[str] = Field(
        None,
        description="失败时的统一错误码（如 PROVIDER_TIMEOUT），成功时为 null",
    )
    input_tokens: int = Field(..., description="输入 token 数量")
    output_tokens: int = Field(..., description="输出 token 数量")
    total_tokens: int = Field(..., description="总 token 数量（input + output）")
    estimated_cost: float = Field(
        ...,
        description="云端估算的调用成本（美元，仅供参考）",
    )
    credits_charged: int = Field(..., description="本次调用实际扣除的 AI 额度")
    latency_ms: Optional[int] = Field(
        None,
        description="调用延迟（毫秒），超时时可能为 null",
    )
    created_at: str = Field(..., description="调用发生时间（UTC，ISO 8601 格式）")


# ============================================================
# 分页列表响应
# ============================================================


class ProviderCallLogListData(BaseModel):
    """Provider 调用日志分页列表数据"""
    items: list[ProviderCallLogItem] = Field(
        default_factory=list,
        description="当前页的调用日志条目列表",
    )
    total: int = Field(..., description="符合条件的总记录数")
    limit: int = Field(..., description="当前每页条数")
    offset: int = Field(..., description="当前偏移量")


class ProviderCallLogListResponse(BaseModel):
    """
    Provider 调用日志查询响应。
    遵循统一响应结构（success / data / error / request_id）。
    """
    success: bool = Field(..., description="请求是否成功")
    data: Optional[ProviderCallLogListData] = Field(
        None, description="成功时返回分页列表数据，失败时为 null"
    )
    error: Optional[ErrorDetail] = Field(None, description="错误详情，成功时为 null")
    request_id: str = Field(..., description="云端生成的请求追踪 ID")
