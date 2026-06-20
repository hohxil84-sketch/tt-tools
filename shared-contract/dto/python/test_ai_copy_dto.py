"""
ai_copy DTO 契约一致性测试。

测试 ai_copy.py 中的 Pydantic 模型与
shared-contract/openapi/ai-copy.yaml 的一致性。
"""

import json

import pytest
from pydantic import ValidationError

from ai_copy import (
    AiCopyGenerateData,
    AiCopyGenerateRequest,
    AiCopyGenerateResponse,
    ErrorDetail,
)


# ============================================================
# ErrorDetail 测试
# ============================================================


class TestErrorDetail:
    """ErrorDetail 通用错误结构测试"""

    def test_create_valid_error_detail(self):
        """正常创建错误详情"""
        err = ErrorDetail(code="CREDITS_NOT_ENOUGH", message="AI 额度不足")
        assert err.code == "CREDITS_NOT_ENOUGH"
        assert err.message == "AI 额度不足"
        assert err.details is None

    def test_create_error_detail_with_details(self):
        """带补充信息的错误详情"""
        err = ErrorDetail(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details={"scene": "缺少必填字段"},
        )
        assert err.details == {"scene": "缺少必填字段"}

    def test_error_detail_missing_code_fails(self):
        """缺少 code 字段应失败"""
        with pytest.raises(ValidationError):
            ErrorDetail(message="需要有效套餐")

    def test_error_detail_missing_message_fails(self):
        """缺少 message 字段应失败"""
        with pytest.raises(ValidationError):
            ErrorDetail(code="CREDITS_NOT_ENOUGH")


# ============================================================
# AiCopyGenerateRequest 测试
# ============================================================


class TestAiCopyGenerateRequest:
    """文案生成请求 DTO 测试"""

    def test_create_minimal_valid_request(self):
        """最小必填字段创建请求 — 不含可选字段"""
        req = AiCopyGenerateRequest(
            scene="poster",
            product_name="快印宣传单",
            selling_points=["当天取件", "高清印刷"],
            tone="direct",
            client_request_id="req_client_abc123",
        )
        assert req.scene == "poster"
        assert req.product_name == "快印宣传单"
        assert req.selling_points == ["当天取件", "高清印刷"]
        assert req.tone == "direct"
        assert req.client_request_id == "req_client_abc123"
        # 可选字段默认 None
        assert req.target_audience is None
        assert req.platform is None
        assert req.extra_requirements is None

    def test_create_full_request(self):
        """全部字段创建请求 — 含所有可选字段"""
        req = AiCopyGenerateRequest(
            scene="poster",
            product_name="快印宣传单",
            selling_points=["当天取件", "高清印刷"],
            target_audience="附近商户",
            tone="direct",
            platform="offline_poster",
            extra_requirements="突出开业活动",
            client_request_id="req_client_xyz789",
        )
        assert req.scene == "poster"
        assert req.target_audience == "附近商户"
        assert req.platform == "offline_poster"
        assert req.extra_requirements == "突出开业活动"

    def test_create_social_media_request(self):
        """社交媒体场景请求"""
        req = AiCopyGenerateRequest(
            scene="social_media",
            product_name="定制名片",
            selling_points=["免费设计", "24小时发货"],
            target_audience="商务人士",
            tone="professional",
            platform="wechat",
            extra_requirements="强调高端质感",
            client_request_id="req_client_sm001",
        )
        assert req.scene == "social_media"
        assert req.tone == "professional"
        assert req.platform == "wechat"

    def test_empty_selling_points(self):
        """空的卖点列表 — 应允许（云端可能自己发挥）"""
        req = AiCopyGenerateRequest(
            scene="email",
            product_name="印刷服务",
            selling_points=[],
            tone="warm",
            client_request_id="req_001",
        )
        assert req.selling_points == []

    def test_missing_scene_fails(self):
        """缺少 scene 字段应失败"""
        with pytest.raises(ValidationError):
            AiCopyGenerateRequest(
                product_name="快印宣传单",
                selling_points=["当天取件"],
                tone="direct",
                client_request_id="req_001",
            )

    def test_missing_product_name_fails(self):
        """缺少 product_name 字段应失败"""
        with pytest.raises(ValidationError):
            AiCopyGenerateRequest(
                scene="poster",
                selling_points=["当天取件"],
                tone="direct",
                client_request_id="req_001",
            )

    def test_missing_tone_fails(self):
        """缺少 tone 字段应失败"""
        with pytest.raises(ValidationError):
            AiCopyGenerateRequest(
                scene="poster",
                product_name="快印宣传单",
                selling_points=["当天取件"],
                client_request_id="req_001",
            )

    def test_missing_client_request_id_fails(self):
        """缺少 client_request_id 字段应失败"""
        with pytest.raises(ValidationError):
            AiCopyGenerateRequest(
                scene="poster",
                product_name="快印宣传单",
                selling_points=["当天取件"],
                tone="direct",
            )

    def test_selling_points_not_list_fails(self):
        """selling_points 不是列表应失败"""
        with pytest.raises(ValidationError):
            AiCopyGenerateRequest(
                scene="poster",
                product_name="快印宣传单",
                selling_points="当天取件,高清印刷",  # 错误：应该是 list
                tone="direct",
                client_request_id="req_001",
            )

    # ---- 客户端禁止提交字段测试 ----

    def test_client_prohibited_user_id_rejected(self):
        """客户端禁止提交 user_id"""
        with pytest.raises(ValidationError):
            AiCopyGenerateRequest(
                scene="poster",
                product_name="快印宣传单",
                selling_points=["当天取件"],
                tone="direct",
                client_request_id="req_001",
                user_id="some-user-id",  # 客户端禁止提交
            )

    def test_client_prohibited_plan_code_rejected(self):
        """客户端禁止提交 plan_code"""
        with pytest.raises(ValidationError):
            AiCopyGenerateRequest(
                scene="poster",
                product_name="快印宣传单",
                selling_points=["当天取件"],
                tone="direct",
                client_request_id="req_001",
                plan_code="pro",  # 客户端禁止提交
            )

    def test_client_prohibited_provider_rejected(self):
        """客户端禁止提交 provider"""
        with pytest.raises(ValidationError):
            AiCopyGenerateRequest(
                scene="poster",
                product_name="快印宣传单",
                selling_points=["当天取件"],
                tone="direct",
                client_request_id="req_001",
                provider="openai",  # 客户端禁止提交
            )

    def test_client_prohibited_model_rejected(self):
        """客户端禁止提交 model"""
        with pytest.raises(ValidationError):
            AiCopyGenerateRequest(
                scene="poster",
                product_name="快印宣传单",
                selling_points=["当天取件"],
                tone="direct",
                client_request_id="req_001",
                model="gpt-4o",  # 客户端禁止提交
            )

    def test_client_prohibited_estimated_cost_rejected(self):
        """客户端禁止提交 estimated_cost"""
        with pytest.raises(ValidationError):
            AiCopyGenerateRequest(
                scene="poster",
                product_name="快印宣传单",
                selling_points=["当天取件"],
                tone="direct",
                client_request_id="req_001",
                estimated_cost=0.002,  # 客户端禁止提交
            )

    def test_client_prohibited_credits_charged_rejected(self):
        """客户端禁止提交 credits_charged"""
        with pytest.raises(ValidationError):
            AiCopyGenerateRequest(
                scene="poster",
                product_name="快印宣传单",
                selling_points=["当天取件"],
                tone="direct",
                client_request_id="req_001",
                credits_charged=1,  # 客户端禁止提交
            )

    # ---- 序列化/反序列化测试 ----

    def test_request_serialization_minimal(self):
        """最小请求序列化为 JSON"""
        req = AiCopyGenerateRequest(
            scene="poster",
            product_name="快印宣传单",
            selling_points=["当天取件", "高清印刷"],
            tone="direct",
            client_request_id="req_client_abc123",
        )
        json_str = req.model_dump_json()
        data = json.loads(json_str)
        assert data["scene"] == "poster"
        assert data["product_name"] == "快印宣传单"
        assert data["selling_points"] == ["当天取件", "高清印刷"]
        assert data["tone"] == "direct"
        assert data["client_request_id"] == "req_client_abc123"
        # 可选未填字段不包含在序列化输出中（pydantic 默认 exclude_none 需显式配置）
        # 但 model_dump_json 默认 exclude_unset=False，会输出 null

    def test_request_deserialization_full(self):
        """从 JSON 反序列化完整请求（对齐 API_INDEX.md 示例）"""
        json_str = json.dumps({
            "scene": "poster",
            "product_name": "快印宣传单",
            "selling_points": ["当天取件", "高清印刷"],
            "target_audience": "附近商户",
            "tone": "direct",
            "platform": "offline_poster",
            "extra_requirements": "突出开业活动",
            "client_request_id": "req_client_xxx",
        })
        req = AiCopyGenerateRequest.model_validate_json(json_str)
        assert req.scene == "poster"
        assert req.product_name == "快印宣传单"
        assert req.selling_points == ["当天取件", "高清印刷"]
        assert req.target_audience == "附近商户"
        assert req.tone == "direct"
        assert req.platform == "offline_poster"
        assert req.extra_requirements == "突出开业活动"
        assert req.client_request_id == "req_client_xxx"

    def test_request_roundtrip(self):
        """请求对象序列化/反序列化往返一致性"""
        original = AiCopyGenerateRequest(
            scene="poster",
            product_name="快印宣传单",
            selling_points=["当天取件", "高清印刷"],
            target_audience="附近商户",
            tone="direct",
            platform="offline_poster",
            extra_requirements="突出开业活动",
            client_request_id="req_client_xxx",
        )
        json_str = original.model_dump_json()
        restored = AiCopyGenerateRequest.model_validate_json(json_str)
        assert restored.scene == original.scene
        assert restored.product_name == original.product_name
        assert restored.selling_points == original.selling_points
        assert restored.target_audience == original.target_audience
        assert restored.tone == original.tone
        assert restored.platform == original.platform
        assert restored.extra_requirements == original.extra_requirements
        assert restored.client_request_id == original.client_request_id


# ============================================================
# AiCopyGenerateData 测试
# ============================================================


class TestAiCopyGenerateData:
    """文案生成结果数据 DTO 测试"""

    def test_create_valid_data(self):
        """正常创建生成结果数据"""
        data = AiCopyGenerateData(
            feature="ai_copy_cloud",
            text="开业大促，高清快印，当天取件！",
            variants=["开业印刷不用等，高清宣传单当天取。"],
            provider="deepseek",
            model="deepseek-chat",
            estimated_cost=0.002,
            credits_charged=1,
            provider_call_id="550e8400-e29b-41d4-a716-446655440000",
        )
        assert data.feature == "ai_copy_cloud"
        assert data.text == "开业大促，高清快印，当天取件！"
        assert len(data.variants) == 1
        assert data.provider == "deepseek"
        assert data.model == "deepseek-chat"
        assert data.estimated_cost == 0.002
        assert data.credits_charged == 1
        assert data.provider_call_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_create_data_with_multiple_variants(self):
        """多个备选文案"""
        data = AiCopyGenerateData(
            feature="ai_copy_cloud",
            text="专业印刷，品质保证！",
            variants=["高品质印刷服务，满足您的商业需求。", "您的品牌，我们的印刷品质。"],
            provider="deepseek",
            model="deepseek-chat",
            estimated_cost=0.003,
            credits_charged=2,
            provider_call_id="660e8400-e29b-41d4-a716-446655440001",
        )
        assert len(data.variants) == 2
        assert data.variants[0] == "高品质印刷服务，满足您的商业需求。"

    def test_feature_must_be_ai_copy_cloud(self):
        """feature 必须为 ai_copy_cloud（OpenAPI const 约束）"""
        # Pydantic Literal 类型校验
        with pytest.raises(ValidationError):
            AiCopyGenerateData(
                feature="wrong_feature_code",  # 错误的功能码
                text="测试文案",
                variants=[],
                provider="deepseek",
                model="deepseek-chat",
                estimated_cost=0.001,
                credits_charged=1,
                provider_call_id="770e8400-e29b-41d4-a716-446655440002",
            )

    def test_missing_feature_fails(self):
        """缺少 feature 字段应失败"""
        with pytest.raises(ValidationError):
            AiCopyGenerateData(
                text="测试文案",
                variants=[],
                provider="deepseek",
                model="deepseek-chat",
                estimated_cost=0.001,
                credits_charged=1,
                provider_call_id="770e8400-e29b-41d4-a716-446655440002",
            )

    def test_missing_text_fails(self):
        """缺少 text 字段应失败"""
        with pytest.raises(ValidationError):
            AiCopyGenerateData(
                feature="ai_copy_cloud",
                variants=[],
                provider="deepseek",
                model="deepseek-chat",
                estimated_cost=0.001,
                credits_charged=1,
                provider_call_id="770e8400-e29b-41d4-a716-446655440002",
            )

    def test_missing_provider_fails(self):
        """缺少 provider 字段应失败"""
        with pytest.raises(ValidationError):
            AiCopyGenerateData(
                feature="ai_copy_cloud",
                text="测试文案",
                variants=[],
                model="deepseek-chat",
                estimated_cost=0.001,
                credits_charged=1,
                provider_call_id="770e8400-e29b-41d4-a716-446655440002",
            )

    def test_data_serialization(self):
        """生成结果序列化为 JSON"""
        data = AiCopyGenerateData(
            feature="ai_copy_cloud",
            text="开业大促，高清快印，当天取件！",
            variants=["开业印刷不用等，高清宣传单当天取。"],
            provider="deepseek",
            model="deepseek-chat",
            estimated_cost=0.002,
            credits_charged=1,
            provider_call_id="550e8400-e29b-41d4-a716-446655440000",
        )
        json_str = data.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["feature"] == "ai_copy_cloud"
        assert parsed["text"] == "开业大促，高清快印，当天取件！"
        assert parsed["provider"] == "deepseek"
        assert parsed["model"] == "deepseek-chat"
        assert parsed["estimated_cost"] == 0.002
        assert parsed["credits_charged"] == 1
        assert isinstance(parsed["variants"], list)

    def test_data_deserialization(self):
        """从 JSON 反序列化生成结果（对齐 API_INDEX.md 示例）"""
        json_str = json.dumps({
            "feature": "ai_copy_cloud",
            "text": "开业大促，高清快印，当天取件！",
            "variants": ["开业印刷不用等，高清宣传单当天取。"],
            "provider": "deepseek",
            "model": "deepseek-chat",
            "estimated_cost": 0.002,
            "credits_charged": 1,
            "provider_call_id": "550e8400-e29b-41d4-a716-446655440000",
        })
        data = AiCopyGenerateData.model_validate_json(json_str)
        assert data.feature == "ai_copy_cloud"
        assert data.text == "开业大促，高清快印，当天取件！"
        assert data.provider == "deepseek"
        assert data.model == "deepseek-chat"
        assert data.estimated_cost == 0.002
        assert data.credits_charged == 1
        assert data.provider_call_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_credits_charged_is_integer(self):
        """credits_charged 必须为整数（OpenAPI type: integer）"""
        data = AiCopyGenerateData(
            feature="ai_copy_cloud",
            text="测试文案",
            variants=[],
            provider="deepseek",
            model="deepseek-chat",
            estimated_cost=0.001,
            credits_charged=5,
            provider_call_id="880e8400-e29b-41d4-a716-446655440003",
        )
        assert isinstance(data.credits_charged, int)
        assert data.credits_charged == 5


# ============================================================
# AiCopyGenerateResponse 测试
# ============================================================


class TestAiCopyGenerateResponse:
    """文案生成响应 DTO 测试"""

    def test_success_response(self):
        """成功响应"""
        resp = AiCopyGenerateResponse(
            success=True,
            data=AiCopyGenerateData(
                feature="ai_copy_cloud",
                text="开业大促，高清快印，当天取件！",
                variants=["开业印刷不用等，高清宣传单当天取。"],
                provider="deepseek",
                model="deepseek-chat",
                estimated_cost=0.002,
                credits_charged=1,
                provider_call_id="550e8400-e29b-41d4-a716-446655440000",
            ),
            error=None,
            request_id="req_cloud_abc123",
        )
        assert resp.success is True
        assert resp.data is not None
        assert resp.data.text == "开业大促，高清快印，当天取件！"
        assert resp.data.credits_charged == 1
        assert resp.error is None
        assert resp.request_id == "req_cloud_abc123"

    def test_error_response_credits_not_enough(self):
        """错误响应 — 额度不足"""
        resp = AiCopyGenerateResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="CREDITS_NOT_ENOUGH",
                message="AI 额度不足，请充值或升级套餐",
            ),
            request_id="req_cloud_def456",
        )
        assert resp.success is False
        assert resp.data is None
        assert resp.error is not None
        assert resp.error.code == "CREDITS_NOT_ENOUGH"
        assert resp.error.message == "AI 额度不足，请充值或升级套餐"

    def test_error_response_provider_timeout(self):
        """错误响应 — Provider 超时"""
        resp = AiCopyGenerateResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="PROVIDER_TIMEOUT",
                message="AI 服务调用超时，请稍后重试",
            ),
            request_id="req_cloud_ghi789",
        )
        assert resp.success is False
        assert resp.error.code == "PROVIDER_TIMEOUT"

    def test_error_response_unauthorized(self):
        """错误响应 — 未认证"""
        resp = AiCopyGenerateResponse(
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

    # ---- 序列化/反序列化测试 ----

    def test_response_serialization_success(self):
        """成功响应序列化为 JSON"""
        resp = AiCopyGenerateResponse(
            success=True,
            data=AiCopyGenerateData(
                feature="ai_copy_cloud",
                text="开业大促，高清快印，当天取件！",
                variants=["开业印刷不用等，高清宣传单当天取。"],
                provider="deepseek",
                model="deepseek-chat",
                estimated_cost=0.002,
                credits_charged=1,
                provider_call_id="550e8400-e29b-41d4-a716-446655440000",
            ),
            error=None,
            request_id="req_cloud_abc123",
        )
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["data"]["text"] == "开业大促，高清快印，当天取件！"
        assert parsed["error"] is None
        assert parsed["request_id"] == "req_cloud_abc123"

    def test_response_serialization_error(self):
        """错误响应序列化为 JSON"""
        resp = AiCopyGenerateResponse(
            success=False,
            data=None,
            error=ErrorDetail(code="CREDITS_NOT_ENOUGH", message="AI 额度不足"),
            request_id="req_cloud_def456",
        )
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is False
        assert parsed["data"] is None
        assert parsed["error"]["code"] == "CREDITS_NOT_ENOUGH"
        assert parsed["request_id"] == "req_cloud_def456"

    def test_response_deserialization_success(self):
        """从 JSON 反序列化成功响应（对齐 API_INDEX.md 示例）"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "feature": "ai_copy_cloud",
                "text": "开业大促，高清快印，当天取件！",
                "variants": ["开业印刷不用等，高清宣传单当天取。"],
                "provider": "deepseek",
                "model": "deepseek-chat",
                "estimated_cost": 0.002,
                "credits_charged": 1,
                "provider_call_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            "error": None,
            "request_id": "req_cloud_abc123",
        })
        resp = AiCopyGenerateResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.text == "开业大促，高清快印，当天取件！"
        assert resp.data.provider == "deepseek"
        assert resp.data.model == "deepseek-chat"
        assert resp.data.estimated_cost == 0.002
        assert resp.data.credits_charged == 1
        assert resp.error is None
        assert resp.request_id == "req_cloud_abc123"

    def test_response_deserialization_error(self):
        """从 JSON 反序列化错误响应"""
        json_str = json.dumps({
            "success": False,
            "data": None,
            "error": {
                "code": "CREDITS_NOT_ENOUGH",
                "message": "AI 额度不足，请充值或升级套餐",
            },
            "request_id": "req_cloud_def456",
        })
        resp = AiCopyGenerateResponse.model_validate_json(json_str)
        assert resp.success is False
        assert resp.data is None
        assert resp.error.code == "CREDITS_NOT_ENOUGH"

    def test_response_success_roundtrip(self):
        """成功响应对象序列化/反序列化往返一致性"""
        original = AiCopyGenerateResponse(
            success=True,
            data=AiCopyGenerateData(
                feature="ai_copy_cloud",
                text="开业大促，高清快印，当天取件！",
                variants=["开业印刷不用等，高清宣传单当天取。"],
                provider="deepseek",
                model="deepseek-chat",
                estimated_cost=0.002,
                credits_charged=1,
                provider_call_id="550e8400-e29b-41d4-a716-446655440000",
            ),
            error=None,
            request_id="req_cloud_abc123",
        )
        json_str = original.model_dump_json()
        restored = AiCopyGenerateResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data.text == original.data.text
        assert restored.data.feature == original.data.feature
        assert restored.data.provider == original.data.provider
        assert restored.data.model == original.data.model
        assert restored.data.estimated_cost == original.data.estimated_cost
        assert restored.data.credits_charged == original.data.credits_charged
        assert restored.data.provider_call_id == original.data.provider_call_id
        assert restored.error == original.error
        assert restored.request_id == original.request_id

    def test_response_error_roundtrip(self):
        """错误响应对象序列化/反序列化往返一致性"""
        original = AiCopyGenerateResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="PROVIDER_TIMEOUT",
                message="AI 服务调用超时",
                details={"retry_after": 5},
            ),
            request_id="req_cloud_timeout001",
        )
        json_str = original.model_dump_json()
        restored = AiCopyGenerateResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data == original.data
        assert restored.error.code == original.error.code
        assert restored.error.message == original.error.message
        assert restored.error.details == original.error.details
        assert restored.request_id == original.request_id


# ============================================================
# YAML / API_INDEX.md 示例一致性测试
# ============================================================


class TestApiIndexExamples:
    """验证 API_INDEX.md 中定义的示例与 DTO 一致"""

    def test_request_example_from_api_index(self):
        """API_INDEX.md 示例请求 — 应与 DTO 兼容"""
        json_str = json.dumps({
            "scene": "poster",
            "product_name": "快印宣传单",
            "selling_points": ["当天取件", "高清印刷"],
            "target_audience": "附近商户",
            "tone": "direct",
            "platform": "offline_poster",
            "extra_requirements": "突出开业活动",
            "client_request_id": "req_client_xxx",
        })
        req = AiCopyGenerateRequest.model_validate_json(json_str)
        assert req.scene == "poster"
        assert req.product_name == "快印宣传单"
        assert req.selling_points == ["当天取件", "高清印刷"]
        assert req.target_audience == "附近商户"
        assert req.tone == "direct"
        assert req.platform == "offline_poster"
        assert req.extra_requirements == "突出开业活动"

    def test_response_example_from_api_index(self):
        """API_INDEX.md 示例响应 — 应与 DTO 兼容"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "feature": "ai_copy_cloud",
                "text": "开业大促，高清快印，当天取件！",
                "variants": ["开业印刷不用等，高清宣传单当天取。"],
                "provider": "deepseek",
                "model": "deepseek-chat",
                "estimated_cost": 0.002,
                "credits_charged": 1,
                "provider_call_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            "error": None,
            "request_id": "req_cloud_abc123",
        })
        resp = AiCopyGenerateResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.feature == "ai_copy_cloud"
        assert resp.data.text == "开业大促，高清快印，当天取件！"
        assert resp.data.variants == ["开业印刷不用等，高清宣传单当天取。"]
        assert resp.data.provider == "deepseek"
        assert resp.data.model == "deepseek-chat"
        assert resp.data.estimated_cost == 0.002
        assert resp.data.credits_charged == 1

    def test_credits_charged_must_be_integer_in_response(self):
        """credits_charged 在响应中必须为整数（OpenAPI type: integer）"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "feature": "ai_copy_cloud",
                "text": "测试文案",
                "variants": [],
                "provider": "deepseek",
                "model": "deepseek-chat",
                "estimated_cost": 0.001,
                "credits_charged": 1,
                "provider_call_id": "990e8400-e29b-41d4-a716-446655440004",
            },
            "error": None,
            "request_id": "req_cloud_test001",
        })
        resp = AiCopyGenerateResponse.model_validate_json(json_str)
        assert isinstance(resp.data.credits_charged, int)
