"""
provider_log DTO 契约一致性测试。

测试 provider_log.py 中的 Pydantic 模型与
shared-contract/openapi/provider-log.yaml 的一致性。
"""

import json

import pytest
from pydantic import ValidationError

from provider_log import (
    ErrorDetail,
    ProviderCallLogItem,
    ProviderCallLogListData,
    ProviderCallLogListResponse,
)


# ============================================================
# ErrorDetail 测试
# ============================================================


class TestErrorDetail:
    """ErrorDetail 通用错误结构测试"""

    def test_create_valid_error_detail(self):
        """正常创建错误详情"""
        err = ErrorDetail(code="AUTH_REQUIRED", message="需要登录")
        assert err.code == "AUTH_REQUIRED"
        assert err.message == "需要登录"
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
            ErrorDetail(message="需要登录")

    def test_error_detail_missing_message_fails(self):
        """缺少 message 字段应失败"""
        with pytest.raises(ValidationError):
            ErrorDetail(code="AUTH_REQUIRED")


# ============================================================
# ProviderCallLogItem 测试
# ============================================================


class TestProviderCallLogItem:
    """Provider 调用日志条目 DTO 测试"""

    def test_create_valid_success_item(self):
        """正常创建成功调用日志条目"""
        item = ProviderCallLogItem(
            id="550e8400-e29b-41d4-a716-446655440000",
            request_id="req_cloud_abc123",
            feature="ai_copy_cloud",
            provider="deepseek",
            model="deepseek-chat",
            status="success",
            error_code=None,
            input_tokens=120,
            output_tokens=80,
            total_tokens=200,
            estimated_cost=0.002,
            credits_charged=1,
            latency_ms=1200,
            created_at="2026-06-20T10:30:00Z",
        )
        assert item.id == "550e8400-e29b-41d4-a716-446655440000"
        assert item.request_id == "req_cloud_abc123"
        assert item.feature == "ai_copy_cloud"
        assert item.provider == "deepseek"
        assert item.model == "deepseek-chat"
        assert item.status == "success"
        assert item.error_code is None
        assert item.input_tokens == 120
        assert item.output_tokens == 80
        assert item.total_tokens == 200
        assert item.estimated_cost == 0.002
        assert item.credits_charged == 1
        assert item.latency_ms == 1200
        assert item.created_at == "2026-06-20T10:30:00Z"

    def test_create_valid_failed_item(self):
        """创建失败调用日志条目"""
        item = ProviderCallLogItem(
            id="550e8400-e29b-41d4-a716-446655440001",
            request_id="req_cloud_def456",
            feature="ai_render_cloud",
            provider="openai",
            model="gpt-4o",
            status="failed",
            error_code="PROVIDER_TIMEOUT",
            input_tokens=50,
            output_tokens=0,
            total_tokens=50,
            estimated_cost=0.0,
            credits_charged=0,
            latency_ms=None,
            created_at="2026-06-20T11:00:00Z",
        )
        assert item.status == "failed"
        assert item.error_code == "PROVIDER_TIMEOUT"
        assert item.credits_charged == 0
        assert item.latency_ms is None

    def test_create_timeout_item(self):
        """创建超时调用日志条目"""
        item = ProviderCallLogItem(
            id="550e8400-e29b-41d4-a716-446655440002",
            request_id="req_cloud_ghi789",
            feature="ai_image_tools_cloud",
            provider="openai",
            model="gpt-4o",
            status="timeout",
            error_code="PROVIDER_TIMEOUT",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            estimated_cost=0.0,
            credits_charged=0,
            latency_ms=30000,
            created_at="2026-06-20T12:00:00Z",
        )
        assert item.status == "timeout"
        assert item.error_code == "PROVIDER_TIMEOUT"
        assert item.total_tokens == 0

    def test_missing_required_fields_fails(self):
        """缺少必填字段应失败"""
        with pytest.raises(ValidationError):
            ProviderCallLogItem(
                id="550e8400-e29b-41d4-a716-446655440000",
                request_id="req_cloud_abc123",
                # 缺少 feature
                provider="deepseek",
                model="deepseek-chat",
                status="success",
                input_tokens=120,
                output_tokens=80,
                total_tokens=200,
                estimated_cost=0.002,
                credits_charged=1,
                created_at="2026-06-20T10:30:00Z",
            )

    def test_item_serialization(self):
        """日志条目序列化为 JSON — 未设置的 nullable 字段序列化为 null"""
        item = ProviderCallLogItem(
            id="550e8400-e29b-41d4-a716-446655440000",
            request_id="req_cloud_abc123",
            feature="ai_copy_cloud",
            provider="deepseek",
            model="deepseek-chat",
            status="success",
            error_code=None,
            input_tokens=120,
            output_tokens=80,
            total_tokens=200,
            estimated_cost=0.002,
            credits_charged=1,
            latency_ms=1200,
            created_at="2026-06-20T10:30:00Z",
        )
        json_str = item.model_dump_json()
        data = json.loads(json_str)
        assert data["id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert data["feature"] == "ai_copy_cloud"
        assert data["provider"] == "deepseek"
        assert data["model"] == "deepseek-chat"
        assert data["status"] == "success"
        assert data["error_code"] is None
        assert data["input_tokens"] == 120
        assert data["output_tokens"] == 80
        assert data["total_tokens"] == 200
        assert data["estimated_cost"] == 0.002
        assert data["credits_charged"] == 1
        assert data["latency_ms"] == 1200
        assert data["created_at"] == "2026-06-20T10:30:00Z"

    def test_item_deserialization(self):
        """从 JSON 反序列化日志条目"""
        json_str = json.dumps({
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "request_id": "req_cloud_abc123",
            "feature": "ai_copy_cloud",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "status": "success",
            "error_code": None,
            "input_tokens": 120,
            "output_tokens": 80,
            "total_tokens": 200,
            "estimated_cost": 0.002,
            "credits_charged": 1,
            "latency_ms": 1200,
            "created_at": "2026-06-20T10:30:00Z",
        })
        item = ProviderCallLogItem.model_validate_json(json_str)
        assert item.id == "550e8400-e29b-41d4-a716-446655440000"
        assert item.feature == "ai_copy_cloud"
        assert item.provider == "deepseek"
        assert item.status == "success"

    def test_item_does_not_contain_private_fields(self):
        """
        隐私字段保护：日志条目不得包含完整 prompt、原图、API Key、
        Token、完整隐私内容等字段。DTO 定义中不应有这些属性。
        """
        item = ProviderCallLogItem(
            id="550e8400-e29b-41d4-a716-446655440000",
            request_id="req_cloud_abc123",
            feature="ai_copy_cloud",
            provider="deepseek",
            model="deepseek-chat",
            status="success",
            input_tokens=120,
            output_tokens=80,
            total_tokens=200,
            estimated_cost=0.002,
            credits_charged=1,
            created_at="2026-06-20T10:30:00Z",
        )
        # 验证没有意外暴露的隐私字段
        assert not hasattr(item, "raw_prompt")
        assert not hasattr(item, "api_key")
        assert not hasattr(item, "token")
        assert not hasattr(item, "raw_usage_json")
        assert not hasattr(item, "original_image")


# ============================================================
# ProviderCallLogListData 测试
# ============================================================


class TestProviderCallLogListData:
    """分页列表数据 DTO 测试"""

    def test_create_empty_list(self):
        """创建空列表"""
        data = ProviderCallLogListData(
            items=[],
            total=0,
            limit=50,
            offset=0,
        )
        assert data.items == []
        assert data.total == 0
        assert data.limit == 50
        assert data.offset == 0

    def test_create_list_with_items(self):
        """创建带条目的列表"""
        item = ProviderCallLogItem(
            id="550e8400-e29b-41d4-a716-446655440000",
            request_id="req_cloud_abc123",
            feature="ai_copy_cloud",
            provider="deepseek",
            model="deepseek-chat",
            status="success",
            input_tokens=120,
            output_tokens=80,
            total_tokens=200,
            estimated_cost=0.002,
            credits_charged=1,
            latency_ms=1200,
            created_at="2026-06-20T10:30:00Z",
        )
        data = ProviderCallLogListData(
            items=[item],
            total=1,
            limit=50,
            offset=0,
        )
        assert len(data.items) == 1
        assert data.items[0].feature == "ai_copy_cloud"
        assert data.total == 1

    def test_list_data_serialization(self):
        """分页列表序列化为 JSON"""
        data = ProviderCallLogListData(
            items=[],
            total=0,
            limit=50,
            offset=0,
        )
        json_str = data.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["items"] == []
        assert parsed["total"] == 0
        assert parsed["limit"] == 50
        assert parsed["offset"] == 0

    def test_list_data_deserialization(self):
        """从 JSON 反序列化分页列表"""
        json_str = json.dumps({
            "items": [],
            "total": 0,
            "limit": 50,
            "offset": 0,
        })
        data = ProviderCallLogListData.model_validate_json(json_str)
        assert data.items == []
        assert data.total == 0


# ============================================================
# ProviderCallLogListResponse 测试
# ============================================================


class TestProviderCallLogListResponse:
    """查询响应 DTO 测试"""

    def test_success_response(self):
        """成功响应 — 返回调用日志列表"""
        item = ProviderCallLogItem(
            id="550e8400-e29b-41d4-a716-446655440000",
            request_id="req_cloud_abc123",
            feature="ai_copy_cloud",
            provider="deepseek",
            model="deepseek-chat",
            status="success",
            input_tokens=120,
            output_tokens=80,
            total_tokens=200,
            estimated_cost=0.002,
            credits_charged=1,
            latency_ms=1200,
            created_at="2026-06-20T10:30:00Z",
        )
        resp = ProviderCallLogListResponse(
            success=True,
            data=ProviderCallLogListData(
                items=[item],
                total=1,
                limit=50,
                offset=0,
            ),
            error=None,
            request_id="req_cloud_resp_001",
        )
        assert resp.success is True
        assert resp.data is not None
        assert len(resp.data.items) == 1
        assert resp.data.items[0].feature == "ai_copy_cloud"
        assert resp.data.total == 1
        assert resp.error is None
        assert resp.request_id == "req_cloud_resp_001"

    def test_success_response_empty(self):
        """成功响应 — 空列表"""
        resp = ProviderCallLogListResponse(
            success=True,
            data=ProviderCallLogListData(
                items=[],
                total=0,
                limit=50,
                offset=0,
            ),
            error=None,
            request_id="req_cloud_resp_002",
        )
        assert resp.success is True
        assert resp.data.items == []
        assert resp.data.total == 0

    def test_error_response_unauthorized(self):
        """错误响应 — 未认证"""
        resp = ProviderCallLogListResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="AUTH_REQUIRED",
                message="需要登录才能查询调用日志",
            ),
            request_id="req_cloud_resp_003",
        )
        assert resp.success is False
        assert resp.data is None
        assert resp.error is not None
        assert resp.error.code == "AUTH_REQUIRED"
        assert resp.error.message == "需要登录才能查询调用日志"

    def test_error_response_validation(self):
        """错误响应 — 参数校验失败"""
        resp = ProviderCallLogListResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="limit 参数超出范围",
                details={"limit": "最大值为 100"},
            ),
            request_id="req_cloud_resp_004",
        )
        assert resp.success is False
        assert resp.error.code == "VALIDATION_ERROR"
        assert resp.error.details == {"limit": "最大值为 100"}

    def test_response_serialization_success(self):
        """成功响应序列化为 JSON"""
        item = ProviderCallLogItem(
            id="550e8400-e29b-41d4-a716-446655440000",
            request_id="req_cloud_abc123",
            feature="ai_copy_cloud",
            provider="deepseek",
            model="deepseek-chat",
            status="success",
            input_tokens=120,
            output_tokens=80,
            total_tokens=200,
            estimated_cost=0.002,
            credits_charged=1,
            latency_ms=1200,
            created_at="2026-06-20T10:30:00Z",
        )
        resp = ProviderCallLogListResponse(
            success=True,
            data=ProviderCallLogListData(
                items=[item],
                total=1,
                limit=50,
                offset=0,
            ),
            error=None,
            request_id="req_cloud_resp_001",
        )
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert len(parsed["data"]["items"]) == 1
        assert parsed["data"]["items"][0]["feature"] == "ai_copy_cloud"
        assert parsed["error"] is None
        assert parsed["request_id"] == "req_cloud_resp_001"

    def test_response_serialization_error(self):
        """错误响应序列化为 JSON"""
        resp = ProviderCallLogListResponse(
            success=False,
            data=None,
            error=ErrorDetail(code="AUTH_REQUIRED", message="需要登录"),
            request_id="req_cloud_resp_003",
        )
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is False
        assert parsed["data"] is None
        assert parsed["error"]["code"] == "AUTH_REQUIRED"
        assert parsed["request_id"] == "req_cloud_resp_003"

    def test_response_deserialization_success(self):
        """从 JSON 反序列化成功响应"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "request_id": "req_cloud_abc123",
                        "feature": "ai_copy_cloud",
                        "provider": "deepseek",
                        "model": "deepseek-chat",
                        "status": "success",
                        "error_code": None,
                        "input_tokens": 120,
                        "output_tokens": 80,
                        "total_tokens": 200,
                        "estimated_cost": 0.002,
                        "credits_charged": 1,
                        "latency_ms": 1200,
                        "created_at": "2026-06-20T10:30:00Z",
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
            },
            "error": None,
            "request_id": "req_cloud_resp_001",
        })
        resp = ProviderCallLogListResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data is not None
        assert resp.data.total == 1
        assert resp.data.items[0].feature == "ai_copy_cloud"
        assert resp.error is None

    def test_response_deserialization_error(self):
        """从 JSON 反序列化错误响应"""
        json_str = json.dumps({
            "success": False,
            "data": None,
            "error": {
                "code": "AUTH_REQUIRED",
                "message": "需要登录才能查询调用日志",
            },
            "request_id": "req_cloud_resp_003",
        })
        resp = ProviderCallLogListResponse.model_validate_json(json_str)
        assert resp.success is False
        assert resp.data is None
        assert resp.error.code == "AUTH_REQUIRED"

    def test_response_deserialization_paginated(self):
        """从 JSON 反序列化带筛选的分页响应"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440010",
                        "request_id": "req_cloud_jkl012",
                        "feature": "ai_render_cloud",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "status": "failed",
                        "error_code": "PROVIDER_RATE_LIMITED",
                        "input_tokens": 30,
                        "output_tokens": 0,
                        "total_tokens": 30,
                        "estimated_cost": 0.0,
                        "credits_charged": 0,
                        "latency_ms": None,
                        "created_at": "2026-06-20T11:00:00Z",
                    }
                ],
                "total": 42,
                "limit": 50,
                "offset": 0,
            },
            "error": None,
            "request_id": "req_cloud_resp_005",
        })
        resp = ProviderCallLogListResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.total == 42
        assert resp.data.items[0].status == "failed"
        assert resp.data.items[0].error_code == "PROVIDER_RATE_LIMITED"


# ============================================================
# YAML 契约一致性测试
# ============================================================

class TestYamlContractConsistency:
    """验证 Python DTO 与 OpenAPI YAML 契约的一致性"""

    def test_success_response_structure(self):
        """
        YAML 示例：成功查询 — 应与 DTO 兼容。
        验证 API_INDEX.md 中定义的字段与 DTO 一致。
        """
        json_str = json.dumps({
            "success": True,
            "data": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "request_id": "req_cloud_abc123",
                        "feature": "ai_copy_cloud",
                        "provider": "deepseek",
                        "model": "deepseek-chat",
                        "status": "success",
                        "error_code": None,
                        "input_tokens": 120,
                        "output_tokens": 80,
                        "total_tokens": 200,
                        "estimated_cost": 0.002,
                        "credits_charged": 1,
                        "latency_ms": 1200,
                        "created_at": "2026-06-20T10:30:00Z",
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
            },
            "error": None,
            "request_id": "req_cloud_resp_001",
        })
        resp = ProviderCallLogListResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data is not None
        assert resp.data.items[0].id == "550e8400-e29b-41d4-a716-446655440000"
        assert resp.data.items[0].feature == "ai_copy_cloud"
        assert resp.data.items[0].provider == "deepseek"
        assert resp.data.items[0].model == "deepseek-chat"
        assert resp.data.items[0].status == "success"
        assert resp.data.items[0].input_tokens == 120
        assert resp.data.items[0].output_tokens == 80
        assert resp.data.items[0].total_tokens == 200
        assert resp.data.items[0].estimated_cost == 0.002
        assert resp.data.items[0].credits_charged == 1
        assert resp.data.items[0].latency_ms == 1200
        assert resp.data.total == 1

    def test_response_roundtrip(self):
        """成功响应对象序列化/反序列化往返一致性"""
        item = ProviderCallLogItem(
            id="550e8400-e29b-41d4-a716-446655440000",
            request_id="req_cloud_abc123",
            feature="ai_copy_cloud",
            provider="deepseek",
            model="deepseek-chat",
            status="success",
            error_code=None,
            input_tokens=120,
            output_tokens=80,
            total_tokens=200,
            estimated_cost=0.002,
            credits_charged=1,
            latency_ms=1200,
            created_at="2026-06-20T10:30:00Z",
        )
        original = ProviderCallLogListResponse(
            success=True,
            data=ProviderCallLogListData(
                items=[item],
                total=1,
                limit=50,
                offset=0,
            ),
            error=None,
            request_id="req_cloud_resp_001",
        )
        json_str = original.model_dump_json()
        restored = ProviderCallLogListResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data.total == original.data.total
        assert restored.data.items[0].feature == original.data.items[0].feature
        assert restored.data.items[0].provider == original.data.items[0].provider
        assert restored.data.items[0].status == original.data.items[0].status
        assert restored.data.items[0].estimated_cost == original.data.items[0].estimated_cost
        assert restored.data.items[0].credits_charged == original.data.items[0].credits_charged
        assert restored.data.items[0].latency_ms == original.data.items[0].latency_ms
        assert restored.error == original.error
        assert restored.request_id == original.request_id

    def test_error_response_roundtrip(self):
        """错误响应对象序列化/反序列化往返一致性"""
        original = ProviderCallLogListResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="AUTH_REQUIRED",
                message="需要登录才能查询调用日志",
            ),
            request_id="req_cloud_resp_003",
        )
        json_str = original.model_dump_json()
        restored = ProviderCallLogListResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data == original.data
        assert restored.error.code == original.error.code
        assert restored.error.message == original.error.message
        assert restored.request_id == original.request_id

    def test_api_index_fields_match(self):
        """
        验证 DTO 字段与 API_INDEX.md 中定义的 Provider Log 字段一致：
        id, request_id, feature, provider, model, status,
        input_tokens, output_tokens, total_tokens, estimated_cost,
        credits_charged, latency_ms, created_at
        """
        defined_fields = {
            "id", "request_id", "feature", "provider", "model",
            "status", "error_code", "input_tokens", "output_tokens", "total_tokens",
            "estimated_cost", "credits_charged", "latency_ms", "created_at",
        }
        # 获取 ProviderCallLogItem 的所有字段名
        dto_fields = set(ProviderCallLogItem.model_fields.keys())
        # 验证所有 API_INDEX.md 定义的字段都在 DTO 中
        assert defined_fields == dto_fields, (
            f"DTO 字段与 API_INDEX.md 不一致："
            f"DTO 多余字段={dto_fields - defined_fields}，"
            f"缺少字段={defined_fields - dto_fields}"
        )
