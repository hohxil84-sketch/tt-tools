"""
local-worker/modules/preflight-check — 印前检查本地实现

检查尺寸、DPI、文件类型、透明通道、低清风险等基础项。
纯本地执行，不依赖 GPU，不调用云端 API。

对外接口：
    PreflightChecker  — 检查器类
    PreflightReport   — 检查报告
    PreflightCheckResult — 单项检查结果
    CheckItem / RiskLevel — 枚举

用法：
    from modules.preflight_check import PreflightChecker

    checker = PreflightChecker()
    report = checker.check("D:\\images\\poster.png")

    if report.has_errors:
        for e in report.errors():
            print(f"[{e.item.value}] {e.message}")
"""

from checker import PreflightChecker
from report import (
    CheckItem,
    RiskLevel,
    PreflightCheckResult,
    PreflightReport,
    RECOMMENDED_MIN_WIDTH,
    RECOMMENDED_MIN_HEIGHT,
    RECOMMENDED_DPI,
    MIN_ACCEPTABLE_DPI,
    SUPPORTED_FORMATS,
)

__all__ = [
    # 核心类
    "PreflightChecker",
    "PreflightReport",
    "PreflightCheckResult",
    # 枚举
    "CheckItem",
    "RiskLevel",
    # 阈值常量
    "RECOMMENDED_MIN_WIDTH",
    "RECOMMENDED_MIN_HEIGHT",
    "RECOMMENDED_DPI",
    "MIN_ACCEPTABLE_DPI",
    "SUPPORTED_FORMATS",
]
