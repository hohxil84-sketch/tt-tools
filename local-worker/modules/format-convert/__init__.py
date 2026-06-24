"""
local-worker/modules/format-convert — 格式转换、压缩、裁剪、旋转本地实现

基于 Pillow 提供纯本地、离线的图像处理能力。
支持格式互转、有损/无损压缩、矩形/锚点裁剪、直角/任意角度旋转。

对外接口：
    FormatConverter    — 格式转换/压缩/裁剪/旋转处理器
    FormatConvertParams — 格式转换参数
    CompressParams     — 压缩参数
    CropParams         — 裁剪参数
    RotateParams       — 旋转参数
    OperationResult    — 操作结果
    ConvertFormat      — 输出格式枚举
    CropAnchor         — 裁剪锚点枚举
    RotateAngle        — 直角旋转角度枚举

用法示例：
    from modules.format_convert import (
        FormatConverter,
        ConvertFormat,
        CropAnchor,
    )

    converter = FormatConverter()

    # 1. 格式转换：PNG → JPEG
    result = converter.convert_format("input.png", ConvertFormat.JPEG, quality=85)

    # 2. 压缩：JPEG 质量压缩
    result = converter.compress("large.jpg", quality=60)

    # 3. 裁剪：矩形区域裁剪
    result = converter.crop("input.png", left=100, top=50, width=400, height=300)

    # 4. 居中裁剪
    result = converter.crop_center("input.png", 400, 300)

    # 5. 锚点裁剪（右下角）
    result = converter.crop_by_anchor("input.png", 400, 300, anchor=CropAnchor.BOTTOM_RIGHT)

    # 6. 旋转：直角旋转 90°
    result = converter.rotate("input.png", 90)

    # 7. 旋转：任意角度 45°
    result = converter.rotate("input.png", 45.5, expand=True)

    # 8. bytes 输入
    result = converter.convert_format(image_bytes, ConvertFormat.WEBP, quality=80)

    # 9. 保存到文件
    result = converter.compress("input.png", quality=70,
                                output_path="D:\\output\\compressed.jpg")

    # 10. 查询支持的格式
    formats = FormatConverter.supported_formats()

    # 11. 获取图片信息
    info = FormatConverter.get_image_info("input.png")

依赖：Pillow（PIL）、local-worker/shared（errors、logging）
不依赖 GPU，不调用云端 API，不涉及 AI 模型。
"""

# 由于目录名含连字符（format-convert），无法作为 Python 包使用相对导入，
# 因此使用直接导入（模块源码目录在运行时会加入 sys.path）
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
from processor import FormatConverter

__all__ = [
    # 核心类
    "FormatConverter",
    "FormatConvertParams",
    "CompressParams",
    "CropParams",
    "RotateParams",
    "OperationResult",
    # 枚举
    "ConvertFormat",
    "CropAnchor",
    "RotateAngle",
    # 常量和映射
    "FORMAT_SUFFIX_MAP",
    "SUPPORTED_INPUT_SUFFIXES",
    "DEFAULT_JPEG_QUALITY",
    "DEFAULT_PNG_COMPRESS_LEVEL",
    "DEFAULT_WEBP_QUALITY",
    "MAX_OUTPUT_DIMENSION",
]
