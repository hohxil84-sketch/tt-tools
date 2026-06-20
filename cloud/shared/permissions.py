"""
cloud-shared 权限/套餐权限检查模块（骨架）。

提供功能码权限检查的基本结构。真实套餐配置查询、额度检查等逻辑
留给 cloud/modules/credits-billing 模块实现。

功能码全集来自 shared-contract/feature-codes.md。
"""
from __future__ import annotations

from typing import Optional


async def check_entitlement(
    plan_code: str,
    feature_code: str,
) -> bool:
    """检查给定套餐是否有权限使用指定功能码（骨架实现）。

    当前骨架：所有套餐默认可使用本地免费功能；付费功能的精细
    权限判断由 cloud/modules/credits-billing 实现。

    Args:
        plan_code: 用户当前套餐编码（如 free / standard / pro）
        feature_code: 功能码（如 resize_image_local_paid）

    Returns:
        True 表示允许使用，False 表示不允许
    """
    # 骨架实现：所有本地功能默认允许。
    # 付费功能权限在 credits-billing 模块中细化。
    _ = plan_code  # 预留参数位，待 credits-billing 模块实现
    _ = feature_code
    return True


async def check_credits_enough(
    balance: int,
    required_credits: int,
) -> bool:
    """检查额度是否足够（骨架实现）。

    真实额度检查和扣费由 cloud/modules/credits-billing 实现。

    Args:
        balance: 当前用户 AI 额度余额
        required_credits: 本次操作需要的额度

    Returns:
        True 表示额度足够，False 表示不足
    """
    _ = balance
    _ = required_credits
    return True
