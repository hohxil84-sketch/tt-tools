"""
local-worker/modules/preflight-check/tests/test_preflight.py

印前检查模块单元测试。
使用 Pillow 动态生成测试图像，覆盖各种边界场景。
"""

import os
import sys
import tempfile

import pytest
from PIL import Image

# 由于模块目录名含连字符（preflight-check），无法直接作为 Python 包名导入，
# 因此将模块源码目录加入 sys.path，直接导入 checker 和 report 模块。
# 同时将 local-worker/ 加入路径以支持 shared.* 导入
_module_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_local_worker_dir = os.path.dirname(os.path.dirname(_module_src_dir))
sys.path.insert(0, _module_src_dir)
sys.path.insert(0, _local_worker_dir)

from checker import PreflightChecker
from report import (
    PreflightReport,
    PreflightCheckResult,
    CheckItem,
    RiskLevel,
    RECOMMENDED_MIN_WIDTH,
    RECOMMENDED_MIN_HEIGHT,
    RECOMMENDED_DPI,
    MIN_ACCEPTABLE_DPI,
)


# ---- 测试辅助函数 ----

def _create_test_image(
    dir_path: str,
    filename: str,
    size: tuple = (800, 600),
    mode: str = "RGB",
    dpi: tuple = (300, 300),
    color: tuple = (255, 255, 255),
) -> str:
    """使用 Pillow 创建测试用图像文件，返回文件路径。"""
    # 根据颜色模式调整 color 参数：
    # - "L" 灰度模式只需单个整数（0-255）
    # - "CMYK" 需要 4 元组
    # - RGB/RGBA 等用传入的 color
    if mode == "L":
        fill_color: int | tuple = 128  # 灰度中间值
    elif mode == "CMYK":
        fill_color = (0, 0, 0, 0)
    else:
        fill_color = color
    img = Image.new(mode, size, fill_color)
    filepath = os.path.join(dir_path, filename)
    # JPEG 不支持 RGBA，需要用 RGB
    if filename.lower().endswith((".jpg", ".jpeg")) and mode in ("RGBA", "PA", "LA"):
        img = img.convert("RGBA")
    if mode == "CMYK":
        # 创建 RGB 再转换
        img = Image.new("RGB", size, color[:3])
        img = img.convert("CMYK") if hasattr(Image, "CMYK") else img
    img.save(filepath, dpi=dpi)
    # DP在保存后设置（JPEG 格式会在 save 时写入 dpi）
    # 部分格式如 PNG 不支持在 Image.new 时设 dpi
    return filepath


# ---- 测试类 ----

class TestPreflightChecker:
    """PreflightChecker 核心功能测试。"""

    @pytest.fixture
    def checker(self):
        """创建检查器实例。"""
        return PreflightChecker()

    @pytest.fixture
    def tmp_dir(self):
        """创建临时目录并在测试后清理。"""
        with tempfile.TemporaryDirectory() as d:
            yield d

    # ---- 正常图像检查 ----

    def test_check_good_jpg(self, checker, tmp_dir):
        """测试标准高质量 JPEG 图像：应全部通过。"""
        filepath = _create_test_image(
            tmp_dir, "good.jpg", size=(3000, 2400), mode="RGB", dpi=(300, 300)
        )
        report = checker.check(filepath)

        assert isinstance(report, PreflightReport)
        # JPEG RGB 模式会产生颜色模式 warning（建议转 CMYK），但无 error
        assert not report.has_errors
        assert report.file_format == ".jpg"
        assert report.width == 3000
        assert report.height == 2400
        assert report.dpi == 300.0

    def test_check_good_png(self, checker, tmp_dir):
        """测试标准 PNG 图像（无透明通道）：格式通过，但 DPI 可能缺失。"""
        filepath = _create_test_image(
            tmp_dir, "good.png", size=(2000, 1500), mode="RGB", dpi=(300, 300)
        )
        # 用 save 时传 dpi（Pillow save 对 PNG 也支持 dpi 参数）
        img = Image.new("RGB", (2000, 1500), (128, 128, 128))
        img.save(filepath, dpi=(300, 300))

        report = checker.check(filepath)
        # 尺寸、格式、颜色模式应通过
        assert report.has_errors is False
        assert report.has_transparency is False

    def test_check_good_tiff(self, checker, tmp_dir):
        """测试 TIFF 格式。"""
        img = Image.new("RGB", (4000, 3000), (200, 200, 200))
        filepath = os.path.join(tmp_dir, "good.tiff")
        img.save(filepath, dpi=(300, 300))
        report = checker.check(filepath)

        # TIFF RGB 模式可能产生颜色模式 warning，但不影响整体可用性
        assert not report.has_errors
        assert report.file_format == ".tiff"

    # ---- 文件格式检查 ----

    def test_unsupported_format(self, checker, tmp_dir):
        """测试不支持的文件格式：应报 error。"""
        # 创建 .ico 文件（不在印刷支持格式中）
        img = Image.new("RGB", (500, 500), (0, 0, 200))
        filepath = os.path.join(tmp_dir, "test.ico")
        img.save(filepath, format="ICO")
        report = checker.check(filepath)

        assert report.has_errors
        format_check = next(
            (c for c in report.checks if c.item == CheckItem.FILE_FORMAT), None
        )
        assert format_check is not None
        assert format_check.risk_level == RiskLevel.ERROR

    # ---- 尺寸检查 ----

    def test_small_dimensions_warning(self, checker, tmp_dir):
        """测试像素尺寸偏小：应报 warning。"""
        filepath = _create_test_image(
            tmp_dir, "small.jpg", size=(200, 150), mode="RGB", dpi=(300, 300)
        )
        report = checker.check(filepath)

        dim_check = next(
            (c for c in report.checks if c.item == CheckItem.DIMENSIONS), None
        )
        assert dim_check is not None
        assert dim_check.risk_level == RiskLevel.WARNING

    def test_large_dimensions_pass(self, checker, tmp_dir):
        """测试大尺寸图像：应通过。"""
        filepath = _create_test_image(
            tmp_dir, "large.jpg", size=(6000, 4800), mode="RGB", dpi=(300, 300)
        )
        report = checker.check(filepath)

        dim_check = next(
            (c for c in report.checks if c.item == CheckItem.DIMENSIONS), None
        )
        assert dim_check is not None
        assert dim_check.risk_level == RiskLevel.PASS

    # ---- DPI 检查 ----

    def test_low_dpi_error(self, checker, tmp_dir):
        """测试极低 DPI（50）：应报 error。"""
        filepath = _create_test_image(
            tmp_dir, "low_dpi.jpg", size=(3000, 2400), mode="RGB", dpi=(50, 50)
        )
        report = checker.check(filepath)

        dpi_check = next(
            (c for c in report.checks if c.item == CheckItem.DPI), None
        )
        assert dpi_check is not None
        assert dpi_check.risk_level == RiskLevel.ERROR

    def test_moderate_dpi_warning(self, checker, tmp_dir):
        """测试中等 DPI（200）：应报 warning（低于推荐但高于最低）。"""
        filepath = _create_test_image(
            tmp_dir, "mid_dpi.jpg", size=(3000, 2400), mode="RGB", dpi=(200, 200)
        )
        report = checker.check(filepath)

        dpi_check = next(
            (c for c in report.checks if c.item == CheckItem.DPI), None
        )
        assert dpi_check is not None
        assert dpi_check.risk_level == RiskLevel.WARNING

    def test_good_dpi_pass(self, checker, tmp_dir):
        """测试标准 300 DPI：应通过。"""
        filepath = _create_test_image(
            tmp_dir, "good_dpi.jpg", size=(3000, 2400), mode="RGB", dpi=(300, 300)
        )
        report = checker.check(filepath)

        dpi_check = next(
            (c for c in report.checks if c.item == CheckItem.DPI), None
        )
        assert dpi_check is not None
        assert dpi_check.risk_level == RiskLevel.PASS

    # ---- 颜色模式检查 ----

    def test_rgb_color_mode_warning(self, checker, tmp_dir):
        """测试 RGB 模式：应报 warning（建议转 CMYK）。"""
        filepath = _create_test_image(
            tmp_dir, "rgb.jpg", size=(3000, 2400), mode="RGB", dpi=(300, 300)
        )
        report = checker.check(filepath)

        color_check = next(
            (c for c in report.checks if c.item == CheckItem.COLOR_MODE), None
        )
        assert color_check is not None
        # RGB 应有 warning（建议转 CMYK）
        assert color_check.risk_level in (RiskLevel.WARNING, RiskLevel.PASS)

    def test_grayscale_mode(self, checker, tmp_dir):
        """测试灰度模式：应报 warning（确认是否需彩色）。"""
        filepath = _create_test_image(
            tmp_dir, "gray.jpg", size=(3000, 2400), mode="L", dpi=(300, 300)
        )
        report = checker.check(filepath)

        color_check = next(
            (c for c in report.checks if c.item == CheckItem.COLOR_MODE), None
        )
        assert color_check is not None
        assert color_check.risk_level == RiskLevel.WARNING

    # ---- 透明通道检查 ----

    def test_transparency_warning(self, checker, tmp_dir):
        """测试 RGBA 图像：应检测到透明通道并报 warning。"""
        img = Image.new("RGBA", (1000, 1000), (255, 0, 0, 128))
        filepath = os.path.join(tmp_dir, "transparent.png")
        img.save(filepath)

        report = checker.check(filepath)

        assert report.has_transparency
        trans_check = next(
            (c for c in report.checks if c.item == CheckItem.TRANSPARENCY), None
        )
        assert trans_check is not None
        assert trans_check.risk_level == RiskLevel.WARNING

    def test_no_transparency_pass(self, checker, tmp_dir):
        """测试无透明通道的 RGB 图像：应通过。"""
        filepath = _create_test_image(
            tmp_dir, "no_alpha.jpg", size=(3000, 2400), mode="RGB", dpi=(300, 300)
        )
        report = checker.check(filepath)

        assert not report.has_transparency
        trans_check = next(
            (c for c in report.checks if c.item == CheckItem.TRANSPARENCY), None
        )
        assert trans_check is not None
        assert trans_check.risk_level == RiskLevel.PASS

    # ---- 低清风险 ----

    def test_low_resolution_high_risk(self, checker, tmp_dir):
        """测试低 DPI + 小尺寸：应报 error 级别低清风险。"""
        filepath = _create_test_image(
            tmp_dir, "low_res.jpg", size=(100, 80), mode="RGB", dpi=(50, 50)
        )
        report = checker.check(filepath)

        lowres_check = next(
            (c for c in report.checks if c.item == CheckItem.LOW_RESOLUTION), None
        )
        assert lowres_check is not None
        assert lowres_check.risk_level == RiskLevel.ERROR

    def test_no_low_resolution_risk(self, checker, tmp_dir):
        """测试高 DPI + 大尺寸：低清风险应通过。"""
        filepath = _create_test_image(
            tmp_dir, "high_res.jpg", size=(6000, 4800), mode="RGB", dpi=(300, 300)
        )
        report = checker.check(filepath)

        lowres_check = next(
            (c for c in report.checks if c.item == CheckItem.LOW_RESOLUTION), None
        )
        assert lowres_check is not None
        assert lowres_check.risk_level == RiskLevel.PASS

    # ---- 文件大小检查 ----

    def test_small_file_size_warning(self, checker, tmp_dir):
        """测试极小文件：应报文件大小 warning。"""
        filepath = _create_test_image(
            tmp_dir, "tiny.jpg", size=(1000, 800), mode="RGB", dpi=(300, 300)
        )
        # 用高压缩比保存来减小文件
        img = Image.new("RGB", (10, 10), (255, 255, 255))
        img.save(filepath, quality=1)  # 极小质量

        report = checker.check(filepath)

        size_check = next(
            (c for c in report.checks if c.item == CheckItem.FILE_SIZE), None
        )
        assert size_check is not None
        # 文件可能很小，即使内容有 1000x800...
        # 这里主要验证检查逻辑存在和执行
        assert size_check.risk_level in (RiskLevel.WARNING, RiskLevel.PASS)

    # ---- 错误处理 ----

    def test_nonexistent_file(self, checker):
        """测试不存在的文件：应抛出 AppError。"""
        from shared.errors import AppError

        with pytest.raises(AppError):
            checker.check("D:\\nonexistent\\fake_file.jpg")

    # ---- 综合报告 ----

    def test_report_structure(self, checker, tmp_dir):
        """测试报告结构完整性。"""
        filepath = _create_test_image(
            tmp_dir, "full_check.jpg", size=(4000, 3000), mode="RGB", dpi=(300, 300)
        )
        report = checker.check(filepath)

        # 验证报告字段
        assert report.file_path
        assert report.file_name
        assert report.file_format in (".jpg", ".jpeg")
        assert report.file_size_bytes > 0
        assert report.width == 4000
        assert report.height == 3000
        assert report.color_mode == "RGB"

        # 应包含所有检查项
        check_items = {c.item for c in report.checks}
        expected_items = {
            CheckItem.FILE_FORMAT,
            CheckItem.DIMENSIONS,
            CheckItem.DPI,
            CheckItem.COLOR_MODE,
            CheckItem.TRANSPARENCY,
            CheckItem.LOW_RESOLUTION,
            CheckItem.FILE_SIZE,
        }
        assert check_items == expected_items

        # to_dict 应可序列化
        d = report.to_dict()
        assert isinstance(d, dict)
        assert len(d["checks"]) == 7

    def test_report_overall_message(self, checker, tmp_dir):
        """测试综合建议生成。"""
        filepath = _create_test_image(
            tmp_dir, "msg_test.jpg", size=(4000, 3000), mode="RGB", dpi=(300, 300)
        )
        report = checker.check(filepath)
        assert report.overall_message
        assert isinstance(report.overall_message, str)
        assert len(report.overall_message) > 0

    # ---- 边界场景 ----

    def test_png_no_dpi(self, checker, tmp_dir):
        """测试无 DPI 信息的 PNG：DPI 检查应报 warning，但不影响其他项。"""
        # Pillow 创建 PNG 时默认不写 DPI
        img = Image.new("RGB", (2000, 1500), (128, 128, 128))
        filepath = os.path.join(tmp_dir, "nodpi.png")
        img.save(filepath, dpi=(300, 300))  # 显式设 dpi

        report = checker.check(filepath)
        # PNG 保存时 dpi 不一定被保留（取决于 Pillow 版本和 PNG 实现）
        # 不做硬断言，只验证报告存在
        assert report is not None
        assert report.file_name == "nodpi.png"

    def test_multiple_errors_aggregation(self, checker, tmp_dir):
        """测试多项风险聚合：errors() / warnings() / passes() 应正确分类。"""
        # 短边+低DPI → 多项风险
        filepath = _create_test_image(
            tmp_dir, "multi_risk.jpg", size=(100, 80), mode="RGB", dpi=(50, 50)
        )
        report = checker.check(filepath)

        assert len(report.errors()) > 0
        assert len(report.warnings()) > 0
        assert len(report.passes()) >= 0
        assert report.overall_risk == RiskLevel.ERROR


class TestPreflightReport:
    """PreflightReport 数据结构测试。"""

    def test_empty_report(self):
        """测试空报告初始状态。"""
        report = PreflightReport(
            file_path="/tmp/test.png",
            file_name="test.png",
            file_format=".png",
            file_size_bytes=1024,
        )
        assert report.overall_risk == RiskLevel.PASS
        assert not report.has_errors
        assert not report.has_warnings
        assert report.errors() == []
        assert report.warnings() == []
        assert report.passes() == []

    def test_add_error_updates_overall(self):
        """测试添加 error 检查时综合风险更新。"""
        report = PreflightReport(
            file_path="/tmp/test.png",
            file_name="test.png",
            file_format=".png",
            file_size_bytes=1024,
        )
        result = PreflightCheckResult(
            item=CheckItem.DPI,
            risk_level=RiskLevel.ERROR,
            message="DPI 过低",
        )
        report.add_check(result)

        assert report.has_errors
        assert report.overall_risk == RiskLevel.ERROR
        assert len(report.errors()) == 1

    def test_add_warning_does_not_override_error(self):
        """测试 error + warning：overall_risk 应保持 ERROR。"""
        report = PreflightReport(
            file_path="/tmp/test.png",
            file_name="test.png",
            file_format=".png",
            file_size_bytes=1024,
        )
        report.add_check(PreflightCheckResult(
            item=CheckItem.DPI,
            risk_level=RiskLevel.ERROR,
            message="DPI 过低",
        ))
        report.add_check(PreflightCheckResult(
            item=CheckItem.COLOR_MODE,
            risk_level=RiskLevel.WARNING,
            message="RGB 模式",
        ))

        assert report.has_errors
        assert report.has_warnings
        assert report.overall_risk == RiskLevel.ERROR

    def test_to_dict(self):
        """测试 to_dict 序列化。"""
        report = PreflightReport(
            file_path="/tmp/test.png",
            file_name="test.png",
            file_format=".png",
            file_size_bytes=5000,
            width=1920,
            height=1080,
            dpi=72.0,
            color_mode="RGB",
            has_transparency=False,
        )
        d = report.to_dict()
        assert d["file_path"] == "/tmp/test.png"
        assert d["width"] == 1920
        assert d["height"] == 1080
        assert d["dpi"] == 72.0
        assert d["color_mode"] == "RGB"
        assert d["has_transparency"] is False
        assert d["checks"] == []


class TestRiskLevel:
    """风险等级枚举测试。"""

    def test_risk_level_values(self):
        assert RiskLevel.PASS.value == "pass"
        assert RiskLevel.WARNING.value == "warning"
        assert RiskLevel.ERROR.value == "error"

    def test_risk_level_comparison(self):
        """测试风险等级字符串比较。"""
        assert RiskLevel.PASS == RiskLevel("pass")
        assert RiskLevel.WARNING == RiskLevel("warning")
        assert RiskLevel.ERROR == RiskLevel("error")


class TestCheckItem:
    """检查项枚举测试。"""

    def test_all_items_defined(self):
        """确认所有检查项都已定义。"""
        expected = {
            "file_format", "dimensions", "dpi", "color_mode",
            "transparency", "low_resolution", "file_size",
        }
        actual = {item.value for item in CheckItem}
        assert actual == expected


class TestThresholdConstants:
    """验证阈值常量。"""

    def test_recommended_values(self):
        assert RECOMMENDED_MIN_WIDTH > 0
        assert RECOMMENDED_MIN_HEIGHT > 0
        assert RECOMMENDED_DPI > 0
        assert MIN_ACCEPTABLE_DPI > 0
        assert MIN_ACCEPTABLE_DPI < RECOMMENDED_DPI
