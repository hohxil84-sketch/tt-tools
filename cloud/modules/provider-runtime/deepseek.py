"""DeepSeek text provider."""
from __future__ import annotations

from typing import Any, Optional

import httpx

from base import BaseProvider
from errors import ProviderError, ProviderErrorCode
from http_utils import messages_to_payload, parse_openai_usage, provider_error_from_status
from models import ProviderCallRequest, ProviderUsage


class DeepSeekProvider(BaseProvider):
    """DeepSeek OpenAI-compatible chat provider.

    DeepSeek is text-only in this product. Image capabilities must route to a
    different provider such as Doubao.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        default_model: str = "deepseek-v4-flash",
        timeout_seconds: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "deepseek"

    async def _do_call(
        self, request: ProviderCallRequest
    ) -> tuple[str, dict[str, Any], Optional[str], dict[str, Any]]:
        if request.capability != "text":
            raise ProviderError(
                code=ProviderErrorCode.PROVIDER_NOT_REGISTERED,
                message=f"DeepSeek does not support capability '{request.capability}'",
                status_code=500,
            )
        if not self._api_key:
            raise ProviderError(
                code=ProviderErrorCode.PROVIDER_AUTH_FAILED,
                message="DEEPSEEK_API_KEY is not configured",
                status_code=502,
            )

        model = request.model or self._default_model
        payload = {
            "model": model,
            "messages": messages_to_payload(request.messages),
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        payload.update(request.extra_options or {})

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if response.status_code >= 400:
            raise provider_error_from_status(response.status_code, response.text)

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError(
                code=ProviderErrorCode.PROVIDER_BAD_RESPONSE,
                message="DeepSeek response missing choices",
                status_code=502,
                details={"response": data},
            )

        message = choices[0].get("message") or {}
        text = message.get("content") or ""
        raw_usage = data.get("usage") or {}
        provider_request_id = str(data.get("id") or response.headers.get("x-request-id") or "")
        raw_meta = {
            "model": data.get("model") or model,
            "finish_reason": choices[0].get("finish_reason"),
        }
        return text, raw_usage, provider_request_id, raw_meta

    def parse_usage(self, raw_usage: dict[str, Any]) -> ProviderUsage:
        return parse_openai_usage(raw_usage)

