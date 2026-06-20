"""
provider-runtime 核心数据模型测试。

验证 ProviderCallRequest、ProviderResult、ProviderUsage、
ChatMessage 等 Pydantic 模型的字段和校验规则。
"""
from __future__ import annotations

import sys
import os

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
from pydantic import ValidationError

from models import (
    ProviderCallRequest,
    ProviderResult,
    ProviderUsage,
    ChatMessage,
)


class TestChatMessage:
    """ChatMessage 模型测试。"""

    def test_create_valid_message(self) -> None:
        """正常创建聊天消息。"""
        msg = ChatMessage(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"

    def test_create_system_message(self) -> None:
        """创建 system 角色消息。"""
        msg = ChatMessage(role="system", content="你是助手")
        assert msg.role == "system"

    def test_missing_role_raises(self) -> None:
        """缺少 role 字段应抛出 ValidationError。"""
        with pytest.raises(ValidationError):
            ChatMessage(content="无角色")  # type: ignore

    def test_missing_content_raises(self) -> None:
        """缺少 content 字段应抛出 ValidationError。"""
        with pytest.raises(ValidationError):
            ChatMessage(role="user")  # type: ignore


class TestProviderCallRequest:
    """ProviderCallRequest 模型测试。"""

    def test_create_minimal_request(self) -> None:
        """最简请求：只含必填字段 model、messages、feature。"""
        req = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="你好")],
            feature="ai_copy_cloud",
        )
        assert req.model == "deepseek-chat"
        assert len(req.messages) == 1
        assert req.feature == "ai_copy_cloud"
        assert req.max_tokens == 2048  # 默认值
        assert req.temperature == 0.7  # 默认值
        assert req.extra_options == {}
        assert req.request_id == ""

    def test_full_request(self) -> None:
        """完整请求：包含所有可选字段。"""
        req = ProviderCallRequest(
            model="gpt-4o",
            messages=[
                ChatMessage(role="system", content="你是助手"),
                ChatMessage(role="user", content="你好"),
            ],
            feature="ai_render_cloud",
            max_tokens=4096,
            temperature=0.3,
            extra_options={"top_p": 0.9},
            request_id="req-full-001",
        )
        assert req.model == "gpt-4o"
        assert len(req.messages) == 2
        assert req.max_tokens == 4096
        assert req.temperature == 0.3
        assert req.extra_options == {"top_p": 0.9}
        assert req.request_id == "req-full-001"

    def test_temperature_range(self) -> None:
        """temperature 必须在 [0, 2] 范围内。"""
        # 正常范围
        req = ProviderCallRequest(
            model="test",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
            temperature=0.0,
        )
        assert req.temperature == 0.0

        req = ProviderCallRequest(
            model="test",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
            temperature=2.0,
        )
        assert req.temperature == 2.0

    def test_temperature_out_of_range_raises(self) -> None:
        """temperature 超出 [0, 2] 范围应抛出 ValidationError。"""
        with pytest.raises(ValidationError):
            ProviderCallRequest(
                model="test",
                messages=[ChatMessage(role="user", content="x")],
                feature="test",
                temperature=2.1,
            )

        with pytest.raises(ValidationError):
            ProviderCallRequest(
                model="test",
                messages=[ChatMessage(role="user", content="x")],
                feature="test",
                temperature=-0.1,
            )

    def test_messages_must_be_non_empty_list(self) -> None:
        """messages 列表不能为空（实际业务逻辑中至少一条消息）。"""
        req = ProviderCallRequest(
            model="test",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        assert len(req.messages) >= 1


class TestProviderUsage:
    """ProviderUsage 模型测试。"""

    def test_default_values(self) -> None:
        """默认构造下所有用量字段为 0。"""
        usage = ProviderUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0
        assert usage.reasoning_tokens == 0
        assert usage.cached_tokens == 0
        assert usage.image_count == 0

    def test_custom_usage(self) -> None:
        """自定义用量字段。"""
        usage = ProviderUsage(
            input_tokens=120,
            output_tokens=80,
            total_tokens=200,
            reasoning_tokens=50,
            cached_tokens=30,
            image_count=2,
        )
        assert usage.input_tokens == 120
        assert usage.output_tokens == 80
        assert usage.total_tokens == 200
        assert usage.reasoning_tokens == 50
        assert usage.cached_tokens == 30
        assert usage.image_count == 2

    def test_usage_is_serializable(self) -> None:
        """ProviderUsage 可序列化为 dict。"""
        usage = ProviderUsage(input_tokens=100, output_tokens=50, total_tokens=150)
        d = usage.model_dump()
        assert d["input_tokens"] == 100
        assert d["output_tokens"] == 50
        assert d["total_tokens"] == 150


class TestProviderResult:
    """ProviderResult 模型测试。"""

    def test_success_result(self) -> None:
        """成功调用结果。"""
        result = ProviderResult(
            provider="deepseek",
            model="deepseek-chat",
            status="success",
            text="广告文案内容",
            usage=ProviderUsage(input_tokens=120, output_tokens=80, total_tokens=200),
            estimated_cost=0.0004,
            provider_request_id="provider-req-001",
            latency_ms=1200,
        )
        assert result.provider == "deepseek"
        assert result.status == "success"
        assert result.text == "广告文案内容"
        assert result.error_code is None
        assert result.error_message is None

    def test_failed_result(self) -> None:
        """失败调用结果。"""
        result = ProviderResult(
            provider="deepseek",
            model="deepseek-chat",
            status="failed",
            usage=ProviderUsage(),  # 失败时 usage 为空
            error_code="PROVIDER_TIMEOUT",
            error_message="调用超时",
            latency_ms=30000,
        )
        assert result.status == "failed"
        assert result.error_code == "PROVIDER_TIMEOUT"
        assert result.error_message == "调用超时"
        assert result.text == ""

    def test_result_aligns_with_interface_spec(self) -> None:
        """验证 ProviderResult 字段对齐 MODULE_INTERFACES.md 输出结构。"""
        result = ProviderResult(
            provider="deepseek",
            model="deepseek-chat",
            status="success",
            text="生成内容",
            files=[],
            usage=ProviderUsage(
                input_tokens=120,
                output_tokens=80,
                total_tokens=200,
            ),
            estimated_cost=0.002,
            raw_usage_json={},
            provider_request_id="provider_req_xxx",
            latency_ms=1200,
        )
        d = result.model_dump()
        # 验证 MODULE_INTERFACES.md 要求的所有字段都存在
        assert "provider" in d
        assert "model" in d
        assert "status" in d
        assert "text" in d
        assert "files" in d
        assert "usage" in d
        assert "estimated_cost" in d
        assert "raw_usage_json" in d
        assert "provider_request_id" in d
        assert "latency_ms" in d

    def test_missing_required_fields_raises(self) -> None:
        """缺少必填字段应抛出 ValidationError。"""
        with pytest.raises(ValidationError):
            ProviderResult()  # type: ignore
