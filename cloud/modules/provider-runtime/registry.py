"""
Provider 注册和路由解析。

所有 Provider 从数据库加载，不再硬编码。
路由逻辑：按 capability 匹配 → 按 priority 降序 → 失败自动降级。
"""
from __future__ import annotations

import os
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging

from deepseek import DeepSeekProvider
from doubao import DoubaoProvider
from openai_compatible import OpenAICompatibleProvider
from errors import ProviderError, ProviderErrorCode

_logger = logging.getLogger(__name__)

# ============================================================
# 能力常量
# ============================================================

TEXT = "text"
IMAGE_GENERATION = "image_generation"
IMAGE_EDIT = "image_edit"

CHEAP = "cheap"
BALANCED = "balanced"
PREMIUM = "premium"

# ============================================================
# 路由目标
# ============================================================


@dataclass(frozen=True)
class RouteTarget:
    provider: str
    model: str


# ============================================================
# Provider 实例工厂
# ============================================================

# 已知 Provider 类型 → 类映射。
# 未列出的类型自动回退到 OpenAICompatibleProvider（完全由 DB 驱动）。
_PROVIDER_CLASSES: dict[str, type] = {
    "deepseek": DeepSeekProvider,          # 向后兼容（有默认 base_url）
    "doubao": DoubaoProvider,              # 特殊：支持图片生成/编辑
    "openai_compatible": OpenAICompatibleProvider,  # 通用（纯 DB 驱动，无默认值）
}


def _decrypt_api_key(encrypted: str | None) -> str:
    """解密 API Key（当前为 base64 简单编码，可替换为 KMS）。"""
    if not encrypted:
        return ""
    import base64
    try:
        return base64.b64decode(encrypted.encode()).decode()
    except Exception:
        return encrypted  # 明文兼容


def _create_provider_instance(row: dict) -> Optional[object]:
    """根据 provider_type 创建 Provider 实例（DB 驱动，无硬编码默认值）。

    - doubao：特殊处理（支持图片生成/编辑）
    - deepseek：向后兼容（无 base_url 时回退到 api.deepseek.com）
    - 其他所有类型：OpenAICompatibleProvider，参数全部从 DB 读取

    Args:
        row: 数据库行字典，含 name, provider_type, api_key_encrypted, base_url, models_json

    Returns:
        Provider 实例，无法创建时返回 None
    """
    ptype = (row.get("provider_type") or "").lower()
    cls = _PROVIDER_CLASSES.get(ptype)

    api_key = _decrypt_api_key(row.get("api_key_encrypted"))
    base_url = row.get("base_url") or ""
    models = row.get("models_json") or {}  # 来自 provider_model_pricing 聚合
    name = row.get("name") or ""

    # -- Doubao：特殊处理（图片生成/编辑接口不走 chat/completions） --
    if ptype == "doubao":
        if cls is None:
            cls = DoubaoProvider
        return cls(
            api_key=api_key,
            base_url=base_url,
            text_model=models.get("text", ""),
            image_model=models.get("image", ""),
            timeout_seconds=60,
        )

    # -- 其他所有类型 → OpenAI 兼容类 --
    if cls is None:
        # 未注册的类型（如 openai、gemini、groq 等）
        # 自动使用 OpenAICompatibleProvider，完全由 DB 驱动
        cls = OpenAICompatibleProvider

    # DeepSeek 向后兼容：数据库没配 base_url 时用默认值
    if ptype == "deepseek" and not base_url:
        base_url = "https://api.deepseek.com"

    # 没有 base_url 的 OpenAI 兼容 Provider 无法工作
    if not base_url:
        _logger.warning("Provider %s 未配置 base_url，跳过", name)
        return None

    return cls(
        api_key=api_key,
        base_url=base_url,
        default_model=models.get("text", ""),
        timeout_seconds=60,
        provider_name=name,
    )


# ============================================================
# DB 加载：从 providers 表加载所有已启用的 Provider
# ============================================================


async def load_providers_from_db(db_session, router) -> int:
    """从数据库加载所有已启用 Provider 到 Router。

    Args:
        db_session: 异步数据库会话
        router: ProviderRouter 实例

    Returns:
        成功加载的 Provider 数量
    """
    from sqlalchemy import text

    result = await db_session.execute(
        text(
            "SELECT p.name, p.provider_type, p.api_key_encrypted, p.base_url, "
            "p.priority, pmp.model_name, ac.code "
            "FROM providers p "
            "INNER JOIN provider_model_pricing pmp ON pmp.provider_id = p.id "
            "INNER JOIN provider_model_capability pmc ON pmc.provider_model_id = pmp.id "
            "INNER JOIN ai_capability ac ON ac.id = pmc.capability_id "
            "WHERE p.is_enabled = true AND pmp.is_active = true AND ac.is_active = true "
            "ORDER BY p.priority DESC, p.name ASC"
        )
    )
    rows = result.all()
    if not rows:
        _logger.warning("数据库中没有已启用的 Provider（需在 provider_model_pricing 中配置模型并绑定能力），AI 功能将不可用")

    router.clear()
    loaded = 0
    # 按 provider name 分组组装 models_json：{capability: model_name}
    prov_data: dict[str, dict] = {}
    for row in rows:
        pname = row[0]
        if pname not in prov_data:
            prov_data[pname] = {
                "name": pname,
                "provider_type": row[1],
                "api_key_encrypted": row[2],
                "base_url": row[3],
                "priority": row[4],
                "models_json": {},
            }
        # ac.code → model_name（同一 capability 多条时先到先得）
        cap_code = row[6] or "text"
        if cap_code not in prov_data[pname]["models_json"]:
            prov_data[pname]["models_json"][cap_code] = row[5]

    for pname, row_dict in prov_data.items():
        instance = _create_provider_instance(row_dict)
        if instance is None:
            continue
        router.register(
            name=row_dict["name"],
            provider=instance,
            models_json=row_dict["models_json"],
            priority=row_dict["priority"],
        )
        loaded += 1
        _logger.info("Provider %s: models=%s", pname, row_dict["models_json"])

    _logger.info("从数据库加载了 %d 个 Provider（模型配置来自 provider_model_pricing）", loaded)
    return loaded


# ============================================================
# 默认路由创建（全局单例）
# ============================================================


_global_router = None


def get_global_router():
    """获取全局 Router 单例。"""
    global _global_router
    if _global_router is None:
        _global_router = _load_provider_router_class()()
    return _global_router


def create_default_router(router_cls=None):
    """创建 Router 并返回（兼容旧接口，不再硬编码任何 Provider）。

    调用方需要在创建后调用 router.load_from_db(db_session) 加载 Provider。
    """
    if router_cls is None:
        router_cls = _load_provider_router_class()
    return router_cls()


def _load_provider_router_class():
    router_path = Path(__file__).with_name("router.py")
    spec = importlib.util.spec_from_file_location(
        "_provider_runtime_router", router_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load provider-runtime router.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ProviderRouter


# ============================================================
# 兼容旧接口的 resolve_route（DB 驱动）
# ============================================================


def resolve_route(
    capability: str = TEXT,
    tier: str = CHEAP,
    feature: str = "",
    router=None,
) -> RouteTarget:
    """解析 capability → Provider + Model（纯 DB 驱动，无兜底）。

    Args:
        capability: 能力类型（text / image_generation / image_edit）
        router: ProviderRouter 实例

    Returns:
        RouteTarget(provider_name, model_name)

    Raises:
        ProviderError: 没有可用的 Provider
    """
    if router is not None:
        candidates = router.get_providers_for_capability(capability)
        if candidates:
            provider_name, model = candidates[0]
            return RouteTarget(provider=provider_name, model=model)

    raise ProviderError(
        code=ProviderErrorCode.PROVIDER_NOT_REGISTERED,
        message=f"没有可用的 Provider 处理 capability '{capability}'，请在后台添加并启用 Provider",
        status_code=500,
    )
