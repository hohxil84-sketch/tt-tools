"""
Provider 错误标准化模块。

将各 Provider 的原始异常和 HTTP 错误映射为统一错误码，
对齐 shared-contract/error-codes.md 中 Provider 相关错误码。

统一错误码对照：
  PROVIDER_TIMEOUT        - 调用超时
  PROVIDER_RATE_LIMITED   - 频率限制 / 并发超限
  PROVIDER_AUTH_FAILED    - API Key 无效或鉴权失败
  PROVIDER_QUOTA_EXCEEDED - 额度用尽
  PROVIDER_BAD_RESPONSE   - Provider 返回异常响应
  PROVIDER_UNAVAILABLE    - Provider 服务不可用
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional


# ============================================================
# 统一错误码常量（对齐 common.yaml / error-codes.md）
# ============================================================

class ProviderErrorCode:
    """Provider 相关的统一错误码。"""

    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"
    PROVIDER_AUTH_FAILED = "PROVIDER_AUTH_FAILED"
    PROVIDER_QUOTA_EXCEEDED = "PROVIDER_QUOTA_EXCEEDED"
    PROVIDER_BAD_RESPONSE = "PROVIDER_BAD_RESPONSE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_NOT_REGISTERED = "PROVIDER_NOT_REGISTERED"


# 可重试的错误码集合：这些错误可能在下一次重试时成功
_RETRYABLE_ERROR_CODES: set[str] = {
    ProviderErrorCode.PROVIDER_TIMEOUT,
    ProviderErrorCode.PROVIDER_RATE_LIMITED,
    ProviderErrorCode.PROVIDER_UNAVAILABLE,
}

# 不可重试的错误码集合：重试不会改变结果
_NON_RETRYABLE_ERROR_CODES: set[str] = {
    ProviderErrorCode.PROVIDER_AUTH_FAILED,
    ProviderErrorCode.PROVIDER_QUOTA_EXCEEDED,
    ProviderErrorCode.PROVIDER_BAD_RESPONSE,
    ProviderErrorCode.PROVIDER_NOT_REGISTERED,
}


# ============================================================
# ProviderError 异常类
# ============================================================


class ProviderError(Exception):
    """Provider 调用统一异常。

    包含统一错误码、中文描述和可选补充信息。
    router 捕获原始异常后，将其映射为本异常。

    Attributes:
        code: 统一错误码
        message: 中文错误描述
        status_code: 对应的 HTTP 状态码建议
        details: 可选补充信息（如原始错误）
    """

    def __init__(
        self,
        code: str = ProviderErrorCode.PROVIDER_UNAVAILABLE,
        message: str = "Provider 服务暂时不可用",
        status_code: int = 502,
        details: Optional[dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


# ============================================================
# 错误映射逻辑
# ============================================================


def map_provider_error(exc: Exception) -> ProviderError:
    """将原始异常映射为统一 ProviderError。

    识别异常类型和错误消息中的关键字，映射为统一错误码。

    Args:
        exc: 原始异常对象

    Returns:
        标准化的 ProviderError 实例
    """
    exc_type = type(exc).__name__
    exc_msg = str(exc).lower()

    # 1. asyncio.TimeoutError → 超时
    if isinstance(exc, asyncio.TimeoutError) or "timeout" in exc_type.lower():
        return ProviderError(
            code=ProviderErrorCode.PROVIDER_TIMEOUT,
            message=f"Provider 调用超时: {str(exc)}",
            status_code=504,
            details={"original_error": str(exc)},
        )

    # 2. 超时关键字
    if "timeout" in exc_msg or "timed out" in exc_msg:
        return ProviderError(
            code=ProviderErrorCode.PROVIDER_TIMEOUT,
            message=f"Provider 调用超时: {str(exc)}",
            status_code=504,
            details={"original_error": str(exc)},
        )

    # 3. 频率限制关键字
    if any(kw in exc_msg for kw in ("rate limit", "rate_limit", "too many requests", "429")):
        return ProviderError(
            code=ProviderErrorCode.PROVIDER_RATE_LIMITED,
            message=f"Provider 频率限制: {str(exc)}",
            status_code=429,
            details={"original_error": str(exc)},
        )

    # 4. 鉴权失败关键字
    if any(kw in exc_msg for kw in (
        "unauthorized", "invalid api key", "incorrect api key",
        "authentication", "auth", "401", "403",
    )):
        return ProviderError(
            code=ProviderErrorCode.PROVIDER_AUTH_FAILED,
            message=f"Provider 鉴权失败: {str(exc)}",
            status_code=502,
            details={"original_error": str(exc)},
        )

    # 5. 额度用尽关键字
    if any(kw in exc_msg for kw in (
        "quota", "insufficient", "billing", "credit",
        "exceeded", "balance",
    )):
        return ProviderError(
            code=ProviderErrorCode.PROVIDER_QUOTA_EXCEEDED,
            message=f"Provider 额度不足: {str(exc)}",
            status_code=502,
            details={"original_error": str(exc)},
        )

    # 6. 连接 / 网络关键字 → 不可用
    if any(kw in exc_msg for kw in (
        "connection", "connect", "network", "dns",
        "refused", "unreachable",
    )):
        return ProviderError(
            code=ProviderErrorCode.PROVIDER_UNAVAILABLE,
            message=f"Provider 网络不可达: {str(exc)}",
            status_code=502,
            details={"original_error": str(exc)},
        )

    # 7. 5xx / 服务端错误 → 不可用
    if any(kw in exc_msg for kw in ("500", "502", "503", "server error", "internal")):
        return ProviderError(
            code=ProviderErrorCode.PROVIDER_UNAVAILABLE,
            message=f"Provider 服务端异常: {str(exc)}",
            status_code=502,
            details={"original_error": str(exc)},
        )

    # 8. 默认：归类为不可用
    return ProviderError(
        code=ProviderErrorCode.PROVIDER_UNAVAILABLE,
        message=f"Provider 调用异常: {str(exc)}",
        status_code=502,
        details={"original_error": str(exc)},
    )


def is_retryable_error(error_code: str) -> bool:
    """判断错误是否可重试。

    超时、频率限制、服务不可用等临时性问题可重试；
    鉴权失败、额度不足等永久性问题不可重试。

    Args:
        error_code: 统一错误码

    Returns:
        True 表示可重试
    """
    return error_code in _RETRYABLE_ERROR_CODES
