"""
local-worker/modules/id-photo/specifications — 证件照规格和底色定义

定义常用证件照尺寸、DPI 标准和背景色。
规格参考国内常见证件照标准（1寸、2寸、小1寸、小2寸等）。
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ---- 标准 DPI ----
# 证件照标准打印分辨率
STANDARD_DPI = 300

# 屏幕预览默认 DPI
SCREEN_DPI = 96


@dataclass
class PhotoSpec:
    """证件照规格定义。

    包含物理尺寸（毫米）和像素尺寸（基于标准 DPI 计算）。
    """

    # 规格名称（中文），如 "1寸"
    name: str

    # 物理尺寸（毫米）
    width_mm: int
    height_mm: int

    # 像素尺寸（基于 DPI 计算，调用方传入 dpi 后得出）
    # 默认使用 STANDARD_DPI = 300
    dpi: int = STANDARD_DPI

    @property
    def width_px(self) -> int:
        """像素宽度 = mm * DPI / 25.4"""
        return round(self.width_mm * self.dpi / 25.4)

    @property
    def height_px(self) -> int:
        """像素高度 = mm * DPI / 25.4"""
        return round(self.height_mm * self.dpi / 25.4)

    @property
    def size_mm(self) -> Tuple[int, int]:
        """返回 (宽_mm, 高_mm) 元组。"""
        return (self.width_mm, self.height_mm)

    @property
    def size_px(self) -> Tuple[int, int]:
        """返回 (宽_px, 高_px) 元组。"""
        return (self.width_px, self.height_px)


# ---- 常用证件照规格 ----
# 尺寸参考：
#   1寸：25mm × 35mm（常见于身份证、驾照等）
#   2寸：35mm × 49mm（常见于护照、简历照等）
#   小1寸：22mm × 32mm（常见于某些签证）
#   小2寸：33mm × 48mm（常见于某些考试报名）

# 默认 DPI 下的规格表
_DEFAULT_SPECS: Dict[str, PhotoSpec] = {}

# 标准规格定义（物理尺寸，mm）
_SPEC_DEFINITIONS = [
    ("1寸", 25, 35),
    ("2寸", 35, 49),
    ("小1寸", 22, 32),
    ("小2寸", 33, 48),
    ("大一寸", 33, 48),
    ("大二寸", 35, 53),
    ("5寸", 89, 127),
]


def _build_default_specs(dpi: int = STANDARD_DPI) -> Dict[str, PhotoSpec]:
    """构造默认规格表。"""
    specs: Dict[str, PhotoSpec] = {}
    for name, w, h in _SPEC_DEFINITIONS:
        specs[name] = PhotoSpec(name=name, width_mm=w, height_mm=h, dpi=dpi)
    return specs


def get_spec(name: str, dpi: int = STANDARD_DPI) -> PhotoSpec:
    """按名称获取证件照规格。

    参数：
        name: 规格名称，如 "1寸"、"2寸"。
        dpi: 目标 DPI，默认 300。

    返回：
        PhotoSpec 对象。

    异常：
        ValueError: 未知规格名称。
    """
    specs = _build_default_specs(dpi)
    if name not in specs:
        raise ValueError(
            f"未知证件照规格: {name}。"
            f"可用规格: {', '.join(specs.keys())}"
        )
    return specs[name]


def list_specs(dpi: int = STANDARD_DPI) -> List[PhotoSpec]:
    """列出所有支持的证件照规格。"""
    specs = _build_default_specs(dpi)
    return list(specs.values())


def get_spec_by_size(
    width_px: int,
    height_px: int,
    dpi: int = STANDARD_DPI,
) -> Optional[PhotoSpec]:
    """根据像素尺寸匹配最接近的规格。

    返回匹配的 PhotoSpec，如果没有接近的规格则返回 None。
    """
    specs = _build_default_specs(dpi)
    best = None
    best_dist = float("inf")
    for spec in specs.values():
        dist = abs(spec.width_px - width_px) + abs(spec.height_px - height_px)
        if dist < best_dist:
            best_dist = dist
            best = spec
    # 如果最小距离超过 50 像素，认为没有匹配
    if best_dist > 50:
        return None
    return best


# ---- 常用背景色 ----
# 证件照常用底色 RGB 值


@dataclass
class BackgroundColor:
    """证件照背景色定义。"""

    # 颜色名称（中文）
    name: str

    # RGB 值
    r: int
    g: int
    b: int

    def to_bgr(self) -> Tuple[int, int, int]:
        """转为 OpenCV 使用的 BGR 顺序。"""
        return (self.b, self.g, self.r)

    def to_rgb(self) -> Tuple[int, int, int]:
        """返回 RGB 值。"""
        return (self.r, self.g, self.b)

    def to_hex(self) -> str:
        """返回十六进制颜色字符串，如 "#FF0000"。"""
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    @property
    def bgr_tuple(self) -> Tuple[int, int, int]:
        """OpenCV BGR 格式的颜色元组。"""
        return self.to_bgr()


# 常用底色定义
# 红色：标准证件照红底 RGB(255, 0, 0) 过于鲜艳，
#       实际常用偏暗一点的红色
# 蓝色：常见于护照照片
# 白色：最常见

BACKGROUND_COLORS: Dict[str, BackgroundColor] = {
    "white": BackgroundColor("白色", 255, 255, 255),
    "red": BackgroundColor("红色", 219, 0, 0),          # 标准红底
    "blue": BackgroundColor("蓝色", 67, 142, 219),       # 护照蓝底
    "light_blue": BackgroundColor("浅蓝", 100, 170, 235), # 浅蓝
    "dark_red": BackgroundColor("深红", 180, 0, 0),       # 深红
    "gray": BackgroundColor("灰色", 200, 200, 200),       # 灰底
}


def get_background_color(name: str) -> BackgroundColor:
    """按名称获取背景色。

    参数：
        name: 颜色名称（支持中文名和英文 key）。

    返回：
        BackgroundColor 对象。

    异常：
        ValueError: 未知颜色名称。
    """
    # 先按英文 key 查找
    if name in BACKGROUND_COLORS:
        return BACKGROUND_COLORS[name]
    # 再按中文名称查找
    for color in BACKGROUND_COLORS.values():
        if color.name == name:
            return color
    raise ValueError(
        f"未知背景色: {name}。"
        f"可用颜色: {', '.join(c.name for c in BACKGROUND_COLORS.values())}"
    )


def list_background_colors() -> List[BackgroundColor]:
    """列出所有支持的背景色。"""
    return list(BACKGROUND_COLORS.values())
