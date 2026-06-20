"""
MockProvider 测试。

验证 MockProvider 的默认行为、配置注入、失败模拟和 usage 解析。
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
import time

from models import ProviderCallRequest, ProviderUsage, ChatMessage
from mock import MockProvider


class TestMockProviderBasic:
    """MockProvider 基础行为测试。"""

    @pytest.mark.asyncio
    async def test_provider_name(self) -> None:
        """provider_name 属性应返回 'mock'。"""
        provider = MockProvider()
        assert provider.provider_name == "mock"

    @pytest.mark.asyncio
    async def test_call_returns_success(self) -> None:
        """默认调用应返回成功结果。"""
        provider = MockProvider()
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="你好")],
            feature="ai_copy_cloud",
        )
        result = await provider.call(request)
        assert result.status == "success"
        assert result.provider == "mock"
        assert result.model == "deepseek-chat"
        assert len(result.text) > 0  # 应有模拟文本

    @pytest.mark.asyncio
    async def test_call_returns_valid_usage(self) -> None:
        """调用结果应包含有效的 usage 数据。"""
        provider = MockProvider()
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="你好")],
            feature="ai_copy_cloud",
        )
        result = await provider.call(request)
        usage = result.usage
        assert isinstance(usage, ProviderUsage)
        assert usage.input_tokens > 0
        assert usage.output_tokens > 0
        assert usage.total_tokens == usage.input_tokens + usage.output_tokens

    @pytest.mark.asyncio
    async def test_call_generates_provider_request_id(self) -> None:
        """每次调用应生成唯一的 provider_request_id。"""
        provider = MockProvider()
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        result1 = await provider.call(request)
        result2 = await provider.call(request)
        assert result1.provider_request_id != result2.provider_request_id
        assert result1.provider_request_id.startswith("mock_req_")

    @pytest.mark.asyncio
    async def test_call_records_latency(self) -> None:
        """调用结果应记录延迟（>= 0）。"""
        provider = MockProvider()
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        result = await provider.call(request)
        assert result.latency_ms >= 0


class TestMockProviderFeatureResponses:
    """MockProvider 按功能码返回模拟文本测试。"""

    @pytest.mark.asyncio
    async def test_ai_copy_feature_returns_copy_text(self) -> None:
        """ai_copy_cloud 功能码应返回文案相关的模拟文本。"""
        provider = MockProvider()
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="写广告")],
            feature="ai_copy_cloud",
        )
        result = await provider.call(request)
        assert result.status == "success"
        assert len(result.text) > 5

    @pytest.mark.asyncio
    async def test_unknown_feature_returns_default_text(self) -> None:
        """未知功能码应返回默认模拟文本。"""
        provider = MockProvider()
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="测试")],
            feature="unknown_feature_xyz",
        )
        result = await provider.call(request)
        assert result.status == "success"
        assert "Mock Provider" in result.text

    @pytest.mark.asyncio
    async def test_different_models_different_usage(self) -> None:
        """不同模型应返回不同的模拟 token 用量。"""
        provider = MockProvider()
        req_deepseek = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        req_gpt = ProviderCallRequest(
            model="gpt-4o",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        r1 = await provider.call(req_deepseek)
        r2 = await provider.call(req_gpt)
        # 不同模型的 usage 应不同
        assert r1.usage.input_tokens != r2.usage.input_tokens

    @pytest.mark.asyncio
    async def test_deepseek_reasoner_has_reasoning_tokens(self) -> None:
        """deepseek-reasoner 模型应模拟推理 token。"""
        provider = MockProvider()
        request = ProviderCallRequest(
            model="deepseek-reasoner",
            messages=[ChatMessage(role="user", content="复杂问题")],
            feature="test",
        )
        result = await provider.call(request)
        # deepseek-reasoner 应有推理 token
        assert result.usage.reasoning_tokens > 0
        # raw_usage_json 应包含 completion_tokens_details
        assert "completion_tokens_details" in result.raw_usage_json


class TestMockProviderConfigure:
    """MockProvider configure() 注入测试。"""

    @pytest.mark.asyncio
    async def test_inject_custom_text(self) -> None:
        """注入自定义文本。"""
        provider = MockProvider()
        provider.configure(text="自定义回复内容")
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        result = await provider.call(request)
        assert result.text == "自定义回复内容"

    @pytest.mark.asyncio
    async def test_inject_custom_usage(self) -> None:
        """注入自定义 usage。"""
        provider = MockProvider()
        provider.configure(usage={"input": 999, "output": 888})
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        result = await provider.call(request)
        assert result.usage.input_tokens == 999
        assert result.usage.output_tokens == 888
        assert result.usage.total_tokens == 999 + 888

    @pytest.mark.asyncio
    async def test_simulate_failure(self) -> None:
        """模拟失败场景。"""
        provider = MockProvider()
        provider.configure(should_fail=True, fail_error_message="模拟网络错误")
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        with pytest.raises(RuntimeError, match="模拟网络错误"):
            await provider.call(request)

    @pytest.mark.asyncio
    async def test_reset_clears_configuration(self) -> None:
        """reset() 应清除所有注入配置。"""
        provider = MockProvider()
        provider.configure(text="注入文本", should_fail=False)
        provider.reset()

        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        result = await provider.call(request)
        # 重置后应返回默认文本，而不是注入文本
        assert result.text != "注入文本"
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_simulate_delay(self) -> None:
        """模拟延迟（设置小的 delay_ms 确保机制工作）。"""
        provider = MockProvider(delay_ms=50)
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        t0 = time.perf_counter()
        result = await provider.call(request)
        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000
        # 延迟应 >= 45ms（允许少量误差）
        assert elapsed_ms >= 45
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_custom_provider_name(self) -> None:
        """自定义 provider_name 构造函数参数。"""
        provider = MockProvider(provider_name="custom-mock")
        request = ProviderCallRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        result = await provider.call(request)
        assert result.provider == "custom-mock"


class TestMockProviderUsageParsing:
    """MockProvider parse_usage() 测试。"""

    def test_parse_openai_style_usage(self) -> None:
        """解析 OpenAI 风格的 usage dict。"""
        provider = MockProvider()
        raw = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }
        usage = provider.parse_usage(raw)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150

    def test_parse_empty_usage(self) -> None:
        """解析空 usage dict。"""
        provider = MockProvider()
        usage = provider.parse_usage({})
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0

    def test_parse_usage_with_reasoning(self) -> None:
        """解析包含推理 token 的 usage。"""
        provider = MockProvider()
        raw = {
            "prompt_tokens": 200,
            "completion_tokens": 100,
            "total_tokens": 300,
            "completion_tokens_details": {"reasoning_tokens": 500},
        }
        usage = provider.parse_usage(raw)
        assert usage.reasoning_tokens == 500

    def test_parse_usage_with_cached(self) -> None:
        """解析包含缓存 token 的 usage。"""
        provider = MockProvider()
        raw = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "cached_tokens": 80,
        }
        usage = provider.parse_usage(raw)
        assert usage.cached_tokens == 80
