"""
Provider 路由器测试。

验证 ProviderRouter 的注册、路由选择、调用转发、错误处理和成本估算集成。
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

from models import ProviderCallRequest, ProviderResult, ChatMessage
from mock import MockProvider
from router import (
    ProviderRouter,
    get_provider_name_for_model,
    call_provider,
    get_provider_for_model,
)
from errors import ProviderError


class TestModelRouting:
    """模型名称 → Provider 名称映射测试。"""

    def test_deepseek_models_route_to_deepseek(self) -> None:
        """deepseek 开头的模型应路由到 deepseek。"""
        assert get_provider_name_for_model("deepseek-chat") == "deepseek"
        assert get_provider_name_for_model("deepseek-reasoner") == "deepseek"

    def test_gpt_models_route_to_openai(self) -> None:
        """gpt- 开头的模型应路由到 openai。"""
        assert get_provider_name_for_model("gpt-4o") == "openai"
        assert get_provider_name_for_model("gpt-4o-mini") == "openai"
        assert get_provider_name_for_model("gpt-4-turbo") == "openai"

    def test_o1_o3_o4_models_route_to_openai(self) -> None:
        """o1/o3/o4 模型应路由到 openai。"""
        assert get_provider_name_for_model("o1-preview") == "openai"
        assert get_provider_name_for_model("o3-mini") == "openai"

    def test_claude_models_route_to_anthropic(self) -> None:
        """claude 模型应路由到 anthropic。"""
        assert get_provider_name_for_model("claude-3-opus") == "anthropic"
        assert get_provider_name_for_model("claude-3.5-sonnet") == "anthropic"

    def test_unknown_model_routes_to_mock(self) -> None:
        """未匹配的模型默认路由到 mock。"""
        assert get_provider_name_for_model("some-random-model") == "mock"

    def test_case_insensitive_routing(self) -> None:
        """路由应不区分大小写。"""
        assert get_provider_name_for_model("GPT-4O") == "openai"
        assert get_provider_name_for_model("DeepSeek-Chat") == "deepseek"


class TestProviderRouterRegistration:
    """ProviderRouter 注册测试。"""

    def test_register_provider(self) -> None:
        """注册 Provider 实例。"""
        router = ProviderRouter()
        provider = MockProvider(provider_name="deepseek")
        router.register("deepseek", provider)
        assert router.get_provider("deepseek") is provider

    def test_get_unregistered_provider_returns_none(self) -> None:
        """获取未注册的 Provider 返回 None。"""
        router = ProviderRouter()
        assert router.get_provider("nonexistent") is None

    def test_list_providers(self) -> None:
        """列出所有已注册的 Provider。"""
        router = ProviderRouter()
        assert router.list_providers() == []
        router.register("mock1", MockProvider(provider_name="mock1"))
        router.register("mock2", MockProvider(provider_name="mock2"))
        assert sorted(router.list_providers()) == ["mock1", "mock2"]


class TestProviderRouterCall:
    """ProviderRouter call() 方法测试。"""

    @pytest.mark.asyncio
    async def test_call_with_explicit_provider(self) -> None:
        """直接指定 Provider 实例调用。"""
        router = ProviderRouter()
        provider = MockProvider()
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="你好")],
            feature="ai_copy_cloud",
        )
        result = await router.call(request, provider=provider)
        assert result.status == "success"
        assert result.provider == "mock"
        assert result.model == "deepseek-chat"
        # 应包含成本估算
        assert result.estimated_cost > 0

    @pytest.mark.asyncio
    async def test_call_through_routing(self) -> None:
        """通过模型路由查找 Provider。"""
        router = ProviderRouter()
        router.register("deepseek", MockProvider(provider_name="deepseek"))
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="你好")],
            feature="ai_copy_cloud",
        )
        result = await router.call(request)
        assert result.status == "success"
        assert result.provider == "deepseek"

    @pytest.mark.asyncio
    async def test_call_unregistered_model_raises(self) -> None:
        """模型对应的 Provider 未注册时应抛出 ProviderError。"""
        router = ProviderRouter()
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        # deepseek-chat 路由到 deepseek，但未注册
        with pytest.raises(ProviderError, match="未注册"):
            await router.call(request)

    @pytest.mark.asyncio
    async def test_call_mock_route_with_mock_registered(self) -> None:
        """未知模型路由到 mock，注册 mock provider 可调用。"""
        router = ProviderRouter()
        router.register("mock", MockProvider())
        request = ProviderCallRequest(
            model="unknown-model-xyz",
            messages=[ChatMessage(role="user", content="测试")],
            feature="test",
        )
        result = await router.call(request)
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_call_handles_provider_failure(self) -> None:
        """Provider 调用失败时应返回失败结果（不抛出异常）。"""
        router = ProviderRouter()
        provider = MockProvider()
        provider.configure(should_fail=True, fail_error_message="模拟失败")
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        # router.call 捕获异常并返回失败 ProviderResult
        result = await router.call(request, provider=provider)
        assert result.status == "failed"
        assert result.error_code is not None
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_call_includes_cost_estimation(self) -> None:
        """成功的调用应包含成本估算。"""
        router = ProviderRouter()
        provider = MockProvider()
        # 注入已知 usage 以验证成本计算
        provider.configure(usage={"input": 1_000_000, "output": 500_000})
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        result = await router.call(request, provider=provider)
        assert result.estimated_cost > 0
        # deepseek-chat: 1M * ¥1 + 0.5M * ¥2 = ¥2.0
        assert result.estimated_cost == pytest.approx(2.0)

    @pytest.mark.asyncio
    async def test_failed_call_cost_is_zero(self) -> None:
        """失败的调用成本估算为 0。"""
        router = ProviderRouter()
        provider = MockProvider()
        provider.configure(should_fail=True)
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        result = await router.call(request, provider=provider)
        assert result.status == "failed"
        assert result.estimated_cost == 0.0


class TestConvenienceFunctions:
    """便捷函数测试。"""

    @pytest.mark.asyncio
    async def test_call_provider_convenience(self) -> None:
        """call_provider 便捷函数应可正常调用。"""
        provider = MockProvider()
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="你好")],
            feature="ai_copy_cloud",
        )
        result = await call_provider(request, provider=provider)
        assert result.status == "success"
        assert result.estimated_cost > 0

    @pytest.mark.asyncio
    async def test_get_provider_for_model(self) -> None:
        """get_provider_for_model 便捷函数。"""
        router = ProviderRouter()
        provider = MockProvider(provider_name="deepseek")
        router.register("deepseek", provider)
        found = await get_provider_for_model("deepseek-chat", router)
        assert found is provider

    @pytest.mark.asyncio
    async def test_get_provider_for_model_not_found(self) -> None:
        """get_provider_for_model 未找到时返回 None。"""
        router = ProviderRouter()
        found = await get_provider_for_model("deepseek-chat", router)
        assert found is None


class TestRouterWithMultipleRealisticScenarios:
    """路由器多场景集成测试。"""

    @pytest.mark.asyncio
    async def test_router_with_mock_providers_for_all_routes(self) -> None:
        """注册所有路由的 mock provider 并逐一验证。"""
        router = ProviderRouter()
        # 注册所有已知路由的 mock provider
        router.register("mock", MockProvider(provider_name="mock"))
        router.register("deepseek", MockProvider(provider_name="deepseek"))
        router.register("openai", MockProvider(provider_name="openai"))
        router.register("anthropic", MockProvider(provider_name="anthropic"))

        # 验证各模型路由
        test_cases = [
            ("deepseek-chat", "deepseek"),
            ("gpt-4o-mini", "openai"),
            ("claude-3-haiku", "anthropic"),
            ("unknown-model", "mock"),
        ]

        for model, expected_provider in test_cases:
            request = ProviderCallRequest(
                model=model,
                messages=[ChatMessage(role="user", content="测试")],
                feature="ai_copy_cloud",
            )
            result = await router.call(request)
            assert result.status == "success"
            assert result.provider == expected_provider
            assert result.model == model

    @pytest.mark.asyncio
    async def test_router_maintains_result_consistency(self) -> None:
        """多次调用结果应保持结构和字段一致。"""
        router = ProviderRouter()
        provider = MockProvider()
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="你好")],
            feature="ai_copy_cloud",
        )
        # 多次调用，验证结构一致
        for _ in range(3):
            result = await router.call(request, provider=provider)
            assert result.status == "success"
            assert result.provider == "mock"
            assert result.model == "deepseek-chat"
            assert isinstance(result.usage.input_tokens, int)
            assert isinstance(result.usage.output_tokens, int)
            assert isinstance(result.estimated_cost, float)
            assert isinstance(result.latency_ms, int)
            assert result.raw_usage_json is not None

    @pytest.mark.asyncio
    async def test_mock_result_includes_latency(self) -> None:
        """验证延迟正确记录。"""
        router = ProviderRouter()
        provider = MockProvider(delay_ms=10)
        request = ProviderCallRequest(
            model="deepseek-chat",
            messages=[ChatMessage(role="user", content="x")],
            feature="test",
        )
        result = await router.call(request, provider=provider)
        assert result.latency_ms >= 0  # 延迟记录非负
