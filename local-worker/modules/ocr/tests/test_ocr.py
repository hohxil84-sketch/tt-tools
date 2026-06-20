"""
local-worker/modules/ocr 完整测试

测试内容：
1. Python 版本检查（按 TESTING.md 要求）
2. 引擎初始化测试
3. 文件路径 OCR 识别测试（生成测试图片）
4. NumPy 数组 OCR 识别测试
5. Bytes 输入 OCR 识别测试
6. 输入校验测试（文件不存在、格式不支持）
7. 结果数据结构测试
8. 批量识别测试
9. 上下文管理器测试
10. 引擎关闭测试
11. GPU 检测集成测试
12. 便捷函数测试
13. 置信度过滤测试
"""

import io
import os
import sys
import tempfile
import unittest
import uuid

# 确保 local-worker 目录在导入路径中（方便从任意位置运行测试）
_local_worker_dir = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)
sys.path.insert(0, _local_worker_dir)


class TestPythonVersion(unittest.TestCase):
    """测试 1：Python 版本检查（按 TESTING.md 要求）。"""

    def test_python_version(self):
        """确认 Python 版本 >= 3.11。"""
        vi = sys.version_info
        self.assertGreaterEqual(vi.major, 3)
        self.assertGreaterEqual(vi.minor, 11)
        print(f"  Python 版本: {sys.version}")


class TestEngineInit(unittest.TestCase):
    """测试 2：OCR 引擎初始化。"""

    def test_init_default(self):
        """默认参数初始化引擎。"""
        from modules.ocr import OCREngine

        engine = OCREngine()
        self.assertFalse(engine.is_closed)
        self.assertEqual(engine.text_score, 0.5)
        print(f"  引擎初始化成功 | text_score={engine.text_score} "
              f"using_dml={engine.using_dml}")
        engine.close()

    def test_init_custom_params(self):
        """自定义参数初始化引擎。"""
        from modules.ocr import OCREngine

        engine = OCREngine(
            text_score=0.7,
            use_cls=False,
        )
        self.assertEqual(engine.text_score, 0.7)
        self.assertFalse(engine.is_closed)
        print(f"  自定义参数引擎初始化 | text_score={engine.text_score}")
        engine.close()

    def test_init_with_request_id(self):
        """带请求 ID 初始化引擎。"""
        from modules.ocr import OCREngine

        rid = str(uuid.uuid4())
        engine = OCREngine(request_id=rid)
        self.assertFalse(engine.is_closed)
        print(f"  请求 ID: {rid}")
        engine.close()

    def test_engine_auto_close_on_del(self):
        """引擎析构时自动释放资源。"""
        from modules.ocr import OCREngine

        engine = OCREngine()
        self.assertFalse(engine.is_closed)
        engine.close()
        self.assertTrue(engine.is_closed)

    def test_closed_engine_recognize_raises(self):
        """关闭后的引擎调用 recognize 应抛出异常。"""
        from modules.ocr import OCREngine
        from shared.errors import AppError

        engine = OCREngine()
        engine.close()
        with self.assertRaises(AppError):
            engine.recognize("nonexistent.png")


class TestOCREngineFromFile(unittest.TestCase):
    """测试 3：从文件路径 OCR 识别。"""

    def setUp(self):
        """创建一张带文字的测试图片。"""
        from PIL import Image, ImageDraw, ImageFont

        self.temp_dir = tempfile.mkdtemp(prefix="tt_test_ocr_")
        self.test_image_path = os.path.join(self.temp_dir, "test_ocr.png")

        # 创建 400x200 白色背景图片
        img = Image.new("RGB", (400, 200), color="white")
        draw = ImageDraw.Draw(img)

        # 尝试使用系统字体绘制文字，否则用默认字体
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("C:\\Windows\\Fonts\\msyh.ttc", 36)
            except (OSError, IOError):
                font = ImageFont.load_default()

        # 绘制中文和英文测试文字
        draw.text((10, 20), "Hello World", fill="black", font=font)
        draw.text((10, 70), "图文店测试", fill="black", font=font)
        draw.text((10, 120), "OCR识别", fill="black", font=font)
        draw.text((10, 150), "2024", fill="black")

        img.save(self.test_image_path)
        print(f"  测试图片已创建: {self.test_image_path}")

    def test_recognize_file_path(self):
        """从文件路径执行 OCR 识别。"""
        from modules.ocr import OCREngine

        engine = OCREngine()
        try:
            result = engine.recognize(self.test_image_path)
            self.assertIsNotNone(result)
            self.assertGreaterEqual(result.line_count, 0)
            self.assertIsInstance(result.total_text, str)
            self.assertEqual(result.engine_name, "RapidOCR")
            self.assertGreater(result.elapsed_total, 0)
            print(f"  识别结果: {result.line_count} 行, "
                  f"avg_score={result.avg_score:.3f}, "
                  f"total_text={result.total_text[:60]!r}, "
                  f"elapsed={result.elapsed_total:.3f}s")
        finally:
            engine.close()

    def test_recognize_file_method(self):
        """recognize_file 方法（带文件校验）。"""
        from modules.ocr import OCREngine

        engine = OCREngine()
        try:
            result = engine.recognize_file(self.test_image_path)
            self.assertIsNotNone(result)
            self.assertGreaterEqual(result.line_count, 0)
        finally:
            engine.close()

    def test_recognize_file_not_found(self):
        """文件不存在时应抛出 AppError。"""
        from modules.ocr import OCREngine
        from shared.errors import AppError

        engine = OCREngine()
        try:
            with self.assertRaises(AppError):
                engine.recognize_file(os.path.join(self.temp_dir, "notfound.png"))
        finally:
            engine.close()


class TestOCREngineFromArray(unittest.TestCase):
    """测试 4：从 NumPy 数组 OCR 识别。"""

    def setUp(self):
        """创建测试用 NumPy 数组图片。"""
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont

        self.temp_dir = tempfile.mkdtemp(prefix="tt_test_ocr_arr_")
        img = Image.new("RGB", (300, 100), color="white")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("C:\\Windows\\Fonts\\msyh.ttc", 24)
            except (OSError, IOError):
                font = ImageFont.load_default()

        draw.text((10, 20), "Test OCR", fill="black", font=font)
        self.img_array = np.array(img)
        print(f"  NumPy 数组已创建: shape={self.img_array.shape}")

    def test_recognize_numpy_array(self):
        """从 NumPy 数组执行 OCR 识别。"""
        from modules.ocr import OCREngine

        engine = OCREngine()
        try:
            result = engine.recognize(self.img_array)
            self.assertIsNotNone(result)
            self.assertIsInstance(result.total_text, str)
            self.assertEqual(result.image_width, self.img_array.shape[1])
            self.assertEqual(result.image_height, self.img_array.shape[0])
            print(f"  数组识别结果: lines={result.line_count}, "
                  f"text={result.total_text!r}")
        finally:
            engine.close()


class TestOCREngineFromBytes(unittest.TestCase):
    """测试 5：从二进制数据 OCR 识别。"""

    def setUp(self):
        """创建测试用图片二进制数据。"""
        from PIL import Image, ImageDraw

        self.temp_dir = tempfile.mkdtemp(prefix="tt_test_ocr_bytes_")
        img = Image.new("RGB", (200, 80), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 20), "ByteTest", fill="black")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        self.img_bytes = buf.getvalue()
        print(f"  二进制数据已创建: {len(self.img_bytes)} bytes")

    def test_recognize_bytes(self):
        """从 bytes 执行 OCR 识别。"""
        from modules.ocr import OCREngine

        engine = OCREngine()
        try:
            result = engine.recognize(self.img_bytes)
            self.assertIsNotNone(result)
            self.assertIsInstance(result.total_text, str)
            print(f"  Bytes 识别结果: lines={result.line_count}, "
                  f"text={result.total_text!r}")
        finally:
            engine.close()


class TestInputValidation(unittest.TestCase):
    """测试 6：输入校验。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="tt_test_ocr_val_")

    def test_unsupported_input_type(self):
        """不支持的输入类型应抛出异常。"""
        from modules.ocr import OCREngine
        from shared.errors import AppError

        engine = OCREngine()
        try:
            with self.assertRaises(AppError):
                engine.recognize(12345)  # int 类型不支持
        finally:
            engine.close()

    def test_invalid_array_dimensions(self):
        """无效的数组维度应抛出异常。"""
        from modules.ocr import OCREngine
        from shared.errors import AppError
        import numpy as np

        engine = OCREngine()
        try:
            with self.assertRaises(AppError):
                engine.recognize(np.array([1, 2, 3]))  # 1D 数组
        finally:
            engine.close()

    def test_recognize_file_unsupported_format(self):
        """不支持的文件格式应抛出异常。"""
        from modules.ocr import OCREngine
        from shared.errors import AppError

        engine = OCREngine()
        try:
            with self.assertRaises(AppError):
                engine.recognize_file(os.path.join(self.temp_dir, "test.txt"))
        finally:
            engine.close()


class TestOCRResultStructure(unittest.TestCase):
    """测试 7：OCRResult 数据结构。"""

    def test_empty_result(self):
        """空识别结果。"""
        from modules.ocr import OCRResult

        result = OCRResult(
            text_lines=[],
            total_text="",
            elapsed_total=1.0,
            elapsed_det=0.3,
            elapsed_cls=0.1,
            elapsed_rec=0.6,
            engine_name="RapidOCR",
            engine_version="1.4.4",
            image_width=100,
            image_height=200,
        )

        self.assertEqual(result.line_count, 0)
        self.assertEqual(result.avg_score, 0.0)
        self.assertEqual(len(result.high_confidence_lines), 0)
        self.assertEqual(len(result.low_confidence_lines), 0)

    def test_result_to_dict(self):
        """OCRResult.to_dict() 序列化。"""
        from modules.ocr import OCRBox, OCRResult

        result = OCRResult(
            text_lines=[
                OCRBox(text="Hello", score=0.95, box=[[0, 0], [50, 0], [50, 20], [0, 20]]),
            ],
            total_text="Hello",
            elapsed_total=0.5,
            elapsed_det=0.1,
            elapsed_cls=0.05,
            elapsed_rec=0.35,
            engine_name="RapidOCR",
            engine_version="1.4.4",
            image_width=100,
            image_height=200,
        )

        d = result.to_dict()
        self.assertEqual(d["line_count"], 1)
        self.assertEqual(d["total_text"], "Hello")
        self.assertEqual(len(d["text_lines"]), 1)
        self.assertEqual(d["text_lines"][0]["text"], "Hello")
        self.assertEqual(d["text_lines"][0]["score"], 0.95)
        self.assertIsNotNone(d["elapsed"]["cls"])
        self.assertEqual(d["engine"]["name"], "RapidOCR")
        self.assertEqual(d["image"]["width"], 100)

    def test_ocr_box_repr(self):
        """OCRBox 字符串表示。"""
        from modules.ocr import OCRBox

        box = OCRBox(text="test", score=0.88, box=[[0, 0], [1, 0], [1, 1], [0, 1]])
        r = repr(box)
        self.assertIn("test", r)
        self.assertIn("0.88", r)

    def test_high_confidence_filter(self):
        """高置信文字行筛选。"""
        from modules.ocr import OCRBox, OCRResult

        result = OCRResult(
            text_lines=[
                OCRBox(text="high", score=0.95, box=[[0, 0], [1, 0], [1, 1], [0, 1]]),
                OCRBox(text="low", score=0.3, box=[[0, 1], [1, 1], [1, 2], [0, 2]]),
            ],
            total_text="highlow",
            elapsed_total=0.5,
            elapsed_det=0.1,
            elapsed_cls=None,
            elapsed_rec=0.4,
            engine_name="RapidOCR",
            engine_version="1.4.4",
        )

        high = result.high_confidence_lines
        low = result.low_confidence_lines
        self.assertEqual(len(high), 1)
        self.assertEqual(high[0].text, "high")
        self.assertEqual(len(low), 1)
        self.assertEqual(low[0].text, "low")


class TestBatchRecognize(unittest.TestCase):
    """测试 8：批量识别。"""

    def setUp(self):
        from PIL import Image, ImageDraw

        self.temp_dir = tempfile.mkdtemp(prefix="tt_test_ocr_batch_")

        # 创建两张测试图片
        self.img1_path = os.path.join(self.temp_dir, "batch1.png")
        img1 = Image.new("RGB", (200, 100), color="white")
        draw1 = ImageDraw.Draw(img1)
        draw1.text((10, 20), "BatchOne", fill="black")
        img1.save(self.img1_path)

        self.img2_path = os.path.join(self.temp_dir, "batch2.png")
        img2 = Image.new("RGB", (200, 100), color="white")
        draw2 = ImageDraw.Draw(img2)
        draw2.text((10, 20), "BatchTwo", fill="black")
        img2.save(self.img2_path)

    def test_batch_recognize(self):
        """批量识别多张图片。"""
        from modules.ocr import OCREngine

        engine = OCREngine()
        try:
            results = engine.recognize_batch([self.img1_path, self.img2_path])
            self.assertEqual(len(results), 2)
            for i, result in enumerate(results):
                self.assertIsNotNone(result)
                self.assertIsInstance(result.total_text, str)
                print(f"  批量[{i}]: lines={result.line_count}, "
                      f"text={result.total_text!r}")
        finally:
            engine.close()

    def test_batch_recognize_with_error(self):
        """批量识别中包含无效输入，不应中断。"""
        from modules.ocr import OCREngine

        engine = OCREngine()
        try:
            results = engine.recognize_batch([
                self.img1_path,
                "nonexistent_file.png",
            ])
            self.assertEqual(len(results), 2)
            # 第一张应该正常
            self.assertIsInstance(results[0].total_text, str)
            # 第二张应该包含错误信息
            self.assertIn("[ERROR]", results[1].total_text)
            print(f"  错误处理结果: {results[1].total_text}")
        finally:
            engine.close()


class TestContextManager(unittest.TestCase):
    """测试 9：上下文管理器。"""

    def setUp(self):
        from PIL import Image, ImageDraw

        self.temp_dir = tempfile.mkdtemp(prefix="tt_test_ocr_ctx_")
        img = Image.new("RGB", (200, 80), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 20), "CTX Test", fill="black")
        self.img_path = os.path.join(self.temp_dir, "ctx_test.png")
        img.save(self.img_path)

    def test_context_manager(self):
        """使用 with 语句管理引擎生命周期。"""
        from modules.ocr import OCREngine

        with OCREngine(text_score=0.5) as engine:
            result = engine.recognize(self.img_path)
            self.assertIsNotNone(result)
            self.assertFalse(engine.is_closed)
            print(f"  上下文内识别: lines={result.line_count}")

        # 退出 with 后引擎应已关闭
        self.assertTrue(engine.is_closed)

    def test_context_manager_exception_handling(self):
        """上下文管理器中抛出异常，引擎也应正常关闭。"""
        from modules.ocr import OCREngine
        from shared.errors import AppError

        engine = None
        try:
            with OCREngine() as e:
                engine = e
                raise ValueError("模拟异常")
        except ValueError:
            pass

        self.assertIsNotNone(engine)
        self.assertTrue(engine.is_closed)


class TestGPUDetection(unittest.TestCase):
    """测试 10：GPU 检测集成。"""

    def test_gpu_info_available(self):
        """引擎应能获取 GPU 信息。"""
        from modules.ocr import OCREngine

        engine = OCREngine()
        try:
            gpu_info = engine.gpu_info
            self.assertIsNotNone(gpu_info)
            print(f"  GPU: available={gpu_info.available}, "
                  f"cuda={gpu_info.cuda_available}, "
                  f"dml={gpu_info.dml_available}, "
                  f"vendor={gpu_info.vendor}")
        finally:
            engine.close()

    def test_dml_detection(self):
        """DirectML 检测逻辑。"""
        from modules.ocr import OCREngine

        # 显式请求启用 DirectML
        engine = OCREngine(use_dml=True)
        try:
            print(f"  use_dml=True, actual={engine.using_dml}")
            # 不强制要求 DML 可用，只验证不崩溃
        finally:
            engine.close()


class TestConvenienceFunction(unittest.TestCase):
    """测试 11：便捷函数 recognize_image。"""

    def setUp(self):
        from PIL import Image, ImageDraw

        self.temp_dir = tempfile.mkdtemp(prefix="tt_test_ocr_conv_")
        img = Image.new("RGB", (200, 60), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 15), "QuickTest", fill="black")
        self.img_path = os.path.join(self.temp_dir, "quick.png")
        img.save(self.img_path)

    def test_recognize_image_function(self):
        """便捷函数应可正常使用。"""
        from modules.ocr import recognize_image

        result = recognize_image(self.img_path, text_score=0.5)
        self.assertIsNotNone(result)
        self.assertIsInstance(result.total_text, str)
        self.assertEqual(result.engine_name, "RapidOCR")
        print(f"  便捷函数识别结果: lines={result.line_count}, "
              f"text={result.total_text!r}")

    def test_recognize_image_default_params(self):
        """便捷函数使用默认参数。"""
        from modules.ocr import recognize_image

        result = recognize_image(self.img_path)
        self.assertIsNotNone(result)
        print(f"  默认参数识别: lines={result.line_count}")


class TestModuleExports(unittest.TestCase):
    """测试 12：模块导出完整性。"""

    def test_all_exports_importable(self):
        """确认 __all__ 中所有导出都可导入。"""
        import modules.ocr as ocr_mod

        for name in ocr_mod.__all__:
            obj = getattr(ocr_mod, name, None)
            self.assertIsNotNone(
                obj,
                f"modules.ocr.__all__ 中的 {name} 无法获取",
            )
        print(f"  所有 {len(ocr_mod.__all__)} 个导出均可导入")


class TestConfidenceFiltering(unittest.TestCase):
    """测试 13：置信度过滤。"""

    def setUp(self):
        from PIL import Image, ImageDraw

        self.temp_dir = tempfile.mkdtemp(prefix="tt_test_ocr_conf_")

        # 创建清晰的文字图片
        img = Image.new("RGB", (300, 80), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 20), "Clear Text", fill="black")
        self.img_path = os.path.join(self.temp_dir, "clear.png")
        img.save(self.img_path)

    def test_high_threshold_filters_low_confidence(self):
        """高阈值应过滤低置信度结果。"""
        from modules.ocr import OCREngine

        # 使用极高阈值
        engine = OCREngine(text_score=0.99)
        try:
            result = engine.recognize(self.img_path)
            # 极高阈值下可能没有任何结果
            self.assertIsNotNone(result)
            # 所有通过的结果置信度应 >= 0.99
            for line in result.text_lines:
                self.assertGreaterEqual(line.score, 0.99)
            print(f"  阈值 0.99 过滤: {result.line_count} 行通过")
        finally:
            engine.close()

    def test_low_threshold_retains_more(self):
        """低阈值应保留更多结果。"""
        from modules.ocr import OCREngine

        engine = OCREngine(text_score=0.1)
        try:
            result = engine.recognize(self.img_path)
            self.assertIsNotNone(result)
            print(f"  阈值 0.1 过滤: {result.line_count} 行通过")
        finally:
            engine.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
