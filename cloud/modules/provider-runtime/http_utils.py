"""Shared helpers for HTTP based providers."""
from __future__ import annotations

from typing import Any

from errors import ProviderError, ProviderErrorCode
from models import ChatMessage, ProviderUsage


def messages_to_payload(messages: list[ChatMessage]) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in messages]


def parse_openai_usage(raw_usage: dict[str, Any]) -> ProviderUsage:
    input_tokens = int(raw_usage.get("prompt_tokens") or raw_usage.get("input_tokens") or 0)
    output_tokens = int(raw_usage.get("completion_tokens") or raw_usage.get("output_tokens") or 0)
    total_tokens = int(raw_usage.get("total_tokens") or input_tokens + output_tokens)

    reasoning_tokens = 0
    completion_details = raw_usage.get("completion_tokens_details")
    if isinstance(completion_details, dict):
        reasoning_tokens = int(completion_details.get("reasoning_tokens") or 0)

    cached_tokens = 0
    prompt_details = raw_usage.get("prompt_tokens_details")
    if isinstance(prompt_details, dict):
        cached_tokens = int(prompt_details.get("cached_tokens") or 0)
    else:
        cached_tokens = int(raw_usage.get("cached_tokens") or 0)

    image_count = int(
        raw_usage.get("image_count")
        or raw_usage.get("generated_images")
        or raw_usage.get("image_num")
        or 0
    )

    return ProviderUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        reasoning_tokens=reasoning_tokens,
        cached_tokens=cached_tokens,
        image_count=image_count,
    )


def provider_error_from_status(status_code: int, text: str) -> ProviderError:
    lowered = text.lower()
    if status_code in {401, 403}:
        return ProviderError(
            code=ProviderErrorCode.PROVIDER_AUTH_FAILED,
            message="Provider authentication failed",
            status_code=502,
            details={"status_code": status_code, "response": text[:1000]},
        )
    if status_code == 429 or "rate limit" in lowered:
        return ProviderError(
            code=ProviderErrorCode.PROVIDER_RATE_LIMITED,
            message="Provider rate limited",
            status_code=429,
            details={"status_code": status_code, "response": text[:1000]},
        )
    if any(word in lowered for word in ("quota", "balance", "insufficient")):
        return ProviderError(
            code=ProviderErrorCode.PROVIDER_QUOTA_EXCEEDED,
            message="Provider quota exceeded",
            status_code=502,
            details={"status_code": status_code, "response": text[:1000]},
        )
    if 500 <= status_code:
        return ProviderError(
            code=ProviderErrorCode.PROVIDER_UNAVAILABLE,
            message="Provider service unavailable",
            status_code=502,
            details={"status_code": status_code, "response": text[:1000]},
        )
    return ProviderError(
        code=ProviderErrorCode.PROVIDER_BAD_RESPONSE,
        message="Provider returned a bad response",
        status_code=502,
        details={"status_code": status_code, "response": text[:1000]},
    )
