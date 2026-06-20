"""
local_paid_tools DTO — 本地付费工具权限校验。

来源：shared-contract/openapi/local-paid-tools.yaml v0.1.0
生成方式：手写，以 OpenAPI 为唯一来源。
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
# 权限检查
# ============================================================


class LocalPaidToolEntitlementRequest(BaseModel):
    """
    本地付费工具套餐权限检查请求。
    客户端不得提交 user_id、plan_code、provider、model 等字段。
    """
    feature: str = Field(
        ...,
        description="本地付费功能码（如 resize_image_local_paid、pdf_image_convert_local_paid）",
    )
    operation: str = Field(
        ...,
        description="操作类型（single / batch）",
    )
    client_request_id: str = Field(
        ...,
        description="桌面端生成的请求追踪 ID，用于去重和幂等",
    )

    # 防御性校验：请求中不得包含客户端禁止提交字段
    model_config = {"extra": "forbid"}


class LocalPaidToolEntitlementData(BaseModel):
    """本地付费工具套餐权限检查结果"""
    allowed: bool = Field(
        ...,
        description="是否允许使用指定功能",
    )
    feature: str = Field(
        ...,
        description="检查的功能码，与请求中的 feature 一致",
    )
    plan_code: str = Field(
        ...,
        description="用户当前套餐编码（free / standard / pro）",
    )
    remaining_free_quota: Optional[int] = Field(
        None,
        description="免费套餐剩余免费使用次数（仅 free 套餐有意义）",
    )
    reason: Optional[str] = Field(
        None,
        description="不允许时的拒绝原因（中文）",
    )


class LocalPaidToolEntitlementResponse(BaseModel):
    """本地付费工具套餐权限检查响应"""
    success: bool = Field(..., description="请求是否成功")
    data: Optional[LocalPaidToolEntitlementData] = Field(
        None, description="权限检查结果，失败时为 null"
    )
    error: Optional[ErrorDetail] = Field(None, description="错误详情，成功时为 null")
    request_id: str = Field(..., description="云端生成的请求追踪 ID")
