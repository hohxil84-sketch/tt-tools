"""
credits_billing DTO — 套餐权限、额度余额、额度流水。

来源：shared-contract/openapi/credits-billing.yaml v0.1.0
生成方式：手写，以 OpenAPI 为唯一来源。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# 枚举
# ============================================================


class ChangeType(str, Enum):
    """额度变动类型"""
    grant = "grant"        # 周期赠送
    consume = "consume"    # 消费扣费
    recharge = "recharge"  # 充值
    refund = "refund"      # 退款
    adjust = "adjust"      # 管理员调整


# ============================================================
# 通用结构
# ============================================================


class ErrorDetail(BaseModel):
    """统一错误详情"""
    code: str = Field(..., description="统一错误码")
    message: str = Field(..., description="人类可读的错误描述（中文）")
    details: Optional[dict] = Field(None, description="可选补充信息")


TData = TypeVar("TData")


class ApiResponse(BaseModel, Generic[TData]):
    """统一 API 响应外层"""
    success: bool = Field(..., description="请求是否成功")
    data: Optional[TData] = Field(None, description="业务数据载荷")
    error: Optional[ErrorDetail] = Field(None, description="错误详情")
    request_id: str = Field(..., description="云端生成的请求追踪 ID")


# ============================================================
# 余额
# ============================================================


class CreditBalance(BaseModel):
    """AI 额度账户余额信息"""
    user_id: UUID = Field(..., description="用户 ID")
    plan_code: str = Field(..., description="当前套餐编码")
    monthly_grant: int = Field(..., description="每计费周期赠送的 AI 额度")
    balance: int = Field(..., description="当前可用 AI 额度余额")
    period_start: Optional[datetime] = Field(None, description="当前计费周期开始时间（UTC）")
    period_end: Optional[datetime] = Field(None, description="当前计费周期结束时间（UTC）")
    status: str = Field(..., description="账户状态（active / frozen）")
    updated_at: datetime = Field(..., description="余额最后更新时间（UTC）")


# 完整响应别名
CreditBalanceResponse = ApiResponse[CreditBalance]


# ============================================================
# 流水
# ============================================================


class CreditLedgerItem(BaseModel):
    """单条额度变动流水记录"""
    id: UUID = Field(..., description="流水记录 ID")
    change_type: ChangeType = Field(..., description="变动类型")
    amount: int = Field(..., description="变动额度值（正数为增加，负数为扣减）")
    balance_after: int = Field(..., description="变动后的账户余额")
    source_type: str = Field(..., description="来源类型（provider_call / order / system / admin）")
    source_id: Optional[UUID] = Field(None, description="来源记录 ID")
    description: Optional[str] = Field(None, description="变动说明（中文）")
    created_at: datetime = Field(..., description="流水记录创建时间（UTC）")


class CreditLedgerData(BaseModel):
    """额度流水分页数据"""
    items: list[CreditLedgerItem] = Field(default_factory=list, description="流水记录列表")
    total: int = Field(..., description="符合条件的总记录数")
    limit: int = Field(..., description="当前页大小")
    offset: int = Field(..., description="当前偏移量")


# 完整响应别名
CreditLedgerResponse = ApiResponse[CreditLedgerData]


# ============================================================
# 权限检查
# ============================================================


class EntitlementCheckRequest(BaseModel):
    """套餐权限检查请求 — 客户端不得提交 user_id、plan_code 等字段"""
    feature: str = Field(..., description="功能码，例如 resize_image_local_paid")
    operation: str = Field(..., description="操作类型（single / batch 等）")
    client_request_id: str = Field(..., description="桌面端生成的请求追踪 ID，用于去重和幂等")


class EntitlementCheckData(BaseModel):
    """套餐权限检查结果"""
    allowed: bool = Field(..., description="是否允许使用指定功能")
    feature: str = Field(..., description="检查的功能码")
    plan_code: str = Field(..., description="用户当前套餐编码")
    remaining_free_quota: Optional[int] = Field(None, description="免费套餐剩余免费额度")
    reason: Optional[str] = Field(None, description="不允许时的拒绝原因（中文）")


# 完整响应别名
EntitlementCheckResponse = ApiResponse[EntitlementCheckData]
