"""
local-worker/modules/pdf-image-convert/specifications — PDF/图片互转规格定义

定义转换方向、输出格式、参数和结果数据结构。
纯数据层，不包含业务逻辑。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union


class ConvertDirection(str, Enum):
    """转换方向。

    PDF_TO_IMAGES:  PDF 转图片 — 将 PDF 的每一页渲染为独立图片。
    IMAGES_TO_PDF:  图片转 PDF — 将一张或多张图片合并为一个 PDF。
    """

    PDF_TO_IMAGES = "pdf_to_images"
    IMAGES_TO_PDF = "images_to_pdf"


class OutputFormat(str, Enum):
    """PDF 转图片时的输出格式。

    PNG:  适合带透明通道的图片，无损压缩，文件较大。
    JPEG: 适合照片和印刷品，有损压缩，文件较小。
    """

    PNG = "png"
    JPEG = "jpeg"


# PDF 转图片时支持的输出图片格式
PDF_TO_IMAGES_SUPPORTED_FORMATS = [OutputFormat.PNG, OutputFormat.JPEG]

# PDF 转图片输出格式对应的文件后缀
FORMAT_SUFFIX_MAP: Dict[OutputFormat, str] = {
    OutputFormat.PNG: ".png",
    OutputFormat.JPEG: ".jpg",
}

# 支持输入的图片格式后缀（图片转 PDF 时接受的输入格式）
SUPPORTED_IMAGE_INPUT_SUFFIXES = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"]

# 支持输入的 PDF 后缀
SUPPORTED_PDF_SUFFIX = ".pdf"

# PDF 转图片默认输出 DPI（用于渲染清晰度）
DEFAULT_PDF_RENDER_DPI = 200

# JPEG 默认输出质量（1-100）
DEFAULT_JPEG_QUALITY = 92

# 最大输出尺寸（像素），防止内存溢出
MAX_OUTPUT_DIMENSION = 15000

# 最大 PDF 页数限制，防止恶意大文件
MAX_PDF_PAGES = 500

# 最大批量图片数量限制（图片转 PDF 时）
MAX_IMAGES_COUNT = 100


@dataclass
class ConvertParams:
    """PDF/图片互转参数。

    direction:        转换方向（PDF→图片 或 图片→PDF）。
    output_format:    PDF 转图片时的输出格式，默认 PNG。
    dpi:              PDF 转图片时的渲染 DPI，默认 200。
                      值越高图片越清晰，但文件越大、处理越慢。
    jpeg_quality:     JPEG 输出质量（1-100），默认 92。
    page_range:       PDF 转图片时的页码范围（1-based），
                      格式为 (start, end)，包含两端。
                      None 表示转换所有页面。
    page_limit:       最多转换的页数上限，默认不限制。
    """
    direction: ConvertDirection = ConvertDirection.PDF_TO_IMAGES
    output_format: OutputFormat = OutputFormat.PNG
    dpi: int = DEFAULT_PDF_RENDER_DPI
    jpeg_quality: int = DEFAULT_JPEG_QUALITY
    page_range: Optional[Tuple[int, int]] = None
    page_limit: Optional[int] = None

    def validate(self) -> List[str]:
        """校验参数合法性，返回错误信息列表。

        返回空列表表示参数有效。
        """
        errors: List[str] = []

        if self.dpi < 72 or self.dpi > 600:
            errors.append(f"DPI 必须在 72-600 之间，当前值: {self.dpi}")

        if self.jpeg_quality < 1 or self.jpeg_quality > 100:
            errors.append(f"JPEG 质量必须在 1-100 之间，当前值: {self.jpeg_quality}")

        if self.page_range is not None:
            start, end = self.page_range
            if start < 1:
                errors.append(f"起始页码必须 >= 1，当前值: {start}")
            if end < start:
                errors.append(f"结束页码必须 >= 起始页码，当前值: start={start}, end={end}")

        if self.page_limit is not None and self.page_limit < 1:
            errors.append(f"页面限制必须 >= 1，当前值: {self.page_limit}")

        return errors


@dataclass
class PageImageResult:
    """单页转换结果。

    page_number:  页码（1-based），图片转 PDF 时为插入序号。
    width:        图片宽度（像素）。
    height:       图片高度（像素）。
    data:         图片二进制数据（bytes）。
    format:       图片格式字符串，如 "png"、"jpeg"。
    size_bytes:   图片字节大小。
    """

    page_number: int = 0
    width: int = 0
    height: int = 0
    data: Optional[bytes] = None
    format: str = ""
    size_bytes: int = 0

    def to_dict(self) -> Dict:
        """转为字典，便于序列化和跨进程传输。"""
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "size_bytes": self.size_bytes,
            # data 不包含在字典中（体积大，由上层根据需要序列化）
        }


@dataclass
class ConvertResult:
    """PDF/图片互转结果。

    success:         是否成功。
    direction:       转换方向。
    source_path:     输入文件路径（输入为文件时）。
    source_format:   输入格式（如 "pdf"、"png"）。
    total_pages:     总页数（PDF→图片）或总输入图片数（图片→PDF）。
    output_pages:    输出页数/图片数量。
    pages:           每页/每图的转换结果列表。
    output_data:     输出文件二进制数据（图片转 PDF 时存放最终 PDF bytes）。
    output_format:   输出格式。
    output_size:     输出文件字节大小。
    warnings:        警告信息列表。
    elapsed_ms:      处理耗时（毫秒）。
    error_message:   错误信息。
    """

    success: bool = False
    direction: Optional[ConvertDirection] = None
    source_path: Optional[str] = None
    source_format: str = ""
    total_pages: int = 0
    output_pages: int = 0
    pages: List[PageImageResult] = field(default_factory=list)
    output_data: Optional[bytes] = None
    output_format: str = ""
    output_size: int = 0
    warnings: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict:
        """转为字典，便于序列化和跨进程传输。"""
        return {
            "success": self.success,
            "direction": self.direction.value if self.direction else None,
            "source_path": self.source_path,
            "source_format": self.source_format,
            "total_pages": self.total_pages,
            "output_pages": self.output_pages,
            "pages": [p.to_dict() for p in self.pages],
            "output_format": self.output_format,
            "output_size": self.output_size,
            "warnings": self.warnings,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "error_message": self.error_message,
        }
