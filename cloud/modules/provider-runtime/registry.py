"""Provider registration and capability/tier routing."""
from __future__ import annotations

import os
import importlib.util
from dataclasses import dataclass
from pathlib import Path

from config import get_settings
from deepseek import DeepSeekProvider
from doubao import DoubaoProvider
from errors import ProviderError, ProviderErrorCode
from mock import MockProvider


TEXT = "text"
VISION_TEXT = "vision_text"
IMAGE_GENERATION = "image_generation"
IMAGE_EDIT = "image_edit"

CHEAP = "cheap"
BALANCED = "balanced"
PREMIUM = "premium"


@dataclass(frozen=True)
class RouteTarget:
    provider: str
    model: str


def resolve_route(capability: str, tier: str = CHEAP, feature: str = "") -> RouteTarget:
    """Resolve capability/tier/feature to provider and model.

    Override order:
    1. AI_ROUTE_<FEATURE>_PROVIDER / MODEL
    2. AI_<CAPABILITY>_<TIER>_PROVIDER / MODEL
    3. AI_<CAPABILITY>_PROVIDER / MODEL
    4. defaults from ProviderRuntimeSettings
    """
    settings = get_settings()
    capability_key = capability.upper()
    tier_key = tier.upper()
    feature_key = _normalize_env_part(feature)

    provider = ""
    model = ""
    if feature_key:
        provider = os.environ.get(f"AI_ROUTE_{feature_key}_PROVIDER", "").strip()
        model = os.environ.get(f"AI_ROUTE_{feature_key}_MODEL", "").strip()

    provider = provider or os.environ.get(f"AI_{capability_key}_{tier_key}_PROVIDER", "").strip()
    model = model or os.environ.get(f"AI_{capability_key}_{tier_key}_MODEL", "").strip()

    provider = provider or os.environ.get(f"AI_{capability_key}_PROVIDER", "").strip()
    model = model or os.environ.get(f"AI_{capability_key}_MODEL", "").strip()

    if capability == TEXT:
        provider = provider or os.environ.get("AI_PROVIDER", "").strip() or settings.ai_text_provider
        model = model or _default_model_for_provider(provider, capability)
    elif capability in {IMAGE_GENERATION, IMAGE_EDIT}:
        provider = provider or os.environ.get("IMAGE_TOOLS_PROVIDER", "").strip() or settings.ai_image_provider
        model = model or _default_model_for_provider(provider, capability)
    elif capability == VISION_TEXT:
        provider = provider or settings.ai_text_fallback_provider
        model = model or _default_model_for_provider(provider, capability)
    else:
        raise ProviderError(
            code=ProviderErrorCode.PROVIDER_NOT_REGISTERED,
            message=f"Unsupported provider capability '{capability}'",
            status_code=500,
        )

    if not provider:
        raise ProviderError(
            code=ProviderErrorCode.PROVIDER_NOT_REGISTERED,
            message=f"No provider configured for capability '{capability}' tier '{tier}'",
            status_code=500,
        )
    if not model:
        model = "mock-model" if provider == "mock" else ""
    if not model:
        raise ProviderError(
            code=ProviderErrorCode.PROVIDER_NOT_REGISTERED,
            message=f"No model configured for provider '{provider}' capability '{capability}'",
            status_code=500,
        )
    return RouteTarget(provider=provider, model=model)


def create_default_router(router_cls=None):
    settings = get_settings()
    if router_cls is None:
        router_cls = _load_provider_router_class()
    router = router_cls()
    router.register("mock", MockProvider(provider_name="mock"))

    if settings.deepseek_enabled:
        router.register(
            "deepseek",
            DeepSeekProvider(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                default_model=settings.deepseek_default_model,
                timeout_seconds=settings.deepseek_timeout_seconds,
            ),
        )

    if settings.doubao_enabled:
        router.register(
            "doubao",
            DoubaoProvider(
                api_key=settings.doubao_api_key,
                base_url=settings.doubao_base_url,
                text_model=settings.doubao_text_model,
                image_model=settings.doubao_image_model,
                image_endpoint=settings.doubao_image_endpoint,
                timeout_seconds=settings.doubao_timeout_seconds,
            ),
        )

    return router


def _load_provider_router_class():
    router_path = Path(__file__).with_name("router.py")
    spec = importlib.util.spec_from_file_location("_provider_runtime_router", router_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load provider-runtime router.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ProviderRouter


def _default_model_for_provider(provider: str, capability: str) -> str:
    settings = get_settings()
    if provider == "mock":
        return "mock-model"
    if provider == "deepseek":
        return settings.deepseek_default_model
    if provider == "doubao":
        if capability in {IMAGE_GENERATION, IMAGE_EDIT}:
            return settings.doubao_image_model
        return settings.doubao_text_model
    return ""


def _normalize_env_part(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.upper()).strip("_")
