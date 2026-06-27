"""
cloud-credits-billing Pydantic 请求/响应 DTO。

所有请求和响应结构对齐 shared-contract/openapi/credits-billing.yaml
和 shared-contract/openapi/local-paid-tools.yaml。
字段命名使用 snake_case，通过 Pydantic 序列化输出。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ============================================================
# 请求 DTO（对齐 OpenAPI requestBody schemas）
# ============================================================


class EntitlementCheckRequest(BaseModel):
    """本地付费功能套餐权限检查请求。

    对齐 credits-billing.yaml #/components/schemas/EntitlementCheckRequest
    和 local-paid-tools.yaml #/components/schemas/LocalPaidToolEntitlementRequest。
    """

    feature: str = Field(..., description="本地付费功能码，如 resize_image_local_paid")
    operation: str = Field(..., description="操作类型：single / batch")
    client_request_id: str = Field(
        ..., description="桌面端生成的请求追踪 ID，用于去重和幂等"
    )


# ============================================================
# 响应 DTO（对齐 OpenAPI 内嵌对象 schemas）
# ============================================================


class CreditBalanceData(BaseModel):
    """额度余额数据，对齐 credits-billing.yaml #/components/schemas/CreditBalance。"""

    user_id: str = Field(..., description="用户 ID（UUID）")
    plan_id: str = Field(..., description="当前套餐 ID（UUID）")
    monthly_grant: int = Field(..., description="周期赠送额度")
    balance: int = Field(..., description="当前 AI 额度余额")
    period_start: Optional[datetime] = Field(default=None, description="周期开始时间")
    period_end: Optional[datetime] = Field(default=None, description="周期结束时间")
    status: str = Field(..., description="账户状态：active / frozen")
    updated_at: datetime = Field(..., description="最后更新时间")


class CreditLedgerItem(BaseModel):
    """额度流水明细，对齐 credits-billing.yaml #/components/schemas/CreditLedgerItem。"""

    id: str = Field(..., description="流水 ID（UUID）")
    change_type: str = Field(..., description="变化类型：grant / consume / recharge / refund / adjust")
    amount: int = Field(..., description="变化值（扣费为负数）")
    balance_after: int = Field(..., description="变化后余额")
    source_type: str = Field(..., description="来源类型：provider_call / order / system / admin")
    source_id: Optional[str] = Field(default=None, description="来源 ID（UUID）")
    description: Optional[str] = Field(default=None, description="中文说明")
    created_at: datetime = Field(..., description="创建时间")


class CreditLedgerListData(BaseModel):
    """额度流水列表，对齐 credits-billing.yaml #/components/schemas/CreditLedgerData。"""

    items: List[CreditLedgerItem] = Field(default_factory=list, description="流水明细列表")
    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="每页条数")
    offset: int = Field(..., description="当前偏移量")


class EntitlementCheckData(BaseModel):
    """权限检查结果，对齐 credits-billing.yaml #/components/schemas/EntitlementCheckData。"""

    allowed: bool = Field(..., description="是否允许使用指定功能")
    feature: str = Field(..., description="检查的功能码")
    plan_id: str = Field(..., description="用户当前套餐 ID（UUID）")
    remaining_free_quota: Optional[int] = Field(
        default=None, description="免费套餐剩余免费使用次数（仅 free 套餐返回）"
    )
    reason: Optional[str] = Field(
        default=None, description="不允许时的拒绝原因（中文）"
    )
