"""
admin-billing Pydantic 请求/响应 DTO。

所有响应结构对齐 shared-contract/openapi/admin-billing.yaml。
字段命名使用 snake_case，通过 Pydantic 序列化为 JSON。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


# ============================================================
# 套餐相关 DTO
# ============================================================


class PlanItem(BaseModel):
    """套餐列表项（摘要信息），对齐 admin-billing.yaml PlanItem。"""

    id: str = Field(..., description="套餐 ID（UUID）")
    name: str = Field(..., description="套餐名称（中文）")
    monthly_grant: int = Field(..., description="每周期赠送 AI 额度")
    status: str = Field(..., description="套餐状态：active / disabled")
    created_at: datetime = Field(..., description="创建时间")


class PlanDetail(BaseModel):
    """套餐详细信息，对齐 admin-billing.yaml PlanDetail。"""

    id: str = Field(..., description="套餐 ID（UUID）")
    name: str = Field(..., description="套餐名称")
    monthly_grant: int = Field(..., description="每周期赠送 AI 额度")
    enabled_features_json: dict[str, Any] = Field(
        default_factory=dict, description="功能开关配置"
    )
    status: str = Field(..., description="套餐状态：active / disabled")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最近更新时间")


class PlanListData(BaseModel):
    """套餐列表响应数据，对齐 admin-billing.yaml PlanListData。"""

    items: list[PlanItem] = Field(default_factory=list, description="套餐列表")


class CreatePlanRequest(BaseModel):
    """创建套餐请求，对齐 admin-billing.yaml CreatePlanRequest。"""

    name: str = Field(..., description="套餐名称（中文）")
    monthly_grant: int = Field(default=0, ge=0, description="每周期赠送 AI 额度")
    enabled_features_json: dict[str, Any] = Field(
        default_factory=dict, description="功能开关配置"
    )


class UpdatePlanRequest(BaseModel):
    """更新套餐配置请求，对齐 admin-billing.yaml UpdatePlanRequest。"""

    name: Optional[str] = Field(default=None, description="套餐名称")
    monthly_grant: Optional[int] = Field(default=None, ge=0, description="每周期赠送 AI 额度")
    enabled_features_json: Optional[dict[str, Any]] = Field(
        default=None, description="功能开关配置"
    )


class UpdatePlanStatusRequest(BaseModel):
    """修改套餐状态请求，对齐 admin-billing.yaml UpdatePlanStatusRequest。"""

    status: str = Field(
        ...,
        description="目标状态：active / disabled",
        pattern="^(active|disabled)$",
    )


class PlanOption(BaseModel):
    """套餐选项（下拉框用），对齐 admin-billing.yaml PlanOption。"""

    id: str = Field(..., description="套餐 ID（UUID）")
    name: str = Field(..., description="套餐中文名")


class PlanOptionsData(BaseModel):
    """套餐选项列表，对齐 admin-billing.yaml PlanOptionsData。"""

    items: list[PlanOption] = Field(default_factory=list, description="套餐选项列表")


# ============================================================
# 订单相关 DTO（管理员视图）
# ============================================================


class AdminOrderItem(BaseModel):
    """管理员订单列表项（含用户账号），对齐 admin-billing.yaml AdminOrderItem。"""

    id: str = Field(..., description="订单 ID（UUID）")
    order_no: str = Field(..., description="订单号")
    order_type: str = Field(..., description="订单类型：plan / credits")
    product_code: str = Field(..., description="产品编码")
    amount_cents: int = Field(..., description="订单金额（单位：分）")
    credit_amount: Optional[int] = Field(default=None, description="充值额度数量")
    currency: str = Field(..., description="币种")
    status: str = Field(..., description="订单状态")
    paid_at: Optional[datetime] = Field(default=None, description="支付时间")
    user_id: str = Field(..., description="下单用户 ID")
    user_account: Optional[str] = Field(default=None, description="下单用户账号")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class AdminOrderDetail(BaseModel):
    """管理员订单详情（含用户信息），对齐 admin-billing.yaml AdminOrderDetail。"""

    id: str = Field(..., description="订单 ID（UUID）")
    order_no: str = Field(..., description="订单号")
    order_type: str = Field(..., description="订单类型")
    product_code: str = Field(..., description="产品编码")
    amount_cents: int = Field(..., description="订单金额（单位：分）")
    credit_amount: Optional[int] = Field(default=None, description="充值额度数量")
    currency: str = Field(..., description="币种")
    status: str = Field(..., description="订单状态")
    paid_at: Optional[datetime] = Field(default=None, description="支付时间")
    user_id: str = Field(..., description="下单用户 ID")
    user_account: Optional[str] = Field(default=None, description="下单用户账号")
    user_display_name: Optional[str] = Field(default=None, description="下单用户展示名称")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class AdminOrderListData(BaseModel):
    """管理员订单列表分页响应数据，对齐 admin-billing.yaml AdminOrderListData。"""

    items: list[AdminOrderItem] = Field(default_factory=list, description="订单列表")
    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="每页条数")
    offset: int = Field(..., description="当前偏移量")


# ============================================================
# 额度管理 DTO（管理员视图）
# ============================================================


class AdminCreditAccountItem(BaseModel):
    """管理员额度账户列表项，对齐 admin-billing.yaml AdminCreditAccountItem。"""

    id: str = Field(..., description="额度账户 ID（UUID）")
    user_id: str = Field(..., description="用户 ID")
    user_account: Optional[str] = Field(default=None, description="用户账号")
    plan_id: Optional[str] = Field(default=None, description="当前套餐 ID（UUID）")
    plan_name: Optional[str] = Field(default=None, description="当前套餐中文名（从 plans 表关联查询）")
    balance: int = Field(..., description="当前 AI 额度余额")
    monthly_grant: int = Field(..., description="每周期赠送额度")
    status: str = Field(..., description="账户状态：active / frozen")
    period_start: Optional[datetime] = Field(default=None, description="计费周期开始")
    period_end: Optional[datetime] = Field(default=None, description="计费周期结束")
    updated_at: datetime = Field(..., description="最后更新时间")


class AdminCreditAccountDetail(BaseModel):
    """管理员额度账户详情，对齐 admin-billing.yaml AdminCreditAccountDetail。"""

    id: str = Field(..., description="额度账户 ID（UUID）")
    user_id: str = Field(..., description="用户 ID")
    user_account: Optional[str] = Field(default=None, description="用户账号")
    user_display_name: Optional[str] = Field(default=None, description="用户展示名称")
    plan_id: Optional[str] = Field(default=None, description="当前套餐 ID（UUID）")
    plan_name: Optional[str] = Field(default=None, description="当前套餐中文名（从 plans 表关联查询）")
    balance: int = Field(..., description="当前 AI 额度余额")
    monthly_grant: int = Field(..., description="每周期赠送额度")
    status: str = Field(..., description="账户状态")
    period_start: Optional[datetime] = Field(default=None, description="计费周期开始")
    period_end: Optional[datetime] = Field(default=None, description="计费周期结束")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")


class AdminCreditAccountListData(BaseModel):
    """管理员额度账户列表分页响应数据，对齐 admin-billing.yaml AdminCreditAccountListData。"""

    items: list[AdminCreditAccountItem] = Field(default_factory=list, description="额度账户列表")
    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="每页条数")
    offset: int = Field(..., description="当前偏移量")


class AdminCreditLedgerItem(BaseModel):
    """管理员额度流水明细，对齐 admin-billing.yaml AdminCreditLedgerItem。"""

    id: str = Field(..., description="流水 ID（UUID）")
    user_id: str = Field(..., description="用户 ID")
    user_account: Optional[str] = Field(default=None, description="用户账号")
    account_id: str = Field(..., description="额度账户 ID")
    change_type: str = Field(..., description="变化类型")
    amount: int = Field(..., description="变化值（扣费为负数）")
    balance_after: int = Field(..., description="变化后余额")
    source_type: str = Field(..., description="来源类型")
    source_id: Optional[str] = Field(default=None, description="来源 ID")
    description: Optional[str] = Field(default=None, description="中文说明")
    created_at: datetime = Field(..., description="创建时间")


class AdminCreditLedgerListData(BaseModel):
    """管理员额度流水列表分页响应数据，对齐 admin-billing.yaml AdminCreditLedgerListData。"""

    items: list[AdminCreditLedgerItem] = Field(default_factory=list, description="流水列表")
    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="每页条数")
    offset: int = Field(..., description="当前偏移量")


class AdjustCreditsRequest(BaseModel):
    """手动调整额度请求，对齐 admin-billing.yaml AdjustCreditsRequest。"""

    user_id: str = Field(..., description="目标用户 ID（UUID）")
    amount: int = Field(..., description="调整额度（正数为赠送，负数为扣除）")
    description: Optional[str] = Field(default=None, description="调整原因说明（中文）")
