"""DeepSeek text provider.

DeepSeek 使用 OpenAI 兼容接口。本类是 OpenAICompatibleProvider 的特化子类，
保留向后兼容的默认值（base_url、default_model）。

新 Provider 应直接使用 OpenAICompatibleProvider，不硬编码任何默认值。
"""
from __future__ import annotations

from openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek OpenAI-compatible chat provider.

    向后兼容：自动设置 base_url、default_model 和 provider_name 默认值。
    也可以通过构造参数覆盖这些默认值。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        default_model: str = "deepseek-v4-flash",
        timeout_seconds: float = 60.0,
        provider_name: str = "deepseek",
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            timeout_seconds=timeout_seconds,
            provider_name=provider_name,
        )
