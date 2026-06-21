"""
local-worker/modules/remove-bg/tests/test_remove_bg.py — 智能抠图模块测试

测试范围：
  - Python 版本和依赖检查
  - 模块导入和导出
  - 模型列表查询
  - 模型加载和缓存管理
  - 背景去除基本功能
  - 文件路径 API
  - 纯色背景合成
  - 输入校验和错误处理
  - 不同模型验证
  - 仅遮罩模式
  - RGBA 输入兼容性
  - 复杂场景图像
"""

import os
import sys
import tempfile
import unittest
import warnings

# 确保模块在 path 中
# 目录名 remove-bg 含连字符，不能作为 Python 包名直接 import
# 将模块目录加入 sys.path 后直接导入文件名
_this_dir = os.path.dirname(os.path.abspath(__file__))
_remove_bg_dir = os.path.join(_this_dir, "..")
if _remove_bg_dir not in sys.path:
    sys.path.insert(0, _remove_bg_dir)

import cv2  # type: ignore
import numpy as np
from PIL import Image  # type: ignore

from processor import (
    RemoveBgResult,
    clear_model_cache,
    composite_on_color,
    is_model_available,
    list_supported_models,
    remove_background,
    remove_background_from_path,
)
from processor import _get_session, _model_cache


# ---- 工具函数：生成测试图像 ----

def _create_test_image_bgr(
    width: int = 320,
    height: int = 240,
    background_color: tuple = (255, 255, 255),
    foreground_color: tuple = (0, 0, 255),
    foreground_rect: tuple = (100, 60, 160, 120),
) -> np.ndarray:
    """创建简单的测试图像：纯色背景上一个矩形前景。

    参数：
        width, height: 图像尺寸。
        background_color: 背景色 BGR。
        foreground_color: 前景色 BGR。
        foreground_rect: 矩形 (x, y, w, h)。

    返回：
        BGR 图像 (H, W, 3)。
    """
    img = np.full((height, width, 3), background_color, dtype=np.uint8)
    x, y, w, h = foreground_rect
    img[y:y + h, x:x + w] = foreground_color
    return img


def _create_gradient_bg_test_image(
    width: int = 320,
    height: int = 240,
) -> np.ndarray:
    """创建渐变背景 + 中心圆前景的测试图像。

    圆形区域模拟人物区域，渐变背景模拟复杂场景。

    返回：
        BGR 图像 (H, W, 3)。
    """
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # 渐变背景
    for x in range(width):
        val = int(255 * x / width)
        img[:, x] = (val, 255 - val, val)

    # 中心红色圆（模拟人物前景）
    cx, cy = width // 2, height // 2
    radius = min(width, height) // 4
    for y in range(height):
        for x in range(width):
            if (x - cx) ** 2 + (y - cy) ** 2 < radius ** 2:
                img[y, x] = (0, 0, 255)
    return img.astype(np.uint8)


def _create_rgba_test_image(
    width: int = 320,
    height: int = 240,
) -> np.ndarray:
    """创建带透明通道的测试图像。

    返回：
        RGBA 图像 (H, W, 4)。
    """
    bgr = _create_test_image_bgr(width, height)
    alpha = np.full((height, width), 255, dtype=np.uint8)
    # 边缘区域设置半透明
    alpha[:60, :] = 128
    alpha[-60:, :] = 128
    rgba = np.dstack([bgr[:, :, ::-1], alpha])  # BGR -> RGB 再附加 Alpha
    return rgba


# ---- 测试类 1：Python 版本和依赖 ----

class TestPythonVersion(unittest.TestCase):
    """测试 1：python --version（按 TESTING.md 要求）。"""

    def test_python_version(self):
        """确认 Python 版本 >= 3.11。"""
        vi = sys.version_info
        self.assertGreaterEqual(vi.major, 3)
        self.assertGreaterEqual(vi.minor, 11)
        print(f"  Python 版本: {sys.version}")


class TestDependencies(unittest.TestCase):
    """测试 2：依赖可用性检查。"""

    def test_rembg_available(self):
        """确认 rembg 可导入。"""
        try:
            import rembg  # type: ignore  # noqa: F401
            print("  rembg 可用")
        except ImportError as e:
            self.skipTest(f"rembg 未安装: {e}")

    def test_cv2_available(self):
        """确认 opencv-python 可导入。"""
        self.assertIsNotNone(cv2.__version__)
        print(f"  OpenCV 版本: {cv2.__version__}")

    def test_pil_available(self):
        """确认 Pillow 可导入。"""
        self.assertIsNotNone(Image.__version__)
        print(f"  Pillow 版本: {Image.__version__}")


# ---- 测试类 3：模块导入和导出 ----

class TestModuleImports(unittest.TestCase):
    """测试 3：模块导入和导出检查。"""

    def test_import_processor(self):
        """确认 processor 模块可导入。"""
        import processor  # noqa: F811
        self.assertIsNotNone(processor)

    def test_exported_functions(self):
        """确认模块导出函数齐全。"""
        self.assertTrue(callable(remove_background))
        self.assertTrue(callable(remove_background_from_path))
        self.assertTrue(callable(composite_on_color))
        self.assertTrue(callable(list_supported_models))
        self.assertTrue(callable(is_model_available))
        self.assertTrue(callable(clear_model_cache))
        self.assertIsNotNone(RemoveBgResult)


# ---- 测试类 4：模型列表 ----

class TestModelList(unittest.TestCase):
    """测试 4：模型列表查询。"""

    def test_list_supported_models(self):
        """列出所有支持模型，确认列表非空。"""
        models = list_supported_models()
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)
        self.assertIn("u2net", models)
        self.assertIn("u2netp", models)
        print(f"  支持模型: {models}")

    def test_is_model_available(self):
        """确认模型可用性检查正确。"""
        self.assertTrue(is_model_available("u2net"))
        self.assertTrue(is_model_available("u2netp"))
        self.assertFalse(is_model_available("invalid_model"))
        self.assertFalse(is_model_available(""))


# ---- 测试类 5：模型加载和缓存 ----

class TestModelCache(unittest.TestCase):
    """测试 5：模型加载和缓存管理。"""

    @classmethod
    def setUpClass(cls):
        """检查 rembg 是否可用。"""
        try:
            import rembg  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("rembg 未安装，跳过模型加载测试")

    def setUp(self):
        """每个测试前清除缓存。"""
        _model_cache.clear()

    def test_load_default_model(self):
        """加载默认模型 u2net。"""
        session = _get_session("u2net")
        self.assertIsNotNone(session)
        print("  默认模型加载成功")

    def test_model_cache_reuse(self):
        """确认模型缓存复用（第二次获取更快）。"""
        _model_cache.clear()

        # 首次加载
        session1 = _get_session("u2netp")
        self.assertIsNotNone(session1)
        self.assertIn("u2netp", _model_cache)

        # 二次获取（应返回同一对象）
        session2 = _get_session("u2netp")
        self.assertIs(session1, session2)
        print("  模型缓存复用验证通过")

    def test_clear_model_cache(self):
        """清除模型缓存。"""
        # 确保缓存中有模型
        _get_session("u2net")
        self.assertGreater(len(_model_cache), 0)

        # 清除全部
        clear_model_cache()
        self.assertEqual(len(_model_cache), 0)
        print("  模型缓存清除验证通过")

    def test_invalid_model_name(self):
        """使用无效模型名应抛出 ValueError。"""
        with self.assertRaises(ValueError):
            _get_session("nonexistent_model")


# ---- 测试类 6：背景去除基本功能 ----

class TestRemoveBackgroundBasic(unittest.TestCase):
    """测试 6：背景去除基本功能。"""

    @classmethod
    def setUpClass(cls):
        """确保 rembg 可用。"""
        try:
            import rembg  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("rembg 未安装，跳过抠图功能测试")

    def setUp(self):
        """每个测试前清除模型缓存。"""
        _model_cache.clear()

    def test_remove_background_simple(self):
        """简单测试图像背景去除。"""
        # 创建测试图像：红色矩形在白色背景上
        image = _create_test_image_bgr()

        result = remove_background(image, model_name="u2netp")

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.image)
        self.assertEqual(result.input_width, 320)
        self.assertEqual(result.input_height, 240)
        # 输出应为 RGBA
        self.assertGreaterEqual(result.image.shape[2], 3)
        self.assertEqual(result.model, "u2netp")
        print(f"  抠图完成: 输入={result.input_width}x{result.input_height}, "
              f"输出={result.output_width}x{result.output_height}")

    def test_remove_background_returns_alpha(self):
        """确认抠图结果包含有效的 Alpha 通道。"""
        image = _create_test_image_bgr()
        result = remove_background(image, model_name="u2netp")

        # 检查 Alpha 通道
        if result.image.shape[2] == 4:
            alpha = result.image[:, :, 3]
            # Alpha 通道值应在 [0, 255]
            self.assertLessEqual(alpha.max(), 255)
            self.assertGreaterEqual(alpha.min(), 0)
            print(f"  Alpha 值域: min={alpha.min()}, max={alpha.max()}")
        else:
            self.fail(f"输出图像通道数异常: {result.image.shape[2]}")

    def test_remove_background_output_size(self):
        """确认输出尺寸与输入一致。"""
        image = _create_test_image_bgr(width=160, height=120)
        result = remove_background(image, model_name="u2netp")

        self.assertEqual(result.output_width, 160)
        self.assertEqual(result.output_height, 120)


# ---- 测试类 7：文件路径 API ----

class TestRemoveBackgroundFromPath(unittest.TestCase):
    """测试 7：文件路径 API。"""

    @classmethod
    def setUpClass(cls):
        """确保 rembg 可用。"""
        try:
            import rembg  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("rembg 未安装，跳过文件路径测试")

    def setUp(self):
        _model_cache.clear()
        self.tmpdir = tempfile.mkdtemp(prefix="remove_bg_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_remove_bg_from_path_rgba_output(self):
        """从文件路径抠图，输出 RGBA PNG。"""
        input_path = os.path.join(self.tmpdir, "input.jpg")
        output_path = os.path.join(self.tmpdir, "output.png")

        # 创建并保存测试图像
        image = _create_test_image_bgr()
        cv2.imwrite(input_path, image)

        result = remove_background_from_path(
            input_path, output_path,
            model_name="u2netp",
            output_rgba=True,
        )

        self.assertIsNotNone(result)
        self.assertTrue(os.path.isfile(output_path))
        # 验证输出文件可读取
        output_img = cv2.imread(output_path, cv2.IMREAD_UNCHANGED)
        self.assertIsNotNone(output_img)
        print(f"  输出文件: {output_path}, 尺寸={output_img.shape}")

    def test_remove_bg_from_path_white_composite(self):
        """抠图后合成到白色背景。"""
        input_path = os.path.join(self.tmpdir, "input2.jpg")
        output_path = os.path.join(self.tmpdir, "output2.jpg")

        image = _create_test_image_bgr()
        cv2.imwrite(input_path, image)

        result = remove_background_from_path(
            input_path, output_path,
            model_name="u2netp",
            output_rgba=False,
            composite_color=(255, 255, 255),
        )

        self.assertIsNotNone(result)
        self.assertTrue(os.path.isfile(output_path))
        # 输出应为 3 通道
        output_img = cv2.imread(output_path)
        self.assertEqual(len(output_img.shape), 3)
        self.assertEqual(output_img.shape[2], 3)
        print(f"  合成输出: {output_path}")

    def test_remove_bg_invalid_input_path(self):
        """无效输入路径应抛出异常。"""
        input_path = os.path.join(self.tmpdir, "nonexistent.jpg")
        output_path = os.path.join(self.tmpdir, "will_not_create.png")

        with self.assertRaises(Exception):
            remove_background_from_path(input_path, output_path, model_name="u2netp")


# ---- 测试类 8：纯色背景合成 ----

class TestCompositeOnColor(unittest.TestCase):
    """测试 8：纯色背景合成。"""

    @classmethod
    def setUpClass(cls):
        try:
            import rembg  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("rembg 未安装")

    def setUp(self):
        _model_cache.clear()

    def test_composite_white_background(self):
        """合成到白色背景。"""
        image = _create_test_image_bgr()
        result = remove_background(image, model_name="u2netp")

        composited = composite_on_color(result, (255, 255, 255))

        self.assertEqual(len(composited.shape), 3)
        self.assertEqual(composited.shape[2], 3)
        # 输出应为 BGR 格式（可直接 cv2.imwrite）
        self.assertEqual(composited.dtype, np.uint8)
        print(f"  合成图像: shape={composited.shape}, dtype={composited.dtype}")

    def test_composite_custom_color(self):
        """合成到自定义颜色。"""
        image = _create_test_image_bgr()
        result = remove_background(image, model_name="u2netp")

        # 红色背景
        composited = composite_on_color(result, (255, 0, 0))

        self.assertEqual(composited.shape[2], 3)
        # 检查边缘区域是否接近红色（BGR=(0,0,255)）
        edge_color = composited[0, 0]  # 左上角，期望为背景色
        # 红色在 BGR 中是 (0, 0, 255)
        self.assertGreaterEqual(edge_color[2], edge_color[0])  # R > B
        self.assertGreaterEqual(edge_color[2], edge_color[1])  # R > G


# ---- 测试类 9：输入校验 ----

class TestInputValidation(unittest.TestCase):
    """测试 9：输入校验和错误处理。"""

    @classmethod
    def setUpClass(cls):
        try:
            import rembg  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("rembg 未安装")

    def test_invalid_input_none(self):
        """None 输入应抛出 ValueError。"""
        with self.assertRaises(ValueError):
            remove_background(None, model_name="u2netp")

    def test_invalid_input_1d(self):
        """1D 输入应抛出 ValueError。"""
        with self.assertRaises(ValueError):
            remove_background(np.zeros(100, dtype=np.uint8), model_name="u2netp")

    def test_invalid_channel_count(self):
        """无效通道数应抛出 ValueError。"""
        # 5 通道（无效）
        bad_image = np.zeros((100, 100, 5), dtype=np.uint8)
        with self.assertRaises(ValueError):
            remove_background(bad_image, model_name="u2netp")

    def test_invalid_model_name(self):
        """无效模型名应抛出 ValueError。"""
        image = _create_test_image_bgr()
        with self.assertRaises(ValueError):
            remove_background(image, model_name="invalid_model")


# ---- 测试类 10：不同模型 ----

class TestDifferentModels(unittest.TestCase):
    """测试 10：不同模型的基本验证。"""

    @classmethod
    def setUpClass(cls):
        try:
            import rembg  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("rembg 未安装")

    def setUp(self):
        _model_cache.clear()

    def test_u2netp_model(self):
        """u2netp 模型抠图。"""
        image = _create_test_image_bgr(160, 120)
        result = remove_background(image, model_name="u2netp")
        self.assertEqual(result.model, "u2netp")
        self.assertIsNotNone(result.image)
        print(f"  u2netp: 输出 shape={result.image.shape}")

    def test_u2net_model(self):
        """u2net 模型抠图。"""
        image = _create_test_image_bgr(120, 80)
        result = remove_background(image, model_name="u2net")
        self.assertEqual(result.model, "u2net")
        self.assertIsNotNone(result.image)
        self.assertIsNotNone(result.alpha_mask)
        print(f"  u2net: 输出 shape={result.image.shape}")


# ---- 测试类 11：Alpha Mask 模式 ----

class TestAlphaMaskOnly(unittest.TestCase):
    """测试 11：仅遮罩模式。"""

    @classmethod
    def setUpClass(cls):
        try:
            import rembg  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("rembg 未安装")

    def setUp(self):
        _model_cache.clear()

    def test_only_mask(self):
        """仅返回 Alpha 遮罩。"""
        image = _create_test_image_bgr(160, 120)
        result = remove_background(image, model_name="u2netp", only_mask=True)

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.alpha_mask)
        print(f"  仅遮罩模式: alpha_mask shape={result.alpha_mask.shape}")


# ---- 测试类 12：RGBA 输入 ----

class TestRGBAInput(unittest.TestCase):
    """测试 12：RGBA 格式输入。"""

    @classmethod
    def setUpClass(cls):
        try:
            import rembg  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("rembg 未安装")

    def setUp(self):
        _model_cache.clear()

    def test_rgba_input(self):
        """RGBA 输入应正常处理。"""
        rgba = _create_rgba_test_image(160, 120)
        result = remove_background(rgba, model_name="u2netp")

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.image)
        print(f"  RGBA 输入: 输出 shape={result.image.shape}")


# ---- 测试类 13：RemoveBgResult 结构 ----

class TestRemoveBgResult(unittest.TestCase):
    """测试 13：RemoveBgResult 数据结构。"""

    @classmethod
    def setUpClass(cls):
        try:
            import rembg  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("rembg 未安装")

    def setUp(self):
        _model_cache.clear()

    def test_result_fields(self):
        """确认所有字段都有有效值。"""
        image = _create_test_image_bgr()
        result = remove_background(image, model_name="u2netp")

        self.assertIsNotNone(result.image)
        self.assertGreater(result.input_width, 0)
        self.assertGreater(result.input_height, 0)
        self.assertGreater(result.output_width, 0)
        self.assertGreater(result.output_height, 0)
        self.assertIsInstance(result.model, str)
        self.assertIsInstance(result.metadata, dict)
        self.assertIn("model", result.metadata)

    def test_result_metadata(self):
        """确认元数据包含必要信息。"""
        image = _create_test_image_bgr()
        result = remove_background(image, model_name="u2netp")

        self.assertIn("model", result.metadata)
        self.assertIn("input_size", result.metadata)
        self.assertEqual(result.metadata["model"], "u2netp")


# ---- 测试类 14：渐变背景复杂场景 ----

class TestComplexImages(unittest.TestCase):
    """测试 14：复杂场景图像测试。"""

    @classmethod
    def setUpClass(cls):
        try:
            import rembg  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("rembg 未安装")

    def setUp(self):
        _model_cache.clear()

    def test_gradient_background(self):
        """渐变背景抠图。"""
        image = _create_gradient_bg_test_image(320, 240)
        result = remove_background(image, model_name="u2netp")

        self.assertIsNotNone(result)
        # 确认输出尺寸与输入一致
        self.assertEqual(result.output_width, 320)
        self.assertEqual(result.output_height, 240)
        fg_pct = np.count_nonzero(result.alpha_mask > 128) / (320 * 240) * 100
        print(f"  渐变背景: Alpha 前景占比={fg_pct:.1f}%")


# ---- 测试类 15：Alpha Matting ----

class TestAlphaMatting(unittest.TestCase):
    """测试 15：Alpha Matting 边缘精细化。"""

    @classmethod
    def setUpClass(cls):
        try:
            import rembg  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("rembg 未安装")

    def setUp(self):
        _model_cache.clear()

    def test_alpha_matting_enabled(self):
        """启用 Alpha Matting 抠图。"""
        image = _create_test_image_bgr(160, 120)
        result = remove_background(
            image,
            model_name="u2netp",
            alpha_matting=True,
        )

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.image)
        self.assertTrue(result.metadata.get("alpha_matting", False))
        print(f"  Alpha Matting: 输出 shape={result.image.shape}")


# ---- 主入口 ----

if __name__ == "__main__":
    # 抑制 rembg 首次加载时的下载进度日志
    warnings.filterwarnings("ignore", category=UserWarning)

    unittest.main(verbosity=2)
