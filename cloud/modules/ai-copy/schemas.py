"""
cloud-ai-copy Pydantic 请求/响应 DTO。

所有请求和响应结构对齐 shared-contract/openapi/ai-copy.yaml。
字段命名使用 snake_case，通过 Pydantic 序列化输出。
"""
from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel, Field


# ============================================================
# 请求 DTO（对齐 OpenAPI ai-copy.yaml AiCopyGenerateRequest）
# ============================================================


class AiCopyGenerateRequest(BaseModel):
    """AI 文案生成请求，对齐 ai-copy.yaml #/components/schemas/AiCopyGenerateRequest。

    客户端不得提交 user_id、provider、model、estimated_cost、credits_charged 等
    服务端决策字段（对齐 API_INDEX.md 全局规则）。
    """

    scene: str = Field(
        ..., description="使用场景，如 poster / social_post / ad_banner / flyer"
    )
    product_name: str = Field(..., description="产品/服务名称，如 '快印宣传单'")
    selling_points: List[str] = Field(..., description="卖点列表，如 ['当天取件', '高清印刷']")
    target_audience: Optional[str] = Field(
        default=None, description="目标受众，如 '附近商户'、'学生群体'"
    )
    tone: str = Field(
        ..., description="文案语气，如 direct / professional / friendly / urgent / elegant"
    )
    platform: Optional[str] = Field(
        default=None,
        description="投放平台，如 offline_poster / wechat / xiaohongshu / douyin",
    )
    extra_requirements: Optional[str] = Field(
        default=None, description="额外要求，如 '突出开业活动'、'强调优惠价格'"
    )
    client_request_id: str = Field(
        ..., description="桌面端生成的请求追踪 ID，用于去重和幂等"
    )


# ============================================================
# 响应 DTO（对齐 OpenAPI ai-copy.yaml AiCopyGenerateData）
# ============================================================


class AiCopyGenerateData(BaseModel):
    """AI 文案生成响应数据，对齐 ai-copy.yaml #/components/schemas/AiCopyGenerateData。

    feature 固定为 'ai_copy_cloud'。
    provider、model、estimated_cost、credits_charged、provider_call_id 由服务端决定。
    """

    feature: str = Field(
        default="ai_copy_cloud", description="功能码，固定为 ai_copy_cloud"
    )
    text: str = Field(..., description="生成的主文案")
    variants: List[str] = Field(
        default_factory=list, description="备选文案变体列表"
    )
    provider: str = Field(..., description="实际使用的 AI Provider 名称")
    model: str = Field(..., description="实际使用的模型名称")
    estimated_cost: float = Field(..., description="估算成本（人民币）")
    credits_charged: int = Field(..., description="实际扣除的 AI 额度")
    provider_call_id: str = Field(..., description="Provider 调用日志 ID（UUID）")


# ============================================================
# 服务层内部 DTO（不直接暴露给 API）
# ============================================================


class GenerateContext(BaseModel):
    """服务层内部使用的生成上下文，聚合鉴权和请求信息。

    用于在 service 层各步骤间传递信息，避免重复传入多个参数。
    """

    user_id: str = Field(..., description="用户 ID")
    device_id: Optional[str] = Field(default=None, description="设备 ID")
    role: str = Field(default="user", description="用户角色")
    plan_code: str = Field(default="free", description="当前套餐编码")
    request_id: str = Field(..., description="云端请求追踪 ID")
