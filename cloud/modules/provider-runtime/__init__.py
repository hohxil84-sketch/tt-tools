"""
cloud-provider-runtime —— Provider 公共调用层。

负责模型路由、调用、usage 解析、成本估算、错误标准化、mock provider。

本模块是 library，不直接暴露 FastAPI 路由端点。上层业务模块通过本模块
调用 AI Provider，本模块统一返回 ProviderResult 结构。

注意：目录名含连字符，Python 无法直接 import cloud.modules.provider-runtime。
使用时需将模块目录加入 sys.path 后直接导入：
    import sys
    sys.path.insert(0, "<project_root>/cloud/modules/provider-runtime")
    from router import ProviderRouter
    from mock import MockProvider

使用示例：
    provider = MockProvider()
    router = ProviderRouter()
    router.register("deepseek", provider)
    result = await router.call(request)
"""
from __future__ import annotations

# 注意：本模块目录名含连字符，内部使用直接导入（非相对导入），
# 与 auth-device 模块保持一致。
# 当模块目录在 sys.path 中时，以下导入正常工作。

# -- 核心数据模型 --
from models import (
    ProviderCallRequest,
    ProviderResult,
    ProviderUsage,
    ChatMessage,
)

# -- 基础接口 --
from base import BaseProvider

# -- Mock Provider --
from mock import MockProvider

# -- 路由 --
from router import ProviderRouter, get_provider_for_model, call_provider

# -- 成本估算 --
from cost import CostEstimator, estimate_cost

# -- 错误标准化 --
from errors import (
    ProviderError,
    map_provider_error,
    is_retryable_error,
)

__all__ = [
    # 核心数据模型
    "ProviderCallRequest",
    "ProviderResult",
    "ProviderUsage",
    "ChatMessage",
    # 基础接口
    "BaseProvider",
    # Mock Provider
    "MockProvider",
    # 路由
    "ProviderRouter",
    "get_provider_for_model",
    "call_provider",
    # 成本估算
    "CostEstimator",
    "estimate_cost",
    # 错误标准化
    "ProviderError",
    "map_provider_error",
    "is_retryable_error",
]
