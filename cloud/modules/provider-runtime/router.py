"""
Provider 路由器。

从数据库加载 Provider 配置，按 capability + priority 路由，
主 Provider 失败时自动降级到下一个。
"""
from __future__ import annotations

import logging
from typing import Optional

from base import BaseProvider
from cost import estimate_cost
from errors import ProviderError, map_provider_error
from models import ProviderCallRequest, ProviderResult, ProviderUsage

_logger = logging.getLogger(__name__)


class ProviderRouter:
    """Provider 路由器（DB 驱动）。

    所有 Provider 从数据库加载，不再硬编码。
    路由：capability 匹配 → priority 降序 → 失败自动降级。

    使用示例：
        router = ProviderRouter()
        await router.load_from_db(db_session)
        result = await router.call_by_capability(request, capability="text")
    """

    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}
        # 元数据：name → {"models_json": {...}, "priority": 0}
        self._meta: dict[str, dict] = {}

    # ============================================================
    # 注册 / 清理
    # ============================================================

    def clear(self) -> None:
        """清空所有已注册 Provider。"""
        self._providers.clear()
        self._meta.clear()

    def register(
        self, name: str, provider: BaseProvider,
        models_json: dict | None = None,
        priority: int = 0,
    ) -> None:
        """注册 Provider 及其元数据。

        Args:
            name: Provider 名称
            provider: Provider 实例
            models_json: 模型配置（如 {"text": "deepseek-chat", "image": "dall-e-3"}）
            priority: 优先级，数字越大越优先
        """
        self._providers[name] = provider
        self._meta[name] = {"models_json": models_json or {}, "priority": priority}
        caps = list((models_json or {}).keys())
        _logger.info("Provider 已注册: %s (priority=%d, caps=%s)", name, priority, caps)

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    # ============================================================
    # Capability 路由
    # ============================================================

    def get_providers_for_capability(
        self, capability: str
    ) -> list[tuple[str, str]]:
        """获取支持某 capability 的 Provider 列表，按 priority 降序。

        Args:
            capability: 如 "text"、"image_generation"、"image_edit"

        Returns:
            [(provider_name, model_name), ...] 按 priority DESC 排序
        """
        candidates = []
        for name, meta in self._meta.items():
            models = meta.get("models_json") or {}
            if capability in models:
                candidates.append((name, models[capability], meta.get("priority", 0)))
        candidates.sort(key=lambda x: x[2], reverse=True)
        return [(n, m) for n, m, _ in candidates]

    # ============================================================
    # DB 加载
    # ============================================================

    async def load_from_db(self, db_session) -> int:
        """从数据库加载所有已启用 Provider 并注册到 Router。

        Args:
            db_session: 异步数据库会话（由调用方提供）

        Returns:
            成功加载的 Provider 数量
        """
        from registry import load_providers_from_db
        return await load_providers_from_db(db_session, self)

    # ============================================================
    # 调用
    # ============================================================

    async def call(
        self,
        request: ProviderCallRequest,
        provider: Optional[BaseProvider] = None,
    ) -> ProviderResult:
        """执行 Provider 调用。

        优先使用 provider 参数；否则按 request.model 查找注册表。

        Args:
            request: Provider 调用请求
            provider: 可选，直接指定 Provider 实例

        Returns:
            ProviderResult
        """
        if provider is None:
            # 按 model 名查找
            provider = self._find_by_name(request.model)
            if provider is None:
                # 查找第一个可用的 Provider 作为兜底
                for p in self._providers.values():
                    provider = p
                    break
            if provider is None:
                raise ProviderError(
                    code="PROVIDER_NOT_REGISTERED",
                    message="没有可用的 AI Provider，请在后台添加并启用",
                    status_code=500,
                )

        try:
            result = await provider.call(request)
        except Exception as exc:
            _logger.warning("Provider 调用异常: %s, error=%s", provider.provider_name, str(exc))
            result = _exception_to_result(exc=exc, provider_name=provider.provider_name, model=request.model)
            return result

        result.estimated_cost = estimate_cost(
            provider=result.provider, model=result.model, usage=result.usage,
        )
        _logger.debug("Provider 调用成功: %s, model=%s, tokens=%d", result.provider, result.model, result.usage.total_tokens)
        return result

    async def call_by_capability(
        self,
        request: ProviderCallRequest,
        capability: str = "text",
    ) -> ProviderResult:
        """按 capability + priority 路由调用，失败自动降级。

        选择最高优先级 Provider 调用；若失败则尝试下一个，
        直到成功或无可用 Provider。

        Args:
            request: Provider 调用请求
            capability: 能力类型（text / image_generation / image_edit）

        Returns:
            ProviderResult（状态为 failed 表示全部降级失败）
        """
        candidates = self.get_providers_for_capability(capability)

        if not candidates:
            return ProviderResult(
                provider="",
                model=request.model or "",
                status="failed",
                usage=ProviderUsage(),
                error_code="NO_PROVIDER",
                error_message=f"没有可用的 Provider 处理 capability '{capability}'，请在后台添加并启用",
            )

        last_result = None
        for provider_name, model in candidates:
            provider = self._providers.get(provider_name)
            if provider is None:
                continue

            _logger.info("尝试 Provider: %s (model=%s, capability=%s)", provider_name, model, capability)
            routed_request = request.model_copy(
                update={"model": model, "capability": capability}
            )
            result = await self.call(request=routed_request, provider=provider)

            if result.status == "success":
                return result

            _logger.warning("Provider %s 调用失败，尝试降级: %s", provider_name, result.error_message)
            last_result = result

        # 所有 Provider 都失败了
        if last_result:
            last_result.error_message = f"所有 Provider 均调用失败（capability={capability}）: " + (last_result.error_message or "")
            return last_result

        return ProviderResult(
            provider="",
            model="",
            status="failed",
            usage=ProviderUsage(),
            error_code="ALL_PROVIDERS_FAILED",
            error_message=f"所有 Provider 均调用失败（capability={capability}）",
        )

    # 兼容旧接口
    async def call_by_route(
        self,
        request: ProviderCallRequest,
        capability: str = "text",
        tier: str = "cheap",
    ) -> ProviderResult:
        """旧接口兼容，直接委托到 call_by_capability。"""
        return await self.call_by_capability(request=request, capability=capability)

    def _find_by_name(self, model: str) -> Optional[BaseProvider]:
        """按模型名匹配 Provider（用于 call() 的兜底查找）。"""
        # 先精确匹配 provider name
        if model in self._providers:
            return self._providers[model]
        # 再按 models_json 中的 model 名匹配
        for name, meta in self._meta.items():
            models = meta.get("models_json") or {}
            if model in models.values():
                return self._providers.get(name)
        return None


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
    """根据模型名称获取已注册的 Provider 实例。"""
    return router._find_by_name(model)


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
