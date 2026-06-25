"""
Provider 路由器。

负责根据模型名称选择对应的 Provider 实例，执行调用，
并处理失败重试、超时和错误标准化。
"""
from __future__ import annotations

import logging
from typing import Optional

from base import BaseProvider
from cost import estimate_cost
from errors import ProviderError, map_provider_error
from models import ProviderCallRequest, ProviderResult, ProviderUsage
from mock import MockProvider

# 模块日志
_logger = logging.getLogger(__name__)


# ============================================================
# 模型 → Provider 映射
# ============================================================

# 模型名称前缀映射表：
#   当模型名以某前缀开头时，路由到对应的 Provider。
#   完整的 SDK Provider（如 OpenAIProvider、DeepSeekProvider）后续开发；
#   当前阶段全部路由到 MockProvider。
_DEFAULT_MODEL_ROUTING: dict[str, str] = {
    "deepseek": "deepseek",
    "gpt-": "openai",
    "o1": "openai",
    "o3": "openai",
    "o4": "openai",
    "claude": "anthropic",
}

# 默认 Provider 名称（当模型没有匹配任何前缀时使用）
_DEFAULT_PROVIDER_NAME = "mock"


def get_provider_name_for_model(model: str) -> str:
    """根据模型名称获取 Provider 标识名。

    按前缀匹配 _DEFAULT_MODEL_ROUTING 表。
    未匹配时返回 "mock"。

    Args:
        model: 模型名称，如 "deepseek-chat"、"gpt-4o"

    Returns:
        Provider 标识名，如 "deepseek"、"openai"、"mock"
    """
    model_lower = model.lower()
    for prefix, provider_name in _DEFAULT_MODEL_ROUTING.items():
        if model_lower.startswith(prefix):
            return provider_name
    return _DEFAULT_PROVIDER_NAME


# ============================================================
# ProviderRouter
# ============================================================


class ProviderRouter:
    """Provider 路由器。

    管理 Provider 实例注册和模型路由。
    上层业务模块通过 call() 方法执行调用。

    使用示例：
        router = ProviderRouter()
        router.register("mock", MockProvider())
        result = await router.call(request)
    """

    def __init__(self):
        """初始化路由器，Provider 映射表为空。"""
        self._providers: dict[str, BaseProvider] = {}

    def register(self, name: str, provider: BaseProvider) -> None:
        """注册一个 Provider 实例。

        Args:
            name: Provider 标识名（与 provider.provider_name 一致）
            provider: Provider 实例
        """
        self._providers[name] = provider
        _logger.info("Provider 已注册: %s -> %s", name, type(provider).__name__)

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        """获取已注册的 Provider 实例。

        Args:
            name: Provider 标识名

        Returns:
            Provider 实例，未注册时返回 None
        """
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        """列出所有已注册的 Provider 名称。"""
        return list(self._providers.keys())

    async def call(
        self,
        request: ProviderCallRequest,
        provider: Optional[BaseProvider] = None,
    ) -> ProviderResult:
        """执行 Provider 调用。

        优先使用 provider 参数传入的实例；否则根据 request.model
        在注册表中查找对应 Provider。

        Args:
            request: Provider 调用请求
            provider: 可选，直接指定 Provider 实例（绕过路由）

        Returns:
            统一的 ProviderResult 结构（含成功和失败状态）

        Raises:
            ProviderError: 当 Provider 未注册且未传入实例时抛出
        """
        # 选择 Provider
        if provider is None:
            provider_name = get_provider_name_for_model(request.model)
            provider = self._providers.get(provider_name)
            if provider is None:
                raise ProviderError(
                    code="PROVIDER_NOT_REGISTERED",
                    message=f"模型 '{request.model}' 对应的 Provider '{provider_name}' 未注册",
                    status_code=500,
                )

        _logger.debug(
            "调用 Provider: %s, 模型: %s, 功能码: %s, request_id: %s",
            provider.provider_name,
            request.model,
            request.feature,
            request.request_id,
        )

        try:
            result = await provider.call(request)
        except Exception as exc:
            _logger.warning(
                "Provider 调用异常: provider=%s, model=%s, error=%s",
                provider.provider_name,
                request.model,
                str(exc),
            )
            # 将原始异常映射为统一 ProviderResult（失败状态）
            result = _exception_to_result(
                exc=exc,
                provider_name=provider.provider_name,
                model=request.model,
            )
            return result

        # 成功时补充成本估算
        result.estimated_cost = estimate_cost(
            provider=result.provider,
            model=result.model,
            usage=result.usage,
        )

        _logger.debug(
            "Provider 调用成功: provider=%s, model=%s, tokens=%d, cost=%.6f, latency=%dms",
            result.provider,
            result.model,
            result.usage.total_tokens,
            result.estimated_cost,
            result.latency_ms,
        )

        return result

    async def call_by_route(
        self,
        request: ProviderCallRequest,
        capability: str = "text",
        tier: str = "cheap",
    ) -> ProviderResult:
        """Execute a call using capability/tier routing.

        Business modules should prefer this method. It resolves
        capability + tier + feature to provider/model, then delegates to call().
        """
        try:
            from registry import resolve_route
        except ModuleNotFoundError:
            import os
            import sys

            # 清理可能冲突的模块缓存（如 config 可能已被其他模块导入）
            # 确保重新导入时从本模块目录加载，而非从 sys.modules 缓存中获取
            # 注意：不能删除 "router" — 调用本模块的上层模块可能已导入自己的 router
            _conflict_names = {
                "models", "mock", "base", "errors", "cost",
                "registry", "config", "deepseek", "doubao", "http_utils",
            }
            for _key in list(sys.modules.keys()):
                if _key in _conflict_names or any(
                    _key.startswith(_cn + ".") for _cn in _conflict_names
                ):
                    del sys.modules[_key]

            module_dir = os.path.dirname(__file__)
            if module_dir not in sys.path:
                sys.path.insert(0, module_dir)
            from registry import resolve_route

        route = resolve_route(
            capability=capability,
            tier=tier,
            feature=request.feature,
        )
        routed_request = request.model_copy(
            update={
                "model": route.model,
                "capability": capability,
                "tier": tier,
            }
        )
        provider = self._providers.get(route.provider)
        if provider is None:
            raise ProviderError(
                code="PROVIDER_NOT_REGISTERED",
                message=(
                    f"Capability '{capability}' tier '{tier}' routes to provider "
                    f"'{route.provider}', but it is not registered"
                ),
                status_code=500,
            )
        return await self.call(request=routed_request, provider=provider)


# ============================================================
# 便捷函数
# ============================================================


async def call_provider(
    request: ProviderCallRequest,
    provider: BaseProvider,
) -> ProviderResult:
    """直接用指定 Provider 实例执行调用并计算成本（便捷函数）。

    适用于测试场景或上层模块已确定 Provider 的场景。

    Args:
        request: Provider 调用请求
        provider: Provider 实例

    Returns:
        统一的 ProviderResult 结构
    """
    router = ProviderRouter()
    return await router.call(request=request, provider=provider)


async def get_provider_for_model(
    model: str,
    router: ProviderRouter,
) -> Optional[BaseProvider]:
    """根据模型名称获取已注册的 Provider 实例。

    Args:
        model: 模型名称
        router: ProviderRouter 实例

    Returns:
        Provider 实例，未注册时返回 None
    """
    provider_name = get_provider_name_for_model(model)
    return router.get_provider(provider_name)


# ============================================================
# 内部辅助
# ============================================================


def _exception_to_result(
    exc: Exception,
    provider_name: str,
    model: str,
) -> ProviderResult:
    """将 Provider 调用异常转换为失败的 ProviderResult。

    Args:
        exc: 原始异常
        provider_name: Provider 标识名
        model: 模型名称

    Returns:
        状态为 "failed" 的 ProviderResult
    """
    mapped = map_provider_error(exc)
    return ProviderResult(
        provider=provider_name,
        model=model,
        status="failed",
        usage=ProviderUsage(),
        error_code=mapped.code,
        error_message=mapped.message,
    )
