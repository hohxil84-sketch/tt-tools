"""
Provider 成本估算模块。

根据 Provider 返回的 usage（token 数、图片数）和模型定价表，
计算单次调用的估算成本（人民币）。

定价来源：各 Provider 官方定价页。不是最终扣费依据；
最终扣费由 credits-billing 模块根据套餐规则计算。
"""
from __future__ import annotations

from models import ProviderUsage


# ============================================================
# 模型定价表（人民币 / 百万 token）
# ============================================================
# 定价为输入价格和输出价格，单位：元 / 百万 token
# 数据来源：各 Provider 官方定价页（截至 2025 年中）
# 注意：实际扣费不以本表为准，仅用于估算

_MODEL_PRICING: dict[str, dict[str, float]] = {
    # -- DeepSeek --
    "deepseek-chat": {
        "input_price_per_million": 1.0,     # ¥1 / 百万输入 token
        "output_price_per_million": 2.0,    # ¥2 / 百万输出 token
        "currency": "CNY",
    },
    "deepseek-reasoner": {
        "input_price_per_million": 4.0,     # ¥4 / 百万输入 token
        "output_price_per_million": 16.0,   # ¥16 / 百万输出 token（含推理）
        "currency": "CNY",
    },
    # -- OpenAI --
    "gpt-4o": {
        "input_price_per_million": 18.31,   # $2.50 → 约 ¥18.31
        "output_price_per_million": 73.24,  # $10.00 → 约 ¥73.24
        "currency": "CNY",
    },
    "gpt-4o-mini": {
        "input_price_per_million": 1.10,    # $0.15 → 约 ¥1.10
        "output_price_per_million": 4.39,   # $0.60 → 约 ¥4.39
        "currency": "CNY",
    },
    "gpt-4-turbo": {
        "input_price_per_million": 73.24,   # $10.00 → 约 ¥73.24
        "output_price_per_million": 219.72, # $30.00 → 约 ¥219.72
        "currency": "CNY",
    },
    # -- Anthropic --
    "claude-3-opus": {
        "input_price_per_million": 109.86,  # $15.00 → 约 ¥109.86
        "output_price_per_million": 549.30, # $75.00 → 约 ¥549.30
        "currency": "CNY",
    },
    "claude-3-sonnet": {
        "input_price_per_million": 21.97,   # $3.00 → 约 ¥21.97
        "output_price_per_million": 109.86, # $15.00 → 约 ¥109.86
        "currency": "CNY",
    },
    "claude-3-haiku": {
        "input_price_per_million": 1.83,    # $0.25 → 约 ¥1.83
        "output_price_per_million": 9.15,   # $1.25 → 约 ¥9.15
        "currency": "CNY",
    },
}

# 默认定价（未知模型使用）
_DEFAULT_PRICING: dict[str, float] = {
    "input_price_per_million": 1.0,
    "output_price_per_million": 2.0,
}


class CostEstimator:
    """成本估算器。

    根据模型定价和 usage 计算单次调用的估算成本。

    使用示例：
        estimator = CostEstimator()
        cost = estimator.estimate("deepseek-chat", usage)
    """

    def estimate(self, model: str, usage: ProviderUsage) -> float:
        """估算单次调用的成本。

        Args:
            model: 模型名称
            usage: Provider 返回的统一用量

        Returns:
            估算成本（人民币），保留 6 位小数精度
        """
        pricing = _MODEL_PRICING.get(model, _DEFAULT_PRICING)

        input_cost = (
            usage.input_tokens / 1_000_000
        ) * pricing["input_price_per_million"]
        output_cost = (
            usage.output_tokens / 1_000_000
        ) * pricing["output_price_per_million"]

        total = input_cost + output_cost
        # 保留 6 位小数（对齐 provider_call_log.estimated_cost 的 decimal(18,6)）
        return round(total, 6)

    def get_pricing(self, model: str) -> dict[str, float]:
        """获取某个模型的定价信息。

        Args:
            model: 模型名称

        Returns:
            定价 dict，含 input_price_per_million、output_price_per_million
        """
        return _MODEL_PRICING.get(model, _DEFAULT_PRICING).copy()


# 全局估算器单例
_cost_estimator = CostEstimator()


def estimate_cost(
    provider: str,
    model: str,
    usage: ProviderUsage,
) -> float:
    """便捷函数：估算单次 Provider 调用的成本。

    Args:
        provider: Provider 名称（当前仅用于扩展预留，计算基于 model）
        model: 模型名称
        usage: 统一用量

    Returns:
        估算成本（人民币）
    """
    return _cost_estimator.estimate(model, usage)
