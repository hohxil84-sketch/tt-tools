"""
admin-ops Pydantic 请求/响应 DTO。

所有响应结构对齐 shared-contract/openapi/admin-ops.yaml。
字段命名使用 snake_case，通过 Pydantic 序列化为 JSON。

规则：
- 不返回 raw_usage_json、raw_meta_json、reasoning_tokens、cached_tokens、
  image_count 等仅服务端使用的字段。
- 不返回完整 prompt、API Key、Token、原图等隐私内容。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


# ============================================================
# Provider 调用日志 DTO（管理员视图）
# ============================================================


class AdminProviderCallLogItem(BaseModel):
    """管理员 Provider 调用日志列表项（含用户账号）。

    对齐 admin-ops.yaml AdminProviderCallLogItem。
    不返回 raw_usage_json、raw_meta_json 等服务端字段。
    """

    id: str = Field(..., description="调用日志 ID（UUID）")
    request_id: str = Field(..., description="请求追踪 ID")
    user_id: str = Field(..., description="用户 ID")
    user_account: Optional[str] = Field(default=None, description="用户账号")
    feature: str = Field(..., description="功能码")
    feature_name: Optional[str] = Field(default=None, description="功能中文名（从 feature_codes 表关联查询）")
    provider: str = Field(..., description="Provider 名称")
    model: str = Field(..., description="模型名称")
    status: str = Field(..., description="调用状态：success / failed / timeout")
    error_code: Optional[str] = Field(default=None, description="失败时的错误码")
    input_tokens: int = Field(..., description="输入 token 数")
    output_tokens: int = Field(..., description="输出 token 数")
    total_tokens: int = Field(..., description="总 token 数")
    estimated_cost: float = Field(..., description="估算成本（人民币）")
    credits_charged: int = Field(..., description="扣除额度")
    latency_ms: Optional[int] = Field(default=None, description="调用延迟（毫秒）")
    created_at: datetime = Field(..., description="调用时间")


class AdminProviderCallLogDetail(BaseModel):
    """管理员 Provider 调用日志详情（含用户展示名称）。

    对齐 admin-ops.yaml AdminProviderCallLogDetail。
    """

    id: str = Field(..., description="调用日志 ID（UUID）")
    request_id: str = Field(..., description="请求追踪 ID")
    user_id: str = Field(..., description="用户 ID")
    user_account: Optional[str] = Field(default=None, description="用户账号")
    user_display_name: Optional[str] = Field(default=None, description="用户展示名称")
    feature: str = Field(..., description="功能码")
    feature_name: Optional[str] = Field(default=None, description="功能中文名（从 feature_codes 表关联查询）")
    provider: str = Field(..., description="Provider 名称")
    model: str = Field(..., description="模型名称")
    status: str = Field(..., description="调用状态")
    error_code: Optional[str] = Field(default=None, description="错误码")
    input_tokens: int = Field(..., description="输入 token 数")
    output_tokens: int = Field(..., description="输出 token 数")
    total_tokens: int = Field(..., description="总 token 数")
    estimated_cost: float = Field(..., description="估算成本（人民币）")
    credits_charged: int = Field(..., description="扣除额度")
    latency_ms: Optional[int] = Field(default=None, description="调用延迟（毫秒）")
    created_at: datetime = Field(..., description="调用时间")


class AdminProviderCallLogListData(BaseModel):
    """管理员 Provider 调用日志列表分页响应数据。

    对齐 admin-ops.yaml AdminProviderCallLogListData。
    """

    items: list[AdminProviderCallLogItem] = Field(
        default_factory=list, description="调用日志列表"
    )
    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="每页条数")
    offset: int = Field(..., description="当前偏移量")


# ============================================================
# 成本统计 DTO
# ============================================================


class CostBreakdownItem(BaseModel):
    """按维度的成本细分统计。

    对齐 admin-ops.yaml CostBreakdownItem。
    """

    key: str = Field(..., description="维度值（功能码或 Provider 名称）")
    key_name: Optional[str] = Field(default=None, description="维度值的中文名（仅 by_feature 时有值）")
    calls: int = Field(..., description="调用次数")
    total_tokens: int = Field(..., description="总 token 数")
    total_cost: float = Field(..., description="总估算成本")
    total_credits: int = Field(..., description="总扣除额度")


class CostStatsData(BaseModel):
    """成本/用量聚合统计数据。

    对齐 admin-ops.yaml CostStatsData。
    """

    total_calls: int = Field(..., description="总 Provider 调用次数")
    total_tokens: int = Field(..., description="总 token 用量")
    total_cost: float = Field(..., description="总估算成本（人民币）")
    total_credits_charged: int = Field(..., description="总扣除 AI 额度")
    by_feature: list[CostBreakdownItem] = Field(
        default_factory=list, description="按功能码细分统计"
    )
    by_provider: list[CostBreakdownItem] = Field(
        default_factory=list, description="按 Provider 细分统计"
    )


# ============================================================
# 风控日志 DTO
# ============================================================


class RiskLogItem(BaseModel):
    """风控日志列表项。

    对齐 admin-ops.yaml RiskLogItem。
    """

    id: str = Field(..., description="风控日志 ID（UUID）")
    user_id: Optional[str] = Field(default=None, description="用户 ID")
    user_account: Optional[str] = Field(default=None, description="用户账号")
    device_id: Optional[str] = Field(default=None, description="设备 ID")
    device_name: Optional[str] = Field(default=None, description="设备名称（从 devices 表关联查询）")
    risk_type: str = Field(..., description="风险类型")
    severity: str = Field(..., description="严重程度：low / medium / high")
    created_at: datetime = Field(..., description="记录时间")


class RiskLogDetail(BaseModel):
    """风控日志详情（含脱敏详情和用户信息）。

    对齐 admin-ops.yaml RiskLogDetail。
    """

    id: str = Field(..., description="风控日志 ID（UUID）")
    user_id: Optional[str] = Field(default=None, description="用户 ID")
    user_account: Optional[str] = Field(default=None, description="用户账号")
    user_display_name: Optional[str] = Field(default=None, description="用户展示名称")
    device_id: Optional[str] = Field(default=None, description="设备 ID")
    device_name: Optional[str] = Field(default=None, description="设备名称（从 devices 表关联查询）")
    risk_type: str = Field(..., description="风险类型")
    severity: str = Field(..., description="严重程度")
    details_json: dict[str, Any] = Field(
        default_factory=dict, description="脱敏详情"
    )
    created_at: datetime = Field(..., description="记录时间")


class RiskLogListData(BaseModel):
    """风控日志列表分页响应数据。

    对齐 admin-ops.yaml RiskLogListData。
    """

    items: list[RiskLogItem] = Field(
        default_factory=list, description="风控日志列表"
    )
    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="每页条数")
    offset: int = Field(..., description="当前偏移量")


# ============================================================
# 功能开关 DTO
# ============================================================


class PlanFeatureFlagsItem(BaseModel):
    """套餐功能开关配置项。

    对齐 admin-ops.yaml PlanFeatureFlagsItem。
    """

    plan_id: str = Field(..., description="套餐 ID（UUID）")
    plan_name: str = Field(..., description="套餐名称")
    enabled_features_json: dict[str, Any] = Field(
        default_factory=dict, description="功能开关配置"
    )
    plan_status: str = Field(..., description="套餐状态：active / disabled")


class FeatureFlagsListData(BaseModel):
    """功能开关配置列表响应数据。

    对齐 admin-ops.yaml FeatureFlagsListData。
    """

    items: list[PlanFeatureFlagsItem] = Field(
        default_factory=list, description="各套餐功能开关配置列表"
    )


class UpdateFeatureFlagsRequest(BaseModel):
    """更新功能开关请求（合并更新）。

    对齐 admin-ops.yaml UpdateFeatureFlagsRequest。
    只更新传入的 key，未传入的 key 保持原值不变。
    """

    enabled_features_json: dict[str, Any] = Field(
        ..., description="功能开关配置（合并到现有配置）"
    )
