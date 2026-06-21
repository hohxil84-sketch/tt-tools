"""
ai_render DTO 契约一致性测试。

测试 ai_render.py 中的 Pydantic 模型与
shared-contract/openapi/ai-render.yaml 的一致性。
"""

import json

import pytest
from pydantic import ValidationError

from ai_render import (
    AiRenderTaskData,
    AiRenderTaskResponse,
    CreateAiRenderTaskRequest,
    CreateAiRenderTaskResponse,
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
            details={"scene_type": "缺少必填字段"},
        )
        assert err.details == {"scene_type": "缺少必填字段"}

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
            url="https://cdn.example.com/render/result_001.png",
            mime_type="image/png",
            width=1920,
            height=1080,
        )
        assert f.file_id == "660e8400-e29b-41d4-a716-446655440001"
        assert f.url == "https://cdn.example.com/render/result_001.png"
        assert f.mime_type == "image/png"
        assert f.width == 1920
        assert f.height == 1080

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
            url="https://cdn.example.com/render/result_002.jpg",
            mime_type="image/jpeg",
            width=1024,
            height=1024,
        )
        json_str = f.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["file_id"] == "770e8400-e29b-41d4-a716-446655440002"
        assert parsed["url"] == "https://cdn.example.com/render/result_002.jpg"
        assert parsed["mime_type"] == "image/jpeg"
        assert parsed["width"] == 1024
        assert parsed["height"] == 1024

    def test_result_file_deserialization(self):
        """从 JSON 反序列化结果文件"""
        json_str = json.dumps({
            "file_id": "880e8400-e29b-41d4-a716-446655440003",
            "url": "https://cdn.example.com/render/result_003.png",
            "mime_type": "image/png",
            "width": 800,
            "height": 600,
        })
        f = ResultFile.model_validate_json(json_str)
        assert f.file_id == "880e8400-e29b-41d4-a716-446655440003"
        assert f.url == "https://cdn.example.com/render/result_003.png"
        assert f.mime_type == "image/png"
        assert f.width == 800
        assert f.height == 600

    def test_result_file_roundtrip(self):
        """结果文件序列化/反序列化往返一致性"""
        original = ResultFile(
            file_id="990e8400-e29b-41d4-a716-446655440004",
            url="https://cdn.example.com/render/result_004.png",
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
# CreateAiRenderTaskRequest 测试
# ============================================================


class TestCreateAiRenderTaskRequest:
    """创建效果图生成任务请求 DTO 测试"""

    def test_create_minimal_valid_request(self):
        """最小必填字段创建请求 — 不含可选字段"""
        req = CreateAiRenderTaskRequest(
            scene_type="interior_design",
            prompt="现代简约风格客厅，白色墙面，木质地板",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
            client_request_id="req_client_abc123",
        )
        assert req.scene_type == "interior_design"
        assert req.prompt == "现代简约风格客厅，白色墙面，木质地板"
        assert req.input_file_ids == ["550e8400-e29b-41d4-a716-446655440000"]
        assert req.client_request_id == "req_client_abc123"
        # 可选字段默认 None
        assert req.style is None
        assert req.size is None

    def test_create_full_request(self):
        """全部字段创建请求 — 含所有可选字段"""
        req = CreateAiRenderTaskRequest(
            scene_type="product_showcase",
            prompt="白色背景，产品居中展示，专业光影",
            input_file_ids=[
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440002",
            ],
            style="modern",
            size="1920x1080",
            client_request_id="req_client_xyz789",
        )
        assert req.scene_type == "product_showcase"
        assert req.style == "modern"
        assert req.size == "1920x1080"
        assert len(req.input_file_ids) == 2

    def test_create_poster_design_request(self):
        """海报设计场景请求"""
        req = CreateAiRenderTaskRequest(
            scene_type="poster_design",
            prompt="开业大促海报，红色为主色调，突出优惠信息",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440003"],
            style="chinese",
            size="1080x1920",
            client_request_id="req_client_pd001",
        )
        assert req.scene_type == "poster_design"
        assert req.style == "chinese"
        assert req.size == "1080x1920"

    def test_empty_input_file_ids(self):
        """空的输入文件列表 — 应允许（可能纯文本生成）"""
        req = CreateAiRenderTaskRequest(
            scene_type="interior_design",
            prompt="纯文本描述的设计方案",
            input_file_ids=[],
            client_request_id="req_001",
        )
        assert req.input_file_ids == []

    def test_missing_scene_type_fails(self):
        """缺少 scene_type 字段应失败"""
        with pytest.raises(ValidationError):
            CreateAiRenderTaskRequest(
                prompt="测试提示词",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
            )

    def test_missing_prompt_fails(self):
        """缺少 prompt 字段应失败"""
        with pytest.raises(ValidationError):
            CreateAiRenderTaskRequest(
                scene_type="interior_design",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
            )

    def test_missing_input_file_ids_fails(self):
        """缺少 input_file_ids 字段应失败"""
        with pytest.raises(ValidationError):
            CreateAiRenderTaskRequest(
                scene_type="interior_design",
                prompt="测试提示词",
                client_request_id="req_001",
            )

    def test_missing_client_request_id_fails(self):
        """缺少 client_request_id 字段应失败"""
        with pytest.raises(ValidationError):
            CreateAiRenderTaskRequest(
                scene_type="interior_design",
                prompt="测试提示词",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
            )

    def test_input_file_ids_not_list_fails(self):
        """input_file_ids 不是列表应失败"""
        with pytest.raises(ValidationError):
            CreateAiRenderTaskRequest(
                scene_type="interior_design",
                prompt="测试提示词",
                input_file_ids="not-a-list",  # 错误：应该是 list
                client_request_id="req_001",
            )

    # ---- 客户端禁止提交字段测试 ----

    def test_client_prohibited_user_id_rejected(self):
        """客户端禁止提交 user_id"""
        with pytest.raises(ValidationError):
            CreateAiRenderTaskRequest(
                scene_type="interior_design",
                prompt="测试提示词",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                user_id="some-user-id",  # 客户端禁止提交
            )

    def test_client_prohibited_plan_code_rejected(self):
        """客户端禁止提交 plan_code"""
        with pytest.raises(ValidationError):
            CreateAiRenderTaskRequest(
                scene_type="interior_design",
                prompt="测试提示词",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                plan_code="pro",  # 客户端禁止提交
            )

    def test_client_prohibited_provider_rejected(self):
        """客户端禁止提交 provider"""
        with pytest.raises(ValidationError):
            CreateAiRenderTaskRequest(
                scene_type="interior_design",
                prompt="测试提示词",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                provider="openai",  # 客户端禁止提交
            )

    def test_client_prohibited_model_rejected(self):
        """客户端禁止提交 model"""
        with pytest.raises(ValidationError):
            CreateAiRenderTaskRequest(
                scene_type="interior_design",
                prompt="测试提示词",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                model="dall-e-3",  # 客户端禁止提交
            )

    def test_client_prohibited_estimated_cost_rejected(self):
        """客户端禁止提交 estimated_cost"""
        with pytest.raises(ValidationError):
            CreateAiRenderTaskRequest(
                scene_type="interior_design",
                prompt="测试提示词",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                estimated_cost=0.05,  # 客户端禁止提交
            )

    def test_client_prohibited_credits_charged_rejected(self):
        """客户端禁止提交 credits_charged"""
        with pytest.raises(ValidationError):
            CreateAiRenderTaskRequest(
                scene_type="interior_design",
                prompt="测试提示词",
                input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
                client_request_id="req_001",
                credits_charged=10,  # 客户端禁止提交
            )

    # ---- 序列化/反序列化测试 ----

    def test_request_serialization_minimal(self):
        """最小请求序列化为 JSON"""
        req = CreateAiRenderTaskRequest(
            scene_type="interior_design",
            prompt="现代简约风格客厅",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
            client_request_id="req_client_abc123",
        )
        json_str = req.model_dump_json()
        data = json.loads(json_str)
        assert data["scene_type"] == "interior_design"
        assert data["prompt"] == "现代简约风格客厅"
        assert data["input_file_ids"] == ["550e8400-e29b-41d4-a716-446655440000"]
        assert data["client_request_id"] == "req_client_abc123"

    def test_request_deserialization_full(self):
        """从 JSON 反序列化完整请求"""
        json_str = json.dumps({
            "scene_type": "interior_design",
            "prompt": "现代简约风格客厅，白色墙面，木质地板",
            "input_file_ids": [
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440002",
            ],
            "style": "modern",
            "size": "1920x1080",
            "client_request_id": "req_client_xxx",
        })
        req = CreateAiRenderTaskRequest.model_validate_json(json_str)
        assert req.scene_type == "interior_design"
        assert req.prompt == "现代简约风格客厅，白色墙面，木质地板"
        assert req.input_file_ids == [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
        ]
        assert req.style == "modern"
        assert req.size == "1920x1080"
        assert req.client_request_id == "req_client_xxx"

    def test_request_roundtrip(self):
        """请求对象序列化/反序列化往返一致性"""
        original = CreateAiRenderTaskRequest(
            scene_type="interior_design",
            prompt="现代简约风格客厅",
            input_file_ids=["550e8400-e29b-41d4-a716-446655440000"],
            style="minimalist",
            size="1024x1024",
            client_request_id="req_client_xxx",
        )
        json_str = original.model_dump_json()
        restored = CreateAiRenderTaskRequest.model_validate_json(json_str)
        assert restored.scene_type == original.scene_type
        assert restored.prompt == original.prompt
        assert restored.input_file_ids == original.input_file_ids
        assert restored.style == original.style
        assert restored.size == original.size
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
            feature="ai_render_cloud",
            estimated_credits=50,
        )
        assert data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert data.status == "queued"
        assert data.feature == "ai_render_cloud"
        assert data.estimated_credits == 50

    def test_feature_must_be_ai_render_cloud(self):
        """feature 必须为 ai_render_cloud（OpenAPI const 约束）"""
        with pytest.raises(ValidationError):
            CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature="wrong_feature_code",  # 错误的功能码
                estimated_credits=50,
            )

    def test_status_must_be_valid_enum(self):
        """status 必须为有效枚举值"""
        with pytest.raises(ValidationError):
            CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="unknown_status",  # 无效状态
                feature="ai_render_cloud",
                estimated_credits=50,
            )

    def test_status_all_valid_values(self):
        """验证所有有效 status 值"""
        for status in ["queued", "running", "succeeded", "failed"]:
            data = CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status=status,
                feature="ai_render_cloud",
                estimated_credits=50,
            )
            assert data.status == status

    def test_missing_task_id_fails(self):
        """缺少 task_id 字段应失败"""
        with pytest.raises(ValidationError):
            CreatedTaskData(
                status="queued",
                feature="ai_render_cloud",
                estimated_credits=50,
            )

    def test_missing_status_fails(self):
        """缺少 status 字段应失败"""
        with pytest.raises(ValidationError):
            CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                feature="ai_render_cloud",
                estimated_credits=50,
            )

    def test_missing_estimated_credits_fails(self):
        """缺少 estimated_credits 字段应失败"""
        with pytest.raises(ValidationError):
            CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature="ai_render_cloud",
            )

    def test_estimated_credits_is_integer(self):
        """estimated_credits 必须为整数（OpenAPI type: integer）"""
        data = CreatedTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="queued",
            feature="ai_render_cloud",
            estimated_credits=100,
        )
        assert isinstance(data.estimated_credits, int)
        assert data.estimated_credits == 100

    def test_created_task_data_serialization(self):
        """创建任务数据序列化为 JSON"""
        data = CreatedTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="queued",
            feature="ai_render_cloud",
            estimated_credits=50,
        )
        json_str = data.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["task_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed["status"] == "queued"
        assert parsed["feature"] == "ai_render_cloud"
        assert parsed["estimated_credits"] == 50

    def test_created_task_data_deserialization(self):
        """从 JSON 反序列化创建任务数据"""
        json_str = json.dumps({
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "queued",
            "feature": "ai_render_cloud",
            "estimated_credits": 50,
        })
        data = CreatedTaskData.model_validate_json(json_str)
        assert data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert data.status == "queued"
        assert data.feature == "ai_render_cloud"
        assert data.estimated_credits == 50


# ============================================================
# AiRenderTaskData 测试
# ============================================================


class TestAiRenderTaskData:
    """任务查询响应数据 DTO 测试"""

    def test_create_queued_task_data(self):
        """创建排队中任务查询数据 — provider 等字段为 None"""
        data = AiRenderTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="queued",
            feature="ai_render_cloud",
            result_files=[],
        )
        assert data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert data.status == "queued"
        assert data.feature == "ai_render_cloud"
        assert data.result_files == []
        assert data.provider is None
        assert data.model is None
        assert data.estimated_cost is None
        assert data.credits_charged is None
        assert data.provider_call_id is None

    def test_create_succeeded_task_data(self):
        """创建成功完成的任务查询数据 — 含结果文件"""
        data = AiRenderTaskData(
            task_id="660e8400-e29b-41d4-a716-446655440001",
            status="succeeded",
            feature="ai_render_cloud",
            result_files=[
                ResultFile(
                    file_id="770e8400-e29b-41d4-a716-446655440002",
                    url="https://cdn.example.com/render/result.png",
                    mime_type="image/png",
                    width=1920,
                    height=1080,
                )
            ],
            provider="replicate",
            model="stability-ai/sdxl",
            estimated_cost=0.05,
            credits_charged=50,
            provider_call_id="880e8400-e29b-41d4-a716-446655440003",
        )
        assert data.status == "succeeded"
        assert len(data.result_files) == 1
        assert data.result_files[0].file_id == "770e8400-e29b-41d4-a716-446655440002"
        assert data.result_files[0].mime_type == "image/png"
        assert data.provider == "replicate"
        assert data.model == "stability-ai/sdxl"
        assert data.estimated_cost == 0.05
        assert data.credits_charged == 50
        assert data.provider_call_id == "880e8400-e29b-41d4-a716-446655440003"

    def test_create_failed_task_data(self):
        """创建失败任务查询数据"""
        data = AiRenderTaskData(
            task_id="990e8400-e29b-41d4-a716-446655440004",
            status="failed",
            feature="ai_render_cloud",
            result_files=[],
        )
        assert data.status == "failed"
        assert data.result_files == []

    def test_create_running_task_data(self):
        """创建运行中任务查询数据"""
        data = AiRenderTaskData(
            task_id="aa0e8400-e29b-41d4-a716-446655440005",
            status="running",
            feature="ai_render_cloud",
            result_files=[],
            provider="replicate",
            model="stability-ai/sdxl",
            provider_call_id="bb0e8400-e29b-41d4-a716-446655440006",
        )
        assert data.status == "running"
        assert data.provider == "replicate"
        assert data.provider_call_id == "bb0e8400-e29b-41d4-a716-446655440006"
        # 运行中尚未扣费
        assert data.estimated_cost is None
        assert data.credits_charged is None

    def test_feature_must_be_ai_render_cloud(self):
        """feature 必须为 ai_render_cloud（OpenAPI const 约束）"""
        with pytest.raises(ValidationError):
            AiRenderTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature="wrong_feature",  # 错误的功能码
                result_files=[],
            )

    def test_status_must_be_valid_enum(self):
        """status 必须为有效枚举值"""
        with pytest.raises(ValidationError):
            AiRenderTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="invalid",
                feature="ai_render_cloud",
                result_files=[],
            )

    def test_status_all_valid_values(self):
        """验证所有有效 status 值"""
        for status in ["queued", "running", "succeeded", "failed"]:
            data = AiRenderTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status=status,
                feature="ai_render_cloud",
                result_files=[],
            )
            assert data.status == status

    def test_missing_task_id_fails(self):
        """缺少 task_id 字段应失败"""
        with pytest.raises(ValidationError):
            AiRenderTaskData(
                status="queued",
                feature="ai_render_cloud",
                result_files=[],
            )

    def test_missing_status_fails(self):
        """缺少 status 字段应失败"""
        with pytest.raises(ValidationError):
            AiRenderTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                feature="ai_render_cloud",
                result_files=[],
            )

    def test_missing_feature_fails(self):
        """缺少 feature 字段应失败"""
        with pytest.raises(ValidationError):
            AiRenderTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                result_files=[],
            )

    def test_multiple_result_files(self):
        """多个结果文件"""
        data = AiRenderTaskData(
            task_id="cc0e8400-e29b-41d4-a716-446655440007",
            status="succeeded",
            feature="ai_render_cloud",
            result_files=[
                ResultFile(
                    file_id="dd0e8400-e29b-41d4-a716-446655440008",
                    mime_type="image/png",
                    width=1920,
                    height=1080,
                ),
                ResultFile(
                    file_id="ee0e8400-e29b-41d4-a716-446655440009",
                    mime_type="image/jpeg",
                    width=800,
                    height=600,
                ),
            ],
            provider="replicate",
            model="stability-ai/sdxl",
            estimated_cost=0.08,
            credits_charged=80,
            provider_call_id="ff0e8400-e29b-41d4-a716-446655440010",
        )
        assert len(data.result_files) == 2
        assert data.result_files[0].mime_type == "image/png"
        assert data.result_files[1].mime_type == "image/jpeg"

    def test_credits_charged_is_integer(self):
        """credits_charged 必须为整数（OpenAPI type: integer）"""
        data = AiRenderTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="succeeded",
            feature="ai_render_cloud",
            result_files=[],
            provider="replicate",
            model="stability-ai/sdxl",
            estimated_cost=0.05,
            credits_charged=50,
            provider_call_id="550e8400-e29b-41d4-a716-446655440001",
        )
        assert isinstance(data.credits_charged, int)
        assert data.credits_charged == 50

    # ---- 序列化/反序列化测试 ----

    def test_task_data_serialization_succeeded(self):
        """成功任务数据序列化为 JSON"""
        data = AiRenderTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="succeeded",
            feature="ai_render_cloud",
            result_files=[
                ResultFile(
                    file_id="660e8400-e29b-41d4-a716-446655440001",
                    url="https://cdn.example.com/render/result.png",
                    mime_type="image/png",
                    width=1920,
                    height=1080,
                )
            ],
            provider="replicate",
            model="stability-ai/sdxl",
            estimated_cost=0.05,
            credits_charged=50,
            provider_call_id="770e8400-e29b-41d4-a716-446655440002",
        )
        json_str = data.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["task_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed["status"] == "succeeded"
        assert parsed["feature"] == "ai_render_cloud"
        assert len(parsed["result_files"]) == 1
        assert parsed["result_files"][0]["file_id"] == "660e8400-e29b-41d4-a716-446655440001"
        assert parsed["provider"] == "replicate"
        assert parsed["model"] == "stability-ai/sdxl"
        assert parsed["estimated_cost"] == 0.05
        assert parsed["credits_charged"] == 50
        assert parsed["provider_call_id"] == "770e8400-e29b-41d4-a716-446655440002"

    def test_task_data_serialization_queued(self):
        """排队中任务数据序列化为 JSON — provider 等字段为 None"""
        data = AiRenderTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="queued",
            feature="ai_render_cloud",
            result_files=[],
        )
        json_str = data.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["task_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed["status"] == "queued"
        assert parsed["feature"] == "ai_render_cloud"
        assert parsed["result_files"] == []

    def test_task_data_deserialization_succeeded(self):
        """从 JSON 反序列化成功任务数据"""
        json_str = json.dumps({
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "succeeded",
            "feature": "ai_render_cloud",
            "result_files": [
                {
                    "file_id": "660e8400-e29b-41d4-a716-446655440001",
                    "url": "https://cdn.example.com/render/result.png",
                    "mime_type": "image/png",
                    "width": 1920,
                    "height": 1080,
                }
            ],
            "provider": "replicate",
            "model": "stability-ai/sdxl",
            "estimated_cost": 0.05,
            "credits_charged": 50,
            "provider_call_id": "770e8400-e29b-41d4-a716-446655440002",
        })
        data = AiRenderTaskData.model_validate_json(json_str)
        assert data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert data.status == "succeeded"
        assert data.feature == "ai_render_cloud"
        assert len(data.result_files) == 1
        assert data.result_files[0].file_id == "660e8400-e29b-41d4-a716-446655440001"
        assert data.provider == "replicate"
        assert data.model == "stability-ai/sdxl"
        assert data.estimated_cost == 0.05
        assert data.credits_charged == 50
        assert data.provider_call_id == "770e8400-e29b-41d4-a716-446655440002"

    def test_task_data_roundtrip(self):
        """任务数据序列化/反序列化往返一致性"""
        original = AiRenderTaskData(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            status="succeeded",
            feature="ai_render_cloud",
            result_files=[
                ResultFile(
                    file_id="660e8400-e29b-41d4-a716-446655440001",
                    url="https://cdn.example.com/render/result.png",
                    mime_type="image/png",
                    width=1920,
                    height=1080,
                )
            ],
            provider="replicate",
            model="stability-ai/sdxl",
            estimated_cost=0.05,
            credits_charged=50,
            provider_call_id="770e8400-e29b-41d4-a716-446655440002",
        )
        json_str = original.model_dump_json()
        restored = AiRenderTaskData.model_validate_json(json_str)
        assert restored.task_id == original.task_id
        assert restored.status == original.status
        assert restored.feature == original.feature
        assert len(restored.result_files) == len(original.result_files)
        assert restored.result_files[0].file_id == original.result_files[0].file_id
        assert restored.provider == original.provider
        assert restored.model == original.model
        assert restored.estimated_cost == original.estimated_cost
        assert restored.credits_charged == original.credits_charged
        assert restored.provider_call_id == original.provider_call_id


# ============================================================
# CreateAiRenderTaskResponse 测试
# ============================================================


class TestCreateAiRenderTaskResponse:
    """创建任务响应 DTO 测试"""

    def test_success_response(self):
        """成功响应"""
        resp = CreateAiRenderTaskResponse(
            success=True,
            data=CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature="ai_render_cloud",
                estimated_credits=50,
            ),
            error=None,
            request_id="req_cloud_abc123",
        )
        assert resp.success is True
        assert resp.data is not None
        assert resp.data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert resp.data.status == "queued"
        assert resp.data.feature == "ai_render_cloud"
        assert resp.data.estimated_credits == 50
        assert resp.error is None
        assert resp.request_id == "req_cloud_abc123"

    def test_error_response_credits_not_enough(self):
        """错误响应 — 额度不足"""
        resp = CreateAiRenderTaskResponse(
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
        resp = CreateAiRenderTaskResponse(
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
        resp = CreateAiRenderTaskResponse(
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
        resp = CreateAiRenderTaskResponse(
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

    # ---- 序列化/反序列化测试 ----

    def test_response_serialization_success(self):
        """成功响应序列化为 JSON"""
        resp = CreateAiRenderTaskResponse(
            success=True,
            data=CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature="ai_render_cloud",
                estimated_credits=50,
            ),
            error=None,
            request_id="req_cloud_abc123",
        )
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["data"]["task_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed["data"]["status"] == "queued"
        assert parsed["data"]["feature"] == "ai_render_cloud"
        assert parsed["data"]["estimated_credits"] == 50
        assert parsed["error"] is None
        assert parsed["request_id"] == "req_cloud_abc123"

    def test_response_serialization_error(self):
        """错误响应序列化为 JSON"""
        resp = CreateAiRenderTaskResponse(
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
                "feature": "ai_render_cloud",
                "estimated_credits": 50,
            },
            "error": None,
            "request_id": "req_cloud_abc123",
        })
        resp = CreateAiRenderTaskResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert resp.data.status == "queued"
        assert resp.data.feature == "ai_render_cloud"
        assert resp.data.estimated_credits == 50
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
        resp = CreateAiRenderTaskResponse.model_validate_json(json_str)
        assert resp.success is False
        assert resp.data is None
        assert resp.error.code == "CREDITS_NOT_ENOUGH"

    def test_response_success_roundtrip(self):
        """成功响应对象序列化/反序列化往返一致性"""
        original = CreateAiRenderTaskResponse(
            success=True,
            data=CreatedTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature="ai_render_cloud",
                estimated_credits=50,
            ),
            error=None,
            request_id="req_cloud_abc123",
        )
        json_str = original.model_dump_json()
        restored = CreateAiRenderTaskResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data.task_id == original.data.task_id
        assert restored.data.status == original.data.status
        assert restored.data.feature == original.data.feature
        assert restored.data.estimated_credits == original.data.estimated_credits
        assert restored.error == original.error
        assert restored.request_id == original.request_id

    def test_response_error_roundtrip(self):
        """错误响应对象序列化/反序列化往返一致性"""
        original = CreateAiRenderTaskResponse(
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
        restored = CreateAiRenderTaskResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data == original.data
        assert restored.error.code == original.error.code
        assert restored.error.message == original.error.message
        assert restored.error.details == original.error.details
        assert restored.request_id == original.request_id


# ============================================================
# AiRenderTaskResponse 测试
# ============================================================


class TestAiRenderTaskResponse:
    """任务查询响应 DTO 测试"""

    def test_success_response_queued(self):
        """成功响应 — 排队中任务"""
        resp = AiRenderTaskResponse(
            success=True,
            data=AiRenderTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="queued",
                feature="ai_render_cloud",
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
        """成功响应 — 已完成任务"""
        resp = AiRenderTaskResponse(
            success=True,
            data=AiRenderTaskData(
                task_id="660e8400-e29b-41d4-a716-446655440001",
                status="succeeded",
                feature="ai_render_cloud",
                result_files=[
                    ResultFile(
                        file_id="770e8400-e29b-41d4-a716-446655440002",
                        url="https://cdn.example.com/render/result.png",
                        mime_type="image/png",
                        width=1920,
                        height=1080,
                    )
                ],
                provider="replicate",
                model="stability-ai/sdxl",
                estimated_cost=0.05,
                credits_charged=50,
                provider_call_id="880e8400-e29b-41d4-a716-446655440003",
            ),
            error=None,
            request_id="req_cloud_task002",
        )
        assert resp.success is True
        assert resp.data.status == "succeeded"
        assert len(resp.data.result_files) == 1
        assert resp.data.provider == "replicate"
        assert resp.data.credits_charged == 50

    def test_error_response_not_found(self):
        """错误响应 — 任务不存在"""
        resp = AiRenderTaskResponse(
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
        resp = AiRenderTaskResponse(
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

    # ---- 序列化/反序列化测试 ----

    def test_response_serialization_success(self):
        """成功响应序列化为 JSON"""
        resp = AiRenderTaskResponse(
            success=True,
            data=AiRenderTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="succeeded",
                feature="ai_render_cloud",
                result_files=[
                    ResultFile(
                        file_id="660e8400-e29b-41d4-a716-446655440001",
                        url="https://cdn.example.com/render/result.png",
                        mime_type="image/png",
                        width=1920,
                        height=1080,
                    )
                ],
                provider="replicate",
                model="stability-ai/sdxl",
                estimated_cost=0.05,
                credits_charged=50,
                provider_call_id="770e8400-e29b-41d4-a716-446655440002",
            ),
            error=None,
            request_id="req_cloud_task005",
        )
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["data"]["task_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed["data"]["status"] == "succeeded"
        assert len(parsed["data"]["result_files"]) == 1
        assert parsed["error"] is None
        assert parsed["request_id"] == "req_cloud_task005"

    def test_response_serialization_error(self):
        """错误响应序列化为 JSON"""
        resp = AiRenderTaskResponse(
            success=False,
            data=None,
            error=ErrorDetail(code="UNKNOWN_ERROR", message="任务不存在"),
            request_id="req_cloud_task006",
        )
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is False
        assert parsed["data"] is None
        assert parsed["error"]["code"] == "UNKNOWN_ERROR"
        assert parsed["request_id"] == "req_cloud_task006"

    def test_response_deserialization_success(self):
        """从 JSON 反序列化成功响应 — 对齐 API_INDEX.md 结构"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "succeeded",
                "feature": "ai_render_cloud",
                "result_files": [
                    {
                        "file_id": "660e8400-e29b-41d4-a716-446655440001",
                        "url": "https://cdn.example.com/render/result.png",
                        "mime_type": "image/png",
                        "width": 1920,
                        "height": 1080,
                    }
                ],
                "provider": "replicate",
                "model": "stability-ai/sdxl",
                "estimated_cost": 0.05,
                "credits_charged": 50,
                "provider_call_id": "770e8400-e29b-41d4-a716-446655440002",
            },
            "error": None,
            "request_id": "req_cloud_task007",
        })
        resp = AiRenderTaskResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert resp.data.status == "succeeded"
        assert resp.data.feature == "ai_render_cloud"
        assert len(resp.data.result_files) == 1
        assert resp.data.provider == "replicate"
        assert resp.data.model == "stability-ai/sdxl"
        assert resp.data.estimated_cost == 0.05
        assert resp.data.credits_charged == 50
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
            "request_id": "req_cloud_task008",
        })
        resp = AiRenderTaskResponse.model_validate_json(json_str)
        assert resp.success is False
        assert resp.data is None
        assert resp.error.code == "UNKNOWN_ERROR"

    def test_response_success_roundtrip(self):
        """成功响应对象序列化/反序列化往返一致性"""
        original = AiRenderTaskResponse(
            success=True,
            data=AiRenderTaskData(
                task_id="550e8400-e29b-41d4-a716-446655440000",
                status="succeeded",
                feature="ai_render_cloud",
                result_files=[
                    ResultFile(
                        file_id="660e8400-e29b-41d4-a716-446655440001",
                        url="https://cdn.example.com/render/result.png",
                        mime_type="image/png",
                        width=1920,
                        height=1080,
                    )
                ],
                provider="replicate",
                model="stability-ai/sdxl",
                estimated_cost=0.05,
                credits_charged=50,
                provider_call_id="770e8400-e29b-41d4-a716-446655440002",
            ),
            error=None,
            request_id="req_cloud_task009",
        )
        json_str = original.model_dump_json()
        restored = AiRenderTaskResponse.model_validate_json(json_str)
        assert restored.success == original.success
        assert restored.data.task_id == original.data.task_id
        assert restored.data.status == original.data.status
        assert restored.data.feature == original.data.feature
        assert len(restored.data.result_files) == len(original.data.result_files)
        assert restored.data.provider == original.data.provider
        assert restored.error == original.error
        assert restored.request_id == original.request_id

    def test_response_error_roundtrip(self):
        """错误响应对象序列化/反序列化往返一致性"""
        original = AiRenderTaskResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="PROVIDER_TIMEOUT",
                message="AI 服务调用超时",
                details={"retry_after": 10},
            ),
            request_id="req_cloud_timeout010",
        )
        json_str = original.model_dump_json()
        restored = AiRenderTaskResponse.model_validate_json(json_str)
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

    def test_create_task_request_from_api_index(self):
        """API_INDEX.md POST 示例请求 — 应与 DTO 兼容"""
        json_str = json.dumps({
            "scene_type": "interior_design",
            "prompt": "现代简约风格客厅，白色墙面，木质地板",
            "input_file_ids": [
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440002",
            ],
            "style": "modern",
            "size": "1920x1080",
            "client_request_id": "req_client_xxx",
        })
        req = CreateAiRenderTaskRequest.model_validate_json(json_str)
        assert req.scene_type == "interior_design"
        assert req.prompt == "现代简约风格客厅，白色墙面，木质地板"
        assert len(req.input_file_ids) == 2
        assert req.style == "modern"
        assert req.size == "1920x1080"

    def test_create_task_response_from_api_index(self):
        """API_INDEX.md POST 示例响应 — 应与 DTO 兼容"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "feature": "ai_render_cloud",
                "estimated_credits": 50,
            },
            "error": None,
            "request_id": "req_cloud_abc123",
        })
        resp = CreateAiRenderTaskResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert resp.data.status == "queued"
        assert resp.data.feature == "ai_render_cloud"
        assert resp.data.estimated_credits == 50

    def test_get_task_response_from_api_index(self):
        """API_INDEX.md GET 示例响应 — 应与 DTO 兼容"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "task_id": "660e8400-e29b-41d4-a716-446655440001",
                "status": "succeeded",
                "feature": "ai_render_cloud",
                "result_files": [
                    {
                        "file_id": "770e8400-e29b-41d4-a716-446655440002",
                        "url": "https://cdn.example.com/render/result.png",
                        "mime_type": "image/png",
                        "width": 1920,
                        "height": 1080,
                    }
                ],
                "provider": "replicate",
                "model": "stability-ai/sdxl",
                "estimated_cost": 0.05,
                "credits_charged": 50,
                "provider_call_id": "880e8400-e29b-41d4-a716-446655440003",
            },
            "error": None,
            "request_id": "req_cloud_def456",
        })
        resp = AiRenderTaskResponse.model_validate_json(json_str)
        assert resp.success is True
        assert resp.data.task_id == "660e8400-e29b-41d4-a716-446655440001"
        assert resp.data.status == "succeeded"
        assert resp.data.feature == "ai_render_cloud"
        assert len(resp.data.result_files) == 1
        assert resp.data.provider == "replicate"
        assert resp.data.model == "stability-ai/sdxl"
        assert resp.data.estimated_cost == 0.05
        assert resp.data.credits_charged == 50
        assert resp.data.provider_call_id == "880e8400-e29b-41d4-a716-446655440003"

    def test_credits_charged_must_be_integer(self):
        """credits_charged 在响应中必须为整数（OpenAPI type: integer）"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "succeeded",
                "feature": "ai_render_cloud",
                "result_files": [],
                "provider": "replicate",
                "model": "stability-ai/sdxl",
                "estimated_cost": 0.05,
                "credits_charged": 50,
                "provider_call_id": "990e8400-e29b-41d4-a716-446655440004",
            },
            "error": None,
            "request_id": "req_cloud_test001",
        })
        resp = AiRenderTaskResponse.model_validate_json(json_str)
        assert isinstance(resp.data.credits_charged, int)

    def test_estimated_credits_must_be_integer(self):
        """estimated_credits 在响应中必须为整数（OpenAPI type: integer）"""
        json_str = json.dumps({
            "success": True,
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "feature": "ai_render_cloud",
                "estimated_credits": 50,
            },
            "error": None,
            "request_id": "req_cloud_test002",
        })
        resp = CreateAiRenderTaskResponse.model_validate_json(json_str)
        assert isinstance(resp.data.estimated_credits, int)
