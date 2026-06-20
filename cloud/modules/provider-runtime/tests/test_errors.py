"""
Provider 错误标准化模块测试。

验证 map_provider_error 异常映射和 is_retryable_error 判断逻辑。
"""
from __future__ import annotations

import sys
import os
import asyncio

# 将项目根目录和模块目录加入 sys.path（目录名含连字符）
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
_MODULE_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "provider-runtime")
if _MODULE_DIR not in sys.path:
    sys.path.insert(0, _MODULE_DIR)

import pytest

from errors import (
    ProviderError,
    ProviderErrorCode,
    map_provider_error,
    is_retryable_error,
    _RETRYABLE_ERROR_CODES,
    _NON_RETRYABLE_ERROR_CODES,
)


class TestProviderErrorCode:
    """错误码常量测试。"""

    def test_all_error_codes_defined(self) -> None:
        """确保所有 Provider 相关错误码都已定义。"""
        assert ProviderErrorCode.PROVIDER_TIMEOUT == "PROVIDER_TIMEOUT"
        assert ProviderErrorCode.PROVIDER_RATE_LIMITED == "PROVIDER_RATE_LIMITED"
        assert ProviderErrorCode.PROVIDER_AUTH_FAILED == "PROVIDER_AUTH_FAILED"
        assert ProviderErrorCode.PROVIDER_QUOTA_EXCEEDED == "PROVIDER_QUOTA_EXCEEDED"
        assert ProviderErrorCode.PROVIDER_BAD_RESPONSE == "PROVIDER_BAD_RESPONSE"
        assert ProviderErrorCode.PROVIDER_UNAVAILABLE == "PROVIDER_UNAVAILABLE"
        assert ProviderErrorCode.PROVIDER_NOT_REGISTERED == "PROVIDER_NOT_REGISTERED"


class TestProviderError:
    """ProviderError 异常类测试。"""

    def test_default_values(self) -> None:
        """默认构造使用 PROVIDER_UNAVAILABLE 和 502。"""
        exc = ProviderError()
        assert exc.code == ProviderErrorCode.PROVIDER_UNAVAILABLE
        assert exc.status_code == 502
        assert isinstance(exc, Exception)

    def test_custom_error(self) -> None:
        """自定义错误。"""
        exc = ProviderError(
            code=ProviderErrorCode.PROVIDER_TIMEOUT,
            message="调用超时",
            status_code=504,
            details={"timeout_seconds": 30},
        )
        assert exc.code == "PROVIDER_TIMEOUT"
        assert exc.message == "调用超时"
        assert exc.status_code == 504
        assert exc.details == {"timeout_seconds": 30}

    def test_str_returns_message(self) -> None:
        """str(ProviderError) 返回 message。"""
        exc = ProviderError(message="测试错误消息")
        assert str(exc) == "测试错误消息"


class TestMapProviderError:
    """map_provider_error 异常映射测试。"""

    def test_map_asyncio_timeout(self) -> None:
        """asyncio.TimeoutError 应映射为 PROVIDER_TIMEOUT。"""
        exc = asyncio.TimeoutError("请求超时")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_TIMEOUT
        assert mapped.status_code == 504

    def test_map_timeout_message(self) -> None:
        """消息中含 'timeout' 应映射为 PROVIDER_TIMEOUT。"""
        exc = Exception("Connection timed out after 30 seconds")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_TIMEOUT

    def test_map_timeout_exception_type(self) -> None:
        """异常类型名含 'Timeout' 应映射为 PROVIDER_TIMEOUT。"""
        class TimeoutException(Exception):
            pass
        exc = TimeoutException("超时")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_TIMEOUT

    def test_map_rate_limit_429(self) -> None:
        """消息中含 '429' 应映射为 PROVIDER_RATE_LIMITED。"""
        exc = Exception("HTTP 429 Too Many Requests")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_RATE_LIMITED
        assert mapped.status_code == 429

    def test_map_rate_limit_keyword(self) -> None:
        """消息中含 'rate limit' 应映射为 PROVIDER_RATE_LIMITED。"""
        exc = Exception("You have exceeded the rate limit")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_RATE_LIMITED

    def test_map_too_many_requests(self) -> None:
        """消息中含 'too many requests' 应映射为 PROVIDER_RATE_LIMITED。"""
        exc = Exception("too many requests, please slow down")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_RATE_LIMITED

    def test_map_auth_failed_unauthorized(self) -> None:
        """消息中含 'unauthorized' 应映射为 PROVIDER_AUTH_FAILED。"""
        exc = Exception("401 Unauthorized - invalid API key")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_AUTH_FAILED

    def test_map_auth_failed_invalid_key(self) -> None:
        """消息中含 'invalid api key' 应映射为 PROVIDER_AUTH_FAILED。"""
        exc = Exception("Incorrect API key provided")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_AUTH_FAILED

    def test_map_auth_failed_403(self) -> None:
        """消息中含 '403' 应映射为 PROVIDER_AUTH_FAILED。"""
        exc = Exception("HTTP 403 Forbidden")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_AUTH_FAILED

    def test_map_quota_exceeded(self) -> None:
        """消息中含 'quota' 应映射为 PROVIDER_QUOTA_EXCEEDED。"""
        exc = Exception("You exceeded your current quota")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_QUOTA_EXCEEDED

    def test_map_insufficient_credits(self) -> None:
        """消息中含 'insufficient' 应映射为 PROVIDER_QUOTA_EXCEEDED。"""
        exc = Exception("insufficient balance for this request")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_QUOTA_EXCEEDED

    def test_map_billing_error(self) -> None:
        """消息中含 'billing' 应映射为 PROVIDER_QUOTA_EXCEEDED。"""
        exc = Exception("Billing account not configured")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_QUOTA_EXCEEDED

    def test_map_connection_refused(self) -> None:
        """消息中含 'connection refused' 应映射为 PROVIDER_UNAVAILABLE。"""
        exc = Exception("Connection refused to api.example.com")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_UNAVAILABLE

    def test_map_network_error(self) -> None:
        """消息中含 'network' 应映射为 PROVIDER_UNAVAILABLE。"""
        exc = Exception("Network is unreachable")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_UNAVAILABLE

    def test_map_dns_error(self) -> None:
        """消息中含 'dns' 应映射为 PROVIDER_UNAVAILABLE。"""
        exc = Exception("DNS resolution failed")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_UNAVAILABLE

    def test_map_server_error_500(self) -> None:
        """消息中含 '500' 应映射为 PROVIDER_UNAVAILABLE。"""
        exc = Exception("Server returned 500 Internal Server Error")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_UNAVAILABLE

    def test_map_server_error_503(self) -> None:
        """消息中含 '503' 应映射为 PROVIDER_UNAVAILABLE。"""
        exc = Exception("503 Service Unavailable")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_UNAVAILABLE

    def test_map_unknown_error_defaults_to_unavailable(self) -> None:
        """未识别的异常默认映射为 PROVIDER_UNAVAILABLE。"""
        exc = Exception("Something completely unexpected happened!")
        mapped = map_provider_error(exc)
        assert mapped.code == ProviderErrorCode.PROVIDER_UNAVAILABLE
        assert "Something completely unexpected" in mapped.message

    def test_map_preserves_original_error_in_details(self) -> None:
        """映射结果应保留原始错误信息。"""
        exc = RuntimeError("Something broke badly")
        mapped = map_provider_error(exc)
        assert mapped.details is not None
        assert mapped.details["original_error"] == "Something broke badly"


class TestIsRetryableError:
    """is_retryable_error 可重试判断测试。"""

    def test_timeout_is_retryable(self) -> None:
        """超时可重试。"""
        assert is_retryable_error(ProviderErrorCode.PROVIDER_TIMEOUT) is True

    def test_rate_limited_is_retryable(self) -> None:
        """频率限制可重试。"""
        assert is_retryable_error(ProviderErrorCode.PROVIDER_RATE_LIMITED) is True

    def test_unavailable_is_retryable(self) -> None:
        """服务不可用可重试。"""
        assert is_retryable_error(ProviderErrorCode.PROVIDER_UNAVAILABLE) is True

    def test_auth_failed_is_not_retryable(self) -> None:
        """鉴权失败不可重试。"""
        assert is_retryable_error(ProviderErrorCode.PROVIDER_AUTH_FAILED) is False

    def test_quota_exceeded_is_not_retryable(self) -> None:
        """额度不足不可重试。"""
        assert is_retryable_error(ProviderErrorCode.PROVIDER_QUOTA_EXCEEDED) is False

    def test_bad_response_is_not_retryable(self) -> None:
        """异常响应不可重试。"""
        assert is_retryable_error(ProviderErrorCode.PROVIDER_BAD_RESPONSE) is False

    def test_not_registered_is_not_retryable(self) -> None:
        """未注册不可重试。"""
        assert is_retryable_error(ProviderErrorCode.PROVIDER_NOT_REGISTERED) is False

    def test_unknown_code_is_not_retryable(self) -> None:
        """未知错误码不可重试。"""
        assert is_retryable_error("SOME_WEIRD_CODE") is False

    def test_retryable_and_non_retryable_are_disjoint(self) -> None:
        """可重试和不可重试错误码集合无交集。"""
        overlap = _RETRYABLE_ERROR_CODES & _NON_RETRYABLE_ERROR_CODES
        assert len(overlap) == 0

    def test_all_known_codes_categorized(self) -> None:
        """所有已知错误码都应被归类（可重试或不可重试）。"""
        all_codes = set()
        for attr in dir(ProviderErrorCode):
            if not attr.startswith("_") and isinstance(
                getattr(ProviderErrorCode, attr), str
            ):
                all_codes.add(getattr(ProviderErrorCode, attr))
        categorized = _RETRYABLE_ERROR_CODES | _NON_RETRYABLE_ERROR_CODES
        assert all_codes == categorized, (
            f"缺少归类的错误码: {all_codes - categorized}"
        )
