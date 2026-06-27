"""
cloud-shared 权限检查模块测试。

验证：check_entitlement 骨架、check_credits_enough 骨架。
"""
from __future__ import annotations

import pytest

from cloud.shared.permissions import check_entitlement, check_credits_enough


class TestCheckEntitlement:
    """套餐权限检查测试（骨架阶段）。"""

    @pytest.mark.asyncio
    async def test_always_returns_true_in_skeleton(self) -> None:
        """骨架阶段所有套餐都应返回 True。"""
        result = await check_entitlement(
            plan_id="plan-free",
            feature_code="resize_image_local_paid",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_any_plan_returns_true(self) -> None:
        """任意套餐都应返回 True。"""
        for plan in ["free", "standard", "pro"]:
            result = await check_entitlement(
                plan_id=f"plan-{plan}",
                feature_code="ai_copy_cloud",
            )
            assert result is True, f"plan={plan} 应返回 True"

    @pytest.mark.asyncio
    async def test_any_feature_returns_true(self) -> None:
        """任意功能码都应返回 True。"""
        for feature in [
            "ocr_local",
            "remove_bg_local",
            "resize_image_local_paid",
            "ai_copy_cloud",
        ]:
            result = await check_entitlement(
                plan_id="plan-free",
                feature_code=feature,
            )
            assert result is True, f"feature={feature} 应返回 True"


class TestCheckCreditsEnough:
    """额度检查测试（骨架阶段）。"""

    @pytest.mark.asyncio
    async def test_always_returns_true_in_skeleton(self) -> None:
        """骨架阶段所有额度检查都应返回 True。"""
        result = await check_credits_enough(
            balance=0,
            required_credits=999,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_zero_balance_returns_true(self) -> None:
        """余额为 0 也返回 True（骨架）。"""
        result = await check_credits_enough(balance=0, required_credits=1)
        assert result is True
