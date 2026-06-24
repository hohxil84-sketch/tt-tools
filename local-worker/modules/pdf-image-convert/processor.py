"""
local-worker/modules/pdf-image-convert/processor — PDF/图片互转核心处理器

基于 PyMuPDF (fitz) 和 Pillow 实现纯本地 PDF/图片互转，支持：
  - PDF 转图片：将 PDF 的每一页渲染为 PNG/JPEG 图片
  - 图片转 PDF：将一张或多张图片合并为一个 PDF 文件
  - 支持文件路径、bytes 和 PIL Image 多种输入方式
  - 可指定 DPI、输出格式、页码范围等参数

不依赖 GPU，不涉及 AI 模型，不调用云端 API。
本地付费功能（pdf_image_convert_local_paid），需桌面端先通过 entitlements/check 校验套餐权限。
"""

import io
import os
import time
from pathlib import Path
from typing import List, Optional, Tuple, Union

import fitz  # PyMuPDF
from PIL import Image

# 引用 local-worker/shared 公共层
from shared.errors import AppError, ErrorCode
from shared.logging import get_logger

from specifications import (
    ConvertDirection,
    OutputFormat,
    ConvertParams,
    ConvertResult,
    PageImageResult,
    FORMAT_SUFFIX_MAP,
    SUPPORTED_IMAGE_INPUT_SUFFIXES,
    SUPPORTED_PDF_SUFFIX,
    MAX_OUTPUT_DIMENSION,
    MAX_PDF_PAGES,
    MAX_IMAGES_COUNT,
    DEFAULT_JPEG_QUALITY,
)

# 模块 logger
logger = get_logger("local-worker.pdf-image-convert")


class PdfImageConverter:
    """PDF/图片互转处理器。

    封装 PDF 转图片和图片转 PDF 两种方向的所有逻辑。
    纯本地执行，不调用云端 API。

    用法：
        converter = PdfImageConverter()

        # PDF 转图片：返回每页的图片 bytes 列表
        result = converter.convert("input.pdf", direction=ConvertDirection.PDF_TO_IMAGES)

        # 图片转 PDF：合并多张图片为一个 PDF
        result = converter.convert(["img1.png", "img2.jpg"],
                                   direction=ConvertDirection.IMAGES_TO_PDF)

        # 便捷方法
        images = converter.pdf_to_images("input.pdf", dpi=300)
        pdf_bytes = converter.images_to_pdf(["img1.png", "img2.jpg"])
    """

    def __init__(self) -> None:
        """初始化处理器。无需模型，只依赖 PyMuPDF 和 Pillow。"""
        pass

    # ===== 主入口 =====

    def convert(
        self,
        source: Union[str, bytes, List[str], List[bytes], List[Image.Image]],
        params: Optional[ConvertParams] = None,
        output_path: Optional[str] = None,
    ) -> ConvertResult:
        """PDF/图片互转主入口。

        根据 params.direction 自动路由到对应转换方法。

        参数：
            source: 输入源。
                    PDF→图片时：文件路径、bytes 或单个 PIL Image。
                    图片→PDF 时：文件路径列表、bytes 列表或 PIL Image 列表。
            params: 转换参数对象，默认 PDF→PNG，200 DPI。
            output_path: 可选输出路径。
                         PDF→图片时：必须是目录（保存每页图片）。
                         图片→PDF 时：必须是文件路径（保存合并后的 PDF）。

        返回：
            ConvertResult：包含输出数据和元信息的结构化结果。

        异常：
            AppError：输入无效或处理失败时抛出。
        """
        if params is None:
            params = ConvertParams()

        # 校验参数
        validation_errors = params.validate()
        if validation_errors:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"转换参数无效: {'; '.join(validation_errors)}",
                details={"errors": validation_errors},
            )

        # 根据方向路由
        if params.direction == ConvertDirection.PDF_TO_IMAGES:
            return self._convert_pdf_to_images(source, params, output_path)
        elif params.direction == ConvertDirection.IMAGES_TO_PDF:
            return self._convert_images_to_pdf(source, params, output_path)
        else:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"不支持的转换方向: {params.direction}",
                details={"direction": params.direction.value},
            )

    # ===== 便捷方法 =====

    def pdf_to_images(
        self,
        source: Union[str, bytes],
        dpi: int = 200,
        output_format: OutputFormat = OutputFormat.PNG,
        page_range: Optional[Tuple[int, int]] = None,
        output_dir: Optional[str] = None,
    ) -> ConvertResult:
        """PDF 转图片便捷方法。

        参数：
            source: PDF 文件路径或 bytes 数据。
            dpi: 渲染 DPI（72-600），默认 200。
            output_format: 输出图片格式，默认 PNG。
            page_range: 页码范围 (start, end)，1-based，包含两端。None 为全部页面。
            output_dir: 可选输出目录，指定后每页图片保存到该目录。

        返回：
            ConvertResult：pages 列表包含每页图片的 data 和元信息。
        """
        params = ConvertParams(
            direction=ConvertDirection.PDF_TO_IMAGES,
            output_format=output_format,
            dpi=dpi,
            page_range=page_range,
        )
        return self.convert(source, params=params, output_path=output_dir)

    def images_to_pdf(
        self,
        images: Union[List[str], List[bytes], List[Image.Image]],
        output_path: Optional[str] = None,
    ) -> ConvertResult:
        """图片转 PDF 便捷方法。

        参数：
            images: 图片文件路径列表、bytes 列表或 PIL Image 列表。
            output_path: 可选输出 PDF 文件路径。

        返回：
            ConvertResult：output_data 包含合并后的 PDF bytes。
        """
        params = ConvertParams(
            direction=ConvertDirection.IMAGES_TO_PDF,
        )
        return self.convert(images, params=params, output_path=output_path)

    # ===== PDF 转图片核心逻辑 =====

    def _convert_pdf_to_images(
        self,
        source: Union[str, bytes],
        params: ConvertParams,
        output_path: Optional[str],
    ) -> ConvertResult:
        """PDF 转图片核心实现。

        使用 PyMuPDF (fitz) 将 PDF 每页渲染为指定 DPI 的图片，
        再通过 Pillow 编码为 PNG 或 JPEG 格式。
        """
        start_time = time.perf_counter()
        warnings: List[str] = []
        source_path = None

        try:
            # 打开 PDF 文档
            if isinstance(source, str):
                source_path = os.path.abspath(source)
                doc = self._open_pdf(source_path)
            elif isinstance(source, bytes):
                doc = self._open_pdf_from_bytes(source)
            else:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    f"PDF 转图片不支持输入类型: {type(source).__name__}",
                    details={"supported_types": ["str", "bytes"]},
                )

            source_format = "pdf"
            total_pages = len(doc)

            # 检查 PDF 页数限制
            if total_pages == 0:
                doc.close()
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    "PDF 文件没有页面",
                    details={"total_pages": 0},
                )
            if total_pages > MAX_PDF_PAGES:
                doc.close()
                raise AppError(
                    ErrorCode.FILE_TOO_LARGE,
                    f"PDF 页数超过限制: {total_pages} > {MAX_PDF_PAGES}",
                    details={
                        "total_pages": total_pages,
                        "max_pages": MAX_PDF_PAGES,
                    },
                )

            # 确定页码范围
            page_range = params.page_range
            if page_range is not None:
                start, end = page_range
                # 1-based 转 0-based
                start_idx = start - 1
                end_idx = min(end - 1, total_pages - 1)
                if start_idx >= total_pages:
                    doc.close()
                    raise AppError(
                        ErrorCode.INVALID_ARGUMENT,
                        f"起始页码 {start} 超出总页数 {total_pages}",
                        details={"start_page": start, "total_pages": total_pages},
                    )
            else:
                start_idx = 0
                end_idx = total_pages - 1

            # 应用页面限制
            if params.page_limit is not None:
                end_idx = min(end_idx, start_idx + params.page_limit - 1)

            selected_pages = list(range(start_idx, end_idx + 1))
            output_count = len(selected_pages)

            # 检查输出目录合法性
            if output_path is not None:
                output_dir_path = Path(output_path)
                if output_dir_path.exists() and not output_dir_path.is_dir():
                    doc.close()
                    raise AppError(
                        ErrorCode.INVALID_ARGUMENT,
                        f"PDF 转图片输出路径必须为目录: {output_path}",
                        details={"output_path": output_path},
                    )
                output_dir_path.mkdir(parents=True, exist_ok=True)

            # 逐页渲染
            pages: List[PageImageResult] = []
            output_suffix = FORMAT_SUFFIX_MAP[params.output_format]

            for page_num_1based in selected_pages:
                page_num = page_num_1based + 1  # 转为 1-based 显示

                # 使用 PyMuPDF 渲染页面到 pixmap
                page = doc[page_num_1based]
                # 计算缩放矩阵以匹配目标 DPI
                zoom = params.dpi / 72.0  # PDF 默认 72 DPI
                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix)

                # 检查输出尺寸
                if pix.width > MAX_OUTPUT_DIMENSION or pix.height > MAX_OUTPUT_DIMENSION:
                    warnings.append(
                        f"第 {page_num} 页渲染尺寸 {pix.width}×{pix.height} "
                        f"超过推荐最大值 {MAX_OUTPUT_DIMENSION}px"
                    )

                # 将 PyMuPDF pixmap 转为 PIL Image
                if pix.alpha:
                    # RGBA 模式
                    pil_img = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
                elif pix.n >= 4:
                    # CMYK 转 RGB
                    pil_img = Image.frombytes("CMYK", (pix.width, pix.height), pix.samples)
                    pil_img = pil_img.convert("RGB")
                else:
                    # RGB 模式
                    pil_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

                # 编码为指定格式的 bytes
                img_data = self._encode_single_image(pil_img, params)

                page_result = PageImageResult(
                    page_number=page_num,
                    width=pil_img.width,
                    height=pil_img.height,
                    data=img_data,
                    format=params.output_format.value,
                    size_bytes=len(img_data),
                )
                pages.append(page_result)

                # 保存到文件（如果指定了输出目录）
                if output_path is not None:
                    filename = f"page_{page_num}{output_suffix}"
                    file_path = str(Path(output_path) / filename)
                    try:
                        Path(file_path).write_bytes(img_data)
                        logger.info("第 %d 页已保存到: %s", page_num, file_path)
                    except Exception as e:
                        warnings.append(f"第 {page_num} 页保存失败: {e}")

                logger.info(
                    "PDF 转图片 | 第 %d/%d 页 | %dx%d | format=%s | size=%d bytes",
                    page_num, total_pages,
                    pil_img.width, pil_img.height,
                    params.output_format.value,
                    len(img_data),
                )

            doc.close()

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            result = ConvertResult(
                success=True,
                direction=ConvertDirection.PDF_TO_IMAGES,
                source_path=source_path,
                source_format=source_format,
                total_pages=total_pages,
                output_pages=output_count,
                pages=pages,
                output_format=params.output_format.value,
                output_size=sum(p.size_bytes for p in pages),
                warnings=warnings,
                elapsed_ms=round(elapsed_ms, 2),
            )

            logger.info(
                "PDF 转图片完成 | 总页数=%d | 输出页数=%d | DPI=%d | format=%s | "
                "输出总大小=%d bytes | 耗时=%.1fms",
                total_pages, output_count, params.dpi,
                params.output_format.value,
                result.output_size, elapsed_ms,
            )

            return result

        except AppError:
            raise
        except Exception as e:
            raise AppError(
                ErrorCode.INTERNAL,
                f"PDF 转图片失败: {e}",
                details={"error": str(e), "source_path": source_path},
            )

    # ===== 图片转 PDF 核心逻辑 =====

    def _convert_images_to_pdf(
        self,
        images: Union[List[str], List[bytes], List[Image.Image]],
        params: ConvertParams,
        output_path: Optional[str],
    ) -> ConvertResult:
        """图片转 PDF 核心实现。

        使用 PyMuPDF (fitz) 将图片逐张转为 PDF 页面后合并。
        输入图片支持透明通道（RGBA 自动转为白色背景）。
        """
        start_time = time.perf_counter()
        warnings: List[str] = []
        source_path = None

        try:
            if not isinstance(images, list):
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    f"图片转 PDF 需要图片列表，收到: {type(images).__name__}",
                    details={"expected": "list"},
                )

            if len(images) == 0:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    "图片列表不能为空",
                    details={"image_count": 0},
                )

            if len(images) > MAX_IMAGES_COUNT:
                raise AppError(
                    ErrorCode.INVALID_ARGUMENT,
                    f"图片数量超过限制: {len(images)} > {MAX_IMAGES_COUNT}",
                    details={
                        "image_count": len(images),
                        "max_count": MAX_IMAGES_COUNT,
                    },
                )

            # 打开所有图片
            pil_images: List[Tuple[str, Image.Image]] = []
            for idx, img_source in enumerate(images):
                label = f"第 {idx + 1} 张图片"
                try:
                    if isinstance(img_source, str):
                        if idx == 0:
                            source_path = os.path.abspath(img_source)
                        pil_img = self._open_image_file(img_source)
                        pil_images.append((label, pil_img))
                    elif isinstance(img_source, bytes):
                        pil_img = self._open_image_from_bytes(img_source)
                        pil_images.append((label, pil_img))
                    elif isinstance(img_source, Image.Image):
                        pil_images.append((label, img_source.copy()))
                    else:
                        raise AppError(
                            ErrorCode.INVALID_ARGUMENT,
                            f"图片列表中第 {idx + 1} 项类型不支持: {type(img_source).__name__}",
                            details={"index": idx, "type": str(type(img_source).__name__)},
                        )
                except AppError:
                    raise
                except Exception as e:
                    raise AppError(
                        ErrorCode.INVALID_ARGUMENT,
                        f"无法打开 {label}: {e}",
                        details={"index": idx, "error": str(e)},
                    )

            # 创建新 PDF 并逐张插入图片
            doc = fitz.open()  # 创建空白 PDF

            pages: List[PageImageResult] = []
            for page_num, (label, pil_img) in enumerate(pil_images, start=1):
                # 处理透明度：RGBA/P 模式先合成为白色背景
                if pil_img.mode in ("RGBA", "PA", "LA"):
                    background = Image.new("RGB", pil_img.size, (255, 255, 255))
                    if pil_img.mode == "PA":
                        pil_img = pil_img.convert("RGBA")
                    if pil_img.mode in ("RGBA", "LA"):
                        background.paste(pil_img, mask=pil_img.split()[-1])
                    pil_img = background
                elif pil_img.mode in ("P", "CMYK", "1", "L"):
                    # 其他模式统一转为 RGB
                    pil_img = pil_img.convert("RGB")

                # 检查尺寸
                if pil_img.width > MAX_OUTPUT_DIMENSION or pil_img.height > MAX_OUTPUT_DIMENSION:
                    warnings.append(
                        f"{label} 尺寸 {pil_img.width}×{pil_img.height} "
                        f"超过推荐最大值 {MAX_OUTPUT_DIMENSION}px"
                    )

                # 将 PIL Image 转为 RGB bytes（JPEG 格式作为中间格式，体积小）
                img_bytes_io = io.BytesIO()
                # 确保是 RGB 模式，因为 JPEG 不支持 RGBA
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                pil_img.save(img_bytes_io, format="JPEG", quality=95)
                img_bytes = img_bytes_io.getvalue()

                # 创建与图片等大的 PDF 页面，使用 fitz 直接插入图片
                page = doc.new_page(width=pil_img.width, height=pil_img.height)
                # 将图片 bytes 插入为页面内容（JPEG 格式）
                page.insert_image(page.rect, stream=img_bytes)

                # 计算图片在 PDF 页面上的尺寸（以点为单位，1pt = 1/72 inch）
                img_width_pt = pil_img.width * 72.0 / 72.0  # 保持像素尺寸
                img_height_pt = pil_img.height * 72.0 / 72.0

                page_result = PageImageResult(
                    page_number=page_num,
                    width=pil_img.width,
                    height=pil_img.height,
                    data=None,  # 图片转 PDF 时单页无独立 data
                    format="pdf_page",
                    size_bytes=0,  # 单页大小难以精确计算
                )
                pages.append(page_result)

                logger.info(
                    "图片转 PDF 中 | %s | %dx%d",
                    label, pil_img.width, pil_img.height,
                )

            # 将合并后的 PDF 写入 bytes
            pdf_bytes_io = io.BytesIO()
            doc.save(pdf_bytes_io)
            doc.close()
            pdf_data = pdf_bytes_io.getvalue()

            # 保存到文件（如果指定了输出路径）
            if output_path is not None:
                self._save_pdf_to_file(pdf_data, output_path)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            result = ConvertResult(
                success=True,
                direction=ConvertDirection.IMAGES_TO_PDF,
                source_path=source_path,
                source_format="images",
                total_pages=len(images),
                output_pages=len(pages),
                pages=pages,
                output_data=pdf_data,
                output_format="pdf",
                output_size=len(pdf_data),
                warnings=warnings,
                elapsed_ms=round(elapsed_ms, 2),
            )

            logger.info(
                "图片转 PDF 完成 | 输入图片数=%d | 输出PDF大小=%d bytes | 耗时=%.1fms",
                len(images), len(pdf_data), elapsed_ms,
            )

            return result

        except AppError:
            raise
        except Exception as e:
            raise AppError(
                ErrorCode.INTERNAL,
                f"图片转 PDF 失败: {e}",
                details={"error": str(e)},
            )

    # ===== 内部方法 =====

    @staticmethod
    def _open_pdf(file_path: str) -> fitz.Document:
        """打开 PDF 文件。

        异常时抛出 AppError。
        """
        path = file_path
        if not os.path.isfile(path):
            raise AppError(
                ErrorCode.FILE_NOT_FOUND,
                f"PDF 文件未找到: {path}",
                details={"path": path},
            )

        suffix = Path(path).suffix.lower()
        if suffix != SUPPORTED_PDF_SUFFIX:
            raise AppError(
                ErrorCode.FILE_UNSUPPORTED_FORMAT,
                f"不支持的文件格式: {suffix}，期望 PDF 文件",
                details={"suffix": suffix, "supported": [SUPPORTED_PDF_SUFFIX]},
            )

        try:
            doc = fitz.open(path)
            return doc
        except Exception as e:
            raise AppError(
                ErrorCode.FILE_READ_ERROR,
                f"无法打开 PDF 文件: {e}",
                details={"path": path, "error": str(e)},
            )

    @staticmethod
    def _open_pdf_from_bytes(data: bytes) -> fitz.Document:
        """从 bytes 数据打开 PDF 文档。

        异常时抛出 AppError。
        """
        if not data:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                "PDF 数据为空",
                details={"data_len": 0},
            )
        try:
            doc = fitz.open(stream=data, filetype="pdf")
            return doc
        except Exception as e:
            raise AppError(
                ErrorCode.INVALID_ARGUMENT,
                f"无法解析 PDF 数据: {e}",
                details={"data_len": len(data), "error": str(e)},
            )

    @staticmethod
    def _open_image_file(file_path: str) -> Image.Image:
        """打开图片文件。

        异常时抛出 AppError。
        """
        path = file_path
        if not os.path.isfile(path):
            raise AppError(
                ErrorCode.FILE_NOT_FOUND,
                f"图片文件未找到: {path}",
                details={"path": path},
            )

        suffix = Path(path).suffix.lower()
        if suffix not in SUPPORTED_IMAGE_INPUT_SUFFIXES:
            raise AppError(
                ErrorCode.FILE_UNSUPPORTED_FORMAT,
                f"不支持的图片格式: {suffix}",
                details={"suffix": suffix, "supported": SUPPORTED_IMAGE_INPUT_SUFFIXES},
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

    @staticmethod
    def _open_image_from_bytes(data: bytes) -> Image.Image:
        """从 bytes 数据打开图片。

        异常时抛出 AppError。
        """
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

    @staticmethod
    def _encode_single_image(
        img: Image.Image,
        params: ConvertParams,
    ) -> bytes:
        """将 PIL Image 编码为目标格式的 bytes。

        参数：
            img: PIL Image 对象。
            params: 转换参数（决定输出格式和质量）。

        返回：
            编码后的图片字节数据。
        """
        buf = io.BytesIO()
        if params.output_format == OutputFormat.JPEG:
            # JPEG 不支持 RGBA，需转为 RGB
            if img.mode in ("RGBA", "LA", "PA", "P"):
                img = img.convert("RGB")
            img.save(buf, format="JPEG", quality=params.jpeg_quality, optimize=True)
        elif params.output_format == OutputFormat.PNG:
            img.save(buf, format="PNG")
        else:
            # 默认使用 PNG
            img.save(buf, format="PNG")

        return buf.getvalue()

    @staticmethod
    def _save_pdf_to_file(data: bytes, file_path: str) -> str:
        """将 PDF bytes 写入文件。

        自动创建不存在的父目录。
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            path.write_bytes(data)
            logger.info("PDF 已保存到: %s (%d bytes)", file_path, len(data))
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
    def get_pdf_info(file_path: str) -> dict:
        """获取 PDF 文件的基本信息（不执行转换）。

        返回包含页数、元数据等的字典。
        """
        doc = PdfImageConverter._open_pdf(file_path)
        try:
            meta = doc.metadata or {}
            return {
                "total_pages": len(doc),
                "format": "PDF",
                "title": meta.get("title", ""),
                "author": meta.get("author", ""),
                "subject": meta.get("subject", ""),
                "producer": meta.get("producer", ""),
                "creation_date": meta.get("creationDate", ""),
            }
        finally:
            doc.close()

    @staticmethod
    def supported_formats() -> dict:
        """返回支持的输入输出格式。"""
        return {
            "pdf_input": [SUPPORTED_PDF_SUFFIX],
            "image_input": SUPPORTED_IMAGE_INPUT_SUFFIXES,
            "image_output": ["png", "jpeg"],
        }
