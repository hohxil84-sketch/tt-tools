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

import statistics
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

# 默认引擎文字置信度阈值（传给 RapidOCR，较低以保留更多结果供 UI 层过滤）
DEFAULT_ENGINE_TEXT_SCORE = 0.0

# 默认 UI 遮罩阈值（低于此值的文字在 formatted_text 中替换为 □）
DEFAULT_MASK_BELOW_SCORE = 0.5

# 最大图片边长（像素），超过会自动缩放
DEFAULT_MAX_SIDE_LEN = 2000

# 模块级日志
logger = get_logger("local-worker.ocr")


def format_ocr_result(
    text_lines: List[OCRBox],
    mask_below_score: Optional[float] = None,
    image_width: Optional[int] = None,
) -> str:
    """按原图坐标排版 OCR 识别结果，生成保留视觉格式的文本。

    算法：
    1. 按文字框中心点 y 坐标分组为行（动态阈值 = 中位文字框高度 × 0.5）
    2. 同一行内按 x 坐标从左到右排序
    3. 行之间按 y 坐标从上到下排序
    4. 根据 x 坐标差距插入空格，还原列间距
    5. 大 y 间距保留额外空行（段落分隔）
    6. 如果指定 mask_below_score，低于阈值的文字替换为等长 □

    参数：
        text_lines: OCR 识别结果列表。
        mask_below_score: UI 置信度遮罩阈值 (0.0~1.0)，None 表示不遮罩。
        image_width: 原图宽度（像素），预留用于更精确的间距计算。

    返回：
        格式化后的多行文本，保留换行和空格排版。
    """
    if not text_lines:
        return ""

    # ---- 辅助函数：计算文字框中心点 ----
    def _center_y(box: List[List[float]]) -> float:
        """文字框中心 y 坐标。"""
        if box and len(box) >= 4:
            return sum(p[1] for p in box[:4]) / 4.0
        return 0.0

    def _center_x(box: List[List[float]]) -> float:
        """文字框中心 x 坐标。"""
        if box and len(box) >= 4:
            return sum(p[0] for p in box[:4]) / 4.0
        return 0.0

    def _box_width(box: List[List[float]]) -> float:
        """文字框近似宽度（取上下边平均值）。"""
        if box and len(box) >= 4:
            top_w = abs(box[1][0] - box[0][0])
            bot_w = abs(box[2][0] - box[3][0])
            return (top_w + bot_w) / 2.0
        return 50.0

    def _box_height(box: List[List[float]]) -> float:
        """文字框近似高度（取左右边平均值）。"""
        if box and len(box) >= 4:
            left_h = abs(box[3][1] - box[0][1])
            right_h = abs(box[2][1] - box[1][1])
            return (left_h + right_h) / 2.0
        return 20.0

    # ---- 1. 计算动态行分组阈值 ----
    heights = [_box_height(line.box) for line in text_lines if line.box and len(line.box) >= 4]
    if heights:
        median_height = statistics.median(heights)
        row_threshold = max(median_height * 0.5, 5.0)  # 至少 5 像素
    else:
        row_threshold = 10.0

    # ---- 2. 按 y 中心初步排序 ----
    sorted_lines = sorted(text_lines, key=lambda l: (_center_y(l.box), _center_x(l.box)))

    # ---- 3. 按 y 邻近度分组成行 ----
    rows: List[List[OCRBox]] = []
    current_row = [sorted_lines[0]]
    current_y = _center_y(sorted_lines[0].box)

    for line in sorted_lines[1:]:
        y = _center_y(line.box)
        if abs(y - current_y) <= row_threshold:
            current_row.append(line)
        else:
            rows.append(current_row)
            current_row = [line]
            current_y = y
    rows.append(current_row)

    # ---- 4. 每行内按 x 坐标从左到右排序 ----
    for row in rows:
        row.sort(key=lambda l: _center_x(l.box))

    # ---- 5. 构建格式化文本行 ----
    # 根据图片宽度估算每像素对应的空格数
    if image_width and image_width > 0:
        px_per_space = max(image_width / 200.0, 4.0)  # 粗略估计：约 200 字符宽
    else:
        px_per_space = 8.0  # 默认每 8px 视为一个空格宽度

    formatted_rows: List[str] = []
    for row in rows:
        parts: List[str] = []
        prev_right_edge: Optional[float] = None

        for line in row:
            # 应用 □ 遮罩
            text = line.text
            if mask_below_score is not None and line.score < mask_below_score:
                text = "□" * len(text)

            x_center = _center_x(line.box)
            box_w = _box_width(line.box)

            if prev_right_edge is not None:
                gap = x_center - prev_right_edge - box_w * 0.5
                # 如果 gap 为负（文字框重叠），放一个空格；否则按比例插入空格
                if gap > px_per_space * 0.5:
                    num_spaces = max(1, round(gap / px_per_space))
                else:
                    num_spaces = 1 if gap > -px_per_space else 0
                parts.append(" " * num_spaces)

            parts.append(text)
            prev_right_edge = x_center + box_w * 0.5

        formatted_rows.append("".join(parts))

    # ---- 6. 大 y 间距加空行（段落分隔） ----
    result_lines: List[str] = []
    prev_row_bottom: Optional[float] = None

    for i, (row, formatted) in enumerate(zip(rows, formatted_rows)):
        if row:
            row_top = min(_center_y(line.box) - _box_height(line.box) * 0.5 for line in row)
            if prev_row_bottom is not None:
                gap = row_top - prev_row_bottom
                # 间距超过 2 倍行高阈值时插入空行
                if gap > row_threshold * 3.0:
                    result_lines.append("")

        result_lines.append(formatted)

        if row:
            prev_row_bottom = max(
                _center_y(line.box) + _box_height(line.box) * 0.5 for line in row
            )

    return "\n".join(result_lines)


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
            text_score=0.0,       # 引擎过滤阈值（低值保留更多结果）
            use_dml=True,
            use_angle_cls=False,
        )
        result = engine.recognize(np_array, mask_below_score=0.5)

        # 作为上下文管理器（自动释放资源）
        with OCREngine() as engine:
            result = engine.recognize(img_bytes)

    线程安全：每个 OCREngine 实例独立持有 RapidOCR 引擎，不共享状态。
    建议每个线程创建独立实例，或使用上下文管理器。

    阈值说明：
        text_score:  传给 RapidOCR 的引擎过滤阈值。设为较低值（如 0.0）可保留
                     低置信度结果，让 UI 层自行决定显示/遮罩。
        mask_below_score: recognize() 时的可选参数，用于在 formatted_text
                         中将低于该阈值的文字替换为 □。
    """

    def __init__(
        self,
        text_score: float = DEFAULT_ENGINE_TEXT_SCORE,
        use_det: bool = True,
        use_cls: bool = True,
        use_rec: bool = True,
        use_dml: bool = False,
        max_side_len: int = DEFAULT_MAX_SIDE_LEN,
        request_id: Optional[str] = None,
    ) -> None:
        """初始化 OCR 引擎。

        参数：
            text_score: 文字识别置信度阈值 (0.0 ~ 1.0)，传给 RapidOCR。
                        低于此值的结果会被 RapidOCR 过滤。
                        默认 0.0 以保留所有结果，UI 过滤由 mask_below_score 控制。
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
            "初始化 OCR 引擎 | engine_text_score=%.2f use_det=%s use_cls=%s use_rec=%s "
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
        mask_below_score: Optional[float] = None,
    ) -> OCRResult:
        """对单张图片执行 OCR 识别。

        参数：
            image: 图片输入，支持：
                - str / Path: 图片文件路径
                - np.ndarray: 图片像素数组（BGR 或 RGB，shape: HxWx3）
                - bytes: 图片二进制数据（PNG/JPEG 等格式）
            image_name: 图片名称（仅用于日志），不传时从路径提取。
            mask_below_score: UI 置信度遮罩阈值 (0.0~1.0)。
                              低于此值的文字在 formatted_text 中替换为 □。
                              None 表示不遮罩。

        返回：
            OCRResult: 包含所有识别文字行、耗时、置信度的结构化结果。
                formatted_text 字段包含按原图坐标排版后的文本。

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

        # 生成排版格式化文本（按原图坐标排列，保留缩进和空格）
        formatted_text = format_ocr_result(
            text_lines,
            mask_below_score=mask_below_score,
            image_width=image_width,
        )

        result = OCRResult(
            text_lines=text_lines,
            total_text=total_text,
            formatted_text=formatted_text,
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
                        formatted_text="",
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
        """当前引擎置信度阈值。"""
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
    text_score: float = DEFAULT_ENGINE_TEXT_SCORE,
    use_dml: bool = False,
    mask_below_score: Optional[float] = None,
) -> OCRResult:
    """便捷函数：对单张图片执行 OCR 识别（自动创建和释放引擎）。

    适用于一次性识别场景。批量识别请使用 OCREngine 实例。

    用法：
        result = recognize_image("path/to/image.png")
        print(result.total_text)
    """
    with OCREngine(text_score=text_score, use_dml=use_dml) as engine:
        return engine.recognize(image, mask_below_score=mask_below_score)
