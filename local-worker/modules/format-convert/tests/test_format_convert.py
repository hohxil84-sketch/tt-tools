"""
local-worker/modules/format-convert/tests/test_format_convert — 格式转换模块测试

覆盖：
  - 模块导入、常量校验
  - 参数校验（FormatConvertParams / CompressParams / CropParams / RotateParams）
  - 格式转换（所有格式互转）
  - 压缩（有损/无损）
  - 裁剪（矩形/居中/锚点）
  - 旋转（直角/任意角度/expand/fillcolor）
  - 输入方式（文件/bytes/PIL Image）
  - 文件输出
  - 查询方法
  - 错误处理
  - 边缘情况

运行方式（从项目根目录，使用模块专用 venv）：
  D:/localPath/venvs/local-worker-format-convert/Scripts/python.exe -m pytest local-worker/modules/format-convert/tests/ -v
"""

import io
import os
import sys
import pytest
from pathlib import Path

# 由于模块目录名含连字符（format-convert），无法直接作为 Python 包名导入，
# 因此将模块源码目录加入 sys.path，直接导入 processor 和 specifications 模块。
_module_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_local_worker_dir = os.path.dirname(os.path.dirname(_module_src_dir))
if _module_src_dir not in sys.path:
    sys.path.insert(0, _module_src_dir)
if _local_worker_dir not in sys.path:
    sys.path.insert(0, _local_worker_dir)

from PIL import Image
from shared.errors import AppError, ErrorCode

from processor import FormatConverter
from specifications import (
    ConvertFormat,
    CropAnchor,
    RotateAngle,
    FormatConvertParams,
    CompressParams,
    CropParams,
    RotateParams,
    OperationResult,
    FORMAT_SUFFIX_MAP,
    SUPPORTED_INPUT_SUFFIXES,
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
                            mode: str = "RGB", color: tuple = (100, 150, 200)) -> bytes:
    """创建测试图片的 bytes 数据。"""
    img = create_test_image(width, height, mode=mode, color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def create_test_image_file(tmp_path, width: int = 800, height: int = 600,
                           fmt: str = "PNG", suffix: str = ".png",
                           mode: str = "RGB") -> str:
    """创建临时测试图片文件，返回文件路径。"""
    img = create_test_image(width, height, mode=mode)
    file_path = os.path.join(str(tmp_path), f"test_{width}x{height}{suffix}")
    img.save(file_path)
    return file_path


@pytest.fixture
def converter():
    """FormatConverter 实例 fixture。"""
    return FormatConverter()


@pytest.fixture
def sample_png(tmp_path):
    """创建示例 PNG 文件并返回其路径。"""
    return create_test_image_file(tmp_path, 800, 600, fmt="PNG", suffix=".png")


@pytest.fixture
def sample_jpg(tmp_path):
    """创建示例 JPG 文件并返回其路径。"""
    return create_test_image_file(tmp_path, 800, 600, fmt="JPEG", suffix=".jpg")


@pytest.fixture
def sample_bmp(tmp_path):
    """创建示例 BMP 文件并返回其路径。"""
    return create_test_image_file(tmp_path, 800, 600, fmt="BMP", suffix=".bmp")


@pytest.fixture
def sample_webp(tmp_path):
    """创建示例 WEBP 文件并返回其路径。"""
    return create_test_image_file(tmp_path, 800, 600, fmt="WEBP", suffix=".webp")


@pytest.fixture
def sample_tiff(tmp_path):
    """创建示例 TIFF 文件并返回其路径。"""
    return create_test_image_file(tmp_path, 800, 600, fmt="TIFF", suffix=".tiff")


@pytest.fixture
def sample_png_bytes():
    """创建示例 PNG bytes。"""
    return create_test_image_bytes(800, 600, fmt="PNG")


@pytest.fixture
def sample_rgba_png(tmp_path):
    """创建带透明通道的 RGBA PNG 文件。"""
    img = create_test_image(800, 600, mode="RGBA", color=(100, 150, 200, 128))
    file_path = os.path.join(str(tmp_path), "test_rgba.png")
    img.save(file_path)
    return file_path


# ===== 模块导入与常量测试 =====

class TestModuleImport:
    """模块导入和常量校验。"""

    def test_import_specifications(self):
        """验证 specifications 模块可正常导入。"""
        import specifications
        assert specifications is not None

    def test_import_processor(self):
        """验证 processor 模块可正常导入。"""
        assert FormatConverter is not None

    def test_import_all_exports(self):
        """验证所有对外导出类/枚举可正常导入。"""
        assert FormatConverter is not None
        assert ConvertFormat is not None
        assert CropAnchor is not None
        assert RotateAngle is not None
        assert FormatConvertParams is not None
        assert CompressParams is not None
        assert CropParams is not None
        assert RotateParams is not None
        assert OperationResult is not None

    def test_python_version(self):
        """验证 Python 版本 >= 3.11。"""
        assert sys.version_info >= (3, 11), f"需要 Python >= 3.11，当前: {sys.version}"

    def test_pillow_available(self):
        """验证 Pillow 已安装。"""
        import PIL
        assert PIL.__version__


class TestConstants:
    """常量和枚举测试。"""

    def test_convert_formats_count(self):
        """验证 ConvertFormat 枚举数量。"""
        assert len(ConvertFormat) == 8  # ORIGINAL + 7 formats

    def test_crop_anchors_count(self):
        """验证 CropAnchor 枚举数量。"""
        assert len(CropAnchor) == 5

    def test_rotate_angles_count(self):
        """验证 RotateAngle 枚举数量。"""
        assert len(RotateAngle) == 3

    def test_supported_input_suffixes(self):
        """验证支持的输入后缀列表。"""
        assert ".png" in SUPPORTED_INPUT_SUFFIXES
        assert ".jpg" in SUPPORTED_INPUT_SUFFIXES
        assert ".bmp" in SUPPORTED_INPUT_SUFFIXES
        assert ".tiff" in SUPPORTED_INPUT_SUFFIXES
        assert ".webp" in SUPPORTED_INPUT_SUFFIXES
        assert ".gif" in SUPPORTED_INPUT_SUFFIXES

    def test_format_suffix_map(self):
        """验证格式→后缀映射。"""
        assert FORMAT_SUFFIX_MAP[ConvertFormat.PNG] == ".png"
        assert FORMAT_SUFFIX_MAP[ConvertFormat.JPEG] == ".jpg"
        assert FORMAT_SUFFIX_MAP[ConvertFormat.BMP] == ".bmp"
        assert FORMAT_SUFFIX_MAP[ConvertFormat.TIFF] == ".tiff"
        assert FORMAT_SUFFIX_MAP[ConvertFormat.WEBP] == ".webp"
        assert FORMAT_SUFFIX_MAP[ConvertFormat.GIF] == ".gif"
        assert FORMAT_SUFFIX_MAP[ConvertFormat.ICO] == ".ico"

    def test_default_quality_values(self):
        """验证默认质量值合理。"""
        assert 1 <= DEFAULT_JPEG_QUALITY <= 100
        assert 0 <= DEFAULT_PNG_COMPRESS_LEVEL <= 9
        assert 1 <= DEFAULT_WEBP_QUALITY <= 100


# ===== 参数校验测试 =====

class TestFormatConvertParams:
    """FormatConvertParams 参数校验测试。"""

    def test_default_params_valid(self):
        """默认参数应该通过校验。"""
        params = FormatConvertParams()
        assert len(params.validate()) == 0

    def test_jpeg_quality_range(self):
        """JPEG 质量范围校验。"""
        params = FormatConvertParams(jpeg_quality=0)
        assert len(params.validate()) > 0
        params2 = FormatConvertParams(jpeg_quality=101)
        assert len(params2.validate()) > 0
        params3 = FormatConvertParams(jpeg_quality=85)
        assert len(params3.validate()) == 0

    def test_png_compress_range(self):
        """PNG 压缩级别范围校验。"""
        params = FormatConvertParams(png_compress=-1)
        assert len(params.validate()) > 0
        params2 = FormatConvertParams(png_compress=10)
        assert len(params2.validate()) > 0
        params3 = FormatConvertParams(png_compress=6)
        assert len(params3.validate()) == 0

    def test_webp_quality_range(self):
        """WEBP 质量范围校验。"""
        params = FormatConvertParams(webp_quality=101)
        assert len(params.validate()) > 0
        params2 = FormatConvertParams(webp_quality=0)
        assert len(params2.validate()) > 0


class TestCompressParams:
    """CompressParams 参数校验测试。"""

    def test_default_params_valid(self):
        """默认压缩参数有效。"""
        params = CompressParams()
        assert len(params.validate()) == 0

    def test_quality_range(self):
        """压缩质量范围。"""
        params = CompressParams(quality=0)
        assert len(params.validate()) > 0
        params2 = CompressParams(quality=101)
        assert len(params2.validate()) > 0

    def test_max_size_bytes(self):
        """max_size_bytes 校验。"""
        params = CompressParams(max_size_bytes=0)
        errors = params.validate()
        assert len(errors) > 0
        params2 = CompressParams(max_size_bytes=1000)
        assert len(params2.validate()) == 0


class TestCropParams:
    """CropParams 参数校验测试。"""

    def test_valid_params(self):
        """有效裁剪参数。"""
        params = CropParams(width=400, height=300)
        assert len(params.validate()) == 0

    def test_zero_width(self):
        """宽度为 0。"""
        params = CropParams(width=0, height=300)
        assert len(params.validate()) > 0

    def test_zero_height(self):
        """高度为 0。"""
        params = CropParams(width=400, height=0)
        assert len(params.validate()) > 0

    def test_negative_dimensions(self):
        """负尺寸。"""
        params = CropParams(width=-100, height=300)
        assert len(params.validate()) > 0

    def test_exceed_max_dimension(self):
        """超过最大尺寸限制。"""
        params = CropParams(width=MAX_OUTPUT_DIMENSION + 1, height=100)
        assert len(params.validate()) > 0


class TestRotateParams:
    """RotateParams 参数校验测试。"""

    def test_default_params_valid(self):
        """默认旋转参数有效。"""
        params = RotateParams()
        assert len(params.validate()) == 0

    def test_angle_range(self):
        """角度范围校验。"""
        params = RotateParams(angle=361)
        assert len(params.validate()) > 0
        params2 = RotateParams(angle=-361)
        assert len(params2.validate()) > 0
        params3 = RotateParams(angle=45)
        assert len(params3.validate()) == 0

    def test_fillcolor_valid(self):
        """填充颜色校验。"""
        params = RotateParams(fillcolor=(255, 0, 0))
        assert len(params.validate()) == 0

    def test_fillcolor_invalid(self):
        """无效填充颜色。"""
        params = RotateParams(fillcolor=(256, 0, 0))
        assert len(params.validate()) > 0
        params2 = RotateParams(fillcolor=(-1, 128, 128))
        assert len(params2.validate()) > 0


# ===== FormatConverter 基础测试 =====

class TestFormatConverterBasic:
    """FormatConverter 基础功能测试。"""

    def test_create_converter(self):
        """创建 FormatConverter 实例。"""
        c = FormatConverter()
        assert c is not None

    def test_supported_formats(self):
        """supported_formats 返回格式信息。"""
        fmt_info = FormatConverter.supported_formats()
        assert "input" in fmt_info
        assert "output" in fmt_info
        assert "suffix_map" in fmt_info

    def test_get_image_info(self, sample_png):
        """get_image_info 返回图片信息。"""
        info = FormatConverter.get_image_info(sample_png)
        assert info["width"] == 800
        assert info["height"] == 600
        assert info["format"] in ("PNG", "png")
        assert "mode" in info


# ===== 格式转换测试 =====

class TestFormatConversion:
    """格式转换测试（所有格式互转）。"""

    def test_png_to_jpeg(self, converter, sample_png):
        """PNG → JPEG。"""
        result = converter.convert_format(sample_png, ConvertFormat.JPEG, quality=85)
        assert result.success
        assert result.output_format == "jpeg"
        assert len(result.output_data) > 0

    def test_png_to_bmp(self, converter, sample_png):
        """PNG → BMP。"""
        result = converter.convert_format(sample_png, ConvertFormat.BMP)
        assert result.success
        assert result.output_format == "bmp"

    def test_png_to_tiff(self, converter, sample_png):
        """PNG → TIFF。"""
        result = converter.convert_format(sample_png, ConvertFormat.TIFF)
        assert result.success
        assert result.output_format == "tiff"

    def test_png_to_webp(self, converter, sample_png):
        """PNG → WEBP。"""
        result = converter.convert_format(sample_png, ConvertFormat.WEBP, webp_quality=80)
        assert result.success
        assert result.output_format == "webp"

    def test_png_to_gif(self, converter, sample_png):
        """PNG → GIF。"""
        result = converter.convert_format(sample_png, ConvertFormat.GIF)
        assert result.success
        assert result.output_format == "gif"

    def test_png_to_ico(self, converter, sample_png):
        """PNG → ICO。"""
        result = converter.convert_format(sample_png, ConvertFormat.ICO)
        assert result.success
        assert result.output_format == "ico"

    def test_jpg_to_png(self, converter, sample_jpg):
        """JPEG → PNG。"""
        result = converter.convert_format(sample_jpg, ConvertFormat.PNG)
        assert result.success
        assert result.output_format == "png"

    def test_jpg_to_webp(self, converter, sample_jpg):
        """JPEG → WEBP。"""
        result = converter.convert_format(sample_jpg, ConvertFormat.WEBP)
        assert result.success
        assert result.output_format == "webp"

    def test_bmp_to_png(self, converter, sample_bmp):
        """BMP → PNG。"""
        result = converter.convert_format(sample_bmp, ConvertFormat.PNG)
        assert result.success
        assert result.output_format == "png"

    def test_original_format(self, converter, sample_png):
        """保持原格式 ORIGINAL。"""
        result = converter.convert_format(sample_png, ConvertFormat.ORIGINAL)
        assert result.success
        assert result.output_format == "png"

    def test_original_format_jpg(self, converter, sample_jpg):
        """保持原格式（JPEG 输入）。"""
        result = converter.convert_format(sample_jpg, ConvertFormat.ORIGINAL)
        assert result.success
        assert result.output_format == "jpeg"

    def test_result_metadata(self, converter, sample_png):
        """验证结果元数据完整。"""
        result = converter.convert_format(sample_png, ConvertFormat.JPEG)
        assert result.source_width == 800
        assert result.source_height == 600
        assert result.output_width == 800
        assert result.output_height == 600
        assert result.elapsed_ms > 0
        assert result.output_data is not None

    def test_result_to_dict(self, converter, sample_png):
        """验证结果可转为字典。"""
        result = converter.convert_format(sample_png, ConvertFormat.JPEG)
        d = result.to_dict()
        assert d["success"] is True
        assert d["source_width"] == 800
        assert d["source_height"] == 600
        assert d["output_format"] == "jpeg"

    def test_rgba_to_jpeg_preserve_alpha(self, converter, sample_rgba_png):
        """RGBA PNG → JPEG 并保留透明（合成白底）。"""
        result = converter.convert_format(sample_rgba_png, ConvertFormat.JPEG, preserve_alpha=True)
        assert result.success
        assert result.output_format == "jpeg"

    def test_rgba_to_jpeg_flatten(self, converter, sample_rgba_png):
        """RGBA PNG → JPEG 不保留透明。"""
        result = converter.convert_format(sample_rgba_png, ConvertFormat.JPEG, preserve_alpha=False)
        assert result.success
        assert result.output_format == "jpeg"

    def test_webp_to_png(self, converter, sample_webp):
        """WEBP → PNG。"""
        result = converter.convert_format(sample_webp, ConvertFormat.PNG)
        assert result.success
        assert result.output_format == "png"

    def test_tiff_to_jpeg(self, converter, sample_tiff):
        """TIFF → JPEG。"""
        result = converter.convert_format(sample_tiff, ConvertFormat.JPEG)
        assert result.success
        assert result.output_format == "jpeg"

    def test_bytes_input_convert(self, converter, sample_png_bytes):
        """bytes 输入格式转换。"""
        result = converter.convert_format(sample_png_bytes, ConvertFormat.JPEG)
        assert result.success
        assert result.output_format == "jpeg"

    def test_pil_image_input(self, converter):
        """PIL Image 输入格式转换。"""
        img = create_test_image(640, 480)
        result = converter.convert_format(img, ConvertFormat.PNG)
        assert result.success
        assert result.output_format == "png"


# ===== 压缩测试 =====

class TestCompression:
    """压缩测试。"""

    def test_jpeg_compress(self, converter, sample_png):
        """JPEG 有损压缩。"""
        result = converter.compress(sample_png, quality=50, target_format=ConvertFormat.JPEG)
        assert result.success
        assert result.output_format == "jpeg"
        assert result.compression_ratio > 0

    def test_png_compress(self, converter, sample_png):
        """PNG 无损压缩（提高压缩级别）。"""
        result = converter.compress(sample_png, png_compress=9, target_format=ConvertFormat.PNG)
        assert result.success
        assert result.output_format == "png"

    def test_webp_compress(self, converter, sample_png):
        """WEBP 压缩。"""
        result = converter.compress(sample_png, quality=50, target_format=ConvertFormat.WEBP)
        assert result.success
        assert result.output_format == "webp"

    def test_low_quality_smaller(self, converter, sample_jpg):
        """低质量输出文件应更小。"""
        result_high = converter.compress(sample_jpg, quality=95, target_format=ConvertFormat.JPEG)
        result_low = converter.compress(sample_jpg, quality=10, target_format=ConvertFormat.JPEG)
        assert result_high.success and result_low.success
        # 低质量应输出更小的文件
        assert result_low.output_size < result_high.output_size, (
            f"q10 size={result_low.output_size} >= q95 size={result_high.output_size}"
        )

    def test_max_size_bytes(self, converter, sample_png):
        """指定 max_size_bytes 应尝试减小文件。"""
        # 先获取不压缩的输出大小
        ref = converter.convert_format(sample_png, ConvertFormat.JPEG, quality=95)
        target_size = ref.output_size // 2  # 目标为一半
        result = converter.compress(
            sample_png, quality=95, target_format=ConvertFormat.JPEG,
            max_size_bytes=target_size,
        )
        assert result.success
        # 结果不应超过原大小太多
        assert result.output_size <= ref.output_size

    def test_compression_ratio(self, converter, sample_png):
        """压缩比应在合理范围。"""
        result = converter.compress(sample_png, quality=50, target_format=ConvertFormat.JPEG)
        assert result.compression_ratio > 0
        assert result.compression_ratio < 2.0  # 通常不应超过 2x

    def test_bytes_input_compress(self, converter, sample_png_bytes):
        """bytes 输入压缩。"""
        result = converter.compress(sample_png_bytes, quality=70, target_format=ConvertFormat.JPEG)
        assert result.success

    def test_original_format_compress(self, converter, sample_jpg):
        """保持原格式压缩。"""
        result = converter.compress(sample_jpg, quality=40)
        assert result.success


# ===== 裁剪测试 =====

class TestCropping:
    """裁剪测试。"""

    def test_basic_crop(self, converter, sample_png):
        """基本矩形裁剪。"""
        result = converter.crop(sample_png, left=100, top=50, width=400, height=300)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 300

    def test_crop_from_origin(self, converter, sample_png):
        """从原点 (0,0) 裁剪。"""
        result = converter.crop(sample_png, left=0, top=0, width=200, height=200)
        assert result.success
        assert result.output_width == 200
        assert result.output_height == 200

    def test_crop_full_image(self, converter, sample_png):
        """裁剪整张图片（区域=原图大小）。"""
        result = converter.crop(sample_png, left=0, top=0, width=800, height=600)
        assert result.success
        assert result.output_width == 800
        assert result.output_height == 600

    def test_crop_center(self, converter, sample_png):
        """居中裁剪。"""
        result = converter.crop_center(sample_png, 400, 300)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 300

    def test_crop_by_anchor_center(self, converter, sample_png):
        """锚点居中裁剪。"""
        result = converter.crop_by_anchor(sample_png, 400, 300, CropAnchor.CENTER)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 300

    def test_crop_by_anchor_top_left(self, converter, sample_png):
        """锚点左上角裁剪。"""
        result = converter.crop_by_anchor(sample_png, 400, 300, CropAnchor.TOP_LEFT)
        assert result.success
        assert result.output_width == 400
        assert result.output_height == 300

    def test_crop_by_anchor_top_right(self, converter, sample_png):
        """锚点右上角裁剪。"""
        result = converter.crop_by_anchor(sample_png, 400, 300, CropAnchor.TOP_RIGHT)
        assert result.success

    def test_crop_by_anchor_bottom_left(self, converter, sample_png):
        """锚点左下角裁剪。"""
        result = converter.crop_by_anchor(sample_png, 400, 300, CropAnchor.BOTTOM_LEFT)
        assert result.success

    def test_crop_by_anchor_bottom_right(self, converter, sample_png):
        """锚点右下角裁剪。"""
        result = converter.crop_by_anchor(sample_png, 400, 300, CropAnchor.BOTTOM_RIGHT)
        assert result.success

    def test_crop_out_of_bounds_right(self, converter, sample_png):
        """裁剪超出右边界应报错。"""
        with pytest.raises(AppError) as exc_info:
            converter.crop(sample_png, left=700, top=0, width=200, height=200)
        assert "超出" in str(exc_info.value.message) or "right" in str(exc_info.value.details).lower()

    def test_crop_out_of_bounds_bottom(self, converter, sample_png):
        """裁剪超出下边界应报错。"""
        with pytest.raises(AppError) as exc_info:
            converter.crop(sample_png, left=0, top=500, width=200, height=200)
        assert "超出" in str(exc_info.value.message) or "bottom" in str(exc_info.value.details).lower()

    def test_crop_output_size(self, converter, sample_png):
        """验证裁剪输出数据有效。"""
        result = converter.crop(sample_png, left=0, top=0, width=100, height=100)
        assert result.output_data is not None
        assert len(result.output_data) > 0
        # 验证输出图片尺寸
        img = Image.open(io.BytesIO(result.output_data))
        assert img.size == (100, 100)

    def test_crop_bytes_input(self, converter, sample_png_bytes):
        """bytes 输入裁剪。"""
        result = converter.crop(sample_png_bytes, left=50, top=50, width=200, height=150)
        assert result.success
        assert result.output_width == 200
        assert result.output_height == 150


# ===== 旋转测试 =====

class TestRotation:
    """旋转测试。"""

    def test_rotate_90(self, converter, sample_png):
        """顺时针旋转 90°。"""
        result = converter.rotate(sample_png, 90)
        assert result.success
        # 90° 旋转后宽高互换
        assert result.output_width == 600
        assert result.output_height == 800

    def test_rotate_180(self, converter, sample_png):
        """旋转 180°。"""
        result = converter.rotate(sample_png, 180)
        assert result.success
        assert result.output_width == 800
        assert result.output_height == 600

    def test_rotate_270(self, converter, sample_png):
        """旋转 270°。"""
        result = converter.rotate(sample_png, 270)
        assert result.success
        assert result.output_width == 600
        assert result.output_height == 800

    def test_rotate_0(self, converter, sample_png):
        """旋转 0°（不变）。"""
        result = converter.rotate(sample_png, 0)
        assert result.success
        assert result.output_width == 800
        assert result.output_height == 600

    def test_rotate_360(self, converter, sample_png):
        """旋转 360°（归一化到 0°）。"""
        result = converter.rotate(sample_png, 360)
        assert result.success
        assert result.output_width == 800
        assert result.output_height == 600

    def test_rotate_arbitrary_expand(self, converter, sample_png):
        """任意角度旋转 + expand=True（画布变大）。"""
        result = converter.rotate(sample_png, 45, expand=True)
        assert result.success
        # expand=True 时画布应比原图大
        assert result.output_width > 800 or result.output_height > 600

    def test_rotate_arbitrary_no_expand(self, converter, sample_png):
        """任意角度旋转 + expand=False（画布不变）。"""
        result = converter.rotate(sample_png, 45, expand=False)
        assert result.success
        assert result.output_width == 800
        assert result.output_height == 600

    def test_rotate_negative_angle(self, converter, sample_png):
        """负角度旋转（逆时针）。"""
        result = converter.rotate(sample_png, -45)
        assert result.success
        assert result.output_width > 0
        assert result.output_height > 0

    def test_rotate_custom_fillcolor(self, converter, sample_png):
        """自定义填充颜色旋转。"""
        result = converter.rotate(sample_png, 45, fillcolor=(255, 0, 0))
        assert result.success

    def test_rotate_bytes_input(self, converter, sample_png_bytes):
        """bytes 输入旋转。"""
        result = converter.rotate(sample_png_bytes, 90)
        assert result.success
        assert result.output_width == 600
        assert result.output_height == 800


# ===== 文件输出测试 =====

class TestFileOutput:
    """文件输出测试。"""

    def test_convert_output_to_file(self, converter, sample_png, tmp_path):
        """格式转换并保存到文件。"""
        output_path = os.path.join(str(tmp_path), "output", "converted.jpg")
        result = converter.convert_format(sample_png, ConvertFormat.JPEG, output_path=output_path)
        assert result.success
        assert os.path.isfile(output_path)

    def test_compress_output_to_file(self, converter, sample_png, tmp_path):
        """压缩并保存到文件。"""
        output_path = os.path.join(str(tmp_path), "compressed.jpg")
        result = converter.compress(sample_png, quality=60, output_path=output_path)
        assert result.success
        assert os.path.isfile(output_path)

    def test_crop_output_to_file(self, converter, sample_png, tmp_path):
        """裁剪并保存到文件。"""
        output_path = os.path.join(str(tmp_path), "cropped.png")
        result = converter.crop(sample_png, left=0, top=0, width=200, height=200,
                                output_path=output_path)
        assert result.success
        assert os.path.isfile(output_path)

    def test_rotate_output_to_file(self, converter, sample_png, tmp_path):
        """旋转并保存到文件。"""
        output_path = os.path.join(str(tmp_path), "rotated.png")
        result = converter.rotate(sample_png, 90, output_path=output_path)
        assert result.success
        assert os.path.isfile(output_path)

    def test_auto_create_dir(self, converter, sample_png, tmp_path):
        """自动创建不存在的输出目录。"""
        output_path = os.path.join(str(tmp_path), "deep", "nested", "path", "out.png")
        result = converter.convert_format(sample_png, ConvertFormat.PNG, output_path=output_path)
        assert result.success
        assert os.path.isfile(output_path)


# ===== 错误处理测试 =====

class TestErrorHandling:
    """错误处理测试。"""

    def test_file_not_found(self, converter):
        """文件不存在应抛出异常。"""
        with pytest.raises(AppError) as exc_info:
            converter.convert_format("D:\\nonexistent\\file.png", ConvertFormat.PNG)
        assert "FILE_NOT_FOUND" in exc_info.value.code.value

    def test_unsupported_format(self, converter, tmp_path):
        """不支持的文件格式应抛出异常。"""
        file_path = os.path.join(str(tmp_path), "test.txt")
        Path(file_path).write_text("not an image")
        with pytest.raises(AppError) as exc_info:
            converter.convert_format(file_path, ConvertFormat.PNG)
        assert "UNSUPPORTED" in exc_info.value.code.value or "UNSUPPORTED" in exc_info.value.code.value

    def test_empty_bytes(self, converter):
        """空 bytes 应抛出异常。"""
        with pytest.raises(AppError):
            converter.convert_format(b"", ConvertFormat.PNG)

    def test_invalid_input_type(self, converter):
        """无效输入类型应抛出异常。"""
        with pytest.raises(AppError):
            converter.convert_format(12345, ConvertFormat.PNG)  # type: ignore

    def test_crop_negative_left(self, converter, sample_png):
        """裁剪左边界为负应报错。"""
        with pytest.raises(AppError) as exc_info:
            converter.crop(sample_png, left=-10, top=0, width=100, height=100)
        # 负值应报错
        assert exc_info.value.code in (ErrorCode.INVALID_ARGUMENT, ErrorCode.INTERNAL)


# ===== 边缘情况测试 =====

class TestEdgeCases:
    """边缘情况测试。"""

    def test_small_image(self, converter):
        """极小图片（1×1）。"""
        data = create_test_image_bytes(1, 1, fmt="PNG")
        result = converter.convert_format(data, ConvertFormat.JPEG)
        assert result.success

    def test_large_crop(self, converter, sample_png):
        """裁剪整个图片。"""
        result = converter.crop(sample_png, left=0, top=0, width=800, height=600)
        assert result.success

    def test_multiple_conversions(self, converter, sample_png):
        """连续多次转换不崩溃。"""
        for _ in range(5):
            result = converter.convert_format(sample_png, ConvertFormat.JPEG)
            assert result.success

    def test_rgba_to_jpeg_output_valid(self, converter, sample_rgba_png):
        """RGBA 转 JPEG 后输出为有效图片。"""
        result = converter.convert_format(sample_rgba_png, ConvertFormat.JPEG)
        assert result.success
        img = Image.open(io.BytesIO(result.output_data))
        assert img.format == "JPEG"
        assert img.mode == "RGB"  # 不应有 alpha

    def test_elapsed_time_recorded(self, converter, sample_png):
        """验证耗时被正确记录。"""
        result = converter.convert_format(sample_png, ConvertFormat.JPEG)
        assert result.elapsed_ms > 0

    def test_png_compress_level_effect(self, converter, sample_png):
        """PNG 压缩级别对文件大小的影响。"""
        r_low = converter.compress(sample_png, png_compress=0, target_format=ConvertFormat.PNG)
        r_high = converter.compress(sample_png, png_compress=9, target_format=ConvertFormat.PNG)
        assert r_low.success and r_high.success


# ===== OperationResult 测试 =====

class TestOperationResult:
    """OperationResult 数据结构测试。"""

    def test_default_result_not_success(self):
        """默认结果 success=False。"""
        r = OperationResult()
        assert r.success is False

    def test_result_with_data(self):
        """带数据的结果。"""
        r = OperationResult(
            success=True,
            source_width=800,
            source_height=600,
            output_width=400,
            output_height=300,
            output_format="jpeg",
            output_size=12345,
            compression_ratio=0.5,
            warnings=["测试警告"],
            elapsed_ms=15.5,
        )
        assert r.success
        d = r.to_dict()
        assert d["success"] is True
        assert d["warnings"] == ["测试警告"]
        assert d["compression_ratio"] == 0.5


# ===== get_image_info 测试 =====

class TestGetImageInfo:
    """get_image_info 测试。"""

    def test_file_info(self, sample_png):
        """获取文件图片信息。"""
        info = FormatConverter.get_image_info(sample_png)
        assert info["width"] == 800
        assert info["height"] == 600

    def test_bytes_info(self, sample_png_bytes):
        """获取 bytes 图片信息。"""
        info = FormatConverter.get_image_info(sample_png_bytes)
        assert info["width"] == 800
        assert info["height"] == 600

    def test_info_invalid_type(self):
        """无效输入类型。"""
        with pytest.raises(AppError):
            FormatConverter.get_image_info(12345)  # type: ignore

    def test_file_not_found(self):
        """文件不存在。"""
        with pytest.raises(AppError):
            FormatConverter.get_image_info("D:\\nonexistent\\x.png")
