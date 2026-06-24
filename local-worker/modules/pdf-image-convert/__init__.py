"""
local-worker/modules/pdf-image-convert — PDF/图片互转本地实现

基于 PyMuPDF (fitz) 和 Pillow 提供纯本地、离线的 PDF/图片互转能力。
支持单文件处理，设计上预留批量扩展。

本地付费功能（pdf_image_convert_local_paid），需桌面端先通过 entitlements/check 校验套餐权限。

对外接口：
    PdfImageConverter   — PDF/图片互转处理器
    ConvertParams       — 转换参数
    ConvertResult       — 转换结果
    PageImageResult     — 单页/单图转换结果
    ConvertDirection    — 转换方向枚举
    OutputFormat        — 输出格式枚举

用法示例：
    from modules.pdf_image_convert import (
        PdfImageConverter,
        ConvertDirection,
        OutputFormat,
    )

    converter = PdfImageConverter()

    # 1. PDF 转图片（文件路径输入，指定 DPI=300）
    result = converter.pdf_to_images("input.pdf", dpi=300)

    # 2. PDF 转图片（bytes 输入，指定页码范围）
    with open("input.pdf", "rb") as f:
        pdf_data = f.read()
    result = converter.pdf_to_images(pdf_data, page_range=(1, 3))

    # 3. PDF 转图片并保存到目录
    result = converter.convert(
        "input.pdf",
        params=ConvertParams(direction=ConvertDirection.PDF_TO_IMAGES, dpi=150),
        output_path="D:\\output\\pdf_pages",
    )

    # 4. 图片转 PDF（多张图片合并）
    result = converter.images_to_pdf(["page1.png", "page2.jpg"])

    # 5. 图片转 PDF（bytes 列表输入）
    result = converter.images_to_pdf([img1_bytes, img2_bytes])

    # 6. 保存合并后的 PDF
    result = converter.images_to_pdf(
        ["img1.png", "img2.jpg"],
        output_path="D:\\output\\merged.pdf",
    )

    # 7. 使用主入口
    result = converter.convert(
        "input.pdf",
        params=ConvertParams(
            direction=ConvertDirection.PDF_TO_IMAGES,
            output_format=OutputFormat.JPEG,
            dpi=200,
            page_range=(1, 5),
        ),
    )

    # 8. 查询支持的格式
    formats = PdfImageConverter.supported_formats()

    # 9. 获取 PDF 信息
    info = PdfImageConverter.get_pdf_info("input.pdf")

依赖：PyMuPDF (fitz)、Pillow、local-worker/shared（file_io、errors、logging）
不依赖 GPU，不调用云端 API，不涉及 AI 模型。
"""

# 由于目录名含连字符（pdf-image-convert），无法作为 Python 包使用相对导入，
# 因此使用直接导入（模块源码目录在运行时会加入 sys.path）
from specifications import (
    ConvertDirection,
    OutputFormat,
    ConvertParams,
    ConvertResult,
    PageImageResult,
    FORMAT_SUFFIX_MAP,
    SUPPORTED_IMAGE_INPUT_SUFFIXES,
    SUPPORTED_PDF_SUFFIX,
    DEFAULT_PDF_RENDER_DPI,
    DEFAULT_JPEG_QUALITY,
    MAX_OUTPUT_DIMENSION,
    MAX_PDF_PAGES,
    MAX_IMAGES_COUNT,
)
from processor import PdfImageConverter

__all__ = [
    # 核心类
    "PdfImageConverter",
    "ConvertParams",
    "ConvertResult",
    "PageImageResult",
    # 枚举
    "ConvertDirection",
    "OutputFormat",
    # 常量和映射
    "FORMAT_SUFFIX_MAP",
    "SUPPORTED_IMAGE_INPUT_SUFFIXES",
    "SUPPORTED_PDF_SUFFIX",
    "DEFAULT_PDF_RENDER_DPI",
    "DEFAULT_JPEG_QUALITY",
    "MAX_OUTPUT_DIMENSION",
    "MAX_PDF_PAGES",
    "MAX_IMAGES_COUNT",
]
