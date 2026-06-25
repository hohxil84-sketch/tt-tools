"""Provider runtime environment configuration.

This module intentionally uses plain environment variables so provider-runtime
can be imported from modules that manipulate sys.path during tests.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_root_dotenv() -> None:
    """Load root .env values when they are not already present."""
    env_path = _project_root() / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _env(name: str, default: str = "") -> str:
    load_root_dotenv()
    return os.environ.get(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name, "true" if default else "false").lower()
    return value in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ProviderRuntimeSettings:
    ai_text_provider: str = "deepseek"
    ai_text_tier: str = "cheap"
    ai_text_fallback_provider: str = "doubao"
    ai_image_provider: str = "doubao"

    deepseek_enabled: bool = False
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_default_model: str = "deepseek-chat"
    deepseek_timeout_seconds: float = 60.0

    doubao_enabled: bool = False
    doubao_api_key: str = ""
    doubao_base_url: str = ""
    doubao_text_model: str = ""
    doubao_image_model: str = ""
    doubao_image_endpoint: str = ""
    doubao_timeout_seconds: float = 120.0


def get_settings() -> ProviderRuntimeSettings:
    return ProviderRuntimeSettings(
        ai_text_provider=_env("AI_TEXT_PROVIDER", "deepseek"),
        ai_text_tier=_env("AI_TEXT_TIER", "cheap"),
        ai_text_fallback_provider=_env("AI_TEXT_FALLBACK_PROVIDER", "doubao"),
        ai_image_provider=_env("AI_IMAGE_PROVIDER", "doubao"),
        deepseek_enabled=_env_bool("DEEPSEEK_ENABLED", bool(_env("DEEPSEEK_API_KEY"))),
        deepseek_api_key=_env("DEEPSEEK_API_KEY"),
        deepseek_base_url=_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_default_model=_env("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat"),
        deepseek_timeout_seconds=float(_env("DEEPSEEK_TIMEOUT_SECONDS", "60")),
        doubao_enabled=_env_bool("DOUBAO_ENABLED", bool(_env("DOUBAO_API_KEY"))),
        doubao_api_key=_env("DOUBAO_API_KEY"),
        doubao_base_url=_env("DOUBAO_BASE_URL"),
        doubao_text_model=_env("DOUBAO_TEXT_MODEL"),
        doubao_image_model=_env("DOUBAO_IMAGE_MODEL"),
        doubao_image_endpoint=_env("DOUBAO_IMAGE_ENDPOINT"),
        doubao_timeout_seconds=float(_env("DOUBAO_TIMEOUT_SECONDS", "120")),
    )
