"""
local-worker/shared 完整测试

测试内容：
1. python --version（按 TESTING.md 要求）
2. worker healthcheck（按 TESTING.md 要求）
3. errors 模块单元测试
4. runtime 模块单元测试
5. model_registry 模块单元测试
6. file_io 模块单元测试
7. logging 模块单元测试
"""

import os
import sys
import tempfile
import unittest

# 确保 local-worker 目录在导入路径中（方便从任意位置运行测试）
# local-worker/shared/tests/ -> shared/ -> local-worker/
_local_worker_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _local_worker_dir)


class TestPythonVersion(unittest.TestCase):
    """测试 1：python --version（按 TESTING.md 要求）。"""

    def test_python_version(self):
        """确认 Python 版本 >= 3.11。"""
        vi = sys.version_info
        self.assertGreaterEqual(vi.major, 3)
        self.assertGreaterEqual(vi.minor, 11)
        print(f"  Python 版本: {sys.version}")


class TestHealthcheck(unittest.TestCase):
    """测试 2：worker healthcheck（按 TESTING.md 要求）。"""

    def test_healthcheck_returns_runtime_info(self):
        """健康检查应返回有效的 RuntimeInfo。"""
        from shared.runtime import healthcheck

        info = healthcheck()
        self.assertIsNotNone(info)
        self.assertIsNotNone(info.cpu)
        self.assertIsNotNone(info.gpu)
        self.assertGreater(info.cpu.cores_logical, 0)
        self.assertEqual(info.platform, sys.platform)
        print(f"  Healthcheck 通过: {info.cpu.cores_logical} 逻辑核心, "
              f"GPU available={info.gpu.available}")


class TestErrorModule(unittest.TestCase):
    """测试 3：errors 模块。"""

    def test_app_error_creation(self):
        """AppError 创建和字段。"""
        from shared.errors import AppError, ErrorCode

        err = AppError(
            ErrorCode.FILE_NOT_FOUND,
            "测试错误",
            details={"path": "/tmp/test.png"},
            request_id="req-001",
        )
        self.assertEqual(err.code, ErrorCode.FILE_NOT_FOUND)
        self.assertEqual(err.message, "测试错误")
        self.assertEqual(err.details, {"path": "/tmp/test.png"})
        self.assertEqual(err.request_id, "req-001")

    def test_app_error_to_dict(self):
        """AppError.to_dict() 输出对齐 OpenAPI ErrorDetail 结构。"""
        from shared.errors import AppError, ErrorCode

        err = AppError(ErrorCode.UNKNOWN, "未知错误")
        d = err.to_dict()

        self.assertFalse(d["success"])
        self.assertIsNone(d["data"])
        self.assertIsNotNone(d["request_id"])
        self.assertEqual(d["error"]["code"], "LOCAL_UNKNOWN")
        self.assertEqual(d["error"]["message"], "未知错误")

    def test_app_error_default_request_id(self):
        """未指定 request_id 时应自动生成 UUID。"""
        from shared.errors import AppError, ErrorCode

        err = AppError(ErrorCode.INTERNAL, "内部错误")
        self.assertIsNotNone(err.request_id)
        self.assertGreater(len(err.request_id), 0)

    def test_error_code_values_unique(self):
        """确认所有 ErrorCode 值唯一。"""
        from shared.errors import ErrorCode

        values = [e.value for e in ErrorCode]
        self.assertEqual(len(values), len(set(values)),
                         f"ErrorCode 存在重复值: {values}")

    def test_error_code_prefix(self):
        """确认错误码都以 LOCAL_ 开头。"""
        from shared.errors import ErrorCode

        for e in ErrorCode:
            self.assertTrue(
                e.value.startswith("LOCAL_"),
                f"错误码 {e.value} 不以 LOCAL_ 开头",
            )


class TestRuntimeModule(unittest.TestCase):
    """测试 4：runtime 模块。"""

    def test_detect_cpu_info(self):
        """CPU 检测返回有效信息。"""
        from shared.runtime import detect_cpu_info

        cpu = detect_cpu_info()
        self.assertIsNotNone(cpu)
        self.assertGreaterEqual(cpu.cores_physical, 1)
        self.assertGreaterEqual(cpu.cores_logical, 1)
        self.assertTrue(len(cpu.arch) > 0)
        print(f"  CPU: {cpu.cores_physical}P/{cpu.cores_logical}L, "
              f"arch={cpu.arch}, avx2={cpu.supports_avx2}, brand={cpu.brand}")

    def test_detect_gpu_info(self):
        """GPU 检测应不抛出异常（GPU 可选）。"""
        from shared.runtime import detect_gpu_info

        gpu = detect_gpu_info()
        self.assertIsNotNone(gpu)
        # GPU 是可选的，不要求 available=True
        print(f"  GPU: available={gpu.available}, cuda={gpu.cuda_available}, "
              f"dml={gpu.dml_available}, name={gpu.name}")

    def test_get_runtime_info(self):
        """综合运行时信息检测。"""
        from shared.runtime import get_runtime_info

        info = get_runtime_info()
        self.assertEqual(info.platform, sys.platform)
        self.assertIsNotNone(info.cpu)
        self.assertIsNotNone(info.gpu)
        self.assertTrue(len(info.python_version) > 0)

    def test_process_message_roundtrip(self):
        """ProcessMessage 序列化和反序列化。"""
        from shared.runtime import ProcessMessage

        msg = ProcessMessage(
            message_type="task",
            payload={"action": "ocr", "file": "test.png"},
            request_id="req-123",
            task_id="task-456",
        )
        data = msg.to_bytes()
        # 反序列化
        decoded = ProcessMessage.from_bytes(data)
        self.assertEqual(decoded.message_type, "task")
        self.assertEqual(decoded.payload["action"], "ocr")
        self.assertEqual(decoded.request_id, "req-123")
        self.assertEqual(decoded.task_id, "task-456")

    def test_process_message_minimal(self):
        """最简 ProcessMessage 序列化。"""
        from shared.runtime import ProcessMessage

        msg = ProcessMessage(message_type="health")
        data = msg.to_bytes()
        decoded = ProcessMessage.from_bytes(data)
        self.assertEqual(decoded.message_type, "health")
        self.assertEqual(decoded.payload, {})


class TestModelRegistry(unittest.TestCase):
    """测试 5：model_registry 模块。"""

    def setUp(self):
        from shared.model_registry import ModelRegistry
        self.registry = ModelRegistry(
            model_root=tempfile.mkdtemp(prefix="tt_test_models_")
        )

    def test_register_model(self):
        """模型注册和查询。"""
        self.registry.register(
            name="test_model",
            display_name="测试模型",
            version="1.0",
            file_name="test.onnx",
            source="test",
        )
        self.assertTrue(self.registry.is_registered("test_model"))
        self.assertIn("test_model", self.registry)
        self.assertEqual(len(self.registry), 1)

    def test_get_model_info_not_registered(self):
        """查询未注册模型应抛出 AppError。"""
        from shared.errors import AppError
        with self.assertRaises(AppError):
            self.registry.get_model_info("nonexistent")

    def test_get_model_path(self):
        """获取模型路径。"""
        self.registry.register(
            name="test_model",
            display_name="测试模型",
            version="1.0",
            file_name="test.onnx",
            source="test",
        )
        path = self.registry.get_model_path("test_model")
        self.assertTrue(path.endswith("test.onnx"))
        self.assertTrue(path.startswith(self.registry.model_root))

    def test_is_model_file_present(self):
        """模型文件存在性检查。"""
        info = self.registry.register(
            name="test_model",
            display_name="测试模型",
            version="1.0",
            file_name="test.onnx",
            source="test",
        )
        self.assertFalse(self.registry.is_model_file_present("test_model"))

    def test_list_models(self):
        """列出所有已注册模型。"""
        for i in range(3):
            self.registry.register(
                name=f"model_{i}",
                display_name=f"模型{i}",
                version="1.0",
                file_name=f"model_{i}.onnx",
                source="test",
            )
        self.assertEqual(len(self.registry.list_models()), 3)

    def test_list_pending_models(self):
        """列出未下载的模型。"""
        self.registry.register(
            name="pending_model",
            display_name="待下载模型",
            version="1.0",
            file_name="pending.onnx",
            source="test",
        )
        pending = self.registry.list_pending_models()
        self.assertEqual(len(pending), 1)

    def test_verify_model_file_missing(self):
        """校验不存在的模型文件应返回 False。"""
        self.registry.register(
            name="missing_model",
            display_name="缺失模型",
            version="1.0",
            file_name="missing.onnx",
            source="test",
        )
        self.assertFalse(self.registry.verify_model("missing_model"))

    def test_verify_model_with_file(self):
        """校验存在的模型文件（无 SHA256）。"""
        import pathlib
        model_path = pathlib.Path(self.registry.model_root) / "valid.onnx"
        model_path.write_bytes(b"fake onnx model data")

        self.registry.register(
            name="valid_model",
            display_name="有效模型",
            version="1.0",
            file_name="valid.onnx",
            source="test",
        )
        self.assertTrue(self.registry.verify_model("valid_model"))

    def test_verify_model_sha256(self):
        """校验模型 SHA256。"""
        import hashlib
        import pathlib

        data = b"test model data for sha256"
        expected_hash = hashlib.sha256(data).hexdigest()

        model_path = pathlib.Path(self.registry.model_root) / "hashed.onnx"
        model_path.write_bytes(data)

        self.registry.register(
            name="hashed_model",
            display_name="有哈希的模型",
            version="1.0",
            file_name="hashed.onnx",
            source="test",
            sha256=expected_hash,
        )
        self.assertTrue(self.registry.verify_model("hashed_model"))

    def test_list_ready_models(self):
        """列出已就绪的模型。"""
        import pathlib
        pathlib.Path(self.registry.model_root, "ready.onnx").write_bytes(b"data")

        self.registry.register(
            name="ready_model",
            display_name="就绪模型",
            version="1.0",
            file_name="ready.onnx",
            source="test",
        )
        ready = self.registry.list_ready_models()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].name, "ready_model")


class TestFileIOModule(unittest.TestCase):
    """测试 6：file_io 模块。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="tt_test_fileio_")
        # 创建测试文件
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("hello world")

    def test_read_file_bytes(self):
        """读取文件二进制数据。"""
        from shared.file_io import read_file_bytes
        data = read_file_bytes(self.test_file)
        self.assertEqual(data, b"hello world")

    def test_read_file_not_found(self):
        """读取不存在文件应抛出 AppError。"""
        from shared.file_io import read_file_bytes
        from shared.errors import AppError
        with self.assertRaises(AppError):
            read_file_bytes(os.path.join(self.temp_dir, "nonexistent.txt"))

    def test_write_file_bytes(self):
        """写入文件。"""
        from shared.file_io import write_file_bytes
        path = os.path.join(self.temp_dir, "output.bin")
        result = write_file_bytes(path, b"binary data")
        self.assertTrue(os.path.exists(path))
        self.assertTrue(os.path.isabs(result))

    def test_write_file_no_overwrite(self):
        """不允许覆盖已存在文件。"""
        from shared.file_io import write_file_bytes
        from shared.errors import AppError

        path = os.path.join(self.temp_dir, "exists.bin")
        write_file_bytes(path, b"first write")
        with self.assertRaises(AppError):
            write_file_bytes(path, b"second write")

    def test_write_file_overwrite(self):
        """允许覆盖已存在文件。"""
        from shared.file_io import write_file_bytes
        path = os.path.join(self.temp_dir, "overwrite.bin")
        write_file_bytes(path, b"first")
        write_file_bytes(path, b"second", overwrite=True)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), b"second")

    def test_get_file_info(self):
        """获取文件信息。"""
        from shared.file_io import get_file_info

        # 创建一个 PNG 后缀的文件
        png_path = os.path.join(self.temp_dir, "image.png")
        with open(png_path, "wb") as f:
            f.write(b"\x89PNG fake")

        info = get_file_info(png_path)
        self.assertEqual(info.suffix, ".png")
        self.assertTrue(info.is_image)
        self.assertFalse(info.is_pdf)
        self.assertGreater(info.size_bytes, 0)

    def test_get_file_info_not_found(self):
        """获取不存在文件的信息应抛出 AppError。"""
        from shared.file_io import get_file_info
        from shared.errors import AppError
        with self.assertRaises(AppError):
            get_file_info(os.path.join(self.temp_dir, "nope.png"))

    def test_validate_file_format(self):
        """文件格式校验。"""
        from shared.file_io import validate_file
        from shared.errors import AppError

        png_path = os.path.join(self.temp_dir, "valid.png")
        with open(png_path, "wb") as f:
            f.write(b"data")

        # 允许 PNG，应通过
        info = validate_file(png_path, allowed_suffixes=[".png"])
        self.assertEqual(info.suffix, ".png")

        # 不允许 TXT，应失败
        with self.assertRaises(AppError):
            validate_file(png_path, allowed_suffixes=[".jpg"])

    def test_validate_file_size(self):
        """文件大小校验。"""
        from shared.file_io import validate_file
        from shared.errors import AppError

        big_path = os.path.join(self.temp_dir, "big.bin")
        with open(big_path, "wb") as f:
            f.write(b"x" * 200)

        # 100 字节上限，200 字节文件应失败
        with self.assertRaises(AppError):
            validate_file(big_path, max_size_bytes=100)

    def test_ensure_directory(self):
        """创建目录。"""
        from shared.file_io import ensure_directory

        new_dir = os.path.join(self.temp_dir, "sub", "deep")
        result = ensure_directory(new_dir)
        self.assertTrue(os.path.isdir(result))

    def test_list_files(self):
        """列出目录文件。"""
        from shared.file_io import list_files

        # 创建几个 test 文件
        for i in range(3):
            with open(os.path.join(self.temp_dir, f"file_{i}.txt"), "w"):
                pass

        files = list_files(self.temp_dir, pattern="*.txt")
        self.assertEqual(len(files), 4)  # 3 new + 1 setUp file

    def test_list_files_recursive(self):
        """递归列出文件。"""
        from shared.file_io import list_files, ensure_directory

        sub = ensure_directory(os.path.join(self.temp_dir, "subdir"))
        with open(os.path.join(sub, "nested.txt"), "w"):
            pass

        files = list_files(self.temp_dir, pattern="*.txt", recursive=True)
        self.assertGreaterEqual(len(files), 1)

    def test_is_safe_path(self):
        """路径安全检查。"""
        from shared.file_io import is_safe_path

        self.assertTrue(is_safe_path(self.temp_dir, self.test_file))
        self.assertFalse(is_safe_path(self.temp_dir, r"C:\Windows\System32\cmd.exe"))


class TestLoggingModule(unittest.TestCase):
    """测试 7：logging 模块。"""

    def setUp(self):
        import logging
        # 重置日志系统
        root = logging.getLogger()
        root.handlers.clear()

    def test_setup_logging(self):
        """日志初始化。"""
        from shared.logging import setup_logging
        import logging

        log_dir = tempfile.mkdtemp(prefix="tt_test_logs_")
        setup_logging(level=logging.DEBUG, log_dir=log_dir, console=False)

        # 检查是否有 handler
        root = logging.getLogger()
        self.assertGreater(len(root.handlers), 0)

        # 检查日志文件是否创建
        import time
        time.sleep(0.1)  # 等文件 flush
        log_files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
        self.assertGreaterEqual(len(log_files), 1)

    def test_get_logger(self):
        """获取 logger 适配器。"""
        from shared.logging import get_logger, setup_logging
        import logging

        log_dir = tempfile.mkdtemp(prefix="tt_test_logs2_")
        # 先重置
        root = logging.getLogger()
        root.handlers.clear()

        setup_logging(level=logging.DEBUG, log_dir=log_dir, console=False)
        logger = get_logger("test_module", request_id="req-test-123")
        self.assertIsNotNone(logger)
        # LoggerAdapter 的 logger 属性指向实际的 Logger
        self.assertEqual(logger.logger.name, "test_module")

    def test_set_log_level(self):
        """动态修改日志级别。"""
        from shared.logging import set_log_level, setup_logging
        import logging

        log_dir = tempfile.mkdtemp(prefix="tt_test_logs3_")
        root = logging.getLogger()
        root.handlers.clear()

        setup_logging(level=logging.INFO, log_dir=log_dir, console=False)
        set_log_level(logging.WARNING)
        self.assertEqual(root.level, logging.WARNING)

    def test_auto_init_logging(self):
        """日志自动初始化（首次调用 get_logger 时）。"""
        import logging
        root = logging.getLogger()
        root.handlers.clear()

        # 重置模块级标志
        import shared.logging as log_mod
        log_mod._log_initialized = False

        from shared.logging import get_logger
        log_dir = tempfile.mkdtemp(prefix="tt_test_logs4_")
        log_mod.DEFAULT_LOG_DIR = log_dir  # 临时改路径

        logger = get_logger("auto_test")
        self.assertIsNotNone(logger)
        self.assertTrue(log_mod._log_initialized)
        # 恢复默认值
        log_mod.DEFAULT_LOG_DIR = r"D:\localPath\logs"


class TestInitExports(unittest.TestCase):
    """测试 __init__.py 导出的公共 API 是否齐全。"""

    def test_all_exports_importable(self):
        """确认 __init__.py __all__ 中所有导出都可导入。"""
        import shared
        for name in shared.__all__:
            obj = getattr(shared, name, None)
            self.assertIsNotNone(
                obj,
                f"shared.__all__ 中的 {name} 无法从 shared 获取",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
