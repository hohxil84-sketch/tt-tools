"""
成本估算模块测试。

验证 CostEstimator 和 estimate_cost 便捷函数的成本计算逻辑。
"""
from __future__ import annotations

import sys
import os

# 将项目根目录和模块目录加入 sys.path（目录名含连字符）
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
_MODULE_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "provider-runtime")
if _MODULE_DIR not in sys.path:
    sys.path.insert(0, _MODULE_DIR)

import pytest

from models import ProviderUsage
from cost import CostEstimator, estimate_cost


class TestCostEstimator:
    """CostEstimator 核心逻辑测试。"""

    def test_estimate_deepseek_chat(self) -> None:
        """DeepSeek Chat 成本估算。"""
        estimator = CostEstimator()
        usage = ProviderUsage(
            input_tokens=1_000_000,  # 100 万输入 token
            output_tokens=500_000,    # 50 万输出 token
        )
        # deepseek-chat: 输入 ¥1/M, 输出 ¥2/M
        # 1 * 1 + 0.5 * 2 = 2.0
        cost = estimator.estimate("deepseek-chat", usage)
        assert cost == pytest.approx(2.0)

    def test_estimate_deepseek_reasoner(self) -> None:
        """DeepSeek Reasoner 成本估算（含推理 token）。"""
        estimator = CostEstimator()
        usage = ProviderUsage(
            input_tokens=200_000,
            output_tokens=50_000,
        )
        # deepseek-reasoner: 输入 ¥4/M, 输出 ¥16/M
        # 0.2 * 4 + 0.05 * 16 = 0.8 + 0.8 = 1.6
        cost = estimator.estimate("deepseek-reasoner", usage)
        assert cost == pytest.approx(1.6)

    def test_estimate_gpt4o(self) -> None:
        """GPT-4o 成本估算。"""
        estimator = CostEstimator()
        usage = ProviderUsage(
            input_tokens=100_000,
            output_tokens=50_000,
        )
        # gpt-4o: 输入 ¥18.31/M, 输出 ¥73.24/M
        # 0.1 * 18.31 + 0.05 * 73.24 = 1.831 + 3.662 = 5.493
        cost = estimator.estimate("gpt-4o", usage)
        assert cost == pytest.approx(5.493)

    def test_estimate_gpt4o_mini(self) -> None:
        """GPT-4o-mini 成本估算（最便宜的 OpenAI 模型）。"""
        estimator = CostEstimator()
        usage = ProviderUsage(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        # gpt-4o-mini: 输入 ¥1.10/M, 输出 ¥4.39/M
        # 1 * 1.10 + 1 * 4.39 = 5.49
        cost = estimator.estimate("gpt-4o-mini", usage)
        assert cost == pytest.approx(5.49)

    def test_estimate_zero_usage(self) -> None:
        """0 token 时应返回 0 成本。"""
        estimator = CostEstimator()
        usage = ProviderUsage()
        cost = estimator.estimate("deepseek-chat", usage)
        assert cost == 0.0

    def test_estimate_unknown_model_uses_default(self) -> None:
        """未知模型使用默认定价。"""
        estimator = CostEstimator()
        usage = ProviderUsage(
            input_tokens=1_000_000,
            output_tokens=500_000,
        )
        # 默认定价: 输入 ¥1/M, 输出 ¥2/M
        # 1 * 1 + 0.5 * 2 = 2.0
        cost = estimator.estimate("unknown-model-xyz", usage)
        assert cost == pytest.approx(2.0)

    def test_estimate_precision(self) -> None:
        """成本应保留 6 位小数精度。"""
        estimator = CostEstimator()
        usage = ProviderUsage(input_tokens=1, output_tokens=1)
        cost = estimator.estimate("deepseek-chat", usage)
        assert isinstance(cost, float)
        # 验证 round 到 6 位小数
        assert cost == round(cost, 6)

    def test_get_pricing_known_model(self) -> None:
        """获取已知模型的定价信息。"""
        estimator = CostEstimator()
        pricing = estimator.get_pricing("deepseek-chat")
        assert "input_price_per_million" in pricing
        assert "output_price_per_million" in pricing
        assert pricing["input_price_per_million"] == 1.0
        assert pricing["output_price_per_million"] == 2.0

    def test_get_pricing_unknown_model_returns_default(self) -> None:
        """获取未知模型的定价应返回默认值。"""
        estimator = CostEstimator()
        pricing = estimator.get_pricing("unknown-model")
        assert "input_price_per_million" in pricing
        assert pricing["input_price_per_million"] == 1.0


class TestEstimateCostFunction:
    """estimate_cost 便捷函数测试。"""

    def test_convenience_function(self) -> None:
        """便捷函数应与 CostEstimator.estimate() 结果一致。"""
        usage = ProviderUsage(input_tokens=200_000, output_tokens=100_000)
        cost = estimate_cost(
            provider="deepseek",
            model="deepseek-chat",
            usage=usage,
        )
        # 0.2 * 1 + 0.1 * 2 = 0.4
        assert cost == pytest.approx(0.4)

    def test_convenience_function_default_model(self) -> None:
        """未注册模型使用默认定价。"""
        usage = ProviderUsage(input_tokens=500_000, output_tokens=500_000)
        cost = estimate_cost(
            provider="unknown",
            model="unknown-model",
            usage=usage,
        )
        # 0.5 * 1 + 0.5 * 2 = 1.5
        assert cost == pytest.approx(1.5)

    def test_claude_opus_pricing(self) -> None:
        """Claude Opus 昂贵模型定价。"""
        estimator = CostEstimator()
        usage = ProviderUsage(input_tokens=200_000, output_tokens=50_000)
        # claude-3-opus: 输入 ¥109.86/M, 输出 ¥549.30/M
        # 0.2 * 109.86 + 0.05 * 549.30 = 21.972 + 27.465 = 49.437
        cost = estimator.estimate("claude-3-opus", usage)
        assert cost == pytest.approx(49.437)

    def test_claude_haiku_pricing(self) -> None:
        """Claude Haiku 便宜模型定价。"""
        estimator = CostEstimator()
        usage = ProviderUsage(input_tokens=1_000_000, output_tokens=500_000)
        # claude-3-haiku: 输入 ¥1.83/M, 输出 ¥9.15/M
        # 1 * 1.83 + 0.5 * 9.15 = 1.83 + 4.575 = 6.405
        cost = estimator.estimate("claude-3-haiku", usage)
        assert cost == pytest.approx(6.405)
