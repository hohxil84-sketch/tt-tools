"""
local-worker/modules/resize-image/tests/test_resize_image — 图片改尺寸模块测试

覆盖：
  - 模块导入、常量校验
  - ResizeParams 参数校验
  - 所有 7 种缩放模式 (EXACT/FIT/FILL/SCALE/SHORT_SIDE/LONG_SIDE/CUSTOM_DPI)
  - 重采样滤镜
  - 格式转换
  - 预设尺寸
  - 输入校验与错误处理
  - 文件输入 / bytes 输入 / PIL Image 输入
  - 文件输出
  - DPI 处理
  - 边缘情况

运行方式（从项目根目录，使用模块专用 venv）：
  D:/localPath/venvs/local-worker-resize-image/Scripts/python.exe -m pytest local-worker/modules/resize-image/tests/ -v
"""

import io
import os
import sys
import tempfile
import pytest
from pathlib import Path

# 由于模块目录名含连字符（resize-image），无法直接作为 Python 包名导入，
# 因此将模块源码目录加入 sys.path，直接导入 processor 和 specifications 模块。
# 同时将 local-worker/ 加入路径以支持 shared.* 导入
_module_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_local_worker_dir = os.path.dirname(os.path.dirname(_module_src_dir))
if _module_src_dir not in sys.path:
    sys.path.insert(0, _module_src_dir)
if _local_worker_dir not in sys.path:
    sys.path.insert(0, _local_worker_dir)

from PIL import Image
from shared.errors import AppError, ErrorCode

from processor import ImageResizer
from specifications import (
    ResizeMode,
    ResampleFilter,
    OutputFormat,
    ResizeParams,
    ResizeResult,
    PRINT_PRESETS,
    SUPPORTED_INPUT_SUFFIXES,
    FORMAT_SUFFIX_MAP,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_PNG_COMPRESS_LEVEL,
    DEFAULT_WEBP_QUALITY,
    MAX_OUTPUT_DIMENSION,
)


# ===== 测试辅助工具 =====

def create_test_image(width: int = 800, height: int = 600, mode: str = "RGB",
                      color: tuple = (100, 150, 200)) -> Image.Image:
    """创建一个纯色测试图片。"""
    return Image.new(mode, (width, height), color)


def create_test_image_bytes(width: int = 800, height: int = 600, fmt: str = "PNG",
                            color: tuple = (100, 150, 200)) -> bytes:
    """创建测试图片的 bytes 数据。"""
    img = create_test_image(width, height, color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def create_test_image_file(tmp_path, width: int = 800, height: int = 600,
                           fmt: str = "PNG", suffix: str = ".png") -> str:
    """创建临时测试图片文件，返回文件路径。"""
    img = create_test_image(width, height)
    file_path = os.path.join(str(tmp_path), f"test_{width}x{height}{suffix}")
    img.save(file_path)
    return file_path


@pytest.fixture
def resizer():
    """ImageResizer 实例 fixture。"""
    return ImageResizer()


@pytest.fixture
def sample_png(tmp_path):
    """创建示例 PNG 文件并返回其路径。"""
    return create_test_image_file(tmp_path, 800, 600, fmt="PNG", suffix=".png")


@pytest.fixture
def sample_jpg(tmp_path):
    """创建示例 JPG 文件并返回其路径。"""
    return create_test_image_file(tmp_path, 800, 600, fmt="JPEG", suffix=".jpg")


@pytest.fixture
def sample_png_bytes():
    """创建示例 PNG bytes。"""
    return create_test_image_bytes(800, 600, fmt="PNG")


# ===== 模块导入与常量测试 =====

class TestModuleImport:
    """模块导入和常量校验。"""

    def test_import_resize_image_module(self):
        """验证模块可正常导入。"""
        import processor
        import specifications
        assert processor is not None
        assert specifications is not None

    def test_import_all_exports(self):
        """验证所有对外导出类/枚举可正常导入。"""
        assert ImageResizer is not None
        assert ResizeParams is not None
        assert ResizeResult is not None
        assert ResizeMode is not None
        assert ResampleFilter is not None
        assert OutputFormat is not None

    def test_python_version(self):
        """验证 Python 版本 >= 3.11。"""
        assert sys.version_info >= (3, 11), f"需要 Python >= 3.11，当前: {sys.version}"

    def test_pillow_available(self):
        """验证 Pillow 已安装。"""
        import PIL
        assert PIL.__version__

    def test_pytest_available(self):
        """验证 pytest 已安装。"""
        import pytest
        assert pytest.__version__


class TestConstants:
    """常量和枚举测试。"""

    def test_print_presets_not_empty(self):
        """验证预设字典不为空。"""
        assert len(PRINT_PRESETS) > 0

    def test_print_presets_all_valid(self):
        """验证所有预设中的尺寸都为正整数。"""
        for key, (w, h, desc) in PRINT_PRESETS.items():
            assert w > 0, f"预设 {key} 宽度无效: {w}"
            assert h > 0, f"预设 {key} 高度无效: {h}"
            assert isinstance(desc, str) and len(desc) > 0, f"预设 {key} 描述无效"

    def test_resize_modes_count(self):
        """验证缩放模式枚举数量。"""
        assert len(ResizeMode) == 7

    def test_resample_filters_count(self):
        """验证重采样滤镜枚举数量。"""
        assert len(ResampleFilter) == 6

    def test_output_formats_count(self):
        """验证输出格式枚举数量。"""
        assert len(OutputFormat) == 6

    def test_resample_filter_to_pil(self):
        """验证所有滤镜都可转换为 PIL 常量。"""
        for f in ResampleFilter:
            pil_val = f.to_pil()
            assert pil_val is not None

    def test_supported_input_suffixes(self):
        """验证支持的输入后缀列表。"""
        assert ".png" in SUPPORTED_INPUT_SUFFIXES
        assert ".jpg" in SUPPORTED_INPUT_SUFFIXES
        assert ".bmp" in SUPPORTED_INPUT_SUFFIXES
        assert ".tiff" in SUPPORTED_INPUT_SUFFIXES
        assert ".webp" in SUPPORTED_INPUT_SUFFIXES

    def test_format_suffix_map(self):
        """验证格式->后缀映射。"""
        assert FORMAT_SUFFIX_MAP[OutputFormat.PNG] == ".png"
        assert FORMAT_SUFFIX_MAP[OutputFormat.JPEG] == ".jpg"
        assert FORMAT_SUFFIX_MAP[OutputFormat.BMP] == ".bmp"
        assert FORMAT_SUFFIX_MAP[OutputFormat.TIFF] == ".tiff"
        assert FORMAT_SUFFIX_MAP[OutputFormat.WEBP] == ".webp"


# ===== ResizeParams 参数校验 =====

class TestResizeParams:
    """ResizeParams 参数校验测试。"""

    def test_default_params_valid(self):
        """带 width/height 的默认参数应该通过校验。"""
        params = ResizeParams(width=800, height=600)
        errors = params.validate()
        assert len(errors) == 0, f"默认参数不应该有错误: {errors}"

    def test_fit_mode_valid(self):
        """FIT 模式有效参数。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=800, height=600)
        assert len(params.validate()) == 0

    def test_exact_mode_no_width_height(self):
        """EXACT 模式缺少 width 和 height。"""
        params = ResizeParams(mode=ResizeMode.EXACT)
        errors = params.validate()
        assert len(errors) > 0
        assert any("至少需要指定" in e for e in errors)

    def test_zero_width(self):
        """宽度为 0 应报错。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=0, height=600)
        errors = params.validate()
        assert len(errors) > 0
        assert any("宽度" in e for e in errors)

    def test_negative_height(self):
        """高度为负数应报错。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=800, height=-100)
        errors = params.validate()
        assert len(errors) > 0

    def test_scale_percent_zero(self):
        """缩放百分比为 0 应报错。"""
        params = ResizeParams(mode=ResizeMode.SCALE, scale_percent=0)
        errors = params.validate()
        assert len(errors) > 0

    def test_scale_percent_negative(self):
        """缩放百分比为负数应报错。"""
        params = ResizeParams(mode=ResizeMode.SCALE, scale_percent=-10)
        errors = params.validate()
        assert len(errors) > 0

    def test_short_side_none(self):
        """SHORT_SIDE 模式缺少 short_side。"""
        params = ResizeParams(mode=ResizeMode.SHORT_SIDE)
        errors = params.validate()
        assert len(errors) > 0
        assert any("short_side" in e for e in errors)

    def test_short_side_zero(self):
        """SHORT_SIDE 模式 short_side 为 0。"""
        params = ResizeParams(mode=ResizeMode.SHORT_SIDE, short_side=0)
        errors = params.validate()
        assert len(errors) > 0

    def test_long_side_none(self):
        """LONG_SIDE 模式缺少 long_side。"""
        params = ResizeParams(mode=ResizeMode.LONG_SIDE)
        errors = params.validate()
        assert len(errors) > 0
        assert any("long_side" in e for e in errors)

    def test_custom_dpi_none(self):
        """CUSTOM_DPI 模式缺少 target_dpi。"""
        params = ResizeParams(mode=ResizeMode.CUSTOM_DPI)
        errors = params.validate()
        assert len(errors) > 0

    def test_jpeg_quality_out_of_range(self):
        """JPEG 质量超出范围。"""
        params = ResizeParams(jpeg_quality=0)
        errors = params.validate()
        assert len(errors) > 0

        params2 = ResizeParams(jpeg_quality=101)
        errors2 = params2.validate()
        assert len(errors2) > 0

    def test_png_compress_level_out_of_range(self):
        """PNG 压缩级别超出范围。"""
        params = ResizeParams(png_compress_level=-1)
        errors = params.validate()
        assert len(errors) > 0

        params2 = ResizeParams(png_compress_level=10)
        errors2 = params2.validate()
        assert len(errors2) > 0

    def test_webp_quality_out_of_range(self):
        """WEBP 质量超出范围。"""
        params = ResizeParams(webp_quality=101)
        errors = params.validate()
        assert len(errors) > 0

    def test_exceed_max_dimension(self):
        """宽度超过最大限制。"""
        params = ResizeParams(mode=ResizeMode.EXACT, width=MAX_OUTPUT_DIMENSION + 1, height=100)
        errors = params.validate()
        assert len(errors) > 0


# ===== ImageResizer 基础功能测试 =====

class TestImageResizerBasic:
    """ImageResizer 基础功能测试。"""

    def test_create_resizer(self):
        """创建 ImageResizer 实例。"""
        r = ImageResizer()
        assert r is not None

    def test_resize_png_fit(self, resizer, sample_png):
        """对 PNG 文件执行 FIT 缩放。"""
        result = resizer.resize(sample_png, preset=None,
                                params=ResizeParams(mode=ResizeMode.FIT, width=400, height=300))
        assert result.success
        assert result.output_width <= 400
        assert result.output_height <= 300
        assert result.output_width == 400 or result.output_height == 300  # 某一边应恰好等于边界
        assert result.output_data is not None
        assert len(result.output_data) > 0

    def test_resize_default_params(self, resizer, sample_png):
        """不传参数时使用默认值（FIT 800×800）。"""
        result = resizer.resize(sample_png)
        assert result.success
        assert result.output_width <= 800
        assert result.output_height <= 800

    def test_result_metadata(self, resizer, sample_png):
        """验证结果元数据完整。"""
        result = resizer.resize(sample_png,
                                params=ResizeParams(mode=ResizeMode.FIT, width=400, height=300))
        assert result.source_width == 800
        assert result.source_height == 600
        assert result.mode == ResizeMode.FIT
        assert result.elapsed_ms > 0

    def test_result_to_dict(self, resizer, sample_png):
        """验证结果可转为字典。"""
        result = resizer.resize(sample_png,
                                params=ResizeParams(mode=ResizeMode.FIT, width=400, height=300))
        d = result.to_dict()
        assert d["success"] is True
        assert d["source_width"] == 800
        assert d["source_height"] == 600
        assert isinstance(d["output_width"], int)
        assert isinstance(d["output_height"], int)

    def test_list_presets(self):
        """list_presets 应返回非空列表。"""
        presets = ImageResizer.list_presets()
        assert len(presets) > 0
        assert "name" in presets[0]
        assert "width" in presets[0]
        assert "height" in presets[0]
        assert "description" in presets[0]

    def test_supported_modes(self):
        """supported_modes 应返回所有模式。"""
        modes = ImageResizer.supported_modes()
        assert "fit" in modes
        assert "exact" in modes
        assert "scale" in modes

    def test_supported_filters(self):
        """supported_filters 应返回所有滤镜。"""
        filters = ImageResizer.supported_filters()
        assert "lanczos" in filters
        assert "bilinear" in filters


# ===== FIT 等比适配模式测试 =====

class TestResizeFitMode:
    """等比适配 (FIT) 模式测试。"""

    def test_fit_width_constrained(self, resizer, sample_png):
        """宽度约束：宽图片缩放到指定宽度。"""
        result = resizer.resize_fit(sample_png, 400, 800)
        assert result.success
        assert result.output_width == 400  # 宽度精确到目标
        assert result.output_height == 300  # 等比：800→400 则 600→300

    def test_fit_height_constrained(self, resizer, sample_png):
        """高度约束：高图片缩放到指定高度。"""
        # 创建竖图 600×800
        img = create_test_image(600, 800)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        result = resizer.resize_fit(img_bytes, 800, 400)
        assert result.success
        assert result.output_height == 400  # 高度精确到目标
        assert result.output_width == 300  # 等比：800→400 则 600→300

    def test_fit_both_smaller(self, resizer, sample_png):
        """原图大于目标尺寸，等比缩小。"""
        result = resizer.resize_fit(sample_png, 200, 150)
        assert result.success
        assert result.output_width <= 200
        assert result.output_height <= 150

    def test_fit_no_enlarge(self, resizer, sample_png):
        """原图小于目标尺寸时默认不放大（ratio≤1）。"""
        result = resizer.resize_fit(sample_png, 2000, 2000)
        assert result.success
        assert result.output_width == 800  # 保持原始尺寸
        assert result.output_height == 600

    def test_fit_square_target(self, resizer, sample_png):
        """正方形目标区域。"""
        result = resizer.resize_fit(sample_png, 400, 400)
        assert result.success
        assert result.output_width <= 400
        assert result.output_height <= 400
        assert result.output_width == 400 or result.output_height == 400

    def test_fit_very_small(self, resizer, sample_png):
        """缩放到极小尺寸。"""
        result = resizer.resize_fit(sample_png, 10, 10)
        assert result.success
        assert result.output_width == 10 or result.output_height == 10
        assert result.output_width <= 10
        assert result.output_height <= 10

    def test_fit_only_width(self, resizer, sample_png):
        """只指定宽度，高度不限。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400)
        result = resizer.resize(sample_png, params=params)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 300

    def test_fit_only_height(self, resizer, sample_png):
        """只指定高度，宽度不限。"""
        params = ResizeParams(mode=ResizeMode.FIT, height=300)
        result = resizer.resize(sample_png, params=params)
        assert result.success
        assert result.output_height == 300
        assert result.output_width == 400


# ===== EXACT 精确尺寸模式测试 =====

class TestResizeExactMode:
    """精确尺寸 (EXACT) 模式测试。"""

    def test_exact_same_ratio(self, resizer, sample_png):
        """同比例精确缩放不会变形。"""
        result = resizer.resize_exact(sample_png, 400, 300)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 300
        assert len(result.warnings) == 0  # 比例相同无警告

    def test_exact_different_ratio(self, resizer, sample_png):
        """不同比例精确缩放会产生警告。"""
        result = resizer.resize_exact(sample_png, 400, 400)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 400
        # 800×600 → 400×400 比例不同，应有警告
        assert len(result.warnings) >= 1
        assert any("拉伸" in w or "变形" in w for w in result.warnings)

    def test_exact_keep_aspect(self, resizer, sample_png):
        """EXACT 模式 keep_aspect=True 应退化为 FIT。"""
        params = ResizeParams(mode=ResizeMode.EXACT, width=400, height=400, keep_aspect=True)
        result = resizer.resize(sample_png, params=params)
        assert result.success
        assert result.output_width <= 400
        assert result.output_height <= 400
        # 应有退化为 FIT 的警告
        assert any("FIT" in w.upper() for w in result.warnings)

    def test_exact_enlarge(self, resizer, sample_png):
        """精确放大。"""
        result = resizer.resize_exact(sample_png, 1600, 1200)
        assert result.success
        assert result.output_width == 1600
        assert result.output_height == 1200


# ===== FILL 等比填充模式测试 =====

class TestResizeFillMode:
    """等比填充 (FILL) 模式测试。"""

    def test_fill_cover(self, resizer, sample_png):
        """填充后应完全覆盖目标尺寸并进行裁剪。"""
        result = resizer.resize_fill(sample_png, 400, 400)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 400

    def test_fill_wide_image(self, resizer, sample_png):
        """宽图片填充正方形应裁剪左右。"""
        result = resizer.resize_fill(sample_png, 400, 400)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 400

    def test_fill_tall_image(self, resizer):
        """高图片填充正方形应裁剪上下。"""
        img = create_test_image_bytes(600, 800, fmt="PNG")
        result = resizer.resize_fill(img, 400, 400)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 400


# ===== SCALE 百分比缩放模式测试 =====

class TestResizeScaleMode:
    """百分比缩放 (SCALE) 模式测试。"""

    def test_scale_50_percent(self, resizer, sample_png):
        """缩放到 50%。"""
        result = resizer.resize_scale(sample_png, 50)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 300
        assert result.scale_ratio == pytest.approx(0.5, rel=0.01)

    def test_scale_200_percent(self, resizer, sample_png):
        """放大到 200%。"""
        result = resizer.resize_scale(sample_png, 200)
        assert result.success
        assert result.output_width == 1600
        assert result.output_height == 1200
        assert result.scale_ratio == pytest.approx(2.0, rel=0.01)

    def test_scale_100_percent(self, resizer, sample_png):
        """100% 不变。"""
        result = resizer.resize_scale(sample_png, 100)
        assert result.success
        assert result.output_width == 800
        assert result.output_height == 600

    def test_scale_25_percent(self, resizer, sample_png):
        """缩放到 25%。"""
        result = resizer.resize_scale(sample_png, 25)
        assert result.success
        assert result.output_width == 200
        assert result.output_height == 150


# ===== SHORT_SIDE 短边约束模式测试 =====

class TestResizeShortSide:
    """短边约束 (SHORT_SIDE) 模式测试。"""

    def test_short_side_wide_image(self, resizer, sample_png):
        """宽图片 (800×600)，短边=600（高度），指定 short_side=300 应缩放到 400×300。"""
        result = resizer.resize_short_side(sample_png, 300)
        assert result.success
        assert result.output_height == 300  # 短边精确到目标
        assert result.output_width == 400  # 长边等比

    def test_short_side_tall_image(self, resizer):
        """高图片 (600×800)，短边=600（宽度），指定 short_side=300 应缩放到 300×400。"""
        img = create_test_image_bytes(600, 800, fmt="PNG")
        result = resizer.resize_short_side(img, 300)
        assert result.success
        assert result.output_width == 300  # 短边精确到目标
        assert result.output_height == 400  # 长边等比


# ===== LONG_SIDE 长边约束模式测试 =====

class TestResizeLongSide:
    """长边约束 (LONG_SIDE) 模式测试。"""

    def test_long_side_wide_image(self, resizer, sample_png):
        """宽图片 (800×600)，长边=800（宽度），指定 long_side=400 应缩放到 400×300。"""
        result = resizer.resize_long_side(sample_png, 400)
        assert result.success
        assert result.output_width == 400  # 长边精确到目标
        assert result.output_height == 300  # 短边等比

    def test_long_side_tall_image(self, resizer):
        """高图片 (600×800)，长边=800（高度），指定 long_side=400 应缩放到 300×400。"""
        img = create_test_image_bytes(600, 800, fmt="PNG")
        result = resizer.resize_long_side(img, 400)
        assert result.success
        assert result.output_height == 400  # 长边精确到目标
        assert result.output_width == 300  # 短边等比

    def test_long_side_square(self, resizer):
        """正方形图片 (800×800)，long_side=400。"""
        img = create_test_image_bytes(800, 800, fmt="PNG")
        result = resizer.resize_long_side(img, 400)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 400


# ===== CUSTOM_DPI 模式测试 =====

class TestResizeCustomDpi:
    """按目标 DPI 缩放 (CUSTOM_DPI) 模式测试。"""

    def test_dpi_upscale(self, resizer, tmp_path):
        """72 DPI → 300 DPI。"""
        img = create_test_image(800, 600)
        file_path = os.path.join(str(tmp_path), "test_72dpi.png")
        img.save(file_path, dpi=(72, 72))

        result = resizer.resize_with_dpi(file_path, 300)
        assert result.success
        # 72→300 缩放比例为 300/72≈4.17，800*4.17≈3333
        assert result.output_width == pytest.approx(3333, abs=1)
        assert result.output_height == pytest.approx(2500, abs=1)

    def test_dpi_upscale_bytes(self, resizer):
        """无 DPI 信息的图片默认 72 DPI。"""
        data = create_test_image_bytes(800, 600, fmt="PNG")
        result = resizer.resize_with_dpi(data, 72)
        assert result.success
        # DPI 相同，无需缩放
        assert result.output_width == 800
        assert result.output_height == 600

    def test_dpi_same(self, resizer, tmp_path):
        """相同 DPI 不缩放。"""
        img = create_test_image(800, 600)
        file_path = os.path.join(str(tmp_path), "test_300dpi.png")
        img.save(file_path, dpi=(300, 300))

        result = resizer.resize_with_dpi(file_path, 300)
        assert result.success
        assert result.output_width == 800
        assert result.output_height == 600
        # DPI 相同时应有警告（不缩放），检查 output尺寸与 source 一致
        assert result.source_width == result.output_width
        assert result.source_height == result.output_height


# ===== 重采样滤镜测试 =====

class TestResampleFilters:
    """重采样滤镜测试。"""

    def test_lanczos(self, resizer, sample_png):
        """LANCZOS 滤镜缩放。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              resample=ResampleFilter.LANCZOS)
        result = resizer.resize(sample_png, params=params)
        assert result.success

    def test_bilinear(self, resizer, sample_png):
        """BILINEAR 滤镜缩放。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              resample=ResampleFilter.BILINEAR)
        result = resizer.resize(sample_png, params=params)
        assert result.success

    def test_bicubic(self, resizer, sample_png):
        """BICUBIC 滤镜缩放。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              resample=ResampleFilter.BICUBIC)
        result = resizer.resize(sample_png, params=params)
        assert result.success

    def test_nearest(self, resizer, sample_png):
        """NEAREST 滤镜缩放。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              resample=ResampleFilter.NEAREST)
        result = resizer.resize(sample_png, params=params)
        assert result.success

    def test_box(self, resizer, sample_png):
        """BOX 滤镜缩放。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              resample=ResampleFilter.BOX)
        result = resizer.resize(sample_png, params=params)
        assert result.success

    def test_hamming(self, resizer, sample_png):
        """HAMMING 滤镜缩放。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              resample=ResampleFilter.HAMMING)
        result = resizer.resize(sample_png, params=params)
        assert result.success


# ===== 格式转换测试 =====

class TestFormatConversion:
    """输出格式转换测试。"""

    def test_output_png(self, resizer, sample_png):
        """输出为 PNG。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              output_format=OutputFormat.PNG)
        result = resizer.resize(sample_png, params=params)
        assert result.success
        assert result.output_format == "png"
        # 验证输出数据是有效的 PNG
        img = Image.open(io.BytesIO(result.output_data))
        assert img.format == "PNG"

    def test_output_jpeg(self, resizer, sample_png):
        """输出为 JPEG。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              output_format=OutputFormat.JPEG)
        result = resizer.resize(sample_png, params=params)
        assert result.success
        assert result.output_format == "jpeg"
        img = Image.open(io.BytesIO(result.output_data))
        assert img.format == "JPEG"

    def test_output_bmp(self, resizer, sample_png):
        """输出为 BMP。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              output_format=OutputFormat.BMP)
        result = resizer.resize(sample_png, params=params)
        assert result.success
        assert result.output_format == "bmp"
        img = Image.open(io.BytesIO(result.output_data))
        assert img.format == "BMP"

    def test_output_tiff(self, resizer, sample_png):
        """输出为 TIFF。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              output_format=OutputFormat.TIFF)
        result = resizer.resize(sample_png, params=params)
        assert result.success
        assert result.output_format == "tiff"

    def test_output_webp(self, resizer, sample_png):
        """输出为 WEBP。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              output_format=OutputFormat.WEBP)
        result = resizer.resize(sample_png, params=params)
        assert result.success
        assert result.output_format == "webp"

    def test_output_original_format_png(self, resizer, sample_png):
        """保持原始格式（PNG 输入）。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              output_format=OutputFormat.ORIGINAL)
        result = resizer.resize(sample_png, params=params)
        assert result.success
        assert result.output_format == "png"

    def test_output_original_format_jpg(self, resizer, sample_jpg):
        """保持原始格式（JPG 输入）。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              output_format=OutputFormat.ORIGINAL)
        result = resizer.resize(sample_jpg, params=params)
        assert result.success
        assert result.output_format == "jpeg"


# ===== 预设尺寸测试 =====

class TestPresets:
    """预设尺寸测试。"""

    def test_preset_id_1inch(self, resizer, sample_png):
        """一寸证件照预设。"""
        result = resizer.resize_by_preset(sample_png, "id_1inch")
        assert result.success
        assert result.output_width <= 295
        assert result.output_height <= 413

    def test_preset_id_2inch(self, resizer, sample_png):
        """二寸证件照预设。"""
        result = resizer.resize_by_preset(sample_png, "id_2inch")
        assert result.success
        assert result.output_width <= 413
        assert result.output_height <= 579

    def test_preset_print_a4_300dpi(self, resizer, sample_png):
        """A4 印刷预设。"""
        result = resizer.resize_by_preset(sample_png, "print_a4_300dpi")
        assert result.success
        assert result.output_width <= 3508
        assert result.output_height <= 2480

    def test_preset_social_square(self, resizer, sample_png):
        """社交媒体方形预设。"""
        result = resizer.resize_by_preset(sample_png, "social_square")
        assert result.success
        assert result.output_width <= 1080
        assert result.output_height <= 1080

    def test_preset_card_standard(self, resizer, sample_png):
        """名片预设。"""
        result = resizer.resize_by_preset(sample_png, "card_standard")
        assert result.success
        assert result.output_width <= 1063
        assert result.output_height <= 638

    def test_unknown_preset(self, resizer, sample_png):
        """未知预设应抛出异常。"""
        with pytest.raises(AppError) as exc_info:
            resizer.resize_by_preset(sample_png, "nonexistent_preset")
        assert "未知预设" in str(exc_info.value.message)

    def test_preset_input_via_main_resize(self, resizer, sample_png):
        """通过主 resize 方法使用 preset 参数。"""
        result = resizer.resize(sample_png, preset="photo_5inch")
        assert result.success

    def test_all_presets_work(self, resizer, sample_png):
        """遍历所有预设确保都可正常执行。"""
        for preset_name in PRINT_PRESETS:
            result = resizer.resize(sample_png, preset=preset_name)
            assert result.success, f"预设 {preset_name} 失败"
            assert result.output_data is not None
            assert len(result.output_data) > 0


# ===== 输入方式测试 =====

class TestInputMethods:
    """不同输入方式测试。"""

    def test_bytes_input(self, resizer, sample_png_bytes):
        """bytes 输入。"""
        result = resizer.resize_bytes(sample_png_bytes,
                                      params=ResizeParams(mode=ResizeMode.FIT, width=400, height=300))
        assert result.success

    def test_pil_image_input(self, resizer):
        """PIL Image 对象输入。"""
        img = create_test_image(640, 480)
        result = resizer.resize(img,
                                params=ResizeParams(mode=ResizeMode.FIT, width=320, height=240))
        assert result.success
        assert result.output_width <= 320
        assert result.output_height <= 240

    def test_file_not_found(self, resizer):
        """文件不存在应抛出异常。"""
        with pytest.raises(AppError) as exc_info:
            resizer.resize("D:\\nonexistent\\file.png")
        assert "FILE_NOT_FOUND" in exc_info.value.code.value

    def test_unsupported_format(self, resizer, tmp_path):
        """不支持的文件格式应抛出异常。"""
        file_path = os.path.join(str(tmp_path), "test.txt")
        Path(file_path).write_text("not an image")
        with pytest.raises(AppError) as exc_info:
            resizer.resize(file_path)
        assert "UNSUPPORTED" in exc_info.value.code.value

    def test_empty_bytes(self, resizer):
        """空 bytes 应抛出异常。"""
        with pytest.raises(AppError):
            resizer.resize_bytes(b"")


# ===== 文件输出测试 =====

class TestFileOutput:
    """文件输出测试。"""

    def test_output_to_file(self, resizer, sample_png, tmp_path):
        """指定输出文件路径保存。"""
        output_path = os.path.join(str(tmp_path), "output", "result.png")
        result = resizer.resize(sample_png,
                                params=ResizeParams(mode=ResizeMode.FIT, width=400, height=300),
                                output_path=output_path)
        assert result.success
        assert os.path.isfile(output_path)
        saved_data = Path(output_path).read_bytes()
        assert len(saved_data) > 0

    def test_output_to_file_auto_create_dir(self, resizer, sample_png, tmp_path):
        """输出目录不存在时自动创建。"""
        output_path = os.path.join(str(tmp_path), "deep", "nested", "dir", "result.jpg")
        result = resizer.resize(sample_png,
                                params=ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                                                    output_format=OutputFormat.JPEG),
                                output_path=output_path)
        assert result.success
        assert os.path.isfile(output_path)

    def test_output_with_jpeg_quality(self, resizer, sample_png):
        """JPEG 输出并指定质量。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              output_format=OutputFormat.JPEG, jpeg_quality=50)
        result = resizer.resize(sample_png, params=params)
        assert result.success
        assert result.output_format == "jpeg"


# ===== DPI 处理测试 =====

class TestDpiHandling:
    """DPI 处理测试。"""

    def test_output_dpi_preserved(self, resizer, tmp_path):
        """有 DPI 信息的图片输出应保留 DPI。"""
        img = create_test_image(800, 600)
        file_path = os.path.join(str(tmp_path), "test_dpi.png")
        img.save(file_path, dpi=(300, 300))

        result = resizer.resize_fit(file_path, 400, 300)
        assert result.success
        assert result.dpi is not None
        # Pillow DPI 可能有微小浮点误差，使用 approx 比较
        assert result.dpi[0] == pytest.approx(300.0, abs=0.01)
        assert result.dpi[1] == pytest.approx(300.0, abs=0.01)

    def test_output_dpi_override(self, resizer, sample_png):
        """手动指定输出 DPI。"""
        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              dpi=(150, 150))
        result = resizer.resize(sample_png, params=params)
        assert result.success
        assert result.dpi == (150.0, 150.0) or result.dpi == (150, 150)


# ===== 边缘情况测试 =====

class TestEdgeCases:
    """边缘情况测试。"""

    def test_1x1_pixel(self, resizer):
        """1×1 像素图片。"""
        data = create_test_image_bytes(1, 1, fmt="PNG")
        result = resizer.resize_scale(data, 200)
        assert result.success
        assert result.output_width == 2
        assert result.output_height == 2

    def test_very_large_image(self, resizer):
        """较大图片的处理。"""
        img = create_test_image(4000, 3000)
        result = resizer.resize_fit(img, 400, 300)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 300

    def test_rgba_image(self, resizer):
        """RGBA 图片缩放到 JPEG（应自动转为 RGB）。"""
        data = create_test_image_bytes(800, 600, fmt="PNG")
        # 创建 RGBA 图片
        img = Image.new("RGBA", (800, 600), (100, 150, 200, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        rgba_data = buf.getvalue()

        params = ResizeParams(mode=ResizeMode.FIT, width=400, height=300,
                              output_format=OutputFormat.JPEG)
        result = resizer.resize_bytes(rgba_data, params=params)
        assert result.success
        assert result.output_format == "jpeg"

    def test_ratio_display(self, resizer, sample_png):
        """验证 scale_ratio 和 ratio_display 正确。"""
        result = resizer.resize_scale(sample_png, 50)
        assert result.scale_ratio == pytest.approx(0.5, rel=0.01)
        assert "缩小" in result.ratio_display

        result2 = resizer.resize_scale(sample_png, 200)
        assert result2.scale_ratio == pytest.approx(2.0, rel=0.01)
        assert "放大" in result2.ratio_display

        result3 = resizer.resize_scale(sample_png, 100)
        assert "原始" in result3.ratio_display


# ===== 性能与资源测试 =====

class TestPerformanceAndResources:
    """性能与资源测试。"""

    def test_multiple_resizes(self, resizer, sample_png):
        """连续多次缩放应不崩溃。"""
        for i in range(10):
            result = resizer.resize_fit(sample_png, 200, 150)
            assert result.success

    def test_batch_different_presets(self, resizer, sample_png):
        """批量不同预设缩放。"""
        presets = ["id_1inch", "id_2inch", "photo_5inch", "social_square"]
        for preset in presets:
            result = resizer.resize(sample_png, preset=preset)
            assert result.success

    def test_elapsed_time_recorded(self, resizer, sample_png):
        """验证耗时被正确记录。"""
        result = resizer.resize_fit(sample_png, 200, 150)
        assert result.elapsed_ms > 0


# ===== ResizeResult 测试 =====

class TestResizeResult:
    """ResizeResult 数据结构测试。"""

    def test_default_result_not_success(self):
        """默认结果 success=False。"""
        r = ResizeResult()
        assert r.success is False

    def test_result_with_data(self):
        """带数据的结果。"""
        r = ResizeResult(
            success=True,
            source_width=800,
            source_height=600,
            output_width=400,
            output_height=300,
            mode=ResizeMode.FIT,
            scale_ratio=0.5,
            output_format="png",
            output_size=12345,
            warnings=["测试警告"],
            elapsed_ms=15.5,
        )
        assert r.success
        assert r.ratio_display == "1:2.00 (缩小)"
        d = r.to_dict()
        assert d["success"] is True
        assert d["warnings"] == ["测试警告"]


# ===== 便捷方法测试 =====

class TestConvenienceMethods:
    """便捷方法测试。"""

    def test_resize_fit_convenience(self, resizer, sample_png):
        """便捷方法 resize_fit。"""
        result = resizer.resize_fit(sample_png, 400, 300)
        assert result.success
        assert result.mode == ResizeMode.FIT

    def test_resize_exact_convenience(self, resizer, sample_png):
        """便捷方法 resize_exact。"""
        result = resizer.resize_exact(sample_png, 400, 300)
        assert result.success
        assert result.mode == ResizeMode.EXACT

    def test_resize_scale_convenience(self, resizer, sample_png):
        """便捷方法 resize_scale。"""
        result = resizer.resize_scale(sample_png, 50)
        assert result.success
        assert result.mode == ResizeMode.SCALE

    def test_resize_short_side_convenience(self, resizer, sample_png):
        """便捷方法 resize_short_side。"""
        result = resizer.resize_short_side(sample_png, 400)
        assert result.success
        assert result.mode == ResizeMode.SHORT_SIDE

    def test_resize_long_side_convenience(self, resizer, sample_png):
        """便捷方法 resize_long_side。"""
        result = resizer.resize_long_side(sample_png, 600)
        assert result.success
        assert result.mode == ResizeMode.LONG_SIDE

    def test_resize_by_preset_convenience(self, resizer, sample_png):
        """便捷方法 resize_by_preset。"""
        result = resizer.resize_by_preset(sample_png, "id_1inch")
        assert result.success
        assert result.mode == ResizeMode.FIT

    def test_resize_with_dpi_convenience(self, resizer, tmp_path):
        """便捷方法 resize_with_dpi。"""
        img = create_test_image(800, 600)
        file_path = os.path.join(str(tmp_path), "test_dpi_conv.png")
        img.save(file_path, dpi=(72, 72))

        result = resizer.resize_with_dpi(file_path, 144)
        assert result.success
        assert result.mode == ResizeMode.CUSTOM_DPI
