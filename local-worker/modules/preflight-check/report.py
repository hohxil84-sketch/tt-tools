"""
local-worker/modules/preflight-check/report — 印前检查报告数据结构

定义检查结果、风险等级和综合报告结构。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class RiskLevel(str, Enum):
    """风险等级。

    pass：无风险，可直接印刷。
    warning：潜在问题，建议人工复核。
    error：明确风险，不建议直接印刷。
    """

    PASS = "pass"
    WARNING = "warning"
    ERROR = "error"


class CheckItem(str, Enum):
    """检查项标识。"""

    FILE_FORMAT = "file_format"          # 文件格式
    DIMENSIONS = "dimensions"            # 图片尺寸
    DPI = "dpi"                          # DPI 分辨率
    COLOR_MODE = "color_mode"            # 颜色模式
    TRANSPARENCY = "transparency"        # 透明通道
    LOW_RESOLUTION = "low_resolution"    # 低清风险
    FILE_SIZE = "file_size"              # 文件大小


# ---- 印前检查推荐阈值 ----

# 印刷推荐最小尺寸（像素）
RECOMMENDED_MIN_WIDTH = 300
RECOMMENDED_MIN_HEIGHT = 300

# 印刷推荐 DPI
RECOMMENDED_DPI = 300
# 最低可接受 DPI（低于此值标记为 error）
MIN_ACCEPTABLE_DPI = 150

# 印刷推荐色彩模式
PRINT_PREFERRED_MODES = {"CMYK", "RGB", "L", "P", "RGBA"}

# 支持的文件格式（后缀列表）
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

# 文件大小下限警告阈值（字节），低于此值可能被过度压缩
MIN_FILE_SIZE_WARN_BYTES = 10 * 1024  # 10KB


@dataclass
class PreflightCheckResult:
    """单项检查结果。

    item：检查项标识。
    risk_level：风险等级（pass/warning/error）。
    message：中文描述信息。
    details：附加详情（如当前值、推荐值）。
    """

    item: CheckItem
    risk_level: RiskLevel
    message: str
    details: Dict = field(default_factory=dict)


@dataclass
class PreflightReport:
    """印前检查综合报告。

    包含所有检查项的结果汇总，以及整体风险评估。
    """

    file_path: str                     # 被检查的文件路径
    file_name: str                     # 文件名
    file_format: str                   # 文件扩展名
    file_size_bytes: int               # 文件大小（字节）

    # 图像属性
    width: Optional[int] = None        # 宽度（像素）
    height: Optional[int] = None       # 高度（像素）
    dpi: Optional[float] = None        # DPI（水平方向）
    dpi_h: Optional[float] = None      # DPI 水平
    dpi_v: Optional[float] = None      # DPI 垂直
    color_mode: Optional[str] = None   # 颜色模式（RGB/CMYK/L 等）
    has_transparency: bool = False     # 是否有透明通道

    # 检查结果列表
    checks: List[PreflightCheckResult] = field(default_factory=list)

    # 整体评估
    overall_risk: RiskLevel = RiskLevel.PASS
    has_errors: bool = False           # 是否有 error 级别风险
    has_warnings: bool = False         # 是否有 warning 级别风险
    overall_message: str = ""          # 综合建议

    def add_check(self, result: PreflightCheckResult) -> None:
        """添加一项检查结果，并更新综合评估。"""
        self.checks.append(result)
        # 更新整体风险等级（取最严重）
        if result.risk_level == RiskLevel.ERROR:
            self.has_errors = True
            self.overall_risk = RiskLevel.ERROR
        elif result.risk_level == RiskLevel.WARNING:
            self.has_warnings = True
            if self.overall_risk != RiskLevel.ERROR:
                self.overall_risk = RiskLevel.WARNING

    def errors(self) -> List[PreflightCheckResult]:
        """获取所有 error 级别的检查结果。"""
        return [c for c in self.checks if c.risk_level == RiskLevel.ERROR]

    def warnings(self) -> List[PreflightCheckResult]:
        """获取所有 warning 级别的检查结果。"""
        return [c for c in self.checks if c.risk_level == RiskLevel.WARNING]

    def passes(self) -> List[PreflightCheckResult]:
        """获取所有 pass 级别的检查结果。"""
        return [c for c in self.checks if c.risk_level == RiskLevel.PASS]

    def to_dict(self) -> Dict:
        """转为字典，便于序列化和跨进程传输。"""
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_format": self.file_format,
            "file_size_bytes": self.file_size_bytes,
            "width": self.width,
            "height": self.height,
            "dpi": self.dpi,
            "dpi_h": self.dpi_h,
            "dpi_v": self.dpi_v,
            "color_mode": self.color_mode,
            "has_transparency": self.has_transparency,
            "checks": [
                {
                    "item": c.item.value,
                    "risk_level": c.risk_level.value,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
            "overall_risk": self.overall_risk.value,
            "has_errors": self.has_errors,
            "has_warnings": self.has_warnings,
            "overall_message": self.overall_message,
        }
