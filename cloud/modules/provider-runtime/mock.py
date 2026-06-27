"""
Mock Provider 实现。

用于开发和测试阶段，不调用真实 AI API，不消耗额度。
返回符合 ProviderResult 结构的模拟数据，外形与真实 API 一致。
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from base import BaseProvider
from models import ProviderCallRequest, ProviderUsage


# ============================================================
# Mock 常用模型的模拟回复
# ============================================================

# 模拟回复模板库：根据功能码和模型返回不同的模拟内容
_MOCK_RESPONSES: dict[str, dict[str, str]] = {
    # 文案生成
    "ai_copy_cloud": {
        "deepseek-chat": "开业大促，高清快印，当天取件！品质印刷，价格实惠，欢迎到店咨询。",
        "gpt-4o": "Grand opening sale! High-quality printing, same-day pickup. Visit us today!",
        "gpt-4o-mini": "快印宣传单，当天取件，高清印刷，附近商户首选。",
    },
    # 效果图
    "ai_render_cloud": {
        "deepseek-chat": "效果图生成任务已创建，预计 30 秒内完成。",
        "gpt-4o": "Render task created successfully. Estimated completion in 30 seconds.",
    },
    # 图片工具
    "upscale_image_cloud": {
        "deepseek-chat": "高清修复任务已提交，正在处理中。",
        "gpt-4o": "Image upscaling task submitted and running.",
    },
    "vectorize_image_cloud": {
        "deepseek-chat": "矢量化任务已提交，正在处理中。",
        "gpt-4o": "Vectorization task submitted and running.",
    },
    "ai_edit_image_cloud": {
        "deepseek-chat": "AI 改图任务已提交，正在处理中。",
        "gpt-4o": "AI image editing task submitted and running.",
    },
    "remove_bg_cloud": {
        "deepseek-chat": "高级抠图任务已提交，正在处理中。",
        "gpt-4o": "Background removal task submitted and running.",
    },
    "ocr_cloud": {
        "deepseek-chat": "OCR 识别任务已提交，正在处理中。",
        "gpt-4o": "OCR task submitted and running.",
    },
}

# 默认模拟回复（功能码或模型没有匹配时使用）
_DEFAULT_MOCK_TEXT = "这是 Mock Provider 返回的模拟结果。"

# 各模型的模拟 token 用量
_MOCK_USAGE: dict[str, dict[str, int]] = {
    "deepseek-chat": {"input": 120, "output": 80},
    "deepseek-reasoner": {"input": 200, "output": 150, "reasoning": 500},
    "gpt-4o": {"input": 100, "output": 60},
    "gpt-4o-mini": {"input": 80, "output": 50},
    "gpt-4-turbo": {"input": 110, "output": 70},
}


class MockProvider(BaseProvider):
    """Mock Provider，返回模拟结果，不调用真实 AI API。

    支持通过 configure() 方法注入自定义响应，用于特定测试场景。

    使用示例：
        provider = MockProvider()
        result = await provider.call(request)

        # 注入自定义响应
        provider.configure({"text": "自定义回复", "usage": {...}})
    """

    def __init__(
        self,
        delay_ms: int = 0,
        provider_name: str = "mock",
    ):
        """初始化 Mock Provider。

        Args:
            delay_ms: 模拟延迟（毫秒），用于测试超时逻辑，默认 0
            provider_name: Provider 标识名，默认 "mock"
        """
        self._provider_name = provider_name
        self._delay_ms = delay_ms
        # 可配置的注入响应，为 None 时使用默认逻辑
        self._injected_text: Optional[str] = None
        self._injected_usage: Optional[dict[str, int]] = None
        self._injected_files: Optional[list[dict[str, Any]]] = None
        self._should_fail: bool = False
        self._fail_error_message: str = "Mock Provider 模拟失败"

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def configure(
        self,
        text: Optional[str] = None,
        usage: Optional[dict[str, int]] = None,
        files: Optional[list[dict[str, Any]]] = None,
        should_fail: bool = False,
        fail_error_message: str = "Mock Provider 模拟失败",
    ) -> None:
        """配置 Mock Provider 的返回行为。

        Args:
            text: 模拟的文本回复，为 None 时用默认逻辑
            usage: 模拟的 token 用量，为 None 时用默认逻辑
            files: 模拟的文件列表
            should_fail: 是否模拟失败
            fail_error_message: 模拟失败时的错误消息
        """
        self._injected_text = text
        self._injected_usage = usage
        self._injected_files = files
        self._should_fail = should_fail
        self._fail_error_message = fail_error_message

    def reset(self) -> None:
        """重置所有注入配置，恢复默认行为。"""
        self._injected_text = None
        self._injected_usage = None
        self._injected_files = None
        self._should_fail = False
        self._fail_error_message = "Mock Provider 模拟失败"

    async def _do_call(
        self, request: ProviderCallRequest
    ) -> tuple[str, dict[str, Any], Optional[str], dict[str, Any]]:
        """执行模拟调用。

        Args:
            request: 调用请求

        Returns:
            (text, raw_usage_dict, provider_request_id, raw_meta_dict)
        """
        # 模拟延迟
        if self._delay_ms > 0:
            await _async_sleep(self._delay_ms)

        # 模拟失败
        if self._should_fail:
            raise RuntimeError(self._fail_error_message)

        # 确定模拟文本
        text = self._injected_text
        if text is None:
            # 按功能码和模型查找模拟回复
            feature_responses = _MOCK_RESPONSES.get(request.feature, {})
            text = feature_responses.get(request.model, _DEFAULT_MOCK_TEXT)

        # 确定模拟 usage
        usage_dict = self._injected_usage
        if usage_dict is None:
            usage_dict = _MOCK_USAGE.get(request.model, {"input": 50, "output": 30})

        raw_usage = {
            "prompt_tokens": usage_dict.get("input", 0),
            "completion_tokens": usage_dict.get("output", 0),
            "total_tokens": usage_dict.get("input", 0) + usage_dict.get("output", 0),
        }
        # 推理 token（如 deepseek-reasoner）
        if "reasoning" in usage_dict:
            raw_usage["completion_tokens_details"] = {
                "reasoning_tokens": usage_dict["reasoning"]
            }

        # 模拟 Provider 请求 ID
        provider_request_id = f"mock_req_{uuid.uuid4().hex[:12]}"

        # 模拟脱敏元数据
        raw_meta = {
            "model": request.model,
            "finish_reason": "stop",
            "mock": True,
        }

        return text, raw_usage, provider_request_id, raw_meta

    def parse_usage(self, raw_usage: dict[str, Any]) -> ProviderUsage:
        """解析 mock 的 usage 数据。

        Args:
            raw_usage: mock 返回的 usage dict

        Returns:
            统一的 ProviderUsage 结构
        """
        input_tokens = raw_usage.get("prompt_tokens", 0)
        output_tokens = raw_usage.get("completion_tokens", 0)
        total_tokens = raw_usage.get("total_tokens", input_tokens + output_tokens)
        reasoning_tokens = 0
        # 尝试从 completion_tokens_details 中提取推理 token
        completion_details = raw_usage.get("completion_tokens_details", {})
        if isinstance(completion_details, dict):
            reasoning_tokens = completion_details.get("reasoning_tokens", 0)

        return ProviderUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            reasoning_tokens=reasoning_tokens,
            cached_tokens=raw_usage.get("cached_tokens", 0),
            image_count=raw_usage.get("image_count", 0),
        )


async def _async_sleep(ms: int) -> None:
    """异步延迟辅助函数。

    使用 asyncio.sleep 实现，避免阻塞事件循环。

    Args:
        ms: 延迟毫秒数
    """
    import asyncio
    await asyncio.sleep(ms / 1000.0)
