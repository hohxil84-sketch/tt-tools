"""
cloud-orders-recharge Pydantic 请求/响应 DTO。

所有请求和响应结构对齐 shared-contract/openapi/orders-recharge.yaml。
金额字段统一使用整数分（amount_cents），不做浮点。
客户端禁止提交 user_id、final_price、plan_code 等决策字段。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ============================================================
# 请求 DTO（对齐 OpenAPI requestBody schemas）
# ============================================================


class CreateOrderRequest(BaseModel):
    """创建订单请求，对齐 orders-recharge.yaml #/components/schemas/CreateOrderRequest。

    客户端只提交 order_type 和 product_code，金额由服务端定价表决定。
    注意：不定义 user_id、final_price、plan_code 字段——
    即使客户端传入也会被 Pydantic 默认忽略（extra=forbid 模式下会拒绝）。
    """

    order_type: str = Field(
        ..., description="订单类型：plan（套餐购买）/ credits（额度充值）"
    )
    product_code: str = Field(
        ..., description="产品编码。plan: standard/pro；credits: credits_100/credits_500/credits_2000"
    )
    client_request_id: str = Field(
        ..., description="客户端请求追踪 ID"
    )


# ============================================================
# 响应 DTO（对齐 OpenAPI 内嵌对象 schemas）
# ============================================================


class OrderData(BaseModel):
    """订单数据，对齐 orders-recharge.yaml #/components/schemas/OrderData。"""

    id: str = Field(..., description="订单 ID（UUID）")
    order_no: str = Field(..., description="订单号")
    order_type: str = Field(..., description="订单类型：plan / credits")
    product_code: str = Field(..., description="产品编码")
    amount_cents: int = Field(..., description="订单金额（单位：分）")
    credit_amount: Optional[int] = Field(
        default=None, description="充值额度数量（仅 credits 类型有值）"
    )
    currency: str = Field(..., description="币种")
    status: str = Field(..., description="订单状态：pending / paid / closed / refunded")
    paid_at: Optional[datetime] = Field(default=None, description="支付时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class OrderListData(BaseModel):
    """订单列表，对齐 orders-recharge.yaml #/components/schemas/OrderListData。"""

    items: List[OrderData] = Field(default_factory=list, description="订单列表")
    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="每页条数")
    offset: int = Field(..., description="当前偏移量")
