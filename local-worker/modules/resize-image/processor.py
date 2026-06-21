"""
local-worker/modules/resize-image/processor — 图片改尺寸核心处理器

基于 Pillow 实现纯本地图片缩放，支持：
  - 精确尺寸 / 等比适配 / 等比填充 / 百分比缩放 / 短边约束 / 长边约束 / DPI 缩放
  - 多种重采样滤镜（LANCZOS / BILINEAR / BICUBIC / NEAREST / BOX / HAMMING）
  - 格式转换（保持原格式 / PNG / JPEG / BMP / TIFF / WEBP）
  - DPI 设置
  - 图文店常用预设尺寸（一寸、二寸、A4 印刷等）

不依赖 GPU，不涉及 AI 模型，纯本地图像处理。
"""

import io
import os
import time
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from PIL import Image

# 引用 local-worker/shared 公共层
from shared.errors import AppError, ErrorCode
from shared.logging import get_logger

from specifications import (
    ResizeMode,
    ResampleFilter,
    OutputFormat,
    ResizeParams,
    ResizeResult,
    PRINT_PRESETS,
    SUPPORTED_INPUT_SUFFIXES,
    FORMAT_SUFFIX_MAP,
    MAX_OUTPUT_DIMENSION,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_PNG_COMPRESS_LEVEL,
    DEFAULT_WEBP_QUALITY,
)

# 模块 logger
logger = get_logger("local-worker.resize-image")


class ImageResizer:
    """图片改尺寸处理器。

    封装了所有改尺寸模式、格式转换和导出策略。
    纯本地执行，不调用云端 API。

    用法：
        resizer = ImageResizer()

        # 方式 1：使用预设尺寸
        result = resizer.resize("input.png", preset="id_1inch")

        # 方式 2：使用参数对象
        params = ResizeParams(mode=ResizeMode.FIT, width=800, height=600)
        result = resizer.resize("input.png", params=params)

        # 方式 3：使用便捷方法
        result = resizer.resize_fit("input.png", 800, 600)
        result = resizer.resize_scale("input.png", 50)
        result = resizer.resize_by_preset("input.png", "print_a4_300dpi")

        # 方式 4：处理 bytes 输入
        result = resizer.resize_bytes(image_bytes, params=params)
    """

    def __init__(self) -> None:
        """初始化处理器。无需模型，只依赖 Pillow。"""
        pass

    # ===== 主入口 =====

    def resize(
        self,
        image: Union[str, bytes, Image.Image],
        params: Optional[ResizeParams] = None,
        preset: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> ResizeResult:
        """图片改尺寸主入口。

        参数：
            image: 输入图像，支持文件路径、bytes 或 PIL Image 对象。
            params: 改尺寸参数对象，与 preset 二选一。
            preset: 预设尺寸名称（如 "id_1inch"、"print_a4_300dpi"），
                    见 PRINT_PRESETS 字典。
            output_path: 可选输出文件路径，不传则只返回内存中的 bytes。

        返回：
            ResizeResult：包含输出数据和元信息的结构化结果。

        异常：
            AppError：输入无效或处理失败时抛出。
        """
        start_time = time.perf_counter()

        # 参数解析：preset 优先
        if preset is not None:
            if params is not None:
                logger.warning("同时指定了 preset 和 params，以 preset 为准")
            params = self._params_from_preset(preset)

        if params is None:
            # 默认参数：等比适配到 800×800
            params = ResizeParams(mode=ResizeMode.FIT, width=800, height=800)

        # 校验参数
        validation_errors = params.validate()
        if validation_errors:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"改尺寸参数无效: {'; '.join(validation_errors)}",
                details={"errors": validation_errors},
            )

        # 打开图像
        source_path = None
        if isinstance(image, str):
            source_path = os.path.abspath(image)
            img = self._open_image(source_path)
        elif isinstance(image, bytes):
            img = self._open_from_bytes(image)
        elif isinstance(image, Image.Image):
            img = image
        else:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"不支持的输入类型: {type(image).__name__}",
                details={"supported_types": ["str", "bytes", "PIL.Image.Image"]},
            )

        # 记录原始尺寸
        source_width, source_height = img.size

        # 检查原始尺寸是否合法
        if source_width <= 0 or source_height <= 0:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"图片尺寸无效: {source_width}×{source_height}",
                details={"width": source_width, "height": source_height},
            )

        # 超过最大输出尺寸限制时发出警告
        warnings: List[str] = []
        if source_width > MAX_OUTPUT_DIMENSION or source_height > MAX_OUTPUT_DIMENSION:
            warnings.append(
                f"原图尺寸 {source_width}×{source_height} 超过推荐最大值 "
                f"{MAX_OUTPUT_DIMENSION}px，处理可能较慢"
            )

        # 执行缩放
        try:
            resized_img, actual_w, actual_h, scale_ratio = self._do_resize(
                img, params, source_width, source_height, warnings
            )
        except Exception as e:
            raise AppError(
                ErrorCode.INTERNAL,
                f"图片缩放失败: {e}",
                details={
                    "source_width": source_width,
                    "source_height": source_height,
                    "mode": params.mode.value,
                    "error": str(e),
                },
            )

        # 处理输出格式
        output_format = params.output_format
        if output_format == OutputFormat.ORIGINAL:
            # 根据原图格式推断输出格式
            fmt = (img.format or "PNG").upper()
            fmt_map = {"JPEG": OutputFormat.JPEG, "PNG": OutputFormat.PNG,
                       "BMP": OutputFormat.BMP, "TIFF": OutputFormat.TIFF,
                       "WEBP": OutputFormat.WEBP, "GIF": OutputFormat.PNG}
            output_format = fmt_map.get(fmt, OutputFormat.PNG)

        # 处理 DPI
        output_dpi = params.dpi
        if output_dpi is None:
            dpi_info = img.info.get("dpi")
            if dpi_info is not None and isinstance(dpi_info, (tuple, list)) and len(dpi_info) >= 2:
                output_dpi = (float(dpi_info[0]), float(dpi_info[1]))

        # 编码输出
        output_data, actual_format = self._encode_image(
            resized_img, output_format, params, output_dpi
        )

        # 写入文件（如果指定了输出路径）
        if output_path:
            self._save_to_file(output_data, output_path)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        result = ResizeResult(
            success=True,
            source_path=source_path,
            source_width=source_width,
            source_height=source_height,
            output_width=actual_w,
            output_height=actual_h,
            mode=params.mode,
            scale_ratio=round(scale_ratio, 6),
            output_format=actual_format,
            output_size=len(output_data),
            output_data=output_data,
            dpi=output_dpi,
            warnings=warnings,
            elapsed_ms=round(elapsed_ms, 2),
        )

        logger.info(
            "改尺寸完成 | mode=%s | %dx%d → %dx%d | ratio=%.3f | "
            "output_format=%s | size=%d bytes | elapsed=%.1fms",
            params.mode.value,
            source_width, source_height,
            actual_w, actual_h,
            scale_ratio,
            actual_format,
            len(output_data),
            elapsed_ms,
        )

        return result

    # ===== 便捷方法 =====

    def resize_fit(
        self,
        image: Union[str, bytes, Image.Image],
        width: int,
        height: int,
        resample: ResampleFilter = ResampleFilter.LANCZOS,
        output_format: OutputFormat = OutputFormat.ORIGINAL,
        output_path: Optional[str] = None,
    ) -> ResizeResult:
        """等比适配缩放 — 保持宽高比，图片完全位于指定边界内。

        这是最常用的缩放模式，适合预览、缩略图等场景。
        """
        params = ResizeParams(
            mode=ResizeMode.FIT,
            width=width,
            height=height,
            resample=resample,
            output_format=output_format,
        )
        return self.resize(image, params=params, output_path=output_path)

    def resize_exact(
        self,
        image: Union[str, bytes, Image.Image],
        width: int,
        height: int,
        resample: ResampleFilter = ResampleFilter.LANCZOS,
        output_format: OutputFormat = OutputFormat.ORIGINAL,
        output_path: Optional[str] = None,
    ) -> ResizeResult:
        """精确尺寸缩放 — 输出严格等于指定的宽×高（可能拉伸变形）。"""
        params = ResizeParams(
            mode=ResizeMode.EXACT,
            width=width,
            height=height,
            keep_aspect=False,
            resample=resample,
            output_format=output_format,
        )
        return self.resize(image, params=params, output_path=output_path)

    def resize_fill(
        self,
        image: Union[str, bytes, Image.Image],
        width: int,
        height: int,
        resample: ResampleFilter = ResampleFilter.LANCZOS,
        output_format: OutputFormat = OutputFormat.ORIGINAL,
        output_path: Optional[str] = None,
    ) -> ResizeResult:
        """等比填充缩放 — 保持宽高比，缩放至完全覆盖边界（居中裁剪超出部分）。"""
        params = ResizeParams(
            mode=ResizeMode.FILL,
            width=width,
            height=height,
            resample=resample,
            output_format=output_format,
        )
        return self.resize(image, params=params, output_path=output_path)

    def resize_scale(
        self,
        image: Union[str, bytes, Image.Image],
        scale_percent: float,
        resample: ResampleFilter = ResampleFilter.LANCZOS,
        output_format: OutputFormat = OutputFormat.ORIGINAL,
        output_path: Optional[str] = None,
    ) -> ResizeResult:
        """百分比缩放 — 按指定百分比缩放（100=原大，50=缩小一半）。"""
        params = ResizeParams(
            mode=ResizeMode.SCALE,
            scale_percent=scale_percent,
            resample=resample,
            output_format=output_format,
        )
        return self.resize(image, params=params, output_path=output_path)

    def resize_short_side(
        self,
        image: Union[str, bytes, Image.Image],
        target_px: int,
        resample: ResampleFilter = ResampleFilter.LANCZOS,
        output_format: OutputFormat = OutputFormat.ORIGINAL,
        output_path: Optional[str] = None,
    ) -> ResizeResult:
        """短边约束缩放 — 指定短边的目标像素，长边等比自动计算。"""
        params = ResizeParams(
            mode=ResizeMode.SHORT_SIDE,
            short_side=target_px,
            resample=resample,
            output_format=output_format,
        )
        return self.resize(image, params=params, output_path=output_path)

    def resize_long_side(
        self,
        image: Union[str, bytes, Image.Image],
        target_px: int,
        resample: ResampleFilter = ResampleFilter.LANCZOS,
        output_format: OutputFormat = OutputFormat.ORIGINAL,
        output_path: Optional[str] = None,
    ) -> ResizeResult:
        """长边约束缩放 — 指定长边的目标像素，短边等比自动计算。"""
        params = ResizeParams(
            mode=ResizeMode.LONG_SIDE,
            long_side=target_px,
            resample=resample,
            output_format=output_format,
        )
        return self.resize(image, params=params, output_path=output_path)

    def resize_by_preset(
        self,
        image: Union[str, bytes, Image.Image],
        preset: str,
        resample: ResampleFilter = ResampleFilter.LANCZOS,
        output_format: OutputFormat = OutputFormat.ORIGINAL,
        output_path: Optional[str] = None,
    ) -> ResizeResult:
        """按预设尺寸缩放。

        可用预设见 PRINT_PRESETS 字典，例如：
        - "id_1inch"、"id_2inch"（证件照）
        - "photo_5inch"、"photo_6inch"（照片）
        - "print_a4_300dpi"（A4 印刷）
        - "card_standard"（名片）
        """
        params = self._params_from_preset(preset)
        params.resample = resample
        params.output_format = output_format
        return self.resize(image, params=params, output_path=output_path)

    def resize_with_dpi(
        self,
        image: Union[str, bytes, Image.Image],
        target_dpi: int,
        resample: ResampleFilter = ResampleFilter.LANCZOS,
        output_format: OutputFormat = OutputFormat.ORIGINAL,
        output_path: Optional[str] = None,
    ) -> ResizeResult:
        """按目标 DPI 缩放 — 根据图片当前 DPI 和目标 DPI 计算缩放比例。

        例如：72 DPI 图片转到 300 DPI，缩放比例为 300/72=4.17x。
        """
        params = ResizeParams(
            mode=ResizeMode.CUSTOM_DPI,
            target_dpi=target_dpi,
            resample=resample,
            output_format=output_format,
        )
        return self.resize(image, params=params, output_path=output_path)

    def resize_bytes(
        self,
        data: bytes,
        params: Optional[ResizeParams] = None,
        preset: Optional[str] = None,
    ) -> ResizeResult:
        """从 bytes 输入执行缩放（便捷方法）。

        适用于内存中的图片数据，不需要先写入磁盘。
        """
        return self.resize(data, params=params, preset=preset)

    # ===== 内部方法 =====

    def _open_image(self, file_path: str) -> Image.Image:
        """打开图片文件。"""
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
            # 加载图片数据确保后续操作不依赖文件句柄
            img.load()
            # 统一转为 RGB 或 RGBA 模式以简化处理
            img = self._normalize_mode(img)
            return img
        except Exception as e:
            raise AppError(
                ErrorCode.FILE_READ_ERROR,
                f"无法打开图片文件: {e}",
                details={"path": path, "error": str(e)},
            )

    def _open_from_bytes(self, data: bytes) -> Image.Image:
        """从 bytes 数据打开图片。"""
        if not data:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                "图片数据为空",
                details={"data_len": 0},
            )
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
            img = self._normalize_mode(img)
            return img
        except Exception as e:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"无法解码图片数据: {e}",
                details={"data_len": len(data), "error": str(e)},
            )

    def _normalize_mode(self, img: Image.Image) -> Image.Image:
        """统一图片模式。

        - 调色板(P) / 灰度(L) → RGBA 或 RGB（保留透明度信息）。
        - CMYK → RGB 以支持所有输出格式。
        - 1-bit(1) → RGB。
        """
        mode = img.mode
        if mode in ("P", "PA", "LA"):
            # 调色板/灰度模式转 RGBA（保留透明度）
            if "A" in mode or "transparency" in img.info:
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")
        elif mode == "1":
            # 1-bit 黑白转 RGB
            img = img.convert("RGB")
        elif mode == "CMYK":
            # CMYK 转 RGB
            img = img.convert("RGB")
        elif mode == "L":
            # 灰度
            img = img.convert("L")
        elif mode not in ("RGB", "RGBA", "L"):
            # 其他未知模式默认转 RGB
            img = img.convert("RGB")
        return img

    def _do_resize(
        self,
        img: Image.Image,
        params: ResizeParams,
        src_w: int,
        src_h: int,
        warnings: List[str],
    ) -> Tuple[Image.Image, int, int, float]:
        """执行缩放核心逻辑。

        参数：
            img: PIL Image 对象。
            params: 缩放参数。
            src_w: 原始宽度。
            src_h: 原始高度。
            warnings: 警告列表，用于收集非致命警告。

        返回：
            (resized_img, output_width, output_height, scale_ratio)
        """
        pil_filter = params.resample.to_pil()
        mode = params.mode

        if mode == ResizeMode.EXACT:
            target_w = params.width if params.width is not None else src_w
            target_h = params.height if params.height is not None else src_h

            if params.keep_aspect:
                # 设置了保持宽高比，降级为 FIT 模式
                warnings.append("EXACT 模式下 keep_aspect=True，已自动切换为等比适配 (FIT)")
                out_w, out_h = self._calc_fit_size(src_w, src_h, target_w, target_h)
            else:
                out_w, out_h = target_w, target_h
                # 非等比缩放可能造成拉伸变形，添加警告
                src_ratio = src_w / src_h
                out_ratio = out_w / out_h
                if abs(src_ratio - out_ratio) > 0.01:
                    warnings.append(
                        f"非等比缩放可能造成拉伸变形 "
                        f"(原图={src_w}×{src_h} 比例={src_ratio:.3f}, "
                        f"目标={out_w}×{out_h} 比例={out_ratio:.3f})"
                    )

        elif mode == ResizeMode.FIT:
            target_w = params.width if params.width is not None else MAX_OUTPUT_DIMENSION
            target_h = params.height if params.height is not None else MAX_OUTPUT_DIMENSION
            out_w, out_h = self._calc_fit_size(src_w, src_h, target_w, target_h)

        elif mode == ResizeMode.FILL:
            target_w = params.width if params.width is not None else src_w
            target_h = params.height if params.height is not None else src_h
            out_w, out_h = self._calc_fill_size(src_w, src_h, target_w, target_h)

        elif mode == ResizeMode.SCALE:
            ratio = params.scale_percent / 100.0
            out_w = max(1, round(src_w * ratio))
            out_h = max(1, round(src_h * ratio))

        elif mode == ResizeMode.SHORT_SIDE:
            target = params.short_side
            if target is None:
                target = src_w  # fallback
            out_w, out_h = self._calc_short_side_size(src_w, src_h, target)

        elif mode == ResizeMode.LONG_SIDE:
            target = params.long_side
            if target is None:
                target = src_w  # fallback
            out_w, out_h = self._calc_long_side_size(src_w, src_h, target)

        elif mode == ResizeMode.CUSTOM_DPI:
            target_dpi = params.target_dpi
            if target_dpi is None:
                target_dpi = 300  # fallback
            # 从原图获取 DPI
            dpi_info = img.info.get("dpi")
            current_dpi = 72.0  # 默认 DPI（许多图片无 DPI 信息时用 72）
            if dpi_info is not None and isinstance(dpi_info, (tuple, list)) and len(dpi_info) >= 2:
                current_dpi = float(dpi_info[0]) if dpi_info[0] else 72.0

            if current_dpi <= 0:
                current_dpi = 72.0

            ratio = target_dpi / current_dpi
            if ratio == 1.0:
                # DPI 相同，无需缩放
                out_w, out_h = src_w, src_h
                warnings.append(f"当前 DPI ({current_dpi:.0f}) 已等于目标 DPI ({target_dpi})，无需缩放")
            else:
                out_w = max(1, round(src_w * ratio))
                out_h = max(1, round(src_h * ratio))

        else:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"不支持的改尺寸模式: {mode.value}",
                details={"mode": mode.value},
            )

        # 输出尺寸边界检查
        if out_w > MAX_OUTPUT_DIMENSION or out_h > MAX_OUTPUT_DIMENSION:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"计算结果超出最大输出尺寸限制: {out_w}×{out_h} > {MAX_OUTPUT_DIMENSION}px",
                details={
                    "calculated_width": out_w,
                    "calculated_height": out_h,
                    "max_dimension": MAX_OUTPUT_DIMENSION,
                },
            )

        # 执行 Pillow resize
        if mode == ResizeMode.FILL:
            # FILL 模式需要先缩放再裁剪
            resized = img.resize((out_w, out_h), pil_filter)
            # 居中裁剪
            left = (out_w - params.width) // 2
            top = (out_h - params.height) // 2
            right = left + params.width
            bottom = top + params.height
            resized = resized.crop((left, top, right, bottom))
            final_w, final_h = params.width, params.height
        else:
            resized = img.resize((out_w, out_h), pil_filter)
            final_w, final_h = out_w, out_h

        # 计算实际缩放比例
        scale_ratio = final_w / src_w

        return resized, final_w, final_h, scale_ratio

    def _encode_image(
        self,
        img: Image.Image,
        output_format: OutputFormat,
        params: ResizeParams,
        dpi: Optional[Tuple[float, float]],
    ) -> Tuple[bytes, str]:
        """将 PIL Image 编码为 bytes。

        返回：(图片字节数据, 实际格式字符串)
        """
        save_kwargs = {}

        # DPI 设置
        if dpi is not None:
            save_kwargs["dpi"] = dpi

        # 根据输出格式设置编码参数和质量
        if output_format == OutputFormat.JPEG:
            # JPEG 不能处理 RGBA，先转 RGB
            if img.mode in ("RGBA", "LA", "PA", "P"):
                img = img.convert("RGB")
            save_kwargs["quality"] = params.jpeg_quality
            save_kwargs["optimize"] = True
            fmt = "JPEG"

        elif output_format == OutputFormat.PNG:
            # PNG 支持 RGBA
            save_kwargs["compress_level"] = params.png_compress_level
            fmt = "PNG"

        elif output_format == OutputFormat.BMP:
            fmt = "BMP"

        elif output_format == OutputFormat.TIFF:
            save_kwargs["compression"] = "tiff_lzw"  # 无损压缩
            fmt = "TIFF"

        elif output_format == OutputFormat.WEBP:
            save_kwargs["quality"] = params.webp_quality
            fmt = "WEBP"

        else:
            # 默认 JPEG
            if img.mode in ("RGBA", "LA", "PA", "P"):
                img = img.convert("RGB")
            save_kwargs["quality"] = params.jpeg_quality
            fmt = "JPEG"

        buf = io.BytesIO()
        img.save(buf, format=fmt, **save_kwargs)
        return buf.getvalue(), fmt.lower()

    def _save_to_file(self, data: bytes, output_path: str) -> str:
        """将图片数据写入文件。

        自动创建不存在的父目录。
        """
        path = Path(output_path)
        # 自动创建父目录
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            path.write_bytes(data)
            logger.info("图片已保存到: %s (%d bytes)", output_path, len(data))
            return str(path.resolve())
        except PermissionError:
            raise AppError(
                ErrorCode.FILE_WRITE_ERROR,
                f"文件写入权限不足: {output_path}",
                details={"path": output_path},
            )
        except Exception as e:
            raise AppError(
                ErrorCode.FILE_WRITE_ERROR,
                f"文件写入失败: {e}",
                details={"path": output_path, "error": str(e)},
            )

    @staticmethod
    def _params_from_preset(preset: str) -> ResizeParams:
        """从预设名称生成 ResizeParams。

        预设不存在时抛出 AppError。
        """
        if preset not in PRINT_PRESETS:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"未知预设尺寸: {preset}",
                details={
                    "preset": preset,
                    "available_presets": sorted(PRINT_PRESETS.keys()),
                },
            )
        w, h, _ = PRINT_PRESETS[preset]
        return ResizeParams(
            mode=ResizeMode.FIT,
            width=w,
            height=h,
            resample=ResampleFilter.LANCZOS,
        )

    # ===== 尺寸计算辅助方法 =====

    @staticmethod
    def _calc_fit_size(src_w: int, src_h: int, max_w: int, max_h: int) -> Tuple[int, int]:
        """计算等比适配尺寸：保持宽高比，不超出边界。"""
        ratio = min(max_w / src_w, max_h / src_h, 1.0)
        return max(1, round(src_w * ratio)), max(1, round(src_h * ratio))

    @staticmethod
    def _calc_fill_size(src_w: int, src_h: int, target_w: int, target_h: int) -> Tuple[int, int]:
        """计算等比填充尺寸：保持宽高比，完全覆盖边界。"""
        ratio = max(target_w / src_w, target_h / src_h)
        return max(1, round(src_w * ratio)), max(1, round(src_h * ratio))

    @staticmethod
    def _calc_short_side_size(src_w: int, src_h: int, target: int) -> Tuple[int, int]:
        """计算短边约束尺寸：短边缩放到目标值，长边等比缩放。"""
        if src_w <= src_h:
            # 宽度是短边
            ratio = target / src_w
        else:
            # 高度是短边
            ratio = target / src_h
        return max(1, round(src_w * ratio)), max(1, round(src_h * ratio))

    @staticmethod
    def _calc_long_side_size(src_w: int, src_h: int, target: int) -> Tuple[int, int]:
        """计算长边约束尺寸：长边缩放到目标值，短边等比缩放。"""
        if src_w >= src_h:
            # 宽度是长边
            ratio = target / src_w
        else:
            # 高度是长边
            ratio = target / src_h
        return max(1, round(src_w * ratio)), max(1, round(src_h * ratio))

    @staticmethod
    def list_presets() -> List[Dict]:
        """列出所有可用预设尺寸。"""
        return [
            {
                "name": key,
                "width": w,
                "height": h,
                "description": desc,
            }
            for key, (w, h, desc) in sorted(PRINT_PRESETS.items())
        ]

    @staticmethod
    def supported_modes() -> List[str]:
        """列出所有支持的改尺寸模式。"""
        return [m.value for m in ResizeMode]

    @staticmethod
    def supported_filters() -> List[str]:
        """列出所有支持的重采样滤镜。"""
        return [f.value for f in ResampleFilter]
