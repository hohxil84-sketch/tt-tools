"""
local-worker/modules/preflight-check/checker — 印前检查核心逻辑

基于 Pillow 读取图像元数据，执行尺寸、DPI、文件类型、
透明通道、低清风险、颜色模式等基础项检查。
不依赖 GPU，不涉及 AI 模型，纯本地规则判断。
"""

import os
from pathlib import Path
from typing import Optional

from PIL import Image

# 引用 local-worker/shared 公共层
# 注意：导入路径使用 shared.* 而非 local_worker.shared，
# 因为 local-worker/ 目录在运行时会加入 sys.path
from shared.errors import AppError, ErrorCode
from shared.logging import get_logger

from report import (
    CheckItem,
    RiskLevel,
    PreflightCheckResult,
    PreflightReport,
    RECOMMENDED_MIN_WIDTH,
    RECOMMENDED_MIN_HEIGHT,
    RECOMMENDED_DPI,
    MIN_ACCEPTABLE_DPI,
    PRINT_PREFERRED_MODES,
    SUPPORTED_FORMATS,
    MIN_FILE_SIZE_WARN_BYTES,
)

# 模块 logger
logger = get_logger(__name__)


class PreflightChecker:
    """印前检查器。

    对输入图像文件执行全套基础检查，生成 PreflightReport。
    纯本地执行，不调用云端 API，不需要套餐权限。

    用法：
        checker = PreflightChecker()
        report = checker.check("D:\\images\\poster.png")
        print(report.to_dict())
    """

    def __init__(self) -> None:
        """初始化检查器。无需模型，只依赖 Pillow。"""
        pass

    def check(self, file_path: str) -> PreflightReport:
        """对指定文件执行全部印前检查，返回综合报告。

        参数：
            file_path: 待检查的图像文件路径。
        返回：
            PreflightReport：包含所有检查结果的综合报告。
        异常：
            AppError：文件不存在、格式不支持或读取失败。
        """
        logger.info("开始印前检查 | file=%s", file_path)

        # ---- 第一步：文件基本信息校验 ----
        # 使用 shared/file_io 校验文件存在性和后缀
        abs_path = os.path.abspath(file_path)
        if not os.path.isfile(abs_path):
            raise AppError(
                ErrorCode.FILE_NOT_FOUND,
                f"印前检查文件不存在: {abs_path}",
                details={"path": abs_path},
            )

        suffix = Path(abs_path).suffix.lower()
        file_size = os.path.getsize(abs_path)

        # 创建初始报告
        report = PreflightReport(
            file_path=abs_path,
            file_name=Path(abs_path).name,
            file_format=suffix,
            file_size_bytes=file_size,
        )

        # ---- 第二步：文件格式检查 ----
        self._check_file_format(report)

        # 如果格式不支持，后续检查无意义
        if report.has_errors:
            self._build_overall_message(report)
            return report

        # ---- 第三步：打开图像并提取元数据 ----
        try:
            img = Image.open(abs_path)
            # 提取图像属性
            self._extract_image_properties(report, img)
        except Exception as e:
            raise AppError(
                ErrorCode.FILE_READ_ERROR,
                f"无法打开图像文件: {e}",
                details={"path": abs_path, "error": str(e)},
            )

        # ---- 第四步：各项检查 ----
        self._check_dimensions(report)
        self._check_dpi(report)
        self._check_color_mode(report)
        self._check_transparency(report)
        self._check_low_resolution(report)
        self._check_file_size(report)

        # ---- 第五步：生成综合建议 ----
        self._build_overall_message(report)

        logger.info(
            "印前检查完成 | file=%s | overall=%s | errors=%d | warnings=%d",
            report.file_name,
            report.overall_risk.value,
            len(report.errors()),
            len(report.warnings()),
        )

        return report

    # ---- 图像属性提取 ----

    def _extract_image_properties(self, report: PreflightReport, img: Image.Image) -> None:
        """从 PIL Image 对象提取图像属性。"""
        # 尺寸
        report.width = img.width
        report.height = img.height

        # DPI — PIL 的 info 字典中可能存储 "dpi" 键
        dpi_info = img.info.get("dpi")
        if dpi_info is not None and isinstance(dpi_info, (tuple, list)) and len(dpi_info) >= 2:
            report.dpi_h = float(dpi_info[0]) if dpi_info[0] else None
            report.dpi_v = float(dpi_info[1]) if dpi_info[1] else None
            # 以水平 DPI 为主
            report.dpi = report.dpi_h
        else:
            report.dpi_h = None
            report.dpi_v = None
            report.dpi = None

        # 颜色模式
        report.color_mode = img.mode

        # 透明通道：RGBA、PA、LA 等模式含 Alpha 通道
        # 或者 info 中标记了 transparency
        has_alpha_modes = {"RGBA", "PA", "LA", "RGBa", "I;16B"}
        report.has_transparency = (
            img.mode in has_alpha_modes
            or "transparency" in img.info
        )

    # ---- 各项检查 ----

    def _check_file_format(self, report: PreflightReport) -> None:
        """检查文件格式是否在印刷支持列表中。"""
        suffix = report.file_format
        if suffix not in SUPPORTED_FORMATS:
            result = PreflightCheckResult(
                item=CheckItem.FILE_FORMAT,
                risk_level=RiskLevel.ERROR,
                message=f"不支持的文件格式: {suffix}",
                details={
                    "current_format": suffix,
                    "supported_formats": sorted(SUPPORTED_FORMATS),
                },
            )
        else:
            result = PreflightCheckResult(
                item=CheckItem.FILE_FORMAT,
                risk_level=RiskLevel.PASS,
                message=f"文件格式 {suffix} 受支持",
                details={"format": suffix},
            )
        report.add_check(result)

    def _check_dimensions(self, report: PreflightReport) -> None:
        """检查图像尺寸是否满足印刷最低要求。"""
        if report.width is None or report.height is None:
            return

        width_ok = report.width >= RECOMMENDED_MIN_WIDTH
        height_ok = report.height >= RECOMMENDED_MIN_HEIGHT

        if not width_ok or not height_ok:
            issues = []
            if not width_ok:
                issues.append(f"宽度={report.width}px（建议≥{RECOMMENDED_MIN_WIDTH}px）")
            if not height_ok:
                issues.append(f"高度={report.height}px（建议≥{RECOMMENDED_MIN_HEIGHT}px）")

            result = PreflightCheckResult(
                item=CheckItem.DIMENSIONS,
                risk_level=RiskLevel.WARNING,
                message=f"图像尺寸偏小: {'; '.join(issues)}",
                details={
                    "current_width": report.width,
                    "current_height": report.height,
                    "recommended_min_width": RECOMMENDED_MIN_WIDTH,
                    "recommended_min_height": RECOMMENDED_MIN_HEIGHT,
                },
            )
        else:
            result = PreflightCheckResult(
                item=CheckItem.DIMENSIONS,
                risk_level=RiskLevel.PASS,
                message=f"图像尺寸 {report.width}×{report.height} 满足最低要求",
                details={
                    "width": report.width,
                    "height": report.height,
                },
            )
        report.add_check(result)

    def _check_dpi(self, report: PreflightReport) -> None:
        """检查 DPI 是否满足印刷要求。

        印刷行业标准为 300 DPI，低于 150 DPI 为严重不达标。
        如果图像无 DPI 信息（如 PNG 文件），给出提示。
        """
        if report.dpi is None:
            result = PreflightCheckResult(
                item=CheckItem.DPI,
                risk_level=RiskLevel.WARNING,
                message="图像未包含 DPI 信息，印刷时可能影响输出尺寸准确性",
                details={
                    "note": "PNG 等格式不强制存储 DPI，请在排版软件中确认输出尺寸",
                },
            )
        elif report.dpi < MIN_ACCEPTABLE_DPI:
            result = PreflightCheckResult(
                item=CheckItem.DPI,
                risk_level=RiskLevel.ERROR,
                message=f"DPI 严重不足: {report.dpi:.0f}（最低要求 {MIN_ACCEPTABLE_DPI}）",
                details={
                    "current_dpi": report.dpi,
                    "min_acceptable_dpi": MIN_ACCEPTABLE_DPI,
                    "recommended_dpi": RECOMMENDED_DPI,
                    "suggestion": "建议使用更高分辨率原图，或缩小输出尺寸",
                },
            )
        elif report.dpi < RECOMMENDED_DPI:
            result = PreflightCheckResult(
                item=CheckItem.DPI,
                risk_level=RiskLevel.WARNING,
                message=f"DPI 低于推荐值: {report.dpi:.0f}（推荐 {RECOMMENDED_DPI}）",
                details={
                    "current_dpi": report.dpi,
                    "recommended_dpi": RECOMMENDED_DPI,
                    "suggestion": "小尺寸印刷（名片等）可接受，大尺寸建议更高分辨率",
                },
            )
        else:
            result = PreflightCheckResult(
                item=CheckItem.DPI,
                risk_level=RiskLevel.PASS,
                message=f"DPI {report.dpi:.0f} 满足印刷要求",
                details={"dpi": report.dpi},
            )
        report.add_check(result)

    def _check_color_mode(self, report: PreflightReport) -> None:
        """检查颜色模式并给出印刷建议。

        CMYK 为印刷最佳，RGB 可用但可能有色差，灰度/调色板需注意。
        """
        mode = report.color_mode or ""
        mode_upper = mode.upper()

        # CMYK 最佳
        if "CMYK" in mode_upper:
            result = PreflightCheckResult(
                item=CheckItem.COLOR_MODE,
                risk_level=RiskLevel.PASS,
                message=f"颜色模式 {mode} 为印刷标准模式",
                details={"color_mode": mode},
            )
        # RGB 可用但需注意色差
        elif "RGB" in mode_upper:
            result = PreflightCheckResult(
                item=CheckItem.COLOR_MODE,
                risk_level=RiskLevel.WARNING,
                message=f"颜色模式为 RGB（{mode}），印刷时可能存在色差，建议转换为 CMYK",
                details={
                    "color_mode": mode,
                    "suggestion": "印刷前在排版软件或印前工具中转换为 CMYK",
                },
            )
        # 灰度
        elif mode_upper in ("L", "LA"):
            result = PreflightCheckResult(
                item=CheckItem.COLOR_MODE,
                risk_level=RiskLevel.WARNING,
                message=f"颜色模式为灰度（{mode}），如需彩色印刷请确认",
                details={
                    "color_mode": mode,
                    "suggestion": "确认客户是否需要彩色印刷",
                },
            )
        # 调色板模式
        elif mode_upper == "P":
            result = PreflightCheckResult(
                item=CheckItem.COLOR_MODE,
                risk_level=RiskLevel.PASS,
                message=f"颜色模式为索引色（{mode}），一般可正常输出",
                details={"color_mode": mode},
            )
        else:
            result = PreflightCheckResult(
                item=CheckItem.COLOR_MODE,
                risk_level=RiskLevel.WARNING,
                message=f"颜色模式 {mode} 非印刷常用模式，请确认输出效果",
                details={"color_mode": mode},
            )
        report.add_check(result)

    def _check_transparency(self, report: PreflightReport) -> None:
        """检查是否存在透明通道。

        透明通道在某些印刷流程（如合并 PDF、拼版）中可能导致异常。
        """
        if report.has_transparency:
            result = PreflightCheckResult(
                item=CheckItem.TRANSPARENCY,
                risk_level=RiskLevel.WARNING,
                message="图像包含透明通道，印刷前建议合成白色底或确认是否需保留透明",
                details={
                    "color_mode": report.color_mode,
                    "suggestion": "在排版软件中确认透明区域效果，必要时先合成实底",
                },
            )
        else:
            result = PreflightCheckResult(
                item=CheckItem.TRANSPARENCY,
                risk_level=RiskLevel.PASS,
                message="图像无透明通道，可正常印刷",
            )
        report.add_check(result)

    def _check_low_resolution(self, report: PreflightReport) -> None:
        """综合评估低清风险：结合 DPI 和尺寸判断实际输出质量。

        低清风险判断逻辑：
        - DPI 低于 150 且尺寸偏小 → error
        - DPI 缺失且尺寸偏小 → warning
        - 其他情况 → pass
        """
        dpi = report.dpi
        width = report.width
        height = report.height

        if width is None or height is None:
            return

        # 计算在推荐 DPI 下的有效物理尺寸（英寸）
        if dpi is not None and dpi > 0:
            physical_width_inch = width / dpi
            physical_height_inch = height / dpi
        else:
            physical_width_inch = None
            physical_height_inch = None

        # 综合评估
        if dpi is not None and dpi < MIN_ACCEPTABLE_DPI:
            # DPI 严重不足
            if physical_width_inch is not None and physical_width_inch < 1.0:
                # 物理尺寸也极小（不足 1 英寸），风险极高
                result = PreflightCheckResult(
                    item=CheckItem.LOW_RESOLUTION,
                    risk_level=RiskLevel.ERROR,
                    message=f"低清风险极高: DPI={dpi:.0f}，有效尺寸仅 {physical_width_inch:.1f}×{physical_height_inch:.1f} 英寸",
                    details={
                        "dpi": dpi,
                        "physical_width_inch": round(physical_width_inch, 2),
                        "physical_height_inch": round(physical_height_inch, 2),
                        "suggestion": "此图像无法满足印刷质量要求，请获取更高分辨率原图",
                    },
                )
            else:
                result = PreflightCheckResult(
                    item=CheckItem.LOW_RESOLUTION,
                    risk_level=RiskLevel.ERROR,
                    message=f"低清风险: DPI={dpi:.0f} 严重不足，建议使用 ≥{MIN_ACCEPTABLE_DPI} DPI 的图像",
                    details={
                        "dpi": dpi,
                        "min_acceptable_dpi": MIN_ACCEPTABLE_DPI,
                        "suggestion": "请替换为高清原图",
                    },
                )
        elif dpi is None and width < RECOMMENDED_MIN_WIDTH and height < RECOMMENDED_MIN_HEIGHT:
            # 无 DPI 且尺寸偏小——无法判断物理尺寸，但像素数明显不足
            result = PreflightCheckResult(
                item=CheckItem.LOW_RESOLUTION,
                risk_level=RiskLevel.WARNING,
                message=f"图像无 DPI 信息且像素尺寸偏小 ({width}×{height})，可能有低清风险",
                details={
                    "width": width,
                    "height": height,
                    "suggestion": "在排版软件中确认输出尺寸是否满足要求",
                },
            )
        else:
            result = PreflightCheckResult(
                item=CheckItem.LOW_RESOLUTION,
                risk_level=RiskLevel.PASS,
                message="未检测到明显低清风险",
                details={
                    "dpi": dpi,
                    "width": width,
                    "height": height,
                },
            )
        report.add_check(result)

    def _check_file_size(self, report: PreflightReport) -> None:
        """检查文件大小是否有异常。

        文件过小可能意味着过度压缩导致质量损失。
        """
        size_bytes = report.file_size_bytes
        size_kb = size_bytes / 1024.0

        if size_bytes < MIN_FILE_SIZE_WARN_BYTES:
            # 文件太小，但如果是小图标可能正常——只给 warning
            result = PreflightCheckResult(
                item=CheckItem.FILE_SIZE,
                risk_level=RiskLevel.WARNING,
                message=f"文件较小 ({size_kb:.1f} KB)，可能被过度压缩或为缩略图",
                details={
                    "file_size_bytes": size_bytes,
                    "file_size_kb": round(size_kb, 1),
                    "warning_threshold_kb": MIN_FILE_SIZE_WARN_BYTES / 1024,
                    "suggestion": "确认是否为原始高质量文件",
                },
            )
        else:
            result = PreflightCheckResult(
                item=CheckItem.FILE_SIZE,
                risk_level=RiskLevel.PASS,
                message=f"文件大小 {size_kb:.1f} KB，正常",
                details={
                    "file_size_bytes": size_bytes,
                    "file_size_kb": round(size_kb, 1),
                },
            )
        report.add_check(result)

    # ---- 综合建议 ----

    def _build_overall_message(self, report: PreflightReport) -> None:
        """根据检查结果生成综合建议。"""
        errors = report.errors()
        warnings = report.warnings()

        if errors and warnings:
            report.overall_message = (
                f"发现 {len(errors)} 项严重风险和 {len(warnings)} 项潜在问题，"
                f"建议修正后再提交印刷。主要问题: {errors[0].message}"
            )
        elif errors:
            report.overall_message = (
                f"发现 {len(errors)} 项严重风险，不建议直接印刷。"
                f"主要问题: {errors[0].message}"
            )
        elif warnings:
            report.overall_message = (
                f"通过基本检查，但有 {len(warnings)} 项注意事项，"
                f"建议人工复核。主要提醒: {warnings[0].message}"
            )
        else:
            report.overall_message = "所有检查项均已通过，可以提交印刷。"
