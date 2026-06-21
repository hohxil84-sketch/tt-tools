"""
local-worker/modules/resize-image/specifications — 图片改尺寸规格定义

定义改尺寸模式、重采样滤镜、常用预设和结果数据结构。
纯数据层，不包含业务逻辑。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ResizeMode(str, Enum):
    """改尺寸模式。

    EXACT:       精确尺寸 — 按指定的宽×高精确输出（可能拉伸变形）。
    FIT:         等比适配 — 保持宽高比，将图片缩放至指定边界内（不超过边界）。
    FILL:        等比填充 — 保持宽高比，缩放至完全覆盖指定边界（可能裁剪超出部分）。
    SCALE:       百分比缩放 — 按指定百分比缩放（100=原大，50=缩小一半）。
    SHORT_SIDE:  短边约束 — 指定短边目标像素，长边按比例自动计算。
    LONG_SIDE:   长边约束 — 指定长边目标像素，短边按比例自动计算。
    CUSTOM_DPI:  按目标 DPI 缩放 — 根据当前 DPI 和目标 DPI 计算缩放比例。
    """

    EXACT = "exact"
    FIT = "fit"
    FILL = "fill"
    SCALE = "scale"
    SHORT_SIDE = "short_side"
    LONG_SIDE = "long_side"
    CUSTOM_DPI = "custom_dpi"


class ResampleFilter(str, Enum):
    """Pillow 重采样滤镜映射。

    LANCZOS:  高质量缩放的默认选择，锐度最高（Pillow 2.7+ 推荐）。
    BILINEAR: 较快，质量尚可，适合缩小。
    BICUBIC:  较慢，质量略高于 BILINEAR，适合放大。
    NEAREST:  最近邻插值，速度最快，质量最低，适合像素风格图片。
    BOX:      盒状滤波器，每像素用源区域平均计算。
    HAMMING:  Hamming 窗口的 sinc 函数插值，Pillow 3.4+ 新增。
    """

    LANCZOS = "lanczos"
    BILINEAR = "bilinear"
    BICUBIC = "bicubic"
    NEAREST = "nearest"
    BOX = "box"
    HAMMING = "hamming"

    # Pillow Image.Resampling 常量映射
    def to_pil(self):
        """转换为 Pillow Image.Resampling 常量。"""
        from PIL import Image

        mapping = {
            ResampleFilter.LANCZOS: Image.Resampling.LANCZOS,
            ResampleFilter.BILINEAR: Image.Resampling.BILINEAR,
            ResampleFilter.BICUBIC: Image.Resampling.BICUBIC,
            ResampleFilter.NEAREST: Image.Resampling.NEAREST,
            ResampleFilter.BOX: Image.Resampling.BOX,
            ResampleFilter.HAMMING: Image.Resampling.HAMMING,
        }
        return mapping[self]


class OutputFormat(str, Enum):
    """输出格式。

    ORIGINAL: 保持原始格式不变（默认）。
    PNG:      适合带透明通道的图片，无损压缩。
    JPEG:     适合照片和印刷品，有损压缩。
    BMP:      Windows 位图，无压缩。
    TIFF:     印刷标准格式，支持多页和透明通道。
    WEBP:     Web 优化格式，文件小。
    """

    ORIGINAL = "original"
    PNG = "png"
    JPEG = "jpeg"
    BMP = "bmp"
    TIFF = "tiff"
    WEBP = "webp"


# ---- 图文店常用预设尺寸 ----

# 预设尺寸：键名 -> (宽度, 高度, 说明)
# 基于 300 DPI 的常见印刷尺寸，单位为像素
PRINT_PRESETS: Dict[str, Tuple[int, int, str]] = {
    # 证件照
    "id_1inch": (295, 413, "一寸证件照 (25×35mm @300DPI)"),
    "id_2inch": (413, 579, "二寸证件照 (35×49mm @300DPI)"),
    "id_small_1inch": (259, 377, "小一寸证件照 (22×32mm @300DPI)"),
    "id_small_2inch": (390, 567, "小二寸证件照 (33×48mm @300DPI)"),
    # 常见照片
    "photo_5inch": (1500, 1050, "五寸照片 (127×89mm @300DPI)"),
    "photo_6inch": (1800, 1200, "六寸照片 (152×102mm @300DPI)"),
    "photo_7inch": (2100, 1500, "七寸照片 (178×127mm @300DPI)"),
    "photo_a4": (3508, 2480, "A4 照片 (297×210mm @300DPI)"),
    "photo_a5": (2480, 1748, "A5 照片 (210×148mm @300DPI)"),
    "photo_a6": (1748, 1240, "A6 照片 (148×105mm @300DPI)"),
    # 印刷标准
    "print_a3_300dpi": (4961, 3508, "A3 印刷 (420×297mm @300DPI)"),
    "print_a4_300dpi": (3508, 2480, "A4 印刷 (297×210mm @300DPI)"),
    "print_a5_300dpi": (2480, 1748, "A5 印刷 (210×148mm @300DPI)"),
    "print_b5_300dpi": (2953, 2087, "B5 印刷 (250×176mm @300DPI)"),
    "print_a4_150dpi": (1754, 1240, "A4 草图预览 (297×210mm @150DPI)"),
    "print_a3_150dpi": (2480, 1754, "A3 草图预览 (420×297mm @150DPI)"),
    # 名片
    "card_standard": (1063, 638, "标准名片 (90×54mm @300DPI)"),
    # 社交/网络
    "social_square": (1080, 1080, "社交媒体方形 (1:1)"),
    "social_portrait": (1080, 1350, "社交媒体竖版 (4:5)"),
    "social_landscape": (1920, 1080, "社交媒体横版 (16:9)"),
}

# 输出图片格式对应的文件后缀
FORMAT_SUFFIX_MAP: Dict[OutputFormat, str] = {
    OutputFormat.PNG: ".png",
    OutputFormat.JPEG: ".jpg",
    OutputFormat.BMP: ".bmp",
    OutputFormat.TIFF: ".tiff",
    OutputFormat.WEBP: ".webp",
}

# JPEG 默认输出质量（1-100）
DEFAULT_JPEG_QUALITY = 92
# PNG 压缩级别（0-9，越大压缩越高）
DEFAULT_PNG_COMPRESS_LEVEL = 6
# WEBP 默认质量
DEFAULT_WEBP_QUALITY = 85

# 支持输入的图片格式后缀
SUPPORTED_INPUT_SUFFIXES = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"]

# 最大输出尺寸（像素），防止内存溢出
MAX_OUTPUT_DIMENSION = 15000


@dataclass
class ResizeParams:
    """改尺寸参数。

    mode:            改尺寸模式。
    width:           目标宽度（EXACT/FIT/FILL 模式）。
    height:          目标高度（EXACT/FIT/FILL 模式）。
    scale_percent:   缩放百分比（SCALE 模式），100 为原大。
    short_side:      短边目标像素（SHORT_SIDE 模式）。
    long_side:       长边目标像素（LONG_SIDE 模式）。
    target_dpi:      目标 DPI（CUSTOM_DPI 模式）。
    resample:        重采样滤镜，默认 LANCZOS。
    keep_aspect:     是否保持宽高比（EXACT 模式设为 True 会退化为 FIT 模式）。
    output_format:   输出格式，默认保持原格式。
    jpeg_quality:    JPEG 输出质量（1-100），默认 92。
    dpi:             输出 DPI 值，None 则保持原始 DPI。
    """

    mode: ResizeMode = ResizeMode.FIT
    width: Optional[int] = None
    height: Optional[int] = None
    scale_percent: float = 100.0
    short_side: Optional[int] = None
    long_side: Optional[int] = None
    target_dpi: Optional[int] = None
    resample: ResampleFilter = ResampleFilter.LANCZOS
    keep_aspect: bool = True
    output_format: OutputFormat = OutputFormat.ORIGINAL
    jpeg_quality: int = DEFAULT_JPEG_QUALITY
    png_compress_level: int = DEFAULT_PNG_COMPRESS_LEVEL
    webp_quality: int = DEFAULT_WEBP_QUALITY
    dpi: Optional[Tuple[float, float]] = None

    def validate(self) -> List[str]:
        """校验参数合法性，返回错误信息列表。

        返回空列表表示参数有效。
        """
        errors: List[str] = []

        if self.scale_percent <= 0:
            errors.append(f"缩放百分比必须大于 0，当前值: {self.scale_percent}")

        if self.mode in (ResizeMode.EXACT, ResizeMode.FIT, ResizeMode.FILL):
            if self.width is not None and self.width <= 0:
                errors.append(f"目标宽度必须大于 0，当前值: {self.width}")
            if self.height is not None and self.height <= 0:
                errors.append(f"目标高度必须大于 0，当前值: {self.height}")
            if self.width is None and self.height is None:
                errors.append("EXACT/FIT/FILL 模式至少需要指定 width 或 height")
            if self.width and self.width > MAX_OUTPUT_DIMENSION:
                errors.append(f"目标宽度超过最大限制 {MAX_OUTPUT_DIMENSION}px")
            if self.height and self.height > MAX_OUTPUT_DIMENSION:
                errors.append(f"目标高度超过最大限制 {MAX_OUTPUT_DIMENSION}px")

        if self.mode == ResizeMode.SHORT_SIDE:
            if self.short_side is None or self.short_side <= 0:
                errors.append(f"SHORT_SIDE 模式必须指定有效的 short_side，当前值: {self.short_side}")
            elif self.short_side > MAX_OUTPUT_DIMENSION:
                errors.append(f"short_side 超过最大限制 {MAX_OUTPUT_DIMENSION}px")

        if self.mode == ResizeMode.LONG_SIDE:
            if self.long_side is None or self.long_side <= 0:
                errors.append(f"LONG_SIDE 模式必须指定有效的 long_side，当前值: {self.long_side}")
            elif self.long_side > MAX_OUTPUT_DIMENSION:
                errors.append(f"long_side 超过最大限制 {MAX_OUTPUT_DIMENSION}px")

        if self.mode == ResizeMode.CUSTOM_DPI:
            if self.target_dpi is None or self.target_dpi <= 0:
                errors.append(f"CUSTOM_DPI 模式必须指定有效的 target_dpi，当前值: {self.target_dpi}")

        if self.jpeg_quality < 1 or self.jpeg_quality > 100:
            errors.append(f"JPEG 质量必须在 1-100 之间，当前值: {self.jpeg_quality}")

        if self.png_compress_level < 0 or self.png_compress_level > 9:
            errors.append(f"PNG 压缩级别必须在 0-9 之间，当前值: {self.png_compress_level}")

        if self.webp_quality < 1 or self.webp_quality > 100:
            errors.append(f"WEBP 质量必须在 1-100 之间，当前值: {self.webp_quality}")

        return errors


@dataclass
class ResizeResult:
    """改尺寸结果。

    success:         是否成功。
    source_path:     原图路径（输入为文件时）。
    source_width:    原图宽度（像素）。
    source_height:   原图高度（像素）。
    output_width:    输出宽度（像素）。
    output_height:   输出高度（像素）。
    mode:            使用的改尺寸模式。
    scale_ratio:     实际缩放比例（输出/输入）。
    output_format:   输出格式。
    output_size:     输出图片字节大小。
    output_data:     输出图片二进制数据（bytes）。
    dpi:             输出 DPI 信息。
    warnings:        警告信息列表（如拉伸变形提示）。
    elapsed_ms:      处理耗时（毫秒）。
    """

    success: bool = False
    source_path: Optional[str] = None
    source_width: int = 0
    source_height: int = 0
    output_width: int = 0
    output_height: int = 0
    mode: Optional[ResizeMode] = None
    scale_ratio: float = 1.0
    output_format: str = ""
    output_size: int = 0
    output_data: Optional[bytes] = None
    dpi: Optional[Tuple[float, float]] = None
    warnings: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0
    error_message: str = ""

    @property
    def ratio_display(self) -> str:
        """缩放比例的可读显示。"""
        if self.scale_ratio == 1.0:
            return "1:1 (原始)"
        elif self.scale_ratio > 1.0:
            return f"{self.scale_ratio:.2f}:1 (放大)"
        else:
            return f"1:{1.0 / self.scale_ratio:.2f} (缩小)"

    def to_dict(self) -> Dict:
        """转为字典，便于序列化和跨进程传输。"""
        return {
            "success": self.success,
            "source_path": self.source_path,
            "source_width": self.source_width,
            "source_height": self.source_height,
            "output_width": self.output_width,
            "output_height": self.output_height,
            "mode": self.mode.value if self.mode else None,
            "scale_ratio": round(self.scale_ratio, 6),
            "output_format": self.output_format,
            "output_size": self.output_size,
            "dpi": list(self.dpi) if self.dpi else None,
            "warnings": self.warnings,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "error_message": self.error_message,
        }
