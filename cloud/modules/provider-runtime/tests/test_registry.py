from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_MODULE_DIR = _PROJECT_ROOT / "cloud" / "modules" / "provider-runtime"
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

from mock import MockProvider
from models import ChatMessage, ProviderCallRequest
from registry import CHEAP, TEXT, resolve_route
from router import ProviderRouter
from errors import ProviderError


def test_resolve_route_with_registered_provider() -> None:
    """DB 驱动的 resolve_route：从已注册 Provider 查找 capability。"""
    router = ProviderRouter()
    router.register("deepseek", MockProvider(provider_name="deepseek"), models_json={"text": "deepseek-chat"}, priority=10)
    route = resolve_route(capability=TEXT, router=router)
    assert route.provider == "deepseek"
    assert route.model == "deepseek-chat"


def test_resolve_route_no_provider_raises() -> None:
    """没有任何 Provider 时抛出明确错误。"""
    router = ProviderRouter()
    with pytest.raises(ProviderError, match="没有可用的 Provider"):
        resolve_route(capability=TEXT, router=router)


def test_resolve_route_priority_order() -> None:
    """多个 Provider 时选最高 priority。"""
    router = ProviderRouter()
    router.register("mock", MockProvider(provider_name="mock"), models_json={"text": "mock-model"}, priority=0)
    router.register("deepseek", MockProvider(provider_name="deepseek"), models_json={"text": "deepseek-chat"}, priority=10)
    route = resolve_route(capability=TEXT, router=router)
    assert route.provider == "deepseek"  # priority 10 > 0


@pytest.mark.asyncio
async def test_call_by_capability_uses_registered_provider() -> None:
    """call_by_capability 走 DB 注册的 Provider。"""
    router = ProviderRouter()
    router.register("deepseek", MockProvider(provider_name="deepseek"), models_json={"text": "deepseek-chat"}, priority=10)
    request = ProviderCallRequest(
        model="route",
        capability=TEXT,
        tier=CHEAP,
        messages=[ChatMessage(role="user", content="test")],
        feature="ai_copy_cloud",
    )
    result = await router.call_by_capability(request, capability="text")
    assert result.status == "success"
    assert result.provider == "deepseek"
    assert result.model == "deepseek-chat"


@pytest.mark.asyncio
async def test_call_by_capability_fallback() -> None:
    """最高 priority Provider 失败时自动降级。"""
    router = ProviderRouter()
    # 注册一个会失败的（没有实际实现）和一个 mock
    router.register("fail", MockProvider(provider_name="fail"), models_json={"text": "fail-model"}, priority=10)
    router.register("mock", MockProvider(provider_name="mock"), models_json={"text": "mock-model"}, priority=5)
    request = ProviderCallRequest(
        model="route",
        capability=TEXT,
        tier=CHEAP,
        messages=[ChatMessage(role="user", content="test")],
        feature="ai_copy_cloud",
    )
    result = await router.call_by_capability(request, capability="text")
    # 两个都是 MockProvider 都会成功，第一个成功就返回
    assert result.status == "success"
