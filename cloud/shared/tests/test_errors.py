"""
cloud-shared 错误处理模块测试。

验证：ErrorDetail 模型、ApiResponse 模型、ErrorCode 常量、
error_response / success_response 辅助函数、AppError 异常类。
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from cloud.shared.errors import (
    ErrorCode,
    ErrorDetail,
    ApiResponse,
    AppError,
    error_response,
    success_response,
)


class TestErrorCode:
    """错误码常量定义测试。"""

    def test_all_error_codes_defined(self) -> None:
        """确保所有分类的错误码都已定义。"""
        # 通用
        assert ErrorCode.UNKNOWN_ERROR == "UNKNOWN_ERROR"
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCode.REQUEST_TIMEOUT == "REQUEST_TIMEOUT"
        assert ErrorCode.NETWORK_ERROR == "NETWORK_ERROR"
        # 鉴权
        assert ErrorCode.AUTH_REQUIRED == "AUTH_REQUIRED"
        assert ErrorCode.AUTH_INVALID_CREDENTIALS == "AUTH_INVALID_CREDENTIALS"
        assert ErrorCode.AUTH_TOKEN_EXPIRED == "AUTH_TOKEN_EXPIRED"
        assert ErrorCode.DEVICE_NOT_BOUND == "DEVICE_NOT_BOUND"
        assert ErrorCode.PERMISSION_DENIED == "PERMISSION_DENIED"
        # 额度
        assert ErrorCode.PLAN_REQUIRED == "PLAN_REQUIRED"
        assert ErrorCode.CREDITS_NOT_ENOUGH == "CREDITS_NOT_ENOUGH"
        assert ErrorCode.BILLING_FAILED == "BILLING_FAILED"
        # Provider
        assert ErrorCode.PROVIDER_TIMEOUT == "PROVIDER_TIMEOUT"
        assert ErrorCode.PROVIDER_RATE_LIMITED == "PROVIDER_RATE_LIMITED"
        assert ErrorCode.PROVIDER_AUTH_FAILED == "PROVIDER_AUTH_FAILED"
        assert ErrorCode.PROVIDER_QUOTA_EXCEEDED == "PROVIDER_QUOTA_EXCEEDED"
        assert ErrorCode.PROVIDER_BAD_RESPONSE == "PROVIDER_BAD_RESPONSE"
        assert ErrorCode.PROVIDER_UNAVAILABLE == "PROVIDER_UNAVAILABLE"


class TestErrorDetail:
    """ErrorDetail 模型测试。"""

    def test_create_minimal(self) -> None:
        """最简 ErrorDetail：只含 code 和 message。"""
        detail = ErrorDetail(code="TEST_ERROR", message="测试错误")
        assert detail.code == "TEST_ERROR"
        assert detail.message == "测试错误"
        assert detail.details is None

    def test_create_with_details(self) -> None:
        """带 details 的 ErrorDetail。"""
        detail = ErrorDetail(
            code="VALIDATION_ERROR",
            message="字段校验失败",
            details={"field": "account", "reason": "必填"},
        )
        assert detail.details == {"field": "account", "reason": "必填"}

    def test_missing_required_fields_raises(self) -> None:
        """缺少必填字段时 Pydantic 应抛出 ValidationError。"""
        with pytest.raises(ValidationError):
            ErrorDetail()  # type: ignore

    def test_model_dump(self) -> None:
        """model_dump 输出应包含 code 和 message。"""
        detail = ErrorDetail(code="ERROR", message="错误")
        d = detail.model_dump()
        assert d["code"] == "ERROR"
        assert d["message"] == "错误"
        assert d["details"] is None


class TestApiResponse:
    """ApiResponse 模型测试。"""

    def test_success_response(self) -> None:
        """成功响应：success=True，error=None。"""
        resp = ApiResponse(
            success=True,
            data={"user": "test"},
            error=None,
            request_id="req-001",
        )
        assert resp.success is True
        assert resp.data == {"user": "test"}
        assert resp.error is None
        assert resp.request_id == "req-001"

    def test_error_response(self) -> None:
        """失败响应：success=False，data=None。"""
        resp = ApiResponse(
            success=False,
            data=None,
            error=ErrorDetail(code="AUTH_REQUIRED", message="请登录"),
            request_id="req-002",
        )
        assert resp.success is False
        assert resp.data is None
        assert resp.error is not None
        assert resp.error.code == "AUTH_REQUIRED"


class TestAppError:
    """AppError 业务异常测试。"""

    def test_default_values(self) -> None:
        """默认构造使用 UNKNOWN_ERROR 和 500。"""
        exc = AppError()
        assert exc.code == ErrorCode.UNKNOWN_ERROR
        assert exc.status_code == 500

    def test_custom_error(self) -> None:
        """自定义错误码、消息和状态码。"""
        exc = AppError(
            code=ErrorCode.CREDITS_NOT_ENOUGH,
            message="额度不足",
            status_code=402,
        )
        assert exc.code == "CREDITS_NOT_ENOUGH"
        assert exc.message == "额度不足"
        assert exc.status_code == 402

    def test_is_exception(self) -> None:
        """AppError 是 Exception 的子类。"""
        exc = AppError()
        assert isinstance(exc, Exception)

    def test_str_returns_message(self) -> None:
        """str(AppError) 应返回 message。"""
        exc = AppError(message="测试消息")
        assert str(exc) == "测试消息"

    def test_with_details(self) -> None:
        """带 details 的 AppError。"""
        exc = AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="校验失败",
            details={"field": "account"},
        )
        assert exc.details == {"field": "account"}


class TestErrorResponseHelper:
    """error_response 辅助函数测试。"""

    def test_basic_error_response(self) -> None:
        """最简错误响应体。"""
        resp = error_response(
            code="TEST_ERROR",
            message="测试错误",
            request_id="req-abc",
        )
        assert resp["success"] is False
        assert resp["data"] is None
        assert resp["error"]["code"] == "TEST_ERROR"
        assert resp["error"]["message"] == "测试错误"
        assert resp["request_id"] == "req-abc"

    def test_error_response_with_details(self) -> None:
        """带 details 的错误响应。"""
        resp = error_response(
            code="VALIDATION_ERROR",
            message="校验失败",
            request_id="req-xyz",
            details={"field": "account"},
        )
        assert resp["error"]["details"] == {"field": "account"}

    def test_error_response_no_details_key_when_none(self) -> None:
        """details 为 None 时响应中不应出现 details 键。"""
        resp = error_response(
            code="ERROR",
            message="错误",
            request_id="req-001",
        )
        assert "details" not in resp["error"]


class TestSuccessResponseHelper:
    """success_response 辅助函数测试。"""

    def test_basic_success_response(self) -> None:
        """最简成功响应体。"""
        resp = success_response(
            data={"id": 1},
            request_id="req-ok",
        )
        assert resp["success"] is True
        assert resp["data"] == {"id": 1}
        assert resp["error"] is None
        assert resp["request_id"] == "req-ok"

    def test_success_response_data_can_be_none(self) -> None:
        """data 可为 None（如 DELETE 操作无返回体）。"""
        resp = success_response(data=None, request_id="req-del")
        assert resp["success"] is True
        assert resp["data"] is None

    def test_success_response_data_can_be_list(self) -> None:
        """data 可为列表。"""
        resp = success_response(data=[1, 2, 3], request_id="req-list")
        assert resp["data"] == [1, 2, 3]
