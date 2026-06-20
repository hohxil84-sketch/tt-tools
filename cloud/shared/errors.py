"""
cloud-shared 统一错误处理模块。

对齐 shared-contract/openapi/common.yaml：
  - ErrorDetail：{ code, message, details? }
  - ApiResponse：{ success, data, error, request_id }

错误码全集来自 shared-contract/error-codes.md。
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================
# 错误码常量（对齐 shared-contract/error-codes.md）
# ============================================================

class ErrorCode:
    """统一错误码全集。"""

    # -- 通用 --
    UNKNOWN_ERROR: str = "UNKNOWN_ERROR"
    VALIDATION_ERROR: str = "VALIDATION_ERROR"
    REQUEST_TIMEOUT: str = "REQUEST_TIMEOUT"
    NETWORK_ERROR: str = "NETWORK_ERROR"

    # -- 鉴权 --
    AUTH_REQUIRED: str = "AUTH_REQUIRED"
    AUTH_INVALID_CREDENTIALS: str = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED: str = "AUTH_TOKEN_EXPIRED"
    DEVICE_NOT_BOUND: str = "DEVICE_NOT_BOUND"
    PERMISSION_DENIED: str = "PERMISSION_DENIED"

    # -- 额度 --
    PLAN_REQUIRED: str = "PLAN_REQUIRED"
    CREDITS_NOT_ENOUGH: str = "CREDITS_NOT_ENOUGH"
    BILLING_FAILED: str = "BILLING_FAILED"

    # -- Provider --
    PROVIDER_TIMEOUT: str = "PROVIDER_TIMEOUT"
    PROVIDER_RATE_LIMITED: str = "PROVIDER_RATE_LIMITED"
    PROVIDER_AUTH_FAILED: str = "PROVIDER_AUTH_FAILED"
    PROVIDER_QUOTA_EXCEEDED: str = "PROVIDER_QUOTA_EXCEEDED"
    PROVIDER_BAD_RESPONSE: str = "PROVIDER_BAD_RESPONSE"
    PROVIDER_UNAVAILABLE: str = "PROVIDER_UNAVAILABLE"


# ============================================================
# Pydantic 模型（对齐 common.yaml Schema）
# ============================================================

class ErrorDetail(BaseModel):
    """统一错误详情结构，对齐 common.yaml #/components/schemas/ErrorDetail。

    - code: 统一错误码
    - message: 人类可读的中文错误描述
    - details: 可选补充信息（如字段级校验错误明细）
    """

    code: str = Field(..., description="统一错误码")
    message: str = Field(..., description="人类可读的中文错误描述")
    details: Optional[dict[str, Any]] = Field(
        default=None, description="可选补充信息"
    )


class ApiResponse(BaseModel):
    """统一 API 响应外层结构，对齐 common.yaml #/components/schemas/ApiResponse。

    所有接口响应必须包含 success / data / error / request_id。
    成功时 error 为 None，失败时 data 为 None。
    """

    success: bool = Field(..., description="请求是否成功")
    data: Any = Field(default=None, description="业务数据载荷")
    error: Optional[ErrorDetail] = Field(default=None, description="错误详情")
    request_id: str = Field(..., description="云端请求追踪 ID")


# ============================================================
# 业务异常类
# ============================================================

class AppError(Exception):
    """业务异常基类，业务逻辑可抛出本异常，由中间件捕获并转为 ErrorResponse。

    使用示例：
        raise AppError(
            code=ErrorCode.CREDITS_NOT_ENOUGH,
            message="AI 额度不足，请充值后再试",
            status_code=402,
        )
    """

    def __init__(
        self,
        code: str = ErrorCode.UNKNOWN_ERROR,
        message: str = "服务内部异常",
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


# ============================================================
# 响应构造辅助函数
# ============================================================

def error_response(
    code: str,
    message: str,
    request_id: str,
    status_code: int = 400,
    details: Optional[dict[str, Any]] = None,
) -> dict:
    """构造统一错误响应体（纯 dict，方便 FastAPI JSONResponse 等直接使用）。

    Args:
        code: 统一错误码
        message: 中文错误描述
        request_id: 请求追踪 ID
        status_code: HTTP 状态码（在 JSONResponse 中设置）
        details: 可选补充信息

    Returns:
        符合 common.yaml ErrorResponse 格式的 dict
    """
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            **({"details": details} if details else {}),
        },
        "request_id": request_id,
    }


def success_response(
    data: Any,
    request_id: str,
) -> dict:
    """构造统一成功响应体。

    Args:
        data: 业务数据载荷
        request_id: 请求追踪 ID

    Returns:
        符合 common.yaml ApiResponse（成功）格式的 dict
    """
    return {
        "success": True,
        "data": data,
        "error": None,
        "request_id": request_id,
    }
