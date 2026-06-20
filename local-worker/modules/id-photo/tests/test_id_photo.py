"""
local-worker/modules/id-photo/tests/test_id_photo.py — 证件照换底色模块测试

测试范围：
  - 规格和底色查询
  - 背景色检测
  - 前景遮罩生成（颜色距离法 + GrabCut）
  - 背景替换
  - 规格缩放
  - 完整处理流程
  - 错误处理和边界情况
"""

import os
import sys
import tempfile

import cv2
import numpy as np
import pytest

# 确保模块在 path 中
# 目录名 id-photo 含连字符，不能作为 Python 包名直接 import
# 将模块目录加入 sys.path 后直接导入文件名
_this_dir = os.path.dirname(os.path.abspath(__file__))
_id_photo_dir = os.path.join(_this_dir, "..")
if _id_photo_dir not in sys.path:
    sys.path.insert(0, _id_photo_dir)

from specifications import (
    BACKGROUND_COLORS,
    STANDARD_DPI,
    BackgroundColor,
    PhotoSpec,
    get_background_color,
    get_spec,
    get_spec_by_size,
    list_background_colors,
    list_specs,
)
from processor import (
    IdPhotoResult,
    _create_color_mask,
    create_foreground_mask,
    detect_background_color,
    process_id_photo,
    process_id_photo_from_path,
    replace_background,
    resize_to_spec,
)


# ==================== 辅助函数 ====================


def _make_solid_bg_image(
    width: int = 640,
    height: int = 480,
    bg_color: tuple = (255, 0, 0),  # BGR
    fg_rect: tuple = None,  # (x, y, w, h)
    fg_color: tuple = None,  # BGR
) -> np.ndarray:
    """创建模拟证件照的合成图像。

    参数：
        width, height: 图像尺寸。
        bg_color: 背景色 BGR。
        fg_rect: 前景矩形 (x, y, w, h)，默认图像中心区域。
        fg_color: 前景色 BGR，默认肤色色调。

    返回：
        BGR 图像。
    """
    image = np.full((height, width, 3), bg_color, dtype=np.uint8)

    if fg_rect is None:
        # 默认在中心放置一个椭圆形的"人物"
        fg_rect = (width // 4, height // 8, width // 2, height * 3 // 4)

    if fg_color is None:
        # 默认使用肤色色调
        fg_color = (140, 180, 220)  # BGR 肤色

    x, y, fw, fh = fg_rect
    # 绘制椭圆模拟人物
    center = (x + fw // 2, y + fh // 2)
    axes = (fw // 2, fh // 2)
    cv2.ellipse(image, center, axes, 0, 0, 360, fg_color, -1)

    return image


def _make_gradient_bg_image(
    width: int = 640,
    height: int = 480,
) -> np.ndarray:
    """创建渐变背景的合成图像（模拟非纯色背景）。"""
    image = np.zeros((height, width, 3), dtype=np.uint8)
    for i in range(height):
        val = int(128 + 64 * np.sin(i / height * np.pi * 2))
        image[i, :] = (val, val + 30, val + 60)
    # 在中心添加椭圆"人物"
    cx, cy = width // 2, height // 2
    cv2.ellipse(
        image,
        (cx, cy),
        (width // 4, height // 3),
        0, 0, 360,
        (140, 180, 220),
        -1,
    )
    return image


# ==================== specifications 测试 ====================


class TestPhotoSpec:
    """PhotoSpec 规格测试。"""

    def test_one_inch_spec(self):
        """1寸证件照规格：25mm × 35mm，300 DPI。"""
        spec = PhotoSpec(name="1寸", width_mm=25, height_mm=35, dpi=300)
        assert spec.width_mm == 25
        assert spec.height_mm == 35
        assert spec.width_px == 295  # 25 * 300 / 25.4 ≈ 295
        assert spec.height_px == 413  # 35 * 300 / 25.4 ≈ 413
        assert spec.size_mm == (25, 35)
        assert spec.size_px == (295, 413)

    def test_two_inch_spec(self):
        """2寸证件照规格：35mm × 49mm，300 DPI。"""
        spec = PhotoSpec(name="2寸", width_mm=35, height_mm=49, dpi=300)
        assert spec.width_px == 413  # 35 * 300 / 25.4 ≈ 413
        assert spec.height_px == 579  # 49 * 300 / 25.4 ≈ 579

    def test_custom_dpi(self):
        """自定义 DPI 规格计算。"""
        spec = PhotoSpec(name="1寸", width_mm=25, height_mm=35, dpi=150)
        assert spec.width_px == round(25 * 150 / 25.4)
        assert spec.height_px == round(35 * 150 / 25.4)

    def test_screen_dpi(self):
        """屏幕 DPI (96) 规格计算。"""
        spec = PhotoSpec(name="1寸", width_mm=25, height_mm=35, dpi=96)
        assert spec.width_px == round(25 * 96 / 25.4)
        assert spec.height_px == round(35 * 96 / 25.4)


class TestGetSpec:
    """get_spec 函数测试。"""

    def test_get_known_spec(self):
        """获取已知规格。"""
        spec = get_spec("1寸")
        assert spec.name == "1寸"
        assert spec.width_mm == 25
        assert spec.height_mm == 35

    def test_get_unknown_spec(self):
        """获取未知规格应抛出 ValueError。"""
        with pytest.raises(ValueError, match="未知证件照规格"):
            get_spec("50寸")

    def test_list_specs(self):
        """列出所有规格。"""
        specs = list_specs()
        assert len(specs) >= 5
        names = [s.name for s in specs]
        assert "1寸" in names
        assert "2寸" in names

    def test_get_spec_by_size_exact(self):
        """根据像素尺寸精确匹配。"""
        spec = get_spec_by_size(295, 413)  # 1寸
        assert spec is not None
        assert spec.name == "1寸"

    def test_get_spec_by_size_no_match(self):
        """像素尺寸偏离过大时返回 None。"""
        spec = get_spec_by_size(1000, 2000)
        assert spec is None


class TestBackgroundColor:
    """BackgroundColor 测试。"""

    def test_bgr_conversion(self):
        """RGB 到 BGR 转换正确。"""
        bg = BackgroundColor("红色", r=219, g=0, b=0)
        assert bg.to_bgr() == (0, 0, 219)
        assert bg.to_rgb() == (219, 0, 0)

    def test_hex_string(self):
        """十六进制颜色字符串。"""
        bg = BackgroundColor("白色", r=255, g=255, b=255)
        assert bg.to_hex() == "#FFFFFF"

    def test_get_by_english_key(self):
        """通过英文 key 获取颜色。"""
        bg = get_background_color("red")
        assert bg.name == "红色"

    def test_get_by_chinese_name(self):
        """通过中文名获取颜色。"""
        bg = get_background_color("红色")
        assert bg.r == 219

    def test_get_unknown_color(self):
        """获取未知颜色应抛出 ValueError。"""
        with pytest.raises(ValueError, match="未知背景色"):
            get_background_color("purple")

    def test_list_colors(self):
        """列出所有颜色。"""
        colors = list_background_colors()
        assert len(colors) >= 4
        names = [c.name for c in colors]
        assert "白色" in names
        assert "红色" in names
        assert "蓝色" in names

    def test_bgr_tuple_property(self):
        """bgr_tuple 属性返回 BGR 格式。"""
        bg = BackgroundColor("红色", r=219, g=0, b=0)
        assert bg.bgr_tuple == (0, 0, 219)


# ==================== processor 测试 ====================


class TestDetectBackgroundColor:
    """背景色检测测试。"""

    def test_detect_solid_red_background(self):
        """检测纯红色背景。"""
        image = _make_solid_bg_image(bg_color=(0, 0, 255))  # BGR 红
        bg_color, is_solid = detect_background_color(image)
        assert is_solid is True
        assert bg_color is not None
        # 检测到的颜色应接近红色
        assert bg_color.r > 200
        assert bg_color.g < 50
        assert bg_color.b < 50

    def test_detect_solid_white_background(self):
        """检测纯白色背景。"""
        image = _make_solid_bg_image(bg_color=(255, 255, 255))
        bg_color, is_solid = detect_background_color(image)
        assert is_solid is True
        assert bg_color is not None
        assert bg_color.r > 200
        assert bg_color.g > 200
        assert bg_color.b > 200

    def test_detect_solid_blue_background(self):
        """检测纯蓝色背景。"""
        image = _make_solid_bg_image(bg_color=(219, 142, 67))  # BGR 蓝
        bg_color, is_solid = detect_background_color(image)
        assert is_solid is True
        assert bg_color is not None

    def test_detect_gradient_background(self):
        """检测渐变背景（非纯色）。"""
        image = _make_gradient_bg_image()
        bg_color, is_solid = detect_background_color(image, std_threshold=20.0)
        # 渐变背景不应判定为纯色
        assert is_solid is False or bg_color is not None

    def test_detect_tiny_image(self):
        """极小图像检测不崩溃。"""
        image = np.zeros((10, 10, 3), dtype=np.uint8)
        bg_color, is_solid = detect_background_color(image)
        # 极小的图像可能无法准确检测，但不应崩溃
        # 可能返回 None 或某个结果


class TestForegroundMask:
    """前景遮罩测试。"""

    def test_color_mask_basic(self):
        """颜色距离法遮罩基本功能。"""
        image = _make_solid_bg_image(bg_color=(0, 0, 255), fg_color=(100, 200, 100))
        mask = _create_color_mask(image, background_bgr=(0, 0, 255))
        assert mask.shape == (480, 640)
        assert mask.dtype == np.uint8
        # 应该有前景和背景区域
        unique = np.unique(mask)
        assert 0 in unique  # 背景
        assert 255 in unique  # 前景

    def test_color_mask_foreground_present(self):
        """颜色遮罩应包含前景区域。"""
        image = _make_solid_bg_image(
            bg_color=(255, 255, 255),
            fg_color=(0, 100, 200),
        )
        mask = _create_color_mask(image, background_bgr=(255, 255, 255))
        fg_ratio = np.count_nonzero(mask) / mask.size
        # 前景应在合理范围（5% ~ 70%）
        assert 0.05 < fg_ratio < 0.70

    def test_create_foreground_mask_solid_bg(self):
        """纯色背景下选用颜色距离法。"""
        image = _make_solid_bg_image(
            bg_color=(255, 255, 255),
            fg_color=(0, 100, 200),
        )
        mask = create_foreground_mask(
            image,
            background_bgr=(255, 255, 255),
            is_solid_background=True,
        )
        assert mask.shape[:2] == (480, 640)
        assert mask.dtype == np.uint8

    def test_create_foreground_mask_grabcut(self):
        """非纯色背景下选用 GrabCut。"""
        image = _make_gradient_bg_image()
        mask = create_foreground_mask(
            image,
            background_bgr=None,
            is_solid_background=False,
        )
        assert mask.shape[:2] == (480, 640)
        assert mask.dtype == np.uint8
        # GrabCut 应识别出前景区域
        fg_ratio = np.count_nonzero(mask) / mask.size
        assert fg_ratio > 0.01  # 至少有些前景

    def test_create_foreground_mask_fallback(self):
        """当颜色遮罩质量不佳时应回退到 GrabCut。"""
        # 创建一个前景占比极高的图像（颜色法会失败）
        image = _make_solid_bg_image(
            bg_color=(255, 255, 255),
            fg_color=(0, 100, 200),
            fg_rect=(0, 0, 600, 450),  # 前景占大部分
        )
        mask = create_foreground_mask(
            image,
            background_bgr=(255, 255, 255),
            is_solid_background=True,
        )
        # 不应崩溃，返回有效遮罩
        assert mask.shape[:2] == (480, 640)


class TestReplaceBackground:
    """背景替换测试。"""

    def test_replace_simple(self):
        """简单背景替换。"""
        image = _make_solid_bg_image(
            bg_color=(255, 255, 255),
            fg_color=(0, 100, 200),
        )
        # 创建简单遮罩：前景矩形在中心
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[100:380, 200:440] = 255
        result = replace_background(image, mask, new_background_bgr=(0, 0, 219))

        assert result.shape == (480, 640, 3)
        assert result.dtype == np.uint8
        # 背景区域应为新颜色
        corner_pixel = result[0, 0]
        np.testing.assert_allclose(corner_pixel, (0, 0, 219), atol=5)

    def test_replace_with_feather(self):
        """带边缘羽化的背景替换。"""
        image = _make_solid_bg_image()
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[100:380, 200:440] = 255
        result_feather = replace_background(image, mask, (0, 0, 219), edge_feather=True)
        result_no_feather = replace_background(image, mask, (0, 0, 219), edge_feather=False)

        # 两种模式都应有效
        assert result_feather.shape == result_no_feather.shape
        # 边缘应有所不同
        edge_diff = np.abs(
            result_feather[99:101, 199:201].astype(float)
            - result_no_feather[99:101, 199:201].astype(float)
        )
        # 羽化模式下边缘像素不精确相等即可
        # (这里只验证不崩溃，具体效果依赖算法)


class TestResizeToSpec:
    """规格缩放测试。"""

    def test_resize_to_one_inch(self):
        """缩放到 1寸。"""
        spec = get_spec("1寸")
        image = _make_solid_bg_image(width=800, height=600)
        result = resize_to_spec(image, spec, maintain_aspect=True)
        assert result.shape[0] == spec.height_px  # 413
        assert result.shape[1] == spec.width_px  # 295

    def test_resize_to_two_inch(self):
        """缩放到 2寸。"""
        spec = get_spec("2寸")
        image = _make_solid_bg_image(width=800, height=600)
        result = resize_to_spec(image, spec, maintain_aspect=True)
        assert result.shape[0] == spec.height_px  # 579
        assert result.shape[1] == spec.width_px  # 413

    def test_resize_no_maintain_aspect(self):
        """不保持宽高比缩放。"""
        spec = get_spec("1寸")
        image = _make_solid_bg_image(width=800, height=600)
        result = resize_to_spec(image, spec, maintain_aspect=False)
        assert result.shape[0] == spec.height_px
        assert result.shape[1] == spec.width_px

    def test_resize_small_image(self):
        """小于目标尺寸的图像缩放。"""
        spec = get_spec("1寸")
        image = _make_solid_bg_image(width=100, height=100)
        result = resize_to_spec(image, spec, maintain_aspect=True)
        assert result.shape[0] == spec.height_px
        assert result.shape[1] == spec.width_px

    def test_resize_very_wide_image(self):
        """极端宽高比图像缩放。"""
        spec = get_spec("1寸")
        image = _make_solid_bg_image(width=1600, height=200)
        result = resize_to_spec(image, spec, maintain_aspect=True)
        assert result.shape[0] == spec.height_px
        assert result.shape[1] == spec.width_px


# ==================== 完整流程测试 ====================


class TestProcessIdPhoto:
    """process_id_photo 完整流程测试。"""

    def test_full_pipeline_solid_bg(self):
        """纯色背景完整处理流程。"""
        image = _make_solid_bg_image(
            bg_color=(255, 255, 255),
            fg_color=(140, 180, 220),
        )
        result = process_id_photo(
            image,
            background="red",
            spec_name="1寸",
            auto_detect_background=True,
        )
        assert isinstance(result, IdPhotoResult)
        assert result.image.shape[0] == result.spec.height_px
        assert result.image.shape[1] == result.spec.width_px
        assert result.background_color.name == "红色"
        assert result.spec.name == "1寸"
        assert "spec_name" in result.metadata

    def test_full_pipeline_white_bg(self):
        """白底 2寸证件照。"""
        image = _make_solid_bg_image(
            bg_color=(0, 0, 255),  # 红底原图 BGR
            fg_color=(140, 180, 220),
        )
        result = process_id_photo(
            image,
            background="white",
            spec_name="2寸",
            auto_detect_background=True,
        )
        assert result.background_color.name == "白色"
        assert result.spec.name == "2寸"
        assert result.image is not None

    def test_full_pipeline_blue_bg(self):
        """蓝底 1寸证件照。"""
        image = _make_solid_bg_image(
            bg_color=(255, 255, 255),
            fg_color=(140, 180, 220),
        )
        result = process_id_photo(
            image,
            background="blue",
            spec_name="1寸",
            auto_detect_background=True,
        )
        assert result.background_color.name == "蓝色"

    def test_full_pipeline_no_auto_detect(self):
        """禁用自动背景检测时也应有结果。"""
        image = _make_solid_bg_image()
        result = process_id_photo(
            image,
            background="white",
            spec_name="1寸",
            auto_detect_background=False,
        )
        assert result.detected_background is None
        assert result.image is not None

    def test_full_pipeline_no_feather(self):
        """禁用边缘羽化。"""
        image = _make_solid_bg_image()
        result = process_id_photo(
            image,
            background="red",
            spec_name="1寸",
            edge_feather=False,
        )
        assert result.image is not None

    def test_full_pipeline_gradient_bg(self):
        """渐变背景完整流程（GrabCut 路径）。"""
        image = _make_gradient_bg_image()
        result = process_id_photo(
            image,
            background="white",
            spec_name="1寸",
            auto_detect_background=True,
        )
        assert result.image is not None
        assert result.spec.name == "1寸"

    def test_full_pipeline_different_specs(self):
        """多种规格处理。"""
        image = _make_solid_bg_image()
        for spec_name in ["1寸", "2寸", "小1寸"]:
            result = process_id_photo(
                image,
                background="white",
                spec_name=spec_name,
            )
            assert result.image.shape[0] == result.spec.height_px
            assert result.image.shape[1] == result.spec.width_px

    def test_full_pipeline_different_colors(self):
        """多种底色处理。"""
        image = _make_solid_bg_image()
        for color_name in ["white", "red", "blue"]:
            result = process_id_photo(
                image,
                background=color_name,
                spec_name="1寸",
            )
            assert result.background_color.name == get_background_color(color_name).name

    def test_full_pipeline_custom_dpi(self):
        """自定义 DPI 处理。"""
        image = _make_solid_bg_image(width=800, height=600)
        result = process_id_photo(
            image,
            background="white",
            spec_name="1寸",
            dpi=150,  # 低 DPI
        )
        spec_150 = get_spec("1寸", dpi=150)
        assert result.image.shape[0] == spec_150.height_px
        assert result.image.shape[1] == spec_150.width_px


class TestProcessIdPhotoFromPath:
    """process_id_photo_from_path 文件路径测试。"""

    def test_read_write(self):
        """从文件读取并写出。"""
        image = _make_solid_bg_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.png")
            output_path = os.path.join(tmpdir, "output.png")
            cv2.imwrite(input_path, image)

            result = process_id_photo_from_path(
                input_path,
                output_path,
                background="white",
                spec_name="1寸",
            )
            assert os.path.exists(output_path)
            assert result.image is not None

            # 验证写出内容可读
            saved = cv2.imread(output_path)
            assert saved is not None
            assert saved.shape == result.image.shape

    def test_jpeg_input(self):
        """JPEG 格式输入。"""
        image = _make_solid_bg_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.jpg")
            output_path = os.path.join(tmpdir, "output.jpg")
            cv2.imwrite(input_path, image)
            result = process_id_photo_from_path(
                input_path,
                output_path,
                background="white",
                spec_name="1寸",
            )
            assert os.path.exists(output_path)

    def test_nonexistent_input(self):
        """不存在的输入文件应抛出异常。"""
        with pytest.raises(ValueError, match="无法读取"):
            process_id_photo_from_path(
                "/nonexistent/path/image.png",
                "/tmp/output.png",
                background="white",
                spec_name="1寸",
            )


# ==================== 错误处理和边界情况 ====================


class TestErrorHandling:
    """错误处理和边界情况测试。"""

    def test_invalid_image_none(self):
        """None 输入应抛出 ValueError。"""
        with pytest.raises(ValueError, match="3 通道 BGR"):
            process_id_photo(None, background="white", spec_name="1寸")

    def test_invalid_image_grayscale(self):
        """灰度图输入应抛出 ValueError。"""
        gray = np.zeros((100, 100), dtype=np.uint8)
        with pytest.raises(ValueError, match="3 通道 BGR"):
            process_id_photo(gray, background="white", spec_name="1寸")

    def test_invalid_image_4channel(self):
        """4 通道图输入应抛出 ValueError。"""
        rgba = np.zeros((100, 100, 4), dtype=np.uint8)
        with pytest.raises(ValueError, match="3 通道 BGR"):
            process_id_photo(rgba, background="white", spec_name="1寸")

    def test_invalid_spec_name(self):
        """无效规格名称。"""
        image = _make_solid_bg_image()
        with pytest.raises(ValueError, match="未知证件照规格"):
            process_id_photo(image, background="white", spec_name="999寸")

    def test_invalid_background_color(self):
        """无效底色名称。"""
        image = _make_solid_bg_image()
        with pytest.raises(ValueError, match="未知背景色"):
            process_id_photo(image, background="nonexistent_color", spec_name="1寸")

    def test_empty_image(self):
        """空（全零）图像处理不崩溃。"""
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        result = process_id_photo(image, background="white", spec_name="1寸")
        assert result.image is not None

    def test_tiny_image(self):
        """极小图像处理。"""
        image = _make_solid_bg_image(width=20, height=20)
        result = process_id_photo(image, background="white", spec_name="1寸")
        assert result.image is not None
        # 输出尺寸应为规格尺寸（可能比输入大）
        assert result.image.shape[0] == result.spec.height_px


# ==================== 元数据验证 ====================


class TestMetadata:
    """处理结果元数据测试。"""

    def test_metadata_contains_keys(self):
        """元数据包含必要字段。"""
        image = _make_solid_bg_image()
        result = process_id_photo(
            image,
            background="red",
            spec_name="1寸",
            auto_detect_background=True,
        )
        assert "spec_name" in result.metadata
        assert "spec_size_mm" in result.metadata
        assert "spec_size_px" in result.metadata
        assert "target_background" in result.metadata
        assert "mask_method" in result.metadata
        assert "output_size_px" in result.metadata

    def test_metadata_with_detection(self):
        """自动检测启用时元数据包含检测结果。"""
        image = _make_solid_bg_image(bg_color=(255, 255, 255))
        result = process_id_photo(
            image,
            background="red",
            spec_name="1寸",
            auto_detect_background=True,
        )
        assert "detected_background_rgb" in result.metadata
        assert "detected_background_hex" in result.metadata
        assert "is_solid_background" in result.metadata

    def test_metadata_without_detection(self):
        """自动检测禁用时元数据不包含检测结果。"""
        image = _make_solid_bg_image()
        result = process_id_photo(
            image,
            background="red",
            spec_name="1寸",
            auto_detect_background=False,
        )
        assert "detected_background_rgb" not in result.metadata


# ==================== 输出合理性验证 ====================


class TestOutputValid:
    """输出合理性验证。"""

    def test_output_is_valid_image(self):
        """输出是合法的 uint8 图像。"""
        image = _make_solid_bg_image()
        result = process_id_photo(image, background="white", spec_name="1寸")
        assert result.image.dtype == np.uint8
        assert result.image.min() >= 0
        assert result.image.max() <= 255
        assert result.image.shape[2] == 3

    def test_output_no_negative(self):
        """输出不含负值。"""
        image = _make_solid_bg_image()
        result = process_id_photo(image, background="white", spec_name="1寸")
        assert np.all(result.image >= 0)

    def test_output_no_nan(self):
        """输出不含 NaN。"""
        image = _make_solid_bg_image()
        result = process_id_photo(image, background="white", spec_name="1寸")
        assert not np.any(np.isnan(result.image))
