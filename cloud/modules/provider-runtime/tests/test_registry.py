from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_MODULE_DIR = _PROJECT_ROOT / "cloud" / "modules" / "provider-runtime"
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

from models import ChatMessage, ProviderCallRequest
from registry import BALANCED, CHEAP, IMAGE_EDIT, TEXT, create_default_router, resolve_route


@pytest.fixture(autouse=True)
def provider_env(monkeypatch: pytest.MonkeyPatch):
    keys = [
        "AI_PROVIDER",
        "IMAGE_TOOLS_PROVIDER",
        "AI_TEXT_PROVIDER",
        "AI_IMAGE_PROVIDER",
        "AI_TEXT_CHEAP_PROVIDER",
        "AI_TEXT_CHEAP_MODEL",
        "AI_IMAGE_EDIT_BALANCED_PROVIDER",
        "AI_IMAGE_EDIT_BALANCED_MODEL",
        "DEEPSEEK_ENABLED",
        "DEEPSEEK_API_KEY",
        "DOUBAO_ENABLED",
        "DOUBAO_API_KEY",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)


def test_legacy_text_provider_env_routes_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setenv("AI_TEXT_PROVIDER", "mock")
    route = resolve_route(TEXT, CHEAP, "ai_copy_cloud")
    assert route.provider == "mock"
    assert route.model == "mock-model"


def test_legacy_image_provider_env_routes_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMAGE_TOOLS_PROVIDER", "mock")
    route = resolve_route(IMAGE_EDIT, BALANCED, "ai_edit_image_cloud")
    assert route.provider == "mock"
    assert route.model == "mock-model"


def test_capability_tier_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_TEXT_CHEAP_PROVIDER", "deepseek")
    monkeypatch.setenv("AI_TEXT_CHEAP_MODEL", "deepseek-v4-flash")
    route = resolve_route(TEXT, CHEAP, "ai_copy_cloud")
    assert route.provider == "deepseek"
    assert route.model == "deepseek-v4-flash"


@pytest.mark.asyncio
async def test_call_by_route_uses_registered_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setenv("AI_TEXT_PROVIDER", "mock")
    router = create_default_router()
    request = ProviderCallRequest(
        model="route",
        capability=TEXT,
        tier=CHEAP,
        messages=[ChatMessage(role="user", content="test")],
        feature="ai_copy_cloud",
    )
    result = await router.call_by_route(request, capability=TEXT, tier=CHEAP)
    assert result.status == "success"
    assert result.provider == "mock"
    assert result.model == "mock-model"
