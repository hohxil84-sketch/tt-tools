"""Doubao provider for text and image capabilities."""
from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from base import BaseProvider
from cost import estimate_cost
from errors import ProviderError, ProviderErrorCode
from http_utils import messages_to_payload, parse_openai_usage, provider_error_from_status
from models import ProviderCallRequest, ProviderResult, ProviderUsage


class DoubaoProvider(BaseProvider):
    """Doubao/Volcengine Ark provider.

    Text calls use an OpenAI-compatible chat endpoint. Image calls are routed to
    DOUBAO_IMAGE_ENDPOINT because image endpoint shapes vary by enabled model.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        text_model: str,
        image_model: str,
        image_endpoint: str = "",
        timeout_seconds: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._text_model = text_model
        self._image_model = image_model
        self._image_endpoint = image_endpoint
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "doubao"

    async def _do_call(
        self, request: ProviderCallRequest
    ) -> tuple[str, dict[str, Any], Optional[str], dict[str, Any]]:
        if request.capability != "text":
            raise ProviderError(
                code=ProviderErrorCode.PROVIDER_BAD_RESPONSE,
                message="Use DoubaoProvider.call for image capabilities",
                status_code=500,
            )
        return await self._call_text(request)

    async def call(self, request: ProviderCallRequest) -> ProviderResult:
        if request.capability == "text":
            return await super().call(request)
        if request.capability in {"image_generation", "image_edit"}:
            return await self._call_image(request)
        raise ProviderError(
            code=ProviderErrorCode.PROVIDER_NOT_REGISTERED,
            message=f"Doubao does not support capability '{request.capability}'",
            status_code=500,
        )

    async def _call_text(
        self, request: ProviderCallRequest
    ) -> tuple[str, dict[str, Any], Optional[str], dict[str, Any]]:
        if not self._api_key:
            raise ProviderError(
                code=ProviderErrorCode.PROVIDER_AUTH_FAILED,
                message="DOUBAO_API_KEY is not configured",
                status_code=502,
            )
        if not self._base_url:
            raise ProviderError(
                code=ProviderErrorCode.PROVIDER_AUTH_FAILED,
                message="DOUBAO_BASE_URL is not configured",
                status_code=502,
            )

        model = request.model or self._text_model
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
                message="Doubao text response missing choices",
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

    async def _call_image(self, request: ProviderCallRequest) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            if not self._api_key:
                raise ProviderError(
                    code=ProviderErrorCode.PROVIDER_AUTH_FAILED,
                    message="DOUBAO_API_KEY is not configured",
                    status_code=502,
                )
            if not self._image_endpoint:
                raise ProviderError(
                    code=ProviderErrorCode.PROVIDER_AUTH_FAILED,
                    message="DOUBAO_IMAGE_ENDPOINT is not configured",
                    status_code=502,
                )

            model = request.model or self._image_model
            prompt = "\n".join(message.content for message in request.messages if message.role != "system")
            payload = {
                "model": model,
                "prompt": prompt,
                "response_format": "url",
            }
            payload.update(request.extra_options or {})

            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    self._image_endpoint,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if response.status_code >= 400:
                raise provider_error_from_status(response.status_code, response.text)

            data = response.json()
            files = _extract_files(data)
            usage = parse_openai_usage(data.get("usage") or {})
            if usage.image_count == 0:
                usage.image_count = len(files) or 1
            estimated_cost = estimate_cost(
                provider=self.provider_name,
                model=model,
                usage=usage,
            )

            return ProviderResult(
                provider=self.provider_name,
                model=model,
                status="success",
                text=data.get("text") or data.get("message") or "",
                files=files,
                usage=usage,
                estimated_cost=estimated_cost,
                raw_usage_json=data.get("usage") or {"image_count": usage.image_count},
                provider_request_id=str(data.get("id") or response.headers.get("x-request-id") or ""),
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if isinstance(exc, ProviderError):
                return ProviderResult(
                    provider=self.provider_name,
                    model=request.model or self._image_model,
                    status="failed",
                    usage=ProviderUsage(),
                    latency_ms=latency_ms,
                    error_code=exc.code,
                    error_message=exc.message,
                )
            raise

    def parse_usage(self, raw_usage: dict[str, Any]) -> ProviderUsage:
        return parse_openai_usage(raw_usage)


def _extract_files(data: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("files", "images", "data", "result"):
        value = data.get(key)
        if isinstance(value, list):
            return [_normalize_file(item) for item in value]
        if isinstance(value, dict):
            nested = _extract_files(value)
            if nested:
                return nested
    return []


def _normalize_file(item: Any) -> dict[str, Any]:
    if isinstance(item, str):
        return {"url": item, "mime_type": "image/png"}
    if not isinstance(item, dict):
        return {"url": str(item), "mime_type": "image/png"}
    url = item.get("url") or item.get("image_url") or item.get("uri") or item.get("b64_json")
    return {
        "file_id": item.get("file_id") or item.get("id") or "",
        "url": url,
        "mime_type": item.get("mime_type") or item.get("type") or "image/png",
        "width": item.get("width"),
        "height": item.get("height"),
    }
