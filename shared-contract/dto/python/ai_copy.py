"""
ai_copy DTO — 云端文案生成 API 契约。

来源：shared-contract/openapi/ai-copy.yaml v0.1.0
生成方式：手写，以 OpenAPI 为唯一来源。

客户端不得提交 provider、model、estimated_cost、credits_charged 等字段。
"""
from __future__ import annotations

from typing import Literal, Optional

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
# 文案生成请求
# ============================================================


class AiCopyGenerateRequest(BaseModel):
    """
    云端文案生成请求。
    客户端不得提交 user_id、device_id、role、plan_code、
    provider、model、estimated_cost、credits_charged 等字段。
    """
    scene: str = Field(
        ...,
        description="使用场景（如 poster、social_media、email）",
    )
    product_name: str = Field(
        ...,
        description="产品名称（如 快印宣传单）",
    )
    selling_points: list[str] = Field(
        ...,
        description="产品卖点列表（如 ['当天取件', '高清印刷']）",
    )
    target_audience: Optional[str] = Field(
        None,
        description="目标受众（如 附近商户、学生群体）",
    )
    tone: str = Field(
        ...,
        description="文案语气（如 direct、professional、warm、humorous）",
    )
    platform: Optional[str] = Field(
        None,
        description="投放平台（如 offline_poster、wechat、xiaohongshu）",
    )
    extra_requirements: Optional[str] = Field(
        None,
        description="额外要求（如 突出开业活动、不超过 50 字）",
    )
    client_request_id: str = Field(
        ...,
        description="桌面端生成的请求追踪 ID，用于去重和幂等",
    )

    # 防御性校验：请求中不得包含客户端禁止提交字段
    model_config = {"extra": "forbid"}


# ============================================================
# 文案生成响应数据
# ============================================================


class AiCopyGenerateData(BaseModel):
    """
    云端文案生成结果数据。
    provider、model、estimated_cost、credits_charged 由云端决定，
    客户端只读展示，不得提交。
    """
    feature: Literal["ai_copy_cloud"] = Field(
        ...,
        description="功能码，固定为 ai_copy_cloud",
    )
    text: str = Field(
        ...,
        description="生成的主文案（如 开业大促，高清快印，当天取件！）",
    )
    variants: list[str] = Field(
        default_factory=list,
        description="生成的备选文案列表",
    )
    provider: str = Field(
        ...,
        description="实际调用的 AI Provider 名称（如 deepseek）",
    )
    model: str = Field(
        ...,
        description="实际使用的模型名称（如 deepseek-chat）",
    )
    estimated_cost: float = Field(
        ...,
        description="云端估算的调用成本（美元，仅供参考）",
    )
    credits_charged: int = Field(
        ...,
        description="本次调用实际扣除的 AI 额度",
    )
    provider_call_id: str = Field(
        ...,
        description="Provider 调用日志关联 ID（UUID）",
    )


# ============================================================
# 文案生成响应
# ============================================================


class AiCopyGenerateResponse(BaseModel):
    """
    云端文案生成 API 响应。
    遵循统一响应结构（success / data / error / request_id）。
    """
    success: bool = Field(..., description="请求是否成功")
    data: Optional[AiCopyGenerateData] = Field(
        None, description="文案生成结果，失败时为 null"
    )
    error: Optional[ErrorDetail] = Field(None, description="错误详情，成功时为 null")
    request_id: str = Field(..., description="云端生成的请求追踪 ID")
