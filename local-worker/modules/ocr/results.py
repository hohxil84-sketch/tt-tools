"""
local-worker/modules/ocr/results — OCR 识别结果数据结构

定义 OCR 引擎返回的标准化结果格式，供调用方（desktop-ocr）使用。
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OCRBox:
    """单个文字区域的检测框和识别结果。

    对应 RapidOCR 返回的单条识别结果。
    """

    text: str  # 识别文本内容
    score: float  # 识别置信度 (0.0 ~ 1.0)
    box: List[List[float]]  # 四点坐标 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]，左上起顺时针

    def __repr__(self) -> str:
        return (
            f"OCRBox(text={self.text!r}, score={self.score:.3f}, "
            f"box={self.box!r})"
        )


@dataclass
class OCRResult:
    """单张图片的完整 OCR 识别结果。

    包含所有检测到的文字区域、耗时信息和引擎信息。
    """

    text_lines: List[OCRBox]  # 所有检测到的文字行
    total_text: str  # 所有文字拼接后的完整文本（按阅读顺序）
    formatted_text: str = ""  # 按原图坐标排版后的格式化文本（保留换行、缩进、空格）
    elapsed_total: float = 0.0  # 总耗时（秒）
    elapsed_det: float = 0.0  # 文字检测耗时（秒）
    elapsed_cls: Optional[float] = None  # 文字方向分类耗时（秒），未启用时为 None
    elapsed_rec: float = 0.0  # 文字识别耗时（秒）
    engine_name: str = "RapidOCR"  # OCR 引擎名称
    engine_version: str = ""  # OCR 引擎版本
    image_width: Optional[int] = None  # 原图宽度（像素）
    image_height: Optional[int] = None  # 原图高度（像素）

    @property
    def line_count(self) -> int:
        """检测到的文字行数。"""
        return len(self.text_lines)

    @property
    def avg_score(self) -> float:
        """平均置信度。"""
        if not self.text_lines:
            return 0.0
        return sum(line.score for line in self.text_lines) / len(self.text_lines)

    @property
    def high_confidence_lines(self) -> List["OCRBox"]:
        """返回置信度 >= 0.9 的高置信文字行。"""
        return [line for line in self.text_lines if line.score >= 0.9]

    @property
    def low_confidence_lines(self) -> List["OCRBox"]:
        """返回置信度 < 0.5 的低置信文字行。"""
        return [line for line in self.text_lines if line.score < 0.5]

    def to_dict(self) -> dict:
        """转为可序列化的字典。"""
        return {
            "line_count": self.line_count,
            "total_text": self.total_text,
            "formatted_text": self.formatted_text,
            "text_lines": [
                {
                    "text": line.text,
                    "score": round(line.score, 4),
                    "box": line.box,
                }
                for line in self.text_lines
            ],
            "elapsed": {
                "total": round(self.elapsed_total, 4),
                "det": round(self.elapsed_det, 4),
                "cls": round(self.elapsed_cls, 4) if self.elapsed_cls is not None else None,
                "rec": round(self.elapsed_rec, 4),
            },
            "engine": {
                "name": self.engine_name,
                "version": self.engine_version,
            },
            "image": {
                "width": self.image_width,
                "height": self.image_height,
            },
        }

    def __repr__(self) -> str:
        return (
            f"OCRResult(lines={self.line_count}, "
            f"total_text={self.total_text[:50]!r}..., "
            f"avg_score={self.avg_score:.3f})"
        )
