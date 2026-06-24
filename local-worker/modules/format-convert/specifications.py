"""
local-worker/modules/format-convert/specifications — 格式转换规格定义

定义格式转换、压缩、裁剪、旋转的枚举、参数和结果数据结构。
纯数据层，不包含业务逻辑。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ConvertFormat(str, Enum):
    """输出格式枚举。

    ORIGINAL: 保持原始格式不变。
    PNG:      PNG 格式，无损压缩，支持透明通道。
    JPEG:     JPEG 格式，有损压缩，适合照片和印刷品。
    BMP:      Windows 位图，无压缩，文件较大。
    TIFF:     TIFF 格式，支持多页和透明通道，印刷标准格式。
    WEBP:     WebP 格式，支持有损/无损，文件小。
    GIF:      GIF 格式，支持动画（仅首帧）。
    ICO:      ICO 图标格式。
    """

    ORIGINAL = "original"
    PNG = "png"
    JPEG = "jpeg"
    BMP = "bmp"
    TIFF = "tiff"
    WEBP = "webp"
    GIF = "gif"
    ICO = "ico"


class CropAnchor(str, Enum):
    """裁剪锚点（对齐方式）。

    CENTER:      居中裁剪。
    TOP_LEFT:    左上角对齐。
    TOP_RIGHT:   右上角对齐。
    BOTTOM_LEFT: 左下角对齐。
    BOTTOM_RIGHT:右下角对齐。
    """

    CENTER = "center"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class RotateAngle(str, Enum):
    """旋转角度（直角旋转）。

    ROTATE_90:  顺时针 90°。
    ROTATE_180: 顺时针 180°。
    ROTATE_270: 顺时针 270°。
    """

    ROTATE_90 = "90"
    ROTATE_180 = "180"
    ROTATE_270 = "270"


# ---- 格式相关常量 ----

# 输出格式对应的文件后缀
FORMAT_SUFFIX_MAP: Dict[ConvertFormat, str] = {
    ConvertFormat.PNG: ".png",
    ConvertFormat.JPEG: ".jpg",
    ConvertFormat.BMP: ".bmp",
    ConvertFormat.TIFF: ".tiff",
    ConvertFormat.WEBP: ".webp",
    ConvertFormat.GIF: ".gif",
    ConvertFormat.ICO: ".ico",
}

# 支持输入的图片格式后缀
SUPPORTED_INPUT_SUFFIXES = [
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif", ".ico",
]

# JPEG 默认输出质量（1-100），默认值 85 为质量和体积的平衡点
DEFAULT_JPEG_QUALITY = 85
# PNG 压缩级别（0-9），6 为默认平衡点
DEFAULT_PNG_COMPRESS_LEVEL = 6
# WEBP 默认质量（1-100）
DEFAULT_WEBP_QUALITY = 85

# 最大输出尺寸（像素），防止内存溢出
MAX_OUTPUT_DIMENSION = 15000
# 最大输入文件大小（字节），默认 100MB
DEFAULT_MAX_INPUT_SIZE = 100 * 1024 * 1024


@dataclass
class FormatConvertParams:
    """格式转换参数。

    format:         目标输出格式（ORIGINAL 表示保持原格式）。
    jpeg_quality:   JPEG 输出质量（1-100），默认 85。
    png_compress:   PNG 压缩级别（0-9），默认 6。
    webp_quality:   WEBP 输出质量（1-100），默认 85。
    preserve_alpha: 是否保留透明通道（对有 alpha 的图片输出为有损格式时，
                    可转为白色背景或不保留 alpha）。
    """

    format: ConvertFormat = ConvertFormat.ORIGINAL
    jpeg_quality: int = DEFAULT_JPEG_QUALITY
    png_compress: int = DEFAULT_PNG_COMPRESS_LEVEL
    webp_quality: int = DEFAULT_WEBP_QUALITY
    preserve_alpha: bool = True

    def validate(self) -> List[str]:
        """校验参数合法性，返回错误信息列表。"""
        errors: List[str] = []
        if self.jpeg_quality < 1 or self.jpeg_quality > 100:
            errors.append(f"JPEG 质量必须在 1-100 之间，当前值: {self.jpeg_quality}")
        if self.png_compress < 0 or self.png_compress > 9:
            errors.append(f"PNG 压缩级别必须在 0-9 之间，当前值: {self.png_compress}")
        if self.webp_quality < 1 or self.webp_quality > 100:
            errors.append(f"WEBP 质量必须在 1-100 之间，当前值: {self.webp_quality}")
        return errors


@dataclass
class CompressParams:
    """压缩参数。

    format:         压缩后的输出格式（ORIGINAL 表示保持原格式）。
    quality:        输出质量（1-100），适用于 JPEG 和 WEBP 有损压缩。
                    值越小压缩率越高、文件越小、质量越低。
    png_compress:   PNG 压缩级别（0-9），9 为最高压缩率。
    max_size_bytes: 目标最大文件大小（字节），作为质量选择的参考依据。
                    仅对有损格式生效，PNG 等无损格式忽略。
    """

    format: ConvertFormat = ConvertFormat.ORIGINAL
    quality: int = 75
    png_compress: int = 9
    max_size_bytes: Optional[int] = None

    def validate(self) -> List[str]:
        """校验参数合法性，返回错误信息列表。"""
        errors: List[str] = []
        if self.quality < 1 or self.quality > 100:
            errors.append(f"压缩质量必须在 1-100 之间，当前值: {self.quality}")
        if self.png_compress < 0 or self.png_compress > 9:
            errors.append(f"PNG 压缩级别必须在 0-9 之间，当前值: {self.png_compress}")
        if self.max_size_bytes is not None and self.max_size_bytes < 1:
            errors.append(f"max_size_bytes 必须 >= 1，当前值: {self.max_size_bytes}")
        return errors


@dataclass
class CropParams:
    """裁剪参数。

    left:   裁剪区域左边界（像素），相对于原图左上角。
    top:    裁剪区域上边界（像素），相对于原图左上角。
    width:  裁剪区域宽度（像素）。
    height: 裁剪区域高度（像素）。
    anchor: 锚点对齐方式，与 left/top 互斥。
            当使用 anchor 时，裁剪区域居中或对齐到指定角。
    """

    width: int = 0
    height: int = 0
    left: int = 0
    top: int = 0
    anchor: Optional[CropAnchor] = None

    def validate(self) -> List[str]:
        """校验参数合法性，返回错误信息列表。"""
        errors: List[str] = []
        if self.width <= 0:
            errors.append(f"裁剪宽度必须大于 0，当前值: {self.width}")
        if self.height <= 0:
            errors.append(f"裁剪高度必须大于 0，当前值: {self.height}")
        if self.width > MAX_OUTPUT_DIMENSION:
            errors.append(f"裁剪宽度超过最大限制 {MAX_OUTPUT_DIMENSION}px，当前值: {self.width}")
        if self.height > MAX_OUTPUT_DIMENSION:
            errors.append(f"裁剪高度超过最大限制 {MAX_OUTPUT_DIMENSION}px，当前值: {self.height}")
        return errors


@dataclass
class RotateParams:
    """旋转参数。

    angle:          旋转角度。
                    - 直角旋转：90、180、270 度（快速，无插值损失）。
                    - 任意角度：支持 0~360 之间的任意值。
    expand:         是否扩展画布以容纳旋转后完整图像。
                    True 时画布变大，False 时保持原画布大小（超出部分被裁剪）。
    fillcolor:      旋转后空白区域的填充颜色，RGB 元组。
                    默认白色 (255, 255, 255)。仅对非直角旋转有效。
    """

    angle: float = 90.0
    expand: bool = True
    fillcolor: Tuple[int, int, int] = (255, 255, 255)

    def validate(self) -> List[str]:
        """校验参数合法性，返回错误信息列表。"""
        errors: List[str] = []
        if self.angle < -360 or self.angle > 360:
            errors.append(f"旋转角度必须在 -360~360 之间，当前值: {self.angle}")
        if len(self.fillcolor) != 3:
            errors.append(f"fillcolor 必须是 RGB 三元组，当前值: {self.fillcolor}")
        else:
            for i, v in enumerate(self.fillcolor):
                if v < 0 or v > 255:
                    errors.append(f"fillcolor[{i}] 超出范围 0-255: {v}")
        return errors


@dataclass
class OperationResult:
    """单次操作结果。

    success:       是否成功。
    source_path:   输入文件路径（输入为文件时）。
    source_width:  原图宽度（像素）。
    source_height: 原图高度（像素）。
    output_width:  输出宽度（像素）。
    output_height: 输出高度（像素）。
    output_format: 输出格式字符串（如 "png"、"jpeg"）。
    output_size:   输出图片字节大小。
    output_data:   输出图片二进制数据（bytes）。
    compression_ratio: 压缩比（输出/输入），仅压缩操作有意义。
    warnings:      警告信息列表。
    elapsed_ms:    处理耗时（毫秒）。
    error_message: 错误信息。
    """

    success: bool = False
    source_path: Optional[str] = None
    source_width: int = 0
    source_height: int = 0
    output_width: int = 0
    output_height: int = 0
    output_format: str = ""
    output_size: int = 0
    output_data: Optional[bytes] = None
    compression_ratio: float = 1.0
    warnings: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict:
        """转为字典，便于序列化和跨进程传输。"""
        return {
            "success": self.success,
            "source_path": self.source_path,
            "source_width": self.source_width,
            "source_height": self.source_height,
            "output_width": self.output_width,
            "output_height": self.output_height,
            "output_format": self.output_format,
            "output_size": self.output_size,
            "compression_ratio": round(self.compression_ratio, 4),
            "warnings": self.warnings,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "error_message": self.error_message,
        }
