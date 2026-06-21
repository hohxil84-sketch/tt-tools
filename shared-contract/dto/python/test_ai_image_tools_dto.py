"""
ai_image_tools DTO 契约一致性测试。

测试 ai_image_tools.py 中的 Pydantic 模型与
shared-contract/openapi/ai-image-tools.yaml 的一致性。
"""

import json

import pytest
from pydantic import ValidationError

from ai_image_tools import (
    AiImageToolTaskData,
    AiImageToolTaskResponse,
    CreateAiImageToolTaskRequest,
    CreateAiImageToolTaskResponse,
    CreatedTaskData,
    ErrorDetail,
    ResultFile,
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
            ErrorDetail(code="CREDITS_NOT_ENOUGH")


# ============================================================
# ResultFile 测试
# ============================================================


class TestResultFile:
    """ResultFile 结果文件结构测试"""

    def test_create_minimal_result_file(self):
        """最小必填字段创建结果文件"""
        f = ResultFile(
            file_id="550e8400-e29b-41d4-a716-446655440000",
            mime_type="image/png",
        )
        assert f.file_id == "550e8400-e29b-41d4-a716-446655440000"
        assert f.mime_type == "image/png"
        assert f.url is None
        assert f.width is None
        assert f.height is None

    def test_create_full_result_file(self):
        """完整字段创建结果文件"""
        f = ResultFile(
            file_id="660e8400-e29b-41d4-a716-446655440001",
            url="https://cdn.example.com/tools/result_001.png",
            mime_type="image/png",
            width=1920,
            height=1080,
        )
        assert f.file_id == "660e8400-e29b-41d4-a716-446655440001"
        assert f.url == "https://cdn.example.com/tools/result_001.png"
        assert f.mime_type == "image/png"
        assert f.width == 1920
        assert f.height == 1080

    def test_result_file_svg_mime_type(self):
        """转矢量功能返回 SVG 文件（矢量图）"""
        f = ResultFile(
            file_id="670e8400-e29b-41d4-a716-446655440002",
            url="https://cdn.example.com/tools/vectorized.svg",
            mime_type="image/svg+xml",
        )
        assert f.mime_type == "image/svg+xml"

    def test_result_file_pdf_mime_type(self):
        """OCR 功能可能返回 PDF 文件"""
        f = ResultFile(
            file_id="680e8400-e29b-41d4-a716-446655440003",
            url="https://cdn.example.com/tools/ocr_result.pdf",
            mime_type="application/pdf",
        )
        assert f.mime_type == "application/pdf"

    def test_result_file_missing_file_id_fails(self):
        """缺少 file_id 字段应失败"""
        with pytest.raises(ValidationError):
            ResultFile(mime_type="image/png")

    def test_result_file_missing_mime_type_fails(self):
        """缺少 mime_type 字段应失败"""
        with pytest.raises(ValidationError):
            ResultFile(file_id="550e8400-e29b-41d4-a716-446655440000")

    def test_result_file_serialization(self):
        """结果文件序列化为 JSON"""
        f = ResultFile(
            file_id="770e8400-e29b-41d4-a716-446655440002",
            url="https://cdn.example.com/tools/result_002.jpg",
            mime_type="image/jpeg",
            width=1024,
            height=1024,
        )
        json_str = f.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["file_id"] == "770e8400-e29b-41d4-a716-446655440002"
        assert parsed["url"] == "https://cdn.example.com/tools/result_002.jpg"
        assert parsed["mime_type"] == "image/jpeg"
        assert parsed["width"] == 1024
        assert parsed["height"] == 1024

    def test_result_file_deserialization(self):
        """从 JSON 反序列化结果文件"""
        json_str = json.dumps({
            "file_id": "880e8400-e29b-41d4-a716-446655440003",
            "url": "https://cdn.example.com/tools/result_003.png",
            "mime_type": "image/png",
            "width": 800,
            "height": 600,
        })
        f = ResultFile.model_validate_json(json_str)
        assert f.file_id == "880e8400-e29b-41d4-a716-446655440003"
        assert f.url == "https://cdn.example.com/tools/result_003.png"
        assert f.mime_type == "image/png"
        assert f.width == 800
        assert f.height == 600

    def test_result_file_roundtrip(self):
        """结果文件序列化/反序列化往返一致性"""
        original = ResultFile(
            file_id="990e8400-e29b-41d4-a716-446655440004",
            url="https://cdn.example.com/tools/result_004.png",
            mime_type="image/png",
            width=1920,
            height=1080,
        )
        json_str = original.model_dump_json()
        restored = ResultFile.model_validate_json(json_str)
        assert restored.file_id == original.file_id
        assert restored.url == original.url
        assert restored.mime_type == original.mime_type
        assert restored.width == original.width
        assert restored.height == original.height


# ============================================================
# CreateAiImageToolTaskRequest 测试
# ============================================================


class TestCreateAiImageToolTaskRequest:
    """创建高级图片 AI 任务请求 DTO 测试"""

    # ---- 正确创建测试 ----

    def test_create_upscale_request(self):
        """创建高清修复任务请求"""
        req = CreateAiImageToolTaskRequest(
            feature="upscale_image_cloud",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
            client_request_id="req_client_upscale_001",
        )
        assert req.feature == "upscale_image_cloud"
        assert req.input_file_ids == ["550e8400-e29b-41d4-a716-446655440000"]
        assert req.client_request_id == "req_client_upscale_001"
        assert req.options is None

    def test_create_vectorize_request(self):
        """创建转矢量任务请求"""
        req = CreateAiImageToolTaskRequest(
            feature="vectorize_image_cloud",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440001"],
            options={"output_format": "svg", "colors": 16},
            client_request_id="req_client_vectorize_001",
        )
        assert req.feature == "vectorize_image_cloud"
        assert req.options == {"output_format": "svg", "colors": 16}

    def test_create_ai_edit_request(self):
        """创建 AI 改图任务请求 — 含编辑选项"""
        req = CreateAiImageToolTaskRequest(
            feature="ai_edit_image_cloud",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440002"],
            options={"operation": "background_replace", "prompt": "白色背景"},
            client_request_id="req_client_edit_001",
        )
        assert req.feature == "ai_edit_image_cloud"
        assert req.options["operation"] == "background_replace"
        assert req.options["prompt"] == "白色背景"

    def test_create_remove_bg_request(self):
        """创建高级抠图任务请求"""
        req = CreateAiImageToolTaskRequest(
            feature="remove_bg_cloud",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440003"],
            options={"refine_edges": True},
            client_request_id="req_client_removebg_001",
        )
        assert req.feature == "remove_bg_cloud"
        assert req.options == {"refine_edges": True}

    def test_create_ocr_request(self):
        """创建高级 OCR 任务请求 — 含语言选项"""
        req = CreateAiImageToolTaskRequest(
            feature="ocr_cloud",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440004"],
            options={"language": "zh-CN", "engine": "accurate"},
            client_request_id="req_client_ocr_001",
        )
        assert req.feature == "ocr_cloud"
        assert req.options["language"] == "zh-CN"
        assert req.options["engine"] == "accurate"

    def test_create_minimal_valid_request(self):
        """最小必填字段创建请求 — 不含 options"""
        req = CreateAiImageToolTaskRequest(
            feature="upscale_image_cloud",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
            client_request_id="req_client_abc123",
        )
        assert req.feature == "upscale_image_cloud"
        assert req.input_file_ids == ["550e8400-e29b-41d4-a716-446655440000"]
        assert req.client_request_id == "req_client_abc123"
        assert req.options is None

    def test_create_request_multiple_input_files(self):
        """多个输入文件的任务请求"""
        req = CreateAiImageToolTaskRequest(
            feature="ocr_cloud",
            input_file_ids=[
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440002",
                "550e8400-e29b-41d4-a716-446655440003",
            ],
            client_request_id="req_client_multi_001",
        )
        assert len(req.input_file_ids) == 3

    def test_empty_input_file_ids(self):
        """空的输入文件列表 — 应允许（某些功能可能不强制需要文件）"""
        req = CreateAiImageToolTaskRequest(
            feature="ai_edit_image_cloud",
            input_file_ids=[],
            client_request_id="req_001",
        )
        assert req.input_file_ids == []

    # ---- 所有功能码验证 ----

    def test_all_valid_features_accepted(self):
        """所有 5 个有效功能码都应通过校验"""
        valid_features = [
            "upscale_image_cloud",
            "vectorize_image_cloud",
            "ai_edit_image_cloud",
            "remove_bg_cloud",
            "ocr_cloud",
        ]
        for feature in valid_features:
            req = CreateAiImageToolTaskRequest(
                feature=feature,
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
            )
            assert req.feature == feature

    # ---- 必填字段缺失测试 ----

    def test_missing_feature_fails(self):
        """缺少 feature 字段应失败"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
            )

    def test_missing_input_file_ids_fails(self):
        """缺少 input_file_ids 字段应失败"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="upscale_image_cloud",
                client_request_id="req_001",
            )

    def test_missing_client_request_id_fails(self):
        """缺少 client_request_id 字段应失败"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="upscale_image_cloud",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
            )

    # ---- 功能码校验测试 ----

    def test_invalid_feature_rejected(self):
        """无效的功能码应被拒绝（不在 enum 列表中）"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="invalid_feature_code",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
            )

    def test_local_free_feature_rejected(self):
        """本地免费功能码不应通过云端 AI 接口提交"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="ocr_local",  # 这是本地免费功能码，不是云端 AI 功能码
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
            )

    def test_ai_copy_feature_rejected(self):
        """其他云端 AI 功能码不应通过本接口提交"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="ai_copy_cloud",  # 文案生成功能码，不是图片工具
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
            )

    # ---- 类型检查测试 ----

    def test_input_file_ids_not_list_fails(self):
        """input_file_ids 不是列表应失败"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="upscale_image_cloud",
                input_file_ids="not-a-list",  # 错误：应该是 list
                client_request_id="req_001",
            )

    def test_feature_not_string_fails(self):
        """feature 不是字符串应失败"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature=123,  # 错误：应该是字符串
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
            )

    # ---- 客户端禁止提交字段测试 ----

    def test_client_prohibited_user_id_rejected(self):
        """客户端禁止提交 user_id"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="upscale_image_cloud",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                user_id="some-user-id",  # 客户端禁止提交
            )

    def test_client_prohibited_plan_code_rejected(self):
        """客户端禁止提交 plan_code"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="upscale_image_cloud",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                plan_code="pro",  # 客户端禁止提交
            )

    def test_client_prohibited_provider_rejected(self):
        """客户端禁止提交 provider"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="upscale_image_cloud",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                provider="openai",  # 客户端禁止提交
            )

    def test_client_prohibited_model_rejected(self):
        """客户端禁止提交 model"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="remove_bg_cloud",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                model="sam-2",  # 客户端禁止提交
            )

    def test_client_prohibited_estimated_cost_rejected(self):
        """客户端禁止提交 estimated_cost"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="upscale_image_cloud",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                estimated_cost=0.05,  # 客户端禁止提交
            )

    def test_client_prohibited_credits_charged_rejected(self):
        """客户端禁止提交 credits_charged"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="upscale_image_cloud",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                credits_charged=10,  # 客户端禁止提交
            )

    def test_client_prohibited_device_id_rejected(self):
        """客户端禁止提交 device_id"""
        with pytest.raises(ValidationError):
            CreateAiImageToolTaskRequest(
                feature="ocr_cloud",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                device_id="device-uuid",  # 客户端禁止提交
            )

    # ---- 序列化/反序列化测试 ----

    def test_request_serialization_minimal(self):
        """最小请求序列化为 JSON"""
        req = CreateAiImageToolTaskRequest(
            feature="upscale_image_cloud",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
            client_request_id="req_client_abc123",
        )
        json_str = req.model_dump_json()
        data = json.loads(json_str)
        assert data["feature"] == "upscale_image_cloud"
        assert data["input_file_ids"] == ["550e8400-e29b-41d4-a716-446655440000"]
        assert data["client_request_id"] == "req_client_abc123"
        # options 为 None 时默认不序列化
        assert "options" not in data or data.get("options") is None

    def test_request_serialization_with_options(self):
        """含 options 的请求序列化为 JSON"""
        req = CreateAiImageToolTaskRequest(
            feature="vectorize_image_cloud",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440001"],
            options={"output_format": "svg", "colors": 16},
            client_request_id="req_client_vec001",
        )
        json_str = req.model_dump_json()
        data = json.loads(json_str)
        assert data["feature"] == "vectorize_image_cloud"
        assert data["options"] == {"output_format": "svg", "colors": 16}

    def test_request_deserialization_full(self):
        """从 JSON 反序列化完整请求 — 对齐 OpenAPI 示例结构"""
        json_str = json.dumps({
            "feature": "remove_bg_cloud",
            "input_file_ids": [
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440002",
            ],
            "options": {"refine_edges": True, "format": "png"},
            "client_request_id": "req_client_xxx",
        })
        req = CreateAiImageToolTaskRequest.model_validate_json(json_str)
        assert req.feature == "remove_bg_cloud"
        assert req.input_file_ids == [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
        ]
        assert req.options == {"refine_edges": True, "format": "png"}
        assert req.client_request_id == "req_client_xxx"

    def test_request_roundtrip(self):
        """请求对象序列化/反序列化往返一致性"""
        original = CreateAiImageToolTaskRequest(
            feature="ocr_cloud",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
            options={"language": "zh-CN", "engine": "accurate"},
            client_request_id="req_client_ocr_rtt",
        )
        json_str = original.model_dump_json()
        restored = CreateAiImageToolTaskRequest.model_validate_json(json_str)
        assert restored.feature == original.feature
        assert restored.input_file_ids == original.input_file_ids
        assert restored.options == original.options
        assert restored.client_request_id == original.client_request_id


# ============================================================
# CreatedTaskData 测试
# ============================================================


class TestCreatedTaskData:
    """创建任务响应数据 DTO 测试"""

    def test_create_valid_queued_task(self):
        """正常创建排队中任务数据"""
        data = CreatedTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="queued",
            feature="upscale_image_cloud",
            estimated_credits=30,
        )
        assert data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert data.status == "queued"
        assert data.feature == "upscale_image_cloud"
        assert data.estimated_credits == 30

    def test_feature_echoes_requested_value(self):
        """feature 字段回显请求中指定的功能码（不限定为单一值）"""
        for feature in [
            "upscale_image_cloud",
            "vectorize_image_cloud",
            "ai_edit_image_cloud",
            "remove_bg_cloud",
            "ocr_cloud",
        ]:
            data = CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature=feature,
                estimated_credits=30,
            )
            assert data.feature == feature

    def test_status_must_be_valid_enum(self):
        """status 必须为有效枚举值"""
        with pytest.raises(ValidationError):
            CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="unknown_status",  # 无效状态
                feature="upscale_image_cloud",
                estimated_credits=30,
            )

    def test_status_all_valid_values(self):
        """验证所有有效 status 值"""
        for status in ["queued", "running", "succeeded", "failed"]:
            data = CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status=status,
                feature="upscale_image_cloud",
                estimated_credits=30,
            )
            assert data.status == status

    def test_missing_task_id_fails(self):
        """缺少 task_id 字段应失败"""
        with pytest.raises(ValidationError):
            CreatedTaskData(
                status="queued",
                feature="upscale_image_cloud",
                estimated_credits=30,
            )

    def test_missing_status_fails(self):
        """缺少 status 字段应失败"""
        with pytest.raises(ValidationError):
            CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                feature="upscale_image_cloud",
                estimated_credits=30,
            )

    def test_missing_feature_fails(self):
        """缺少 feature 字段应失败"""
        with pytest.raises(ValidationError):
            CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                estimated_credits=30,
            )

    def test_missing_estimated_credits_fails(self):
        """缺少 estimated_credits 字段应失败"""
        with pytest.raises(ValidationError):
            CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature="upscale_image_cloud",
            )

    def test_estimated_credits_is_integer(self):
        """estimated_credits 必须为整数（OpenAPI type: integer）"""
        data = CreatedTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="queued",
            feature="ocr_cloud",
            estimated_credits=100,
        )
        assert isinstance(data.estimated_credits, int)
        assert data.estimated_credits == 100

    def test_created_task_data_serialization(self):
        """创建任务数据序列化为 JSON"""
        data = CreatedTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="queued",
            feature="upscale_image_cloud",
            estimated_credits=30,
        )
        json_str = data.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["task_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed["status"] == "queued"
        assert parsed["feature"] == "upscale_image_cloud"
        assert parsed["estimated_credits"] == 30

    def test_created_task_data_deserialization(self):
        """从 JSON 反序列化创建任务数据"""
        json_str = json.dumps({
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "queued",
            "feature": "remove_bg_cloud",
            "estimated_credits": 50,
        })
        data = CreatedTaskData.model_validate_json(json_str)
        assert data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert data.status == "queued"
        assert data.feature == "remove_bg_cloud"
        assert data.estimated_credits == 50


# ============================================================
# AiImageToolTaskData 测试
# ============================================================


class TestAiImageToolTaskData:
    """任务查询响应数据 DTO 测试"""

    def test_create_queued_task_data(self):
        """创建排队中任务查询数据 — provider 等字段为 None"""
        data = AiImageToolTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="queued",
            feature="upscale_image_cloud",
            result_files=[],
        )
        assert data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert data.status == "queued"
        assert data.feature == "upscale_image_cloud"
        assert data.result_files == []
        assert data.result_json is None
        assert data.provider is None
        assert data.model is None
        assert data.estimated_cost is None
        assert data.credits_charged is None
        assert data.provider_call_id is None

    def test_create_succeeded_upscale_task_data(self):
        """创建成功完成的高清修复任务查询数据 — 含结果文件"""
        data = AiImageToolTaskData(
            task_id="660e8400-e29b-41d4-a716-446655440001",
            status="succeeded",
            feature="upscale_image_cloud",
            result_files=[
                ResultFile(
                    file_id="770e8400-e29b-41d4-a716-446655440002",
                    url="https://cdn.example.com/tools/upscaled.png",
                    mime_type="image/png",
                    width=3840,
                    height=2160,
                )
            ],
            result_json={"original_width": 1920, "original_height": 1080, "scale": 2},
            provider="replicate",
            model="real-esrgan",
            estimated_cost=0.03,
            credits_charged=30,
            provider_call_id="880e8400-e29b-41d4-a716-446655440003",
        )
        assert data.status == "succeeded"
        assert data.feature == "upscale_image_cloud"
        assert len(data.result_files) == 1
        assert data.result_files[0].file_id == "770e8400-e29b-41d4-a716-446655440002"
        assert data.result_files[0].mime_type == "image/png"
        assert data.result_files[0].width == 3840
        assert data.result_json == {"original_width": 1920, "original_height": 1080, "scale": 2}
        assert data.provider == "replicate"
        assert data.model == "real-esrgan"
        assert data.estimated_cost == 0.03
        assert data.credits_charged == 30
        assert data.provider_call_id == "880e8400-e29b-41d4-a716-446655440003"

    def test_create_succeeded_ocr_task_data(self):
        """创建成功完成的 OCR 任务查询数据 — 含 OCR 文本结果"""
        data = AiImageToolTaskData(
            task_id="990e8400-e29b-41d4-a716-446655440004",
            status="succeeded",
            feature="ocr_cloud",
            result_files=[
                ResultFile(
                    file_id="aa0e8400-e29b-41d4-a716-446655440005",
                    url="https://cdn.example.com/tools/ocr_text.json",
                    mime_type="application/json",
                )
            ],
            result_json={
                "text": "今天去图文店打印名片",
                "confidence": 0.95,
                "language": "zh-CN",
            },
            provider="deepseek",
            model="deepseek-vl",
            estimated_cost=0.005,
            credits_charged=5,
            provider_call_id="bb0e8400-e29b-41d4-a716-446655440006",
        )
        assert data.status == "succeeded"
        assert data.feature == "ocr_cloud"
        assert data.result_json["text"] == "今天去图文店打印名片"
        assert data.result_json["confidence"] == 0.95
        assert data.provider == "deepseek"
        assert data.model == "deepseek-vl"

    def test_create_succeeded_vectorize_task_data(self):
        """创建成功完成的转矢量任务 — 含矢量图层信息"""
        data = AiImageToolTaskData(
            task_id="cc0e8400-e29b-41d4-a716-446655440007",
            status="succeeded",
            feature="vectorize_image_cloud",
            result_files=[
                ResultFile(
                    file_id="dd0e8400-e29b-41d4-a716-446655440008",
                    url="https://cdn.example.com/tools/vectorized.svg",
                    mime_type="image/svg+xml",
                )
            ],
            result_json={"paths": 152, "colors_used": 8, "format": "svg"},
            provider="vectorizer-ai",
            model="vectorizer-v2",
            estimated_cost=0.02,
            credits_charged=20,
            provider_call_id="ee0e8400-e29b-41d4-a716-446655440009",
        )
        assert data.feature == "vectorize_image_cloud"
        assert data.result_files[0].mime_type == "image/svg+xml"
        assert data.result_json["paths"] == 152

    def test_create_failed_task_data(self):
        """创建失败任务查询数据"""
        data = AiImageToolTaskData(
            task_id="ff0e8400-e29b-41d4-a716-446655440010",
            status="failed",
            feature="ai_edit_image_cloud",
            result_files=[],
        )
        assert data.status == "failed"
        assert data.result_files == []
        assert data.result_json is None

    def test_create_running_task_data(self):
        """创建运行中任务查询数据"""
        data = AiImageToolTaskData(
            task_id="110e8400-e29b-41d4-a716-446655440011",
            status="running",
            feature="remove_bg_cloud",
            result_files=[],
            provider="replicate",
            model="sam-2",
            provider_call_id="120e8400-e29b-41d4-a716-446655440012",
        )
        assert data.status == "running"
        assert data.provider == "replicate"
        assert data.model == "sam-2"
        assert data.provider_call_id == "120e8400-e29b-41d4-a716-446655440012"
        # 运行中尚未扣费
        assert data.estimated_cost is None
        assert data.credits_charged is None

    def test_status_must_be_valid_enum(self):
        """status 必须为有效枚举值"""
        with pytest.raises(ValidationError):
            AiImageToolTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="invalid_status",  # 无效状态
                feature="upscale_image_cloud",
                result_files=[],
            )

    def test_status_all_valid_values(self):
        """验证所有有效 status 值"""
        for status in ["queued", "running", "succeeded", "failed"]:
            data = AiImageToolTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status=status,
                feature="upscale_image_cloud",
                result_files=[],
            )
            assert data.status == status

    def test_missing_task_id_fails(self):
        """缺少 task_id 字段应失败"""
        with pytest.raises(ValidationError):
            AiImageToolTaskData(
                status="queued",
                feature="upscale_image_cloud",
                result_files=[],
            )

    def test_missing_status_fails(self):
        """缺少 status 字段应失败"""
        with pytest.raises(ValidationError):
            AiImageToolTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                feature="upscale_image_cloud",
                result_files=[],
            )

    def test_missing_feature_fails(self):
        """缺少 feature 字段应失败"""
        with pytest.raises(ValidationError):
            AiImageToolTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                result_files=[],
            )

    def test_result_files_defaults_to_empty_list(self):
        """未提供 result_files 时应默认空列表"""
        data = AiImageToolTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="queued",
            feature="upscale_image_cloud",
        )
        assert data.result_files == []

    def test_credits_charged_is_integer(self):
        """credits_charged 必须为整数（OpenAPI type: integer）"""
        data = AiImageToolTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="succeeded",
            feature="upscale_image_cloud",
            result_files=[],
            provider="replicate",
            model="real-esrgan",
            estimated_cost=0.05,
            credits_charged=50,
            provider_call_id="550e8400-e29b-41d4-a716-446655440001",
        )
        assert isinstance(data.credits_charged, int)
        assert data.credits_charged == 50

    # ---- 序列化/反序列化测试 ----

    def test_queued_task_data_serialization(self):
        """排队中任务数据序列化为 JSON — provider 等字段不序列化"""
        data = AiImageToolTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="queued",
            feature="upscale_image_cloud",
            result_files=[],
        )
        json_str = data.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["task_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed["status"] == "queued"
        assert parsed["feature"] == "upscale_image_cloud"
        assert parsed["result_files"] == []

    def test_succeeded_task_data_serialization(self):
        """成功任务数据序列化为 JSON — 含完整字段"""
        data = AiImageToolTaskData(
            task_id="660e8400-e29b-41d4-a716-446655440001",
            status="succeeded",
            feature="ocr_cloud",
            result_files=[
                ResultFile(
                    file_id="770e8400-e29b-41d4-a716-446655440002",
                    url="https://cdn.example.com/tools/ocr_result.json",
                    mime_type="application/json",
                )
            ],
            result_json={"text": "测试文本行", "confidence": 0.92},
            provider="deepseek",
            model="deepseek-vl",
            estimated_cost=0.005,
            credits_charged=5,
            provider_call_id="880e8400-e29b-41d4-a716-446655440003",
        )
        json_str = data.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["task_id"] == "660e8400-e29b-41d4-a716-446655440001"
        assert parsed["status"] == "succeeded"
        assert parsed["feature"] == "ocr_cloud"
        assert len(parsed["result_files"]) == 1
        assert parsed["result_json"] == {"text": "测试文本行", "confidence": 0.92}
        assert parsed["provider"] == "deepseek"
        assert parsed["model"] == "deepseek-vl"
        assert parsed["estimated_cost"] == 0.005
        assert parsed["credits_charged"] == 5

    def test_task_data_deserialization_succeeded(self):
        """从 JSON 反序列化成功任务数据"""
        json_str = json.dumps({
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "succeeded",
            "feature": "remove_bg_cloud",
            "result_files": [
                {
                    "file_id": "660e8400-e29b-41d4-a716-446655440001",
                    "url": "https://cdn.example.com/tools/bg_removed.png",
                    "mime_type": "image/png",
                    "width": 1024,
                    "height": 768,
                }
            ],
            "result_json": {"has_transparency": True},
            "provider": "replicate",
            "model": "sam-2",
            "estimated_cost": 0.04,
            "credits_charged": 40,
            "provider_call_id": "770e8400-e29b-41d4-a716-446655440002",
        })
        data = AiImageToolTaskData.model_validate_json(json_str)
        assert data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert data.status == "succeeded"
        assert data.feature == "remove_bg_cloud"
        assert len(data.result_files) == 1
        assert data.result_files[0].file_id == "660e8400-e29b-41d4-a716-446655440001"
        assert data.result_json == {"has_transparency": True}
        assert data.provider == "replicate"
        assert data.model == "sam-2"
        assert data.estimated_cost == 0.04
        assert data.credits_charged == 40
        assert data.provider_call_id == "770e8400-e29b-41d4-a716-446655440002"

    def test_task_data_roundtrip(self):
        """任务数据序列化/反序列化往返一致性"""
        original = AiImageToolTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="succeeded",
            feature="vectorize_image_cloud",
            result_files=[
                ResultFile(
                    file_id="660e8400-e29b-41d4-a716-446655440001",
                    url="https://cdn.example.com/tools/result.svg",
                    mime_type="image/svg+xml",
                )
            ],
            result_json={"paths": 100, "colors": 8},
            provider="vectorizer-ai",
            model="vectorizer-v2",
            estimated_cost=0.02,
            credits_charged=20,
            provider_call_id="770e8400-e29b-41d4-a716-446655440002",
        )
        json_str = original.model_dump_json()
        restored = AiImageToolTaskData.model_validate_json(json_str)
        assert restored.task_id == original.task_id
        assert restored.status == original.status
        assert restored.feature == original.feature
        assert len(restored.result_files) == len(original.result_files)
        assert restored.result_files[0].file_id == original.result_files[0].file_id
        assert restored.result_json == original.result_json
        assert restored.provider == original.provider
        assert restored.model == original.model
        assert restored.estimated_cost == original.estimated_cost
        assert restored.credits_charged == original.credits_charged
        assert restored.provider_call_id == original.provider_call_id


# ============================================================
# CreateAiImageToolTaskResponse 测试
# ============================================================


class TestCreateAiImageToolTaskResponse:
    """创建任务响应 DTO 测试"""

    def test_success_response_upscale(self):
        """成功响应 — 高清修复任务"""
        resp = CreateAiImageToolTaskResponse(
            success=True,
            data=CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature="upscale_image_cloud",
                estimated_credits=30,
            ),
            error=None,
            request_id="req_cloud_abc123",
        )
        assert resp.success is True
        assert resp.data is not None
        assert resp.data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert resp.data.status == "queued"
        assert resp.data.feature == "upscale_image_cloud"
        assert resp.data.estimated_credits == 30
        assert resp.error is None
        assert resp.request_id == "req_cloud_abc123"

    def test_success_response_ocr(self):
        """成功响应 — OCR 任务"""
        resp = CreateAiImageToolTaskResponse(
            success=True,
            data=CreatedTaskData(
                task_id="660e8400-e29b-41d4-a716-446655440001",
                status="queued",
                feature="ocr_cloud",
                estimated_credits=5,
            ),
            error=None,
            request_id="req_cloud_ocr001",
        )
        assert resp.success is True
        assert resp.data.feature == "ocr_cloud"
        assert resp.data.estimated_credits == 5

    def test_error_response_credits_not_enough(self):
        """错误响应 — 额度不足"""
        resp = CreateAiImageToolTaskResponse(
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
        resp = CreateAiImageToolTaskResponse(
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
        resp = CreateAiImageToolTaskResponse(
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

    def test_error_response_permission_denied(self):
        """错误响应 — 套餐权限不足"""
        resp = CreateAiImageToolTaskResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="PERMISSION_DENIED",
                message="当前套餐不支持此功能，请升级套餐",
            ),
            request_id="req_cloud_mno345",
        )
        assert resp.success is False
        assert resp.error.code == "PERMISSION_DENIED"

    def test_error_response_validation_error(self):
        """错误响应 — 参数校验失败"""
        resp = CreateAiImageToolTaskResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="参数校验失败",
                details={"feature": "不支持的功能码"},
            ),
            request_id="req_cloud_val001",
        )
        assert resp.success is False
        assert resp.error.code == "VALIDATION_ERROR"
        assert resp.error.details == {"feature": "不支持的功能码"}

    # ---- 序列化/反序列化测试 ----

    def test_response_serialization_success(self):
        """成功响应序列化为 JSON"""
        resp = CreateAiImageToolTaskResponse(
            success=True,
            data=CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature="remove_bg_cloud",
                estimated_credits=40,
            ),
            error=None,
            request_id="req_cloud_abc123",
        )
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["data"]["task_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed["data"]["status"] == "queued"
        assert parsed["data"]["feature"] == "remove_bg_cloud"
        assert parsed["data"]["estimated_credits"] == 40
        assert parsed["error"] is None
        assert parsed["request_id"] == "req_cloud_abc123"

    def test_response_serialization_error(self):
        """错误响应序列化为 JSON"""
        resp = CreateAiImageToolTaskResponse(
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
        """从 JSON 反序列化成功响应"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "feature": "upscale_image_cloud",
                "estimated_credits": 30,
            },
            "error": None,
            "request_id": "req_cloud_abc123",
        })
        resp = CreateAiImageToolTaskResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert resp.data.status == "queued"
        assert resp.data.feature == "upscale_image_cloud"
        assert resp.data.estimated_credits == 30
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
        resp = CreateAiImageToolTaskResponse.model_validate_json(json_str)
        assert resp.success is False
        assert resp.data is None
        assert resp.error.code == "CREDITS_NOT_ENOUGH"

    def test_response_success_roundtrip(self):
        """成功响应对象序列化/反序列化往返一致性"""
        original = CreateAiImageToolTaskResponse(
            success=True,
            data=CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature="vectorize_image_cloud",
                estimated_credits=20,
            ),
            error=None,
            request_id="req_cloud_abc123",
        )
        json_str = original.model_dump_json()
        restored = CreateAiImageToolTaskResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data.task_id == original.data.task_id
        assert restored.data.status == original.data.status
        assert restored.data.feature == original.data.feature
        assert restored.data.estimated_credits == original.data.estimated_credits
        assert restored.error == original.error
        assert restored.request_id == original.request_id

    def test_response_error_roundtrip(self):
        """错误响应对象序列化/反序列化往返一致性"""
        original = CreateAiImageToolTaskResponse(
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
        restored = CreateAiImageToolTaskResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data == original.data
        assert restored.error.code == original.error.code
        assert restored.error.message == original.error.message
        assert restored.error.details == original.error.details
        assert restored.request_id == original.request_id


# ============================================================
# AiImageToolTaskResponse 测试
# ============================================================


class TestAiImageToolTaskResponse:
    """任务查询响应 DTO 测试"""

    def test_success_response_queued(self):
        """成功响应 — 排队中任务"""
        resp = AiImageToolTaskResponse(
            success=True,
            data=AiImageToolTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature="upscale_image_cloud",
                result_files=[],
            ),
            error=None,
            request_id="req_cloud_task001",
        )
        assert resp.success is True
        assert resp.data is not None
        assert resp.data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert resp.data.status == "queued"
        assert resp.data.result_files == []
        assert resp.error is None

    def test_success_response_succeeded(self):
        """成功响应 — 已完成任务，含结果文件和 OCR 数据"""
        resp = AiImageToolTaskResponse(
            success=True,
            data=AiImageToolTaskData(
                task_id="660e8400-e29b-41d4-a716-446655440001",
                status="succeeded",
                feature="ocr_cloud",
                result_files=[
                    ResultFile(
                        file_id="770e8400-e29b-41d4-a716-446655440002",
                        url="https://cdn.example.com/tools/ocr_text.json",
                        mime_type="application/json",
                    )
                ],
                result_json={"text": "测试文本", "confidence": 0.95},
                provider="deepseek",
                model="deepseek-vl",
                estimated_cost=0.005,
                credits_charged=5,
                provider_call_id="880e8400-e29b-41d4-a716-446655440003",
            ),
            error=None,
            request_id="req_cloud_task002",
        )
        assert resp.success is True
        assert resp.data.status == "succeeded"
        assert len(resp.data.result_files) == 1
        assert resp.data.result_json == {"text": "测试文本", "confidence": 0.95}
        assert resp.data.provider == "deepseek"
        assert resp.data.credits_charged == 5

    def test_error_response_not_found(self):
        """错误响应 — 任务不存在"""
        resp = AiImageToolTaskResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="UNKNOWN_ERROR",
                message="任务不存在或已过期",
            ),
            request_id="req_cloud_task003",
        )
        assert resp.success is False
        assert resp.data is None
        assert resp.error is not None
        assert resp.error.code == "UNKNOWN_ERROR"

    def test_error_response_unauthorized(self):
        """错误响应 — 未认证"""
        resp = AiImageToolTaskResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="AUTH_REQUIRED",
                message="需要登录才能查询任务",
            ),
            request_id="req_cloud_task004",
        )
        assert resp.success is False
        assert resp.error.code == "AUTH_REQUIRED"

    def test_error_response_provider_failed(self):
        """错误响应 — Provider 调用失败（任务状态失败关联）"""
        resp = AiImageToolTaskResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="PROVIDER_BAD_RESPONSE",
                message="AI 服务返回异常，请稍后重试",
            ),
            request_id="req_cloud_task005",
        )
        assert resp.success is False
        assert resp.error.code == "PROVIDER_BAD_RESPONSE"

    # ---- 序列化/反序列化测试 ----

    def test_response_serialization_success(self):
        """成功响应序列化为 JSON"""
        resp = AiImageToolTaskResponse(
            success=True,
            data=AiImageToolTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="succeeded",
                feature="remove_bg_cloud",
                result_files=[
                    ResultFile(
                        file_id="660e8400-e29b-41d4-a716-446655440001",
                        url="https://cdn.example.com/tools/bg_removed.png",
                        mime_type="image/png",
                        width=1024,
                        height=768,
                    )
                ],
                result_json={"has_transparency": True},
                provider="replicate",
                model="sam-2",
                estimated_cost=0.04,
                credits_charged=40,
                provider_call_id="770e8400-e29b-41d4-a716-446655440002",
            ),
            error=None,
            request_id="req_cloud_task006",
        )
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["data"]["task_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed["data"]["status"] == "succeeded"
        assert parsed["data"]["feature"] == "remove_bg_cloud"
        assert len(parsed["data"]["result_files"]) == 1
        assert parsed["error"] is None
        assert parsed["request_id"] == "req_cloud_task006"

    def test_response_serialization_error(self):
        """错误响应序列化为 JSON"""
        resp = AiImageToolTaskResponse(
            success=False,
            data=None,
            error=ErrorDetail(code="UNKNOWN_ERROR", message="任务不存在"),
            request_id="req_cloud_task007",
        )
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is False
        assert parsed["data"] is None
        assert parsed["error"]["code"] == "UNKNOWN_ERROR"
        assert parsed["request_id"] == "req_cloud_task007"

    def test_response_deserialization_success(self):
        """从 JSON 反序列化成功响应 — 对齐 API_INDEX.md 结构"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "succeeded",
                "feature": "upscale_image_cloud",
                "result_files": [
                    {
                        "file_id": "660e8400-e29b-41d4-a716-446655440001",
                        "url": "https://cdn.example.com/tools/upscaled.png",
                        "mime_type": "image/png",
                        "width": 3840,
                        "height": 2160,
                    }
                ],
                "result_json": {"original_width": 1920, "original_height": 1080, "scale": 2},
                "provider": "replicate",
                "model": "real-esrgan",
                "estimated_cost": 0.03,
                "credits_charged": 30,
                "provider_call_id": "770e8400-e29b-41d4-a716-446655440002",
            },
            "error": None,
            "request_id": "req_cloud_task008",
        })
        resp = AiImageToolTaskResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert resp.data.status == "succeeded"
        assert resp.data.feature == "upscale_image_cloud"
        assert len(resp.data.result_files) == 1
        assert resp.data.result_json == {"original_width": 1920, "original_height": 1080, "scale": 2}
        assert resp.data.provider == "replicate"
        assert resp.data.model == "real-esrgan"
        assert resp.data.estimated_cost == 0.03
        assert resp.data.credits_charged == 30
        assert resp.error is None

    def test_response_deserialization_error(self):
        """从 JSON 反序列化错误响应"""
        json_str = json.dumps({
            "success": False,
            "data": None,
            "error": {
                "code": "UNKNOWN_ERROR",
                "message": "任务不存在或已过期",
            },
            "request_id": "req_cloud_task009",
        })
        resp = AiImageToolTaskResponse.model_validate_json(json_str)
        assert resp.success is False
        assert resp.data is None
        assert resp.error.code == "UNKNOWN_ERROR"

    def test_response_success_roundtrip(self):
        """成功响应对象序列化/反序列化往返一致性"""
        original = AiImageToolTaskResponse(
            success=True,
            data=AiImageToolTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="succeeded",
                feature="ai_edit_image_cloud",
                result_files=[
                    ResultFile(
                        file_id="660e8400-e29b-41d4-a716-446655440001",
                        url="https://cdn.example.com/tools/edited.png",
                        mime_type="image/png",
                        width=1920,
                        height=1080,
                    )
                ],
                result_json={"operation": "background_replace"},
                provider="replicate",
                model="instruct-pix2pix",
                estimated_cost=0.06,
                credits_charged=60,
                provider_call_id="770e8400-e29b-41d4-a716-446655440002",
            ),
            error=None,
            request_id="req_cloud_task010",
        )
        json_str = original.model_dump_json()
        restored = AiImageToolTaskResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data.task_id == original.data.task_id
        assert restored.data.status == original.data.status
        assert restored.data.feature == original.data.feature
        assert len(restored.data.result_files) == len(original.data.result_files)
        assert restored.data.result_json == original.data.result_json
        assert restored.data.provider == original.data.provider
        assert restored.error == original.error
        assert restored.request_id == original.request_id

    def test_response_error_roundtrip(self):
        """错误响应对象序列化/反序列化往返一致性"""
        original = AiImageToolTaskResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="PROVIDER_TIMEOUT",
                message="AI 服务调用超时",
                details={"retry_after": 10},
            ),
            request_id="req_cloud_timeout011",
        )
        json_str = original.model_dump_json()
        restored = AiImageToolTaskResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data == original.data
        assert restored.error.code == original.error.code
        assert restored.error.message == original.error.message
        assert restored.error.details == original.error.details
        assert restored.request_id == original.request_id


# ============================================================
# OpenAPI YAML / API_INDEX.md 示例一致性测试
# ============================================================


class TestApiIndexExamples:
    """验证 API_INDEX.md 中定义的示例与 DTO 一致"""

    def test_create_task_request_from_api_index(self):
        """API_INDEX.md POST 示例请求 — 应与 DTO 兼容"""
        json_str = json.dumps({
            "feature": "upscale_image_cloud",
            "input_file_ids": [
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440002",
            ],
            "options": {"scale": 2, "format": "png"},
            "client_request_id": "req_client_xxx",
        })
        req = CreateAiImageToolTaskRequest.model_validate_json(json_str)
        assert req.feature == "upscale_image_cloud"
        assert len(req.input_file_ids) == 2
        assert req.options == {"scale": 2, "format": "png"}
        assert req.client_request_id == "req_client_xxx"

    def test_create_task_response_from_api_index(self):
        """API_INDEX.md POST 示例响应 — 应与 DTO 兼容"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "feature": "upscale_image_cloud",
                "estimated_credits": 30,
            },
            "error": None,
            "request_id": "req_cloud_abc123",
        })
        resp = CreateAiImageToolTaskResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert resp.data.status == "queued"
        assert resp.data.feature == "upscale_image_cloud"
        assert resp.data.estimated_credits == 30

    def test_get_task_response_from_api_index(self):
        """API_INDEX.md GET 示例响应 — 应与 DTO 兼容（同云端 AI 任务查询结构）"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "task_id": "660e8400-e29b-41d4-a716-446655440001",
                "status": "succeeded",
                "feature": "remove_bg_cloud",
                "result_files": [
                    {
                        "file_id": "770e8400-e29b-41d4-a716-446655440002",
                        "url": "https://cdn.example.com/tools/bg_removed.png",
                        "mime_type": "image/png",
                        "width": 1024,
                        "height": 768,
                    }
                ],
                "result_json": {"has_transparency": True},
                "provider": "replicate",
                "model": "sam-2",
                "estimated_cost": 0.04,
                "credits_charged": 40,
                "provider_call_id": "880e8400-e29b-41d4-a716-446655440003",
            },
            "error": None,
            "request_id": "req_cloud_def456",
        })
        resp = AiImageToolTaskResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.task_id == "660e8400-e29b-41d4-a716-446655440001"
        assert resp.data.status == "succeeded"
        assert resp.data.feature == "remove_bg_cloud"
        assert len(resp.data.result_files) == 1
        assert resp.data.provider == "replicate"
        assert resp.data.model == "sam-2"
        assert resp.data.estimated_cost == 0.04
        assert resp.data.credits_charged == 40
        assert resp.data.provider_call_id == "880e8400-e29b-41d4-a716-446655440003"

    def test_credits_charged_must_be_integer(self):
        """credits_charged 在响应中必须为整数（OpenAPI type: integer）"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "succeeded",
                "feature": "ocr_cloud",
                "result_files": [],
                "provider": "deepseek",
                "model": "deepseek-vl",
                "estimated_cost": 0.005,
                "credits_charged": 5,
                "provider_call_id": "990e8400-e29b-41d4-a716-446655440004",
            },
            "error": None,
            "request_id": "req_cloud_test001",
        })
        resp = AiImageToolTaskResponse.model_validate_json(json_str)
        assert isinstance(resp.data.credits_charged, int)

    def test_estimated_credits_must_be_integer(self):
        """estimated_credits 在响应中必须为整数（OpenAPI type: integer）"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "feature": "upscale_image_cloud",
                "estimated_credits": 30,
            },
            "error": None,
            "request_id": "req_cloud_test002",
        })
        resp = CreateAiImageToolTaskResponse.model_validate_json(json_str)
        assert isinstance(resp.data.estimated_credits, int)

    def test_empty_options_request_from_api_index(self):
        """API_INDEX.md POST 示例不含 options 字段 — 应与 DTO 兼容"""
        json_str = json.dumps({
            "feature": "ocr_cloud",
            "input_file_ids": ["550e8400-e29b-41d4-a716-446655440001"],
            "client_request_id": "req_client_ocr_001",
        })
        req = CreateAiImageToolTaskRequest.model_validate_json(json_str)
        assert req.feature == "ocr_cloud"
        assert req.options is None

    def test_null_result_json_handled(self):
        """result_json 为 null 时的兼容性 — OpenAPI nullable 语义"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "succeeded",
                "feature": "upscale_image_cloud",
                "result_files": [],
                "result_json": None,
                "provider": "replicate",
                "model": "real-esrgan",
                "estimated_cost": 0.03,
                "credits_charged": 30,
            },
            "error": None,
            "request_id": "req_cloud_nulljson",
        })
        resp = AiImageToolTaskResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.result_json is None
