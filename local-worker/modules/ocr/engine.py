"""
local-worker/modules/ocr/engine — OCR 引擎核心

基于 RapidOCR (ONNX Runtime) 的本地 OCR 识别实现。
支持：
  - 从图片文件路径识别
  - 从 NumPy 数组识别（桌面端或共享层预处理后传入）
  - 从二进制数据识别
  - CPU 推理（ONNX Runtime CPU），可选 DirectML GPU 加速
  - 文字方向自动矫正（分类器）

模型文件：
  - ch_PP-OCRv4_det_infer.onnx  — 文字检测模型（约 4.5 MB）
  - ch_ppocr_mobile_v2.0_cls_infer.onnx — 文字方向分类模型（约 0.6 MB）
  - ch_PP-OCRv4_rec_infer.onnx — 文字识别模型（约 10.4 MB）
  模型随 rapidocr-onnxruntime 包安装，存储在 site-packages 下。

依赖：
  - rapidocr-onnxruntime >= 1.4.0
  - onnxruntime >= 1.7.0
  - shared (local-worker/shared)
"""

import time
import uuid
from pathlib import Path
from typing import List, Optional, Union

import numpy as np

from shared.errors import AppError, ErrorCode
from shared.logging import get_logger
from shared.file_io import validate_file
from shared.runtime import detect_gpu_info

from .results import OCRBox, OCRResult

# 本模块支持的图片格式后缀
SUPPORTED_IMAGE_SUFFIXES = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"]

# RapidOCR 版本（安装时确定）
RAPIDOCR_VERSION = "1.4.4"

# 默认文字置信度阈值
DEFAULT_TEXT_SCORE = 0.5

# 最大图片边长（像素），超过会自动缩放
DEFAULT_MAX_SIDE_LEN = 2000

# 模块级日志
logger = get_logger("local-worker.ocr")


class OCREngine:
    """本地 OCR 识别引擎（RapidOCR 封装）。

    封装了 RapidOCR 的初始化、参数配置和识别流程，
    将原始识别结果转换为统一的 OCRResult 格式。

    用法：
        # 基础用法
        engine = OCREngine()
        result = engine.recognize("path/to/image.png")
        print(result.total_text)

        # 自定义参数
        engine = OCREngine(
            text_score=0.7,
            use_dml=True,
            use_angle_cls=False,
        )
        result = engine.recognize(np_array)

        # 作为上下文管理器（自动释放资源）
        with OCREngine() as engine:
            result = engine.recognize(img_bytes)

    线程安全：每个 OCREngine 实例独立持有 RapidOCR 引擎，不共享状态。
    建议每个线程创建独立实例，或使用上下文管理器。
    """

    def __init__(
        self,
        text_score: float = DEFAULT_TEXT_SCORE,
        use_det: bool = True,
        use_cls: bool = True,
        use_rec: bool = True,
        use_dml: bool = False,
        max_side_len: int = DEFAULT_MAX_SIDE_LEN,
        request_id: Optional[str] = None,
    ) -> None:
        """初始化 OCR 引擎。

        参数：
            text_score: 文字识别置信度阈值 (0.0 ~ 1.0)，低于此值的结果会被过滤。
            use_det: 是否启用文字检测（定位文字区域）。
            use_cls: 是否启用文字方向分类器（自动旋转 180° 颠倒文字）。
            use_rec: 是否启用文字识别。
            use_dml: 是否尝试使用 DirectML GPU 加速（仅 Windows）。
            max_side_len: 图片最大边长，超过会等比缩放。
            request_id: 请求追踪 ID，不传则自动生成。

        异常：
            AppError: 模型加载失败时抛出。
        """
        self._request_id = request_id or str(uuid.uuid4())
        self._logger = get_logger("local-worker.ocr", request_id=self._request_id)

        # 记录引擎参数
        self._text_score = text_score
        self._use_det = use_det
        self._use_cls = use_cls
        self._use_rec = use_rec
        self._use_dml = use_dml
        self._max_side_len = max_side_len

        # 检测 GPU 可用性，决定是否使用 DirectML
        self._gpu_info = detect_gpu_info()
        actual_use_dml = use_dml and self._gpu_info.dml_available

        if use_dml and not self._gpu_info.dml_available:
            self._logger.warning(
                "请求启用 DirectML 但当前系统不可用，回退到 CPU 推理"
            )

        self._logger.info(
            "初始化 OCR 引擎 | text_score=%.2f use_det=%s use_cls=%s use_rec=%s "
            "use_dml=%s actual_dml=%s max_side_len=%d",
            text_score, use_det, use_cls, use_rec,
            use_dml, actual_use_dml, max_side_len,
        )

        # 初始化 RapidOCR 引擎
        try:
            self._engine = self._create_engine(actual_use_dml)
        except Exception as e:
            raise AppError(
                ErrorCode.MODEL_LOAD_FAILED,
                f"OCR 模型加载失败: {e}",
                details={
                    "engine": "RapidOCR",
                    "version": RAPIDOCR_VERSION,
                    "error": str(e),
                },
                request_id=self._request_id,
            )

        self._closed = False

    def _create_engine(self, use_dml: bool):
        """创建 RapidOCR 引擎实例。

        延迟导入以确保依赖在安装后才加载。
        """
        from rapidocr_onnxruntime import RapidOCR

        engine = RapidOCR(
            text_score=self._text_score,
            use_det=self._use_det,
            use_cls=self._use_cls,
            use_rec=self._use_rec,
            use_dml=use_dml,
            max_side_len=self._max_side_len,
            print_verbose=False,
        )
        return engine

    # ---- 公共识别接口 ----

    def recognize(
        self,
        image: Union[str, np.ndarray, bytes, Path],
        image_name: Optional[str] = None,
    ) -> OCRResult:
        """对单张图片执行 OCR 识别。

        参数：
            image: 图片输入，支持：
                - str / Path: 图片文件路径
                - np.ndarray: 图片像素数组（BGR 或 RGB，shape: HxWx3）
                - bytes: 图片二进制数据（PNG/JPEG 等格式）
            image_name: 图片名称（仅用于日志），不传时从路径提取。

        返回：
            OCRResult: 包含所有识别文字行、耗时、置信度的结构化结果。

        异常：
            AppError: 文件不存在、格式不支持、识别失败时抛出。
        """
        if self._closed:
            raise AppError(
                ErrorCode.INTERNAL,
                "OCR 引擎已关闭，请创建新实例",
                request_id=self._request_id,
            )

        # 输入预处理：统一转为 RapidOCR 接受的格式
        input_data, image_width, image_height = self._prepare_input(image)
        file_label = image_name or self._get_image_label(image)

        self._logger.info(
            "开始 OCR 识别 | image=%s size=%dx%d",
            file_label, image_width, image_height,
        )

        try:
            # 调用 RapidOCR
            start_time = time.perf_counter()
            raw_result, elapse_list = self._engine(input_data)
            total_elapsed = time.perf_counter() - start_time

        except Exception as e:
            raise AppError(
                ErrorCode.MODEL_INFERENCE_FAILED,
                f"OCR 推理失败: {e}",
                details={
                    "image": file_label,
                    "image_width": image_width,
                    "image_height": image_height,
                    "error": str(e),
                },
                request_id=self._request_id,
            )

        # 解析耗时列表
        # RapidOCR 返回的 elapse_list 格式：[det_time, cls_time, rec_time]
        # 注意：无文字检测结果时 elapse_list 可能为 None
        if elapse_list and len(elapse_list) > 0:
            elapsed_det = float(elapse_list[0]) if len(elapse_list) > 0 else 0.0
            elapsed_cls = float(elapse_list[1]) if len(elapse_list) > 1 else None
            elapsed_rec = float(elapse_list[-1])
        else:
            elapsed_det = 0.0
            elapsed_cls = None
            elapsed_rec = 0.0

        # 解析识别结果
        text_lines: List[OCRBox] = []
        if raw_result:
            for item in raw_result:
                # RapidOCR 返回格式：[[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], text, score]
                box, text, score = item
                text_lines.append(
                    OCRBox(
                        text=str(text),
                        score=float(score),
                        box=[[float(p[0]), float(p[1])] for p in box],
                    )
                )

        # 按阅读顺序拼接文本（左上到右下，从上到下）
        total_text = "".join(line.text for line in text_lines)

        result = OCRResult(
            text_lines=text_lines,
            total_text=total_text,
            elapsed_total=round(total_elapsed, 4),
            elapsed_det=round(elapsed_det, 4),
            elapsed_cls=round(elapsed_cls, 4) if elapsed_cls is not None else None,
            elapsed_rec=round(elapsed_rec, 4),
            engine_name="RapidOCR",
            engine_version=RAPIDOCR_VERSION,
            image_width=image_width,
            image_height=image_height,
        )

        self._logger.info(
            "OCR 识别完成 | image=%s lines=%d avg_score=%.3f elapsed=%.3fs",
            file_label, result.line_count, result.avg_score, total_elapsed,
        )

        return result

    def recognize_file(self, file_path: str) -> OCRResult:
        """从文件路径执行 OCR 识别（带文件校验）。

        在校验文件存在性和格式后调用 recognize()。
        """
        # 校验文件
        validate_file(
            file_path,
            allowed_suffixes=SUPPORTED_IMAGE_SUFFIXES,
        )
        return self.recognize(file_path)

    def recognize_batch(
        self,
        images: List[Union[str, np.ndarray, bytes]],
    ) -> List[OCRResult]:
        """批量识别多张图片。

        参数：
            images: 图片列表，每项可以是路径、numpy 数组或 bytes。

        返回：
            OCRResult 列表，与输入顺序一致。
            单张图片识别失败不会中断整个批次，
            失败图片对应的结果中 text_lines 为空且 total_text 为错误信息。
        """
        results: List[OCRResult] = []
        for i, img in enumerate(images):
            try:
                result = self.recognize(img, image_name=f"batch[{i}]")
                results.append(result)
            except AppError as e:
                self._logger.error(
                    "批量识别第 %d 张失败: %s", i, e.message
                )
                # 返回一个空结果标记失败
                results.append(
                    OCRResult(
                        text_lines=[],
                        total_text=f"[ERROR] {e.message}",
                        elapsed_total=0.0,
                        elapsed_det=0.0,
                        elapsed_cls=None,
                        elapsed_rec=0.0,
                        engine_name="RapidOCR",
                        engine_version=RAPIDOCR_VERSION,
                    )
                )
        return results

    # ---- 资源管理 ----

    def close(self) -> None:
        """释放 OCR 引擎资源。

        调用后此实例不可再用，需创建新实例。
        """
        if self._closed:
            return
        self._closed = True
        self._logger.info("OCR 引擎已关闭")
        # RapidOCR 没有显式 close 方法，清除引用让 GC 回收
        self._engine = None

    def __enter__(self) -> "OCREngine":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
        return None

    def __del__(self) -> None:
        """析构时自动释放资源。"""
        if not self._closed:
            try:
                self.close()
            except Exception:
                pass  # 析构函数中忽略所有异常

    # ---- 内部方法 ----

    def _prepare_input(
        self, image: Union[str, np.ndarray, bytes, Path]
    ) -> tuple:
        """预处理输入：统一转换为 RapidOCR 可接受的格式，同时获取图片尺寸。

        返回：
            (input_data, width, height)
        """
        if isinstance(image, (str, Path)):
            # 文件路径
            path = str(image)
            if not Path(path).is_file():
                raise AppError(
                    ErrorCode.FILE_NOT_FOUND,
                    f"图片文件未找到: {path}",
                    details={"path": path},
                    request_id=self._request_id,
                )
            # RapidOCR 直接接受文件路径，同时读取宽高
            import cv2
            img_array = cv2.imread(path)
            if img_array is None:
                raise AppError(
                    ErrorCode.FILE_READ_ERROR,
                    f"无法读取图片: {path}，文件可能损坏或格式不支持",
                    details={"path": path},
                    request_id=self._request_id,
                )
            height, width = img_array.shape[:2]
            return path, width, height

        elif isinstance(image, np.ndarray):
            # NumPy 数组
            if image.ndim < 2:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    "图片数组维度不足，需要至少 2 维 (HxW) 或 3 维 (HxWxC)",
                    details={"ndim": image.ndim},
                    request_id=self._request_id,
                )
            height, width = image.shape[:2]
            return image, width, height

        elif isinstance(image, bytes):
            # 二进制数据
            import cv2
            nparr = np.frombuffer(image, np.uint8)
            img_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img_array is None:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    "无法解码图片二进制数据，格式可能不支持",
                    details={"data_len": len(image)},
                    request_id=self._request_id,
                )
            height, width = img_array.shape[:2]
            return img_array, width, height

        else:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"不支持的图片输入类型: {type(image).__name__}",
                details={"supported_types": ["str", "Path", "np.ndarray", "bytes"]},
                request_id=self._request_id,
            )

    def _get_image_label(
        self, image: Union[str, np.ndarray, bytes, Path]
    ) -> str:
        """从输入中提取图片标签（用于日志）。"""
        if isinstance(image, (str, Path)):
            return Path(image).name
        elif isinstance(image, np.ndarray):
            return f"ndarray({image.shape})"
        elif isinstance(image, bytes):
            return f"bytes({len(image)})"
        return "unknown"

    # ---- 属性 ----

    @property
    def is_closed(self) -> bool:
        """引擎是否已关闭。"""
        return self._closed

    @property
    def text_score(self) -> float:
        """当前置信度阈值。"""
        return self._text_score

    @property
    def using_dml(self) -> bool:
        """是否使用 DirectML GPU 加速。"""
        return self._use_dml and self._gpu_info.dml_available

    @property
    def gpu_info(self):
        """当前 GPU 检测信息。"""
        return self._gpu_info


# ---- 便捷函数 ----

def recognize_image(
    image: Union[str, np.ndarray, bytes],
    text_score: float = DEFAULT_TEXT_SCORE,
    use_dml: bool = False,
) -> OCRResult:
    """便捷函数：对单张图片执行 OCR 识别（自动创建和释放引擎）。

    适用于一次性识别场景。批量识别请使用 OCREngine 实例。

    用法：
        result = recognize_image("path/to/image.png")
        print(result.total_text)
    """
    with OCREngine(text_score=text_score, use_dml=use_dml) as engine:
        return engine.recognize(image)
