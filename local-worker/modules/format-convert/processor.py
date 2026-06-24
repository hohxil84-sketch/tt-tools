"""
local-worker/modules/format-convert/processor — 格式转换、压缩、裁剪、旋转核心处理器

基于 Pillow 实现纯本地图像处理，支持：
  - 格式转换：PNG / JPEG / BMP / TIFF / WEBP / GIF / ICO 互转
  - 压缩：有损质量压缩（JPEG/WEBP）、PNG 无损压缩
  - 裁剪：矩形区域裁剪、锚点自动裁剪
  - 旋转：直角旋转（90°/180°/270°）、任意角度旋转（含画布扩展）

不依赖 GPU，不涉及 AI 模型，不调用云端 API。
"""

import io
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from PIL import Image

# 引用 local-worker/shared 公共层
from shared.errors import AppError, ErrorCode
from shared.logging import get_logger

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

# 模块 logger
logger = get_logger("local-worker.format-convert")


class FormatConverter:
    """格式转换、压缩、裁剪、旋转处理器。

    封装所有图像处理操作，纯本地执行。
    支持文件路径、bytes 和 PIL Image 多种输入方式。

    用法：
        converter = FormatConverter()

        # 格式转换
        result = converter.convert_format("input.png", ConvertFormat.JPEG, quality=85)

        # 压缩
        result = converter.compress("input.png", quality=60)

        # 裁剪
        result = converter.crop("input.png", left=100, top=50, width=400, height=300)
        # 或居中对齐裁剪
        result = converter.crop_center("input.png", 400, 300)

        # 旋转
        result = converter.rotate("input.png", 90)
        result = converter.rotate_arbitrary("input.png", 45.5)
    """

    def __init__(self) -> None:
        """初始化处理器。无需模型，只依赖 Pillow。"""
        pass

    # ===== 主入口：格式转换 =====

    def convert_format(
        self,
        image: Union[str, bytes, Image.Image],
        target_format: ConvertFormat = ConvertFormat.ORIGINAL,
        quality: int = DEFAULT_JPEG_QUALITY,
        png_compress: int = DEFAULT_PNG_COMPRESS_LEVEL,
        webp_quality: int = DEFAULT_WEBP_QUALITY,
        preserve_alpha: bool = True,
        output_path: Optional[str] = None,
    ) -> OperationResult:
        """格式转换主入口。

        将输入图片转换为指定的输出格式。

        参数：
            image: 输入图像，支持文件路径、bytes 或 PIL Image 对象。
            target_format: 目标格式，ORIGINAL 表示保持原格式。
            quality: JPEG/WEBP 输出质量（1-100）。
            png_compress: PNG 压缩级别（0-9）。
            webp_quality: WEBP 输出质量（1-100）。
            preserve_alpha: 是否保留透明通道。
            output_path: 可选输出文件路径。

        返回：
            OperationResult：包含输出数据和元信息的结构化结果。
        """
        params = FormatConvertParams(
            format=target_format,
            jpeg_quality=quality,
            png_compress=png_compress,
            webp_quality=webp_quality,
            preserve_alpha=preserve_alpha,
        )
        return self._execute_convert_format(image, params, output_path)

    def convert_format_with_params(
        self,
        image: Union[str, bytes, Image.Image],
        params: FormatConvertParams,
        output_path: Optional[str] = None,
    ) -> OperationResult:
        """使用参数对象执行格式转换。"""
        return self._execute_convert_format(image, params, output_path)

    def _execute_convert_format(
        self,
        image: Union[str, bytes, Image.Image],
        params: FormatConvertParams,
        output_path: Optional[str],
    ) -> OperationResult:
        """格式转换核心实现。"""
        start_time = time.perf_counter()
        warnings: List[str] = []
        source_path = None

        try:
            # 校验参数
            validation_errors = params.validate()
            if validation_errors:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    f"格式转换参数无效: {'; '.join(validation_errors)}",
                    details={"errors": validation_errors},
                )

            # 打开图像
            img, source_path, source_format = self._open_image(image)

            source_width, source_height = img.size
            input_size = 0  # 用于计算压缩比

            # 确定目标格式
            if params.format == ConvertFormat.ORIGINAL:
                target_format = self._detect_format(img, source_path)
            else:
                target_format = params.format

            # 格式转换编码
            output_data, actual_format = self._encode_to_format(
                img, target_format, params
            )

            # 写入文件
            if output_path:
                self._save_to_file(output_data, output_path)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            result = OperationResult(
                success=True,
                source_path=source_path,
                source_width=source_width,
                source_height=source_height,
                output_width=source_width,
                output_height=source_height,
                output_format=actual_format,
                output_size=len(output_data),
                output_data=output_data,
                warnings=warnings,
                elapsed_ms=round(elapsed_ms, 2),
            )

            logger.info(
                "格式转换完成 | %dx%d | %s → %s | size=%d bytes | elapsed=%.1fms",
                source_width, source_height,
                source_format or "bytes", actual_format,
                len(output_data), elapsed_ms,
            )

            return result

        except AppError:
            raise
        except Exception as e:
            raise AppError(
                ErrorCode.INTERNAL,
                f"格式转换失败: {e}",
                details={"error": str(e)},
            )

    # ===== 主入口：压缩 =====

    def compress(
        self,
        image: Union[str, bytes, Image.Image],
        quality: int = 75,
        target_format: ConvertFormat = ConvertFormat.ORIGINAL,
        png_compress: int = 9,
        max_size_bytes: Optional[int] = None,
        output_path: Optional[str] = None,
    ) -> OperationResult:
        """压缩图片。

        对有损格式（JPEG/WEBP）通过降低质量压缩，
        对无损格式（PNG）通过提高压缩级别压缩。

        参数：
            image: 输入图像。
            quality: 有损格式输出质量（1-100），默认 75。
            target_format: 目标格式（ORIGINAL 保持原格式）。
            png_compress: PNG 压缩级别（0-9），默认 9（最高压缩）。
            max_size_bytes: 目标最大文件大小（字节），有损格式通过降质量逼近。
            output_path: 可选输出文件路径。

        返回：
            OperationResult：包含压缩比等信息的结构化结果。
        """
        params = CompressParams(
            format=target_format,
            quality=quality,
            png_compress=png_compress,
            max_size_bytes=max_size_bytes,
        )
        return self._execute_compress(image, params, output_path)

    def compress_with_params(
        self,
        image: Union[str, bytes, Image.Image],
        params: CompressParams,
        output_path: Optional[str] = None,
    ) -> OperationResult:
        """使用参数对象执行压缩。"""
        return self._execute_compress(image, params, output_path)

    def _execute_compress(
        self,
        image: Union[str, bytes, Image.Image],
        params: CompressParams,
        output_path: Optional[str],
    ) -> OperationResult:
        """压缩核心实现。

        有损压缩（JPEG/WEBP）：通过降低 quality 值来减小文件大小。
        无损压缩（PNG）：通过压缩级别控制，或转 JPEG 做大幅有损压缩。
        """
        start_time = time.perf_counter()
        warnings: List[str] = []

        try:
            # 校验参数
            validation_errors = params.validate()
            if validation_errors:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    f"压缩参数无效: {'; '.join(validation_errors)}",
                    details={"errors": validation_errors},
                )

            # 打开图像
            img, source_path, source_format = self._open_image(image)
            source_width, source_height = img.size

            # 计算输入大小（对于文件路径）
            if source_path:
                input_size = os.path.getsize(source_path)
            else:
                # bytes 输入时估算原始大小
                buf = io.BytesIO()
                img.save(buf, format=img.format or "PNG")
                input_size = len(buf.getvalue())

            # 确定目标格式
            if params.format == ConvertFormat.ORIGINAL:
                target_format = self._detect_format(img, source_path)
            else:
                target_format = params.format

            # 执行压缩编码
            output_data, actual_format = self._encode_compressed(
                img, target_format, params, warnings
            )

            # 若指定 max_size_bytes 且使用有损格式，通过迭代降质量逼近目标大小
            if params.max_size_bytes is not None and len(output_data) > params.max_size_bytes:
                if target_format in (ConvertFormat.JPEG, ConvertFormat.WEBP):
                    output_data = self._iterative_quality_compress(
                        img, target_format, len(output_data), params, warnings
                    )
                else:
                    warnings.append(
                        f"max_size_bytes 仅对 JPEG/WEBP 有效，"
                        f"当前格式 {actual_format} 不支持质量迭代调整"
                    )

            output_size = len(output_data)
            compression_ratio = output_size / input_size if input_size > 0 else 1.0

            # 写入文件
            if output_path:
                self._save_to_file(output_data, output_path)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            result = OperationResult(
                success=True,
                source_path=source_path,
                source_width=source_width,
                source_height=source_height,
                output_width=source_width,
                output_height=source_height,
                output_format=actual_format,
                output_size=output_size,
                output_data=output_data,
                compression_ratio=round(compression_ratio, 4),
                warnings=warnings,
                elapsed_ms=round(elapsed_ms, 2),
            )

            logger.info(
                "压缩完成 | %dx%d | format=%s | %d → %d bytes | ratio=%.2f | elapsed=%.1fms",
                source_width, source_height, actual_format,
                input_size, output_size, compression_ratio, elapsed_ms,
            )

            return result

        except AppError:
            raise
        except Exception as e:
            raise AppError(
                ErrorCode.INTERNAL,
                f"压缩失败: {e}",
                details={"error": str(e)},
            )

    # ===== 主入口：裁剪 =====

    def crop(
        self,
        image: Union[str, bytes, Image.Image],
        left: int = 0,
        top: int = 0,
        width: int = 100,
        height: int = 100,
        output_path: Optional[str] = None,
    ) -> OperationResult:
        """矩形区域裁剪。

        参数：
            image: 输入图像。
            left: 裁剪左边界（像素）。
            top: 裁剪上边界（像素）。
            width: 裁剪宽度（像素）。
            height: 裁剪高度（像素）。
            output_path: 可选输出文件路径。

        返回：
            OperationResult。
        """
        params = CropParams(left=left, top=top, width=width, height=height)
        return self._execute_crop(image, params, output_path)

    def crop_with_params(
        self,
        image: Union[str, bytes, Image.Image],
        params: CropParams,
        output_path: Optional[str] = None,
    ) -> OperationResult:
        """使用参数对象执行裁剪。"""
        return self._execute_crop(image, params, output_path)

    def crop_center(
        self,
        image: Union[str, bytes, Image.Image],
        width: int,
        height: int,
        output_path: Optional[str] = None,
    ) -> OperationResult:
        """居中裁剪 — 从图片中心裁剪指定尺寸。

        如果裁剪区域超出原图范围，自动裁剪到图片边界。
        """
        img, source_path, _ = self._open_image(image)
        src_w, src_h = img.size
        left = max(0, (src_w - width) // 2)
        top_val = max(0, (src_h - height) // 2)
        params = CropParams(left=left, top=top_val, width=width, height=height, anchor=CropAnchor.CENTER)
        return self._execute_crop(image, params, output_path)

    def crop_by_anchor(
        self,
        image: Union[str, bytes, Image.Image],
        width: int,
        height: int,
        anchor: CropAnchor = CropAnchor.CENTER,
        output_path: Optional[str] = None,
    ) -> OperationResult:
        """按锚点裁剪。

        参数：
            image: 输入图像。
            width: 裁剪宽度。
            height: 裁剪高度。
            anchor: 对齐方式（CENTER / TOP_LEFT / TOP_RIGHT / BOTTOM_LEFT / BOTTOM_RIGHT）。
            output_path: 可选输出文件路径。
        """
        img, source_path, _ = self._open_image(image)
        src_w, src_h = img.size
        left, top_val = self._calc_anchor_position(src_w, src_h, width, height, anchor)
        params = CropParams(left=left, top=top_val, width=width, height=height, anchor=anchor)
        return self._execute_crop(image, params, output_path)

    def _execute_crop(
        self,
        image: Union[str, bytes, Image.Image],
        params: CropParams,
        output_path: Optional[str],
    ) -> OperationResult:
        """裁剪核心实现。"""
        start_time = time.perf_counter()
        warnings: List[str] = []

        try:
            # 校验参数
            validation_errors = params.validate()
            if validation_errors:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    f"裁剪参数无效: {'; '.join(validation_errors)}",
                    details={"errors": validation_errors},
                )

            # 打开图像
            img, source_path, source_format = self._open_image(image)
            src_w, src_h = img.size

            # 如果使用锚点模式（anchor 不为 None 且 left/top 未由调用者计算）
            if params.anchor is not None:
                left, top_val = self._calc_anchor_position(
                    src_w, src_h, params.width, params.height, params.anchor
                )
            else:
                left, top_val = params.left, params.top

            # 边界检查：裁剪区域必须在原图范围内
            if left < 0 or top_val < 0:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    f"裁剪起点不能为负数: left={left}, top={top_val}",
                    details={"left": left, "top": top_val},
                )

            right = left + params.width
            bottom = top_val + params.height

            if right > src_w:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    f"裁剪区域超出图片右边界: right={right} > src_width={src_w}",
                    details={"right": right, "source_width": src_w},
                )
            if bottom > src_h:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    f"裁剪区域超出图片下边界: bottom={bottom} > src_height={src_h}",
                    details={"bottom": bottom, "source_height": src_h},
                )

            # 执行裁剪 - Pillow crop((left, upper, right, lower))
            cropped = img.crop((left, top_val, right, bottom))

            # 编码输出（保持原格式）
            output_data, actual_format = self._encode_to_format(
                cropped,
                self._detect_format(img, source_path),
                FormatConvertParams(),
            )

            # 写入文件
            if output_path:
                self._save_to_file(output_data, output_path)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            result = OperationResult(
                success=True,
                source_path=source_path,
                source_width=src_w,
                source_height=src_h,
                output_width=params.width,
                output_height=params.height,
                output_format=actual_format,
                output_size=len(output_data),
                output_data=output_data,
                warnings=warnings,
                elapsed_ms=round(elapsed_ms, 2),
            )

            logger.info(
                "裁剪完成 | %dx%d → %dx%d | crop=(%d,%d,%d,%d) | elapsed=%.1fms",
                src_w, src_h, params.width, params.height,
                left, top_val, right, bottom, elapsed_ms,
            )

            return result

        except AppError:
            raise
        except Exception as e:
            raise AppError(
                ErrorCode.INTERNAL,
                f"裁剪失败: {e}",
                details={"error": str(e)},
            )

    # ===== 主入口：旋转 =====

    def rotate(
        self,
        image: Union[str, bytes, Image.Image],
        angle: float,
        expand: bool = True,
        fillcolor: Tuple[int, int, int] = (255, 255, 255),
        output_path: Optional[str] = None,
    ) -> OperationResult:
        """旋转图片。

        对于 90° / 180° / 270° 直角旋转使用高效无损方法，
        其余角度使用 Pillow 插值旋转。

        参数：
            image: 输入图像。
            angle: 旋转角度（正数为顺时针）。
            expand: 是否扩展画布以容纳完整图像。
            fillcolor: 空白区域填充颜色（RGB）。
            output_path: 可选输出文件路径。

        返回：
            OperationResult。
        """
        params = RotateParams(angle=angle, expand=expand, fillcolor=fillcolor)
        return self._execute_rotate(image, params, output_path)

    def rotate_with_params(
        self,
        image: Union[str, bytes, Image.Image],
        params: RotateParams,
        output_path: Optional[str] = None,
    ) -> OperationResult:
        """使用参数对象执行旋转。"""
        return self._execute_rotate(image, params, output_path)

    def _execute_rotate(
        self,
        image: Union[str, bytes, Image.Image],
        params: RotateParams,
        output_path: Optional[str],
    ) -> OperationResult:
        """旋转核心实现。"""
        start_time = time.perf_counter()
        warnings: List[str] = []

        try:
            # 校验参数
            validation_errors = params.validate()
            if validation_errors:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    f"旋转参数无效: {'; '.join(validation_errors)}",
                    details={"errors": validation_errors},
                )

            # 打开图像
            img, source_path, source_format = self._open_image(image)
            src_w, src_h = img.size

            # 归一化角度到 0-360
            angle = params.angle % 360

            # 判断是否为直角旋转（90/180/270）
            is_right_angle = abs(angle - 90) < 1e-6 or abs(angle - 180) < 1e-6 or abs(angle - 270) < 1e-6 or abs(angle) < 1e-6

            if is_right_angle and abs(angle) > 1e-6:
                # 直角旋转：使用 transpose 方法，快速且无损
                if abs(angle - 90) < 1e-6:
                    rotated = img.transpose(Image.ROTATE_270)  # PIL ROTATE_270 = 逆时针270 = 顺时针90
                elif abs(angle - 180) < 1e-6:
                    rotated = img.transpose(Image.ROTATE_180)
                elif abs(angle - 270) < 1e-6:
                    rotated = img.transpose(Image.ROTATE_90)  # PIL ROTATE_90 = 逆时针90 = 顺时针270
                else:
                    rotated = img

                # 直角旋转后宽高可能互换（90/270 时）
                if abs(angle - 90) < 1e-6 or abs(angle - 270) < 1e-6:
                    out_w, out_h = src_h, src_w
                else:
                    out_w, out_h = src_w, src_h
            else:
                # 非直角旋转：使用 rotate 方法（带插值）
                # Pillow 的 rotate 按逆时针，需要取反
                pil_angle = -angle if angle != 0 else 0
                rotated = img.rotate(
                    pil_angle,
                    expand=params.expand,
                    fillcolor=params.fillcolor,
                    resample=Image.Resampling.BICUBIC,
                )
                out_w, out_h = rotated.size

            # 检查输出尺寸
            if out_w > MAX_OUTPUT_DIMENSION or out_h > MAX_OUTPUT_DIMENSION:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    f"旋转后尺寸 {out_w}×{out_h} 超过最大限制 {MAX_OUTPUT_DIMENSION}px",
                    details={"output_width": out_w, "output_height": out_h},
                )

            # 编码输出
            output_data, actual_format = self._encode_to_format(
                rotated,
                self._detect_format(img, source_path),
                FormatConvertParams(),
            )

            # 写入文件
            if output_path:
                self._save_to_file(output_data, output_path)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            result = OperationResult(
                success=True,
                source_path=source_path,
                source_width=src_w,
                source_height=src_h,
                output_width=out_w,
                output_height=out_h,
                output_format=actual_format,
                output_size=len(output_data),
                output_data=output_data,
                warnings=warnings,
                elapsed_ms=round(elapsed_ms, 2),
            )

            logger.info(
                "旋转完成 | %dx%d → %dx%d | angle=%.1f° | expand=%s | elapsed=%.1fms",
                src_w, src_h, out_w, out_h,
                params.angle, params.expand, elapsed_ms,
            )

            return result

        except AppError:
            raise
        except Exception as e:
            raise AppError(
                ErrorCode.INTERNAL,
                f"旋转失败: {e}",
                details={"error": str(e)},
            )

    # ===== 内部方法：图片 IO =====

    def _open_image(
        self, image: Union[str, bytes, Image.Image]
    ) -> Tuple[Image.Image, Optional[str], Optional[str]]:
        """统一打开图片输入。

        支持文件路径、bytes 和 PIL Image 三种输入。

        返回：(PIL Image, 文件路径或None, 源格式字符串或None)
        """
        if isinstance(image, str):
            file_path = os.path.abspath(image)
            img = self._open_image_file(file_path)
            source_format = Path(file_path).suffix.lower().lstrip(".")
            return img, file_path, source_format
        elif isinstance(image, bytes):
            img = self._open_image_bytes(image)
            return img, None, None
        elif isinstance(image, Image.Image):
            return image.copy(), None, None
        else:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"不支持的输入类型: {type(image).__name__}",
                details={"supported_types": ["str", "bytes", "PIL.Image.Image"]},
            )

    def _open_image_file(self, file_path: str) -> Image.Image:
        """从文件打开图片，带校验。"""
        path = file_path
        if not os.path.isfile(path):
            raise AppError(
                ErrorCode.FILE_NOT_FOUND,
                f"图片文件未找到: {path}",
                details={"path": path},
            )

        suffix = Path(path).suffix.lower()
        if suffix not in SUPPORTED_INPUT_SUFFIXES:
            raise AppError(
                ErrorCode.FILE_UNSUPPORTED_FORMAT,
                f"不支持的图片格式: {suffix}",
                details={"suffix": suffix, "supported": SUPPORTED_INPUT_SUFFIXES},
            )

        try:
            img = Image.open(path)
            img.load()
            return img
        except Exception as e:
            raise AppError(
                ErrorCode.FILE_READ_ERROR,
                f"无法打开图片文件: {e}",
                details={"path": path, "error": str(e)},
            )

    def _open_image_bytes(self, data: bytes) -> Image.Image:
        """从 bytes 打开图片。"""
        if not data:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                "图片数据为空",
                details={"data_len": 0},
            )
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
            return img
        except Exception as e:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"无法解码图片数据: {e}",
                details={"data_len": len(data), "error": str(e)},
            )

    # ===== 内部方法：格式检测与编码 =====

    @staticmethod
    def _detect_format(img: Image.Image, source_path: Optional[str]) -> ConvertFormat:
        """检测图片的原始格式。

        优先使用文件后缀，其次使用 PIL 检测的格式。
        """
        if source_path:
            suffix = Path(source_path).suffix.lower()
            suffix_map = {
                ".png": ConvertFormat.PNG,
                ".jpg": ConvertFormat.JPEG,
                ".jpeg": ConvertFormat.JPEG,
                ".bmp": ConvertFormat.BMP,
                ".tiff": ConvertFormat.TIFF,
                ".tif": ConvertFormat.TIFF,
                ".webp": ConvertFormat.WEBP,
                ".gif": ConvertFormat.GIF,
                ".ico": ConvertFormat.ICO,
            }
            if suffix in suffix_map:
                return suffix_map[suffix]

        # 回退到 PIL 检测的格式
        pil_format = (img.format or "PNG").upper()
        fmt_map = {
            "JPEG": ConvertFormat.JPEG,
            "PNG": ConvertFormat.PNG,
            "BMP": ConvertFormat.BMP,
            "TIFF": ConvertFormat.TIFF,
            "WEBP": ConvertFormat.WEBP,
            "GIF": ConvertFormat.GIF,
            "ICO": ConvertFormat.ICO,
        }
        return fmt_map.get(pil_format, ConvertFormat.PNG)

    def _encode_to_format(
        self,
        img: Image.Image,
        target_format: ConvertFormat,
        params: FormatConvertParams,
    ) -> Tuple[bytes, str]:
        """将 PIL Image 编码为目标格式的 bytes。

        返回：(图片字节数据, 实际格式字符串)
        """
        buf = io.BytesIO()
        save_kwargs = {}

        if target_format == ConvertFormat.JPEG:
            # JPEG 不支持 RGBA，需处理透明通道
            if img.mode in ("RGBA", "LA", "PA", "P"):
                if params.preserve_alpha:
                    # 转为白色背景的 RGB
                    img = self._flatten_alpha(img)
                else:
                    img = img.convert("RGB")
            elif img.mode != "RGB":
                img = img.convert("RGB")
            save_kwargs["quality"] = params.jpeg_quality
            save_kwargs["optimize"] = True
            fmt = "JPEG"

        elif target_format == ConvertFormat.PNG:
            # PNG 原生支持 RGBA
            save_kwargs["compress_level"] = params.png_compress
            fmt = "PNG"

        elif target_format == ConvertFormat.BMP:
            fmt = "BMP"

        elif target_format == ConvertFormat.TIFF:
            save_kwargs["compression"] = "tiff_lzw"
            fmt = "TIFF"

        elif target_format == ConvertFormat.WEBP:
            save_kwargs["quality"] = params.webp_quality
            if not params.preserve_alpha and img.mode in ("RGBA", "LA", "PA"):
                img = self._flatten_alpha(img)
            fmt = "WEBP"

        elif target_format == ConvertFormat.GIF:
            # GIF 不支持 RGBA，需量化处理
            if img.mode in ("RGBA", "LA", "PA"):
                if not params.preserve_alpha:
                    img = self._flatten_alpha(img)
            img = img.convert("P", palette=Image.Palette.ADAPTIVE)
            fmt = "GIF"

        elif target_format == ConvertFormat.ICO:
            # ICO 需要特定尺寸，先转为 RGBA 再保存
            if img.mode not in ("RGBA", "RGB"):
                if img.mode in ("LA", "PA", "P") and params.preserve_alpha:
                    img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")
            fmt = "ICO"

        else:
            # 默认 JPEG
            if img.mode in ("RGBA", "LA", "PA", "P"):
                img = self._flatten_alpha(img)
            save_kwargs["quality"] = params.jpeg_quality
            fmt = "JPEG"

        img.save(buf, format=fmt, **save_kwargs)
        return buf.getvalue(), fmt.lower()

    def _encode_compressed(
        self,
        img: Image.Image,
        target_format: ConvertFormat,
        params: CompressParams,
        warnings: List[str],
    ) -> Tuple[bytes, str]:
        """按压缩参数编码图片。

        有损压缩：使用 JPEG/WEBP 格式，通过 quality 控制压缩率。
        无损压缩：使用 PNG，通过 compress_level 控制。
        """
        buf = io.BytesIO()
        save_kwargs = {}

        if target_format == ConvertFormat.JPEG:
            if img.mode in ("RGBA", "LA", "PA", "P"):
                img = self._flatten_alpha(img)
            elif img.mode != "RGB":
                img = img.convert("RGB")
            save_kwargs["quality"] = params.quality
            save_kwargs["optimize"] = True
            fmt = "JPEG"

        elif target_format == ConvertFormat.WEBP:
            save_kwargs["quality"] = params.quality
            if img.mode in ("RGBA", "LA", "PA"):
                img = self._flatten_alpha(img)
            fmt = "WEBP"

        elif target_format == ConvertFormat.PNG:
            save_kwargs["compress_level"] = params.png_compress
            fmt = "PNG"

        elif target_format == ConvertFormat.ORIGINAL:
            # 保持原格式但提升压缩级别
            if img.mode in ("RGBA", "LA") or (img.format and img.format.upper() == "PNG"):
                save_kwargs["compress_level"] = params.png_compress
                fmt = "PNG"
            elif img.format and img.format.upper() == "JPEG":
                if img.mode in ("RGBA", "LA", "PA", "P"):
                    img = self._flatten_alpha(img)
                save_kwargs["quality"] = params.quality
                save_kwargs["optimize"] = True
                fmt = "JPEG"
            else:
                if img.mode in ("RGBA", "LA", "PA", "P"):
                    img = self._flatten_alpha(img)
                save_kwargs["quality"] = params.quality
                save_kwargs["optimize"] = True
                fmt = "JPEG"
        else:
            # 其他格式：默认转为 JPEG 做有损压缩
            if img.mode in ("RGBA", "LA", "PA", "P"):
                img = self._flatten_alpha(img)
            save_kwargs["quality"] = params.quality
            save_kwargs["optimize"] = True
            fmt = "JPEG"

        img.save(buf, format=fmt, **save_kwargs)
        return buf.getvalue(), fmt.lower()

    def _iterative_quality_compress(
        self,
        img: Image.Image,
        target_format: ConvertFormat,
        current_size: int,
        params: CompressParams,
        warnings: List[str],
    ) -> bytes:
        """迭代降低质量直到文件大小接近目标 max_size_bytes。

        对有损格式（JPEG/WEBP），逐步降低 quality 以逼近目标大小。
        最少降至 quality=5，无法满足时返回最低质量的结果。
        """
        if params.max_size_bytes is None or current_size <= params.max_size_bytes:
            buf = io.BytesIO()
            fmt = "JPEG" if target_format == ConvertFormat.JPEG else "WEBP"
            img.save(buf, format=fmt, quality=params.quality, optimize=True)
            return buf.getvalue()

        target_size = params.max_size_bytes
        best_data = None
        best_quality = params.quality

        # 二分法逼近目标大小
        min_q, max_q = 5, params.quality
        iteration = 0
        max_iterations = 10

        while min_q <= max_q and iteration < max_iterations:
            mid_q = (min_q + max_q) // 2
            buf = io.BytesIO()
            fmt = "JPEG" if target_format == ConvertFormat.JPEG else "WEBP"
            if img.mode in ("RGBA", "LA", "PA", "P"):
                img_rgb = self._flatten_alpha(img)
            else:
                img_rgb = img
            img_rgb.save(buf, format=fmt, quality=mid_q, optimize=True)
            data = buf.getvalue()
            size = len(data)

            if size <= target_size:
                best_data = data
                best_quality = mid_q
                max_q = mid_q - 1  # 尝试更高质量
            else:
                min_q = mid_q + 1  # 降低质量

            iteration += 1

        if best_data is not None:
            warnings.append(
                f"通过迭代质量调整逼近目标大小 {target_size} bytes，"
                f"最终 quality={best_quality}，实际大小={len(best_data)} bytes"
            )
            return best_data
        else:
            # 无法达到目标，返回最低质量
            buf = io.BytesIO()
            fmt = "JPEG" if target_format == ConvertFormat.JPEG else "WEBP"
            if img.mode in ("RGBA", "LA", "PA", "P"):
                img = self._flatten_alpha(img)
            img.save(buf, format=fmt, quality=5, optimize=True)
            data = buf.getvalue()
            warnings.append(
                f"无法达到目标大小 {target_size} bytes，"
                f"已使用最低质量 (quality=5)，实际大小={len(data)} bytes"
            )
            return data

    @staticmethod
    def _flatten_alpha(img: Image.Image) -> Image.Image:
        """将带透明通道的图片合成为白色背景的 RGB 图片。

        用于有损格式（JPEG）输出时处理 RGBA 图片。
        """
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[3])  # alpha 通道作为 mask
            elif img.mode == "LA":
                background.paste(img, mask=img.split()[1])
            return background
        elif img.mode == "PA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[3])
            return background
        elif img.mode == "P":
            # 调色板模式带透明
            if "transparency" in img.info:
                img = img.convert("RGBA")
                return FormatConverter._flatten_alpha(img)
        # 其他模式直接转 RGB
        return img.convert("RGB")

    @staticmethod
    def _calc_anchor_position(
        src_w: int, src_h: int, crop_w: int, crop_h: int, anchor: CropAnchor
    ) -> Tuple[int, int]:
        """根据锚点计算裁剪的左上角坐标。

        参数：
            src_w, src_h: 原图宽高。
            crop_w, crop_h: 裁剪宽高。
            anchor: 锚点对齐方式。

        返回：
            (left, top) 裁剪起点坐标。
        """
        if anchor == CropAnchor.CENTER:
            left = (src_w - crop_w) // 2
            top_val = (src_h - crop_h) // 2
        elif anchor == CropAnchor.TOP_LEFT:
            left = 0
            top_val = 0
        elif anchor == CropAnchor.TOP_RIGHT:
            left = src_w - crop_w
            top_val = 0
        elif anchor == CropAnchor.BOTTOM_LEFT:
            left = 0
            top_val = src_h - crop_h
        elif anchor == CropAnchor.BOTTOM_RIGHT:
            left = src_w - crop_w
            top_val = src_h - crop_h
        else:
            left = (src_w - crop_w) // 2
            top_val = (src_h - crop_h) // 2

        return left, top_val

    @staticmethod
    def _save_to_file(data: bytes, file_path: str) -> str:
        """将图片数据写入文件。

        自动创建不存在的父目录。
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            path.write_bytes(data)
            logger.info("文件已保存到: %s (%d bytes)", file_path, len(data))
            return str(path.resolve())
        except PermissionError:
            raise AppError(
                ErrorCode.FILE_WRITE_ERROR,
                f"文件写入权限不足: {file_path}",
                details={"path": file_path},
            )
        except Exception as e:
            raise AppError(
                ErrorCode.FILE_WRITE_ERROR,
                f"文件写入失败: {e}",
                details={"path": file_path, "error": str(e)},
            )

    # ===== 辅助查询方法 =====

    @staticmethod
    def supported_formats() -> Dict:
        """返回支持的输入输出格式。"""
        return {
            "input": SUPPORTED_INPUT_SUFFIXES,
            "output": [f.value for f in ConvertFormat],
            "suffix_map": {f.value: s for f, s in FORMAT_SUFFIX_MAP.items()},
        }

    @staticmethod
    def get_image_info(image: Union[str, bytes]) -> Dict:
        """获取图片文件的基本信息（不执行转换）。

        返回包含尺寸、格式、模式等的字典。
        """
        if isinstance(image, str):
            path = image
            if not os.path.isfile(path):
                raise AppError(
                    ErrorCode.FILE_NOT_FOUND,
                    f"图片文件未找到: {path}",
                    details={"path": path},
                )
            img = Image.open(path)
        elif isinstance(image, bytes):
            img = Image.open(io.BytesIO(image))
        else:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"不支持的输入类型: {type(image).__name__}",
            )

        try:
            dpi = img.info.get("dpi")
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format or "unknown",
                "mode": img.mode,
                "dpi": list(dpi) if dpi else None,
            }
        finally:
            img.close()
