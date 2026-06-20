"""
local_paid_tools DTO 契约一致性测试。

测试 local_paid_tools.py 中的 Pydantic 模型与
shared-contract/openapi/local-paid-tools.yaml 的一致性。
"""

import json

import pytest
from pydantic import ValidationError

from local_paid_tools import (
    ErrorDetail,
    LocalPaidToolEntitlementData,
    LocalPaidToolEntitlementRequest,
    LocalPaidToolEntitlementResponse,
)


# ============================================================
# ErrorDetail 测试
# ============================================================


class TestErrorDetail:
    """ErrorDetail 通用错误结构测试"""

    def test_create_valid_error_detail(self):
        """正常创建错误详情"""
        err = ErrorDetail(code="PLAN_REQUIRED", message="需要有效套餐")
        assert err.code == "PLAN_REQUIRED"
        assert err.message == "需要有效套餐"
        assert err.details is None

    def test_create_error_detail_with_details(self):
        """带补充信息的错误详情"""
        err = ErrorDetail(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details={"feature": "不支持的功能码"},
        )
        assert err.details == {"feature": "不支持的功能码"}

    def test_error_detail_missing_code_fails(self):
        """缺少 code 字段应失败"""
        with pytest.raises(ValidationError):
            ErrorDetail(message="需要有效套餐")

    def test_error_detail_missing_message_fails(self):
        """缺少 message 字段应失败"""
        with pytest.raises(ValidationError):
            ErrorDetail(code="PLAN_REQUIRED")


# ============================================================
# LocalPaidToolEntitlementRequest 测试
# ============================================================


class TestLocalPaidToolEntitlementRequest:
    """权限检查请求 DTO 测试"""

    def test_create_valid_request(self):
        """正常创建权限检查请求"""
        req = LocalPaidToolEntitlementRequest(
            feature="resize_image_local_paid",
            operation="single",
            client_request_id="local_req_20260620_001",
        )
        assert req.feature == "resize_image_local_paid"
        assert req.operation == "single"
        assert req.client_request_id == "local_req_20260620_001"

    def test_create_batch_request(self):
        """批量操作权限检查请求"""
        req = LocalPaidToolEntitlementRequest(
            feature="resize_image_local_paid",
            operation="batch",
            client_request_id="local_req_20260620_003",
        )
        assert req.operation == "batch"

    def test_create_pdf_convert_request(self):
        """PDF 互转权限检查请求"""
        req = LocalPaidToolEntitlementRequest(
            feature="pdf_image_convert_local_paid",
            operation="single",
            client_request_id="local_req_20260620_002",
        )
        assert req.feature == "pdf_image_convert_local_paid"

    def test_missing_feature_fails(self):
        """缺少 feature 字段应失败"""
        with pytest.raises(ValidationError):
            LocalPaidToolEntitlementRequest(
                operation="single",
                client_request_id="local_req_001",
            )

    def test_missing_operation_fails(self):
        """缺少 operation 字段应失败"""
        with pytest.raises(ValidationError):
            LocalPaidToolEntitlementRequest(
                feature="resize_image_local_paid",
                client_request_id="local_req_001",
            )

    def test_missing_client_request_id_fails(self):
        """缺少 client_request_id 字段应失败"""
        with pytest.raises(ValidationError):
            LocalPaidToolEntitlementRequest(
                feature="resize_image_local_paid",
                operation="single",
            )

    def test_client_prohibited_fields_rejected(self):
        """
        客户端禁止提交字段检查。
        model_config = {"extra": "forbid"} 确保请求中不能包含
        user_id、plan_code、provider、model 等字段。
        """
        with pytest.raises(ValidationError):
            LocalPaidToolEntitlementRequest(
                feature="resize_image_local_paid",
                operation="single",
                client_request_id="local_req_001",
                user_id="some-user-id",  # 客户端禁止提交
            )

    def test_client_prohibited_plan_code_rejected(self):
        """客户端禁止提交 plan_code"""
        with pytest.raises(ValidationError):
            LocalPaidToolEntitlementRequest(
                feature="resize_image_local_paid",
                operation="single",
                client_request_id="local_req_001",
                plan_code="pro",  # 客户端禁止提交
            )

    def test_client_prohibited_provider_rejected(self):
        """客户端禁止提交 provider"""
        with pytest.raises(ValidationError):
            LocalPaidToolEntitlementRequest(
                feature="resize_image_local_paid",
                operation="single",
                client_request_id="local_req_001",
                provider="openai",  # 客户端禁止提交
            )

    def test_request_serialization(self):
        """请求序列化为 JSON"""
        req = LocalPaidToolEntitlementRequest(
            feature="resize_image_local_paid",
            operation="single",
            client_request_id="local_req_20260620_001",
        )
        json_str = req.model_dump_json()
        data = json.loads(json_str)
        assert data["feature"] == "resize_image_local_paid"
        assert data["operation"] == "single"
        assert data["client_request_id"] == "local_req_20260620_001"

    def test_request_deserialization(self):
        """从 JSON 反序列化请求"""
        json_str = json.dumps({
            "feature": "resize_image_local_paid",
            "operation": "single",
            "client_request_id": "local_req_20260620_001",
        })
        req = LocalPaidToolEntitlementRequest.model_validate_json(json_str)
        assert req.feature == "resize_image_local_paid"
        assert req.operation == "single"
        assert req.client_request_id == "local_req_20260620_001"


# ============================================================
# LocalPaidToolEntitlementData 测试
# ============================================================


class TestLocalPaidToolEntitlementData:
    """权限检查结果 DTO 测试"""

    def test_allowed_standard_plan(self):
        """标准套餐权限通过"""
        data = LocalPaidToolEntitlementData(
            allowed=True,
            feature="resize_image_local_paid",
            plan_code="standard",
        )
        assert data.allowed is True
        assert data.feature == "resize_image_local_paid"
        assert data.plan_code == "standard"
        assert data.remaining_free_quota is None
        assert data.reason is None

    def test_allowed_pro_plan(self):
        """专业套餐权限通过"""
        data = LocalPaidToolEntitlementData(
            allowed=True,
            feature="resize_image_local_paid",
            plan_code="pro",
        )
        assert data.allowed is True
        assert data.plan_code == "pro"

    def test_denied_free_quota_exceeded(self):
        """免费套餐额度用完"""
        data = LocalPaidToolEntitlementData(
            allowed=False,
            feature="resize_image_local_paid",
            plan_code="free",
            remaining_free_quota=0,
            reason="免费套餐当日使用次数已用完，请升级套餐",
        )
        assert data.allowed is False
        assert data.plan_code == "free"
        assert data.remaining_free_quota == 0
        assert data.reason == "免费套餐当日使用次数已用完，请升级套餐"

    def test_denied_no_reason(self):
        """权限不通过但无原因说明"""
        data = LocalPaidToolEntitlementData(
            allowed=False,
            feature="pdf_image_convert_local_paid",
            plan_code="free",
        )
        assert data.allowed is False
        assert data.reason is None

    def test_free_with_remaining_quota(self):
        """免费套餐还有剩余次数"""
        data = LocalPaidToolEntitlementData(
            allowed=True,
            feature="resize_image_local_paid",
            plan_code="free",
            remaining_free_quota=8,
        )
        assert data.allowed is True
        assert data.remaining_free_quota == 8

    def test_data_serialization(self):
        """权限结果序列化为 JSON — 未设置的 nullable 字段序列化为 null"""
        data = LocalPaidToolEntitlementData(
            allowed=True,
            feature="resize_image_local_paid",
            plan_code="standard",
        )
        json_str = data.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["allowed"] is True
        assert parsed["feature"] == "resize_image_local_paid"
        assert parsed["plan_code"] == "standard"
        # nullable 字段未设置时序列化为 null，与 OpenAPI nullable: true 一致
        assert parsed["remaining_free_quota"] is None
        assert parsed["reason"] is None

    def test_data_deserialization(self):
        """从 JSON 反序列化权限结果"""
        json_str = json.dumps({
            "allowed": True,
            "feature": "resize_image_local_paid",
            "plan_code": "standard",
        })
        data = LocalPaidToolEntitlementData.model_validate_json(json_str)
        assert data.allowed is True
        assert data.plan_code == "standard"


# ============================================================
# LocalPaidToolEntitlementResponse 测试
# ============================================================


class TestLocalPaidToolEntitlementResponse:
    """权限检查响应 DTO 测试"""

    def test_success_response(self):
        """成功响应 — 权限通过"""
        resp = LocalPaidToolEntitlementResponse(
            success=True,
            data=LocalPaidToolEntitlementData(
                allowed=True,
                feature="resize_image_local_paid",
                plan_code="standard",
            ),
            error=None,
            request_id="req_cloud_abc123",
        )
        assert resp.success is True
        assert resp.data is not None
        assert resp.data.allowed is True
        assert resp.error is None
        assert resp.request_id == "req_cloud_abc123"

    def test_success_response_denied(self):
        """成功响应 — 权限不通过（success=true 但 allowed=false）"""
        resp = LocalPaidToolEntitlementResponse(
            success=True,
            data=LocalPaidToolEntitlementData(
                allowed=False,
                feature="resize_image_local_paid",
                plan_code="free",
                remaining_free_quota=0,
                reason="免费套餐当日使用次数已用完，请升级套餐",
            ),
            error=None,
            request_id="req_cloud_def456",
        )
        assert resp.success is True
        assert resp.data.allowed is False
        assert resp.data.reason == "免费套餐当日使用次数已用完，请升级套餐"

    def test_error_response(self):
        """错误响应 — 系统级错误（success=false）"""
        resp = LocalPaidToolEntitlementResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="PLAN_REQUIRED",
                message="需要有效套餐才能使用此功能",
            ),
            request_id="req_cloud_ghi789",
        )
        assert resp.success is False
        assert resp.data is None
        assert resp.error is not None
        assert resp.error.code == "PLAN_REQUIRED"
        assert resp.error.message == "需要有效套餐才能使用此功能"

    def test_error_response_unauthorized(self):
        """错误响应 — 未认证"""
        resp = LocalPaidToolEntitlementResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="AUTH_REQUIRED",
                message="需要登录才能使用此功能",
            ),
            request_id="req_cloud_jkl012",
        )
        assert resp.success is False
        assert resp.error.code == "AUTH_REQUIRED"

    def test_response_serialization_success(self):
        """成功响应序列化为 JSON"""
        resp = LocalPaidToolEntitlementResponse(
            success=True,
            data=LocalPaidToolEntitlementData(
                allowed=True,
                feature="resize_image_local_paid",
                plan_code="standard",
            ),
            error=None,
            request_id="req_cloud_abc123",
        )
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["data"]["allowed"] is True
        assert parsed["error"] is None
        assert parsed["request_id"] == "req_cloud_abc123"

    def test_response_serialization_error(self):
        """错误响应序列化为 JSON"""
        resp = LocalPaidToolEntitlementResponse(
            success=False,
            data=None,
            error=ErrorDetail(code="PLAN_REQUIRED", message="需要有效套餐"),
            request_id="req_cloud_ghi789",
        )
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is False
        assert parsed["data"] is None
        assert parsed["error"]["code"] == "PLAN_REQUIRED"
        assert parsed["request_id"] == "req_cloud_ghi789"

    def test_response_deserialization_success(self):
        """从 JSON 反序列化成功响应"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "allowed": True,
                "feature": "resize_image_local_paid",
                "plan_code": "standard",
            },
            "error": None,
            "request_id": "req_cloud_abc123",
        })
        resp = LocalPaidToolEntitlementResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.allowed is True
        assert resp.data.plan_code == "standard"
        assert resp.error is None

    def test_response_deserialization_error(self):
        """从 JSON 反序列化错误响应"""
        json_str = json.dumps({
            "success": False,
            "data": None,
            "error": {
                "code": "PLAN_REQUIRED",
                "message": "需要有效套餐才能使用此功能",
            },
            "request_id": "req_cloud_ghi789",
        })
        resp = LocalPaidToolEntitlementResponse.model_validate_json(json_str)
        assert resp.success is False
        assert resp.data is None
        assert resp.error.code == "PLAN_REQUIRED"


# ============================================================
# YAML 示例一致性测试
# ============================================================


class TestYamlExamples:
    """验证 YAML 文件中定义的示例与 DTO 一致"""

    def test_example_resize_image_allowed(self):
        """YAML 示例：改尺寸权限通过 — 应与 DTO 兼容"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "allowed": True,
                "feature": "resize_image_local_paid",
                "plan_code": "standard",
                "remaining_free_quota": None,
                "reason": None,
            },
            "error": None,
            "request_id": "req_cloud_abc123",
        })
        resp = LocalPaidToolEntitlementResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.allowed is True
        assert resp.data.plan_code == "standard"

    def test_example_free_quota_exceeded(self):
        """YAML 示例：免费额度已用完 — 应与 DTO 兼容"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "allowed": False,
                "feature": "resize_image_local_paid",
                "plan_code": "free",
                "remaining_free_quota": 0,
                "reason": "免费套餐当日使用次数已用完，请升级套餐",
            },
            "error": None,
            "request_id": "req_cloud_def456",
        })
        resp = LocalPaidToolEntitlementResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.allowed is False
        assert resp.data.plan_code == "free"
        assert resp.data.remaining_free_quota == 0

    def test_example_plan_required(self):
        """YAML 示例：需要有效套餐 — 应与 DTO 兼容"""
        json_str = json.dumps({
            "success": False,
            "data": None,
            "error": {
                "code": "PLAN_REQUIRED",
                "message": "需要有效套餐才能使用此功能",
                "details": None,
            },
            "request_id": "req_cloud_ghi789",
        })
        resp = LocalPaidToolEntitlementResponse.model_validate_json(json_str)
        assert resp.success is False
        assert resp.data is None
        assert resp.error.code == "PLAN_REQUIRED"

    def test_request_serialization_roundtrip(self):
        """请求对象序列化/反序列化往返一致性"""
        original = LocalPaidToolEntitlementRequest(
            feature="resize_image_local_paid",
            operation="single",
            client_request_id="local_req_20260620_001",
        )
        json_str = original.model_dump_json()
        restored = LocalPaidToolEntitlementRequest.model_validate_json(json_str)
        assert restored.feature == original.feature
        assert restored.operation == original.operation
        assert restored.client_request_id == original.client_request_id

    def test_response_success_roundtrip(self):
        """成功响应对象序列化/反序列化往返一致性"""
        original = LocalPaidToolEntitlementResponse(
            success=True,
            data=LocalPaidToolEntitlementData(
                allowed=True,
                feature="resize_image_local_paid",
                plan_code="standard",
            ),
            error=None,
            request_id="req_cloud_abc123",
        )
        json_str = original.model_dump_json()
        restored = LocalPaidToolEntitlementResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data.allowed == original.data.allowed
        assert restored.data.feature == original.data.feature
        assert restored.data.plan_code == original.data.plan_code
        assert restored.error == original.error
        assert restored.request_id == original.request_id

    def test_response_error_roundtrip(self):
        """错误响应对象序列化/反序列化往返一致性"""
        original = LocalPaidToolEntitlementResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="PLAN_REQUIRED",
                message="需要有效套餐才能使用此功能",
            ),
            request_id="req_cloud_ghi789",
        )
        json_str = original.model_dump_json()
        restored = LocalPaidToolEntitlementResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data == original.data
        assert restored.error.code == original.error.code
        assert restored.error.message == original.error.message
        assert restored.request_id == original.request_id
