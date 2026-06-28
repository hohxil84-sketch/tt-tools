"""
OpenAI 兼容 Provider —— 通用类。

覆盖所有使用 OpenAI chat/completions 接口格式的 Provider：
DeepSeek、OpenAI、Gemini（OpenAI 兼容模式）、Groq、Together AI 等。

与 DeepSeekProvider 不同：本类完全由数据库驱动，不硬编码任何 URL 或模型名。
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

from base import BaseProvider
from errors import ProviderError, ProviderErrorCode
from http_utils import messages_to_payload, parse_openai_usage, provider_error_from_status
from models import ProviderCallRequest, ProviderUsage


class OpenAICompatibleProvider(BaseProvider):
    """通用 OpenAI 兼容 Provider。

    通过数据库 providers 表的字段驱动：
    - base_url: API 地址（由后台配置，如 https://api.deepseek.com）
    - default_model: 默认模型（由后台 model_name 决定）
    - provider_name: Provider 标识名（由后台 name 决定）

    支持的 capability 由 provider_model_pricing 表决定，
    router 根据 capability 选择对应 model_name 后通过 request.model 传入。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str = "",
        timeout_seconds: float = 60.0,
        provider_name: str = "",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout_seconds = timeout_seconds
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def _do_call(
        self, request: ProviderCallRequest
    ) -> tuple[str, dict[str, Any], Optional[str], dict[str, Any]]:
        """执行 API 调用。

        所有 capability 均尝试调用，不预先拒绝。
        如果 API 不支持该 capability，由 Provider 返回错误，
        router 捕获后自动降级。
        """
        if not self._api_key:
            raise ProviderError(
                code=ProviderErrorCode.PROVIDER_AUTH_FAILED,
                message=f"{self._provider_name} API Key 未配置",
                status_code=502,
            )

        # 模型名：优先 request.model（router 根据 capability 设定），
        # 否则用构造时传入的 default_model
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
                message=f"{self._provider_name} response missing choices",
                status_code=502,
                details={"response": data},
            )

        message = choices[0].get("message") or {}
        text = message.get("content") or ""
        raw_usage = data.get("usage") or {}
        provider_request_id = str(
            data.get("id") or response.headers.get("x-request-id") or ""
        )
        raw_meta = {
            "model": data.get("model") or model,
            "finish_reason": choices[0].get("finish_reason"),
        }
        return text, raw_usage, provider_request_id, raw_meta

    def parse_usage(self, raw_usage: dict[str, Any]) -> ProviderUsage:
        return parse_openai_usage(raw_usage)
