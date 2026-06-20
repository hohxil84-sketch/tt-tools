"""
Provider 抽象基类。

所有 Provider 实现（mock、OpenAI、DeepSeek 等）必须继承此基类，
实现统一的调用接口和 usage 解析方法。
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from models import ProviderCallRequest, ProviderResult, ProviderUsage


class BaseProvider(ABC):
    """Provider 抽象基类。

    子类必须实现：
      - _do_call()：执行实际 API 调用
      - provider_name()：返回 Provider 标识名
      - parse_usage()：从 Provider 原始响应中提取统一用量结构
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """返回 Provider 标识名，如 'deepseek'、'openai'。"""
        ...

    @abstractmethod
    async def _do_call(
        self, request: ProviderCallRequest
    ) -> tuple[str, dict[str, Any], Optional[str], dict[str, Any]]:
        """执行实际 Provider API 调用。

        子类必须实现该方法，封装具体的 HTTP / SDK 调用逻辑。

        Args:
            request: 统一的调用请求

        Returns:
            (text, raw_usage_dict, provider_request_id, raw_meta_dict)
            - text: 生成文本内容
            - raw_usage_dict: Provider 返回的原始 usage 数据
            - provider_request_id: Provider 侧的请求 ID
            - raw_meta_dict: 脱敏元数据（如模型名、finish_reason 等）
        """
        ...

    @abstractmethod
    def parse_usage(self, raw_usage: dict[str, Any]) -> ProviderUsage:
        """从 Provider 原始 usage JSON 中解析统一用量结构。

        Args:
            raw_usage: Provider 返回的 usage dict

        Returns:
            统一的 ProviderUsage 结构
        """
        ...

    async def call(self, request: ProviderCallRequest) -> ProviderResult:
        """统一调用入口：计时、调用、解析 usage、组装结果。

        子类通常不需要覆盖此方法；它封装了通用的计时和结果组装逻辑，
        把具体的 API 调用委托给 _do_call()。

        Args:
            request: 统一的调用请求

        Returns:
            统一的 ProviderResult 结构
        """
        t0 = time.perf_counter()
        try:
            text, raw_usage, provider_req_id, raw_meta = await self._do_call(request)
            latency_ms = int((time.perf_counter() - t0) * 1000)

            usage = self.parse_usage(raw_usage)

            return ProviderResult(
                provider=self.provider_name,
                model=request.model,
                status="success",
                text=text,
                usage=usage,
                estimated_cost=0.0,  # 成本由上层 CostEstimator 计算
                raw_usage_json=raw_usage,
                provider_request_id=provider_req_id,
                latency_ms=latency_ms,
            )
        except Exception:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            # 异常交由 router / 上层统一处理并转换为失败 ProviderResult
            raise
