"""
local-worker/modules/resize-image — 图片改尺寸本地实现

基于 Pillow 提供纯本地、离线的图片缩放能力。
支持常见印刷尺寸、多种缩放模式和导出策略。
本地付费功能（resize_image_local_paid），需桌面端先通过 entitlements/check 校验套餐权限。

对外接口：
    ImageResizer  — 图片改尺寸处理器
    ResizeParams  — 改尺寸参数
    ResizeResult  — 改尺寸结果
    ResizeMode    — 缩放模式枚举
    ResampleFilter— 重采样滤镜枚举
    OutputFormat  — 输出格式枚举
    PRINT_PRESETS — 图文店常用预设尺寸字典

用法示例：
    from modules.resize_image import ImageResizer, ResizeParams, ResizeMode

    resizer = ImageResizer()

    # 1. 使用预设尺寸（一寸证件照）
    result = resizer.resize("input.png", preset="id_1inch")

    # 2. 等比适配缩放
    result = resizer.resize_fit("input.png", 800, 600)

    # 3. 百分比缩放
    result = resizer.resize_scale("input.png", 50)

    # 4. 自定义参数
    params = ResizeParams(
        mode=ResizeMode.FIT,
        width=1920,
        height=1080,
        output_format=OutputFormat.JPEG,
        jpeg_quality=85,
    )
    result = resizer.resize("input.png", params=params)

    # 5. 保存到文件
    result = resizer.resize("input.png", preset="print_a4_300dpi",
                            output_path="D:\\output\\print_a4.jpg")

    # 6. 从 bytes 处理
    result = resizer.resize_bytes(image_bytes, preset="social_square")

    # 7. 查看所有可用预设
    presets = ImageResizer.list_presets()
    for p in presets:
        print(f"{p['name']}: {p['width']}×{p['height']} - {p['description']}")

依赖：Pillow（PIL）、local-worker/shared（file_io、errors、logging）
不依赖 GPU，不调用云端 API，不涉及 AI 模型。
"""

# 由于目录名含连字符（resize-image），无法作为 Python 包使用相对导入，
# 因此使用直接导入（模块源码目录在运行时会加入 sys.path）
from specifications import (
    ResizeMode,
    ResampleFilter,
    OutputFormat,
    ResizeParams,
    ResizeResult,
    PRINT_PRESETS,
    SUPPORTED_INPUT_SUFFIXES,
    FORMAT_SUFFIX_MAP,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_PNG_COMPRESS_LEVEL,
    DEFAULT_WEBP_QUALITY,
)
from processor import ImageResizer

__all__ = [
    # 核心类
    "ImageResizer",
    "ResizeParams",
    "ResizeResult",
    # 枚举
    "ResizeMode",
    "ResampleFilter",
    "OutputFormat",
    # 预设和常量
    "PRINT_PRESETS",
    "SUPPORTED_INPUT_SUFFIXES",
    "FORMAT_SUFFIX_MAP",
    "DEFAULT_JPEG_QUALITY",
    "DEFAULT_PNG_COMPRESS_LEVEL",
    "DEFAULT_WEBP_QUALITY",
]
