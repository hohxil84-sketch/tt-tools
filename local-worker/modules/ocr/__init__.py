"""
local-worker/modules/ocr — 本地 OCR 文字识别模块

基于 RapidOCR (ONNX Runtime) 提供离线、免费的文字识别能力。
支持中文和英文的印刷体文字检测与识别。

主要入口：
  - OCREngine: OCR 引擎类，适合批量或需自定义参数场景
  - recognize_image: 便捷函数，适合一次性识别

用法示例：
    from modules.ocr import OCREngine, recognize_image

    # 方式 1：OCREngine（批量/自定义参数）
    engine = OCREngine(text_score=0.6)
    result = engine.recognize("input.png")
    print(result.total_text)

    # 方式 2：便捷函数（一次性）
    result = recognize_image("input.png", text_score=0.5)

    # 方式 3：上下文管理器
    with OCREngine() as engine:
        result = engine.recognize("input.png")

输出结构：
    OCRResult
      ├── text_lines: List[OCRBox]  # 每行文字 + 坐标 + 置信度
      ├── total_text: str           # 拼接后完整文本
      ├── elapsed_*: float          # 各阶段耗时
      └── engine_name/version       # 引擎信息

模型：
  - ch_PP-OCRv4_det_infer.onnx (~4.5 MB)  — 文字检测
  - ch_ppocr_mobile_v2.0_cls_infer.onnx (~0.6 MB) — 文字方向分类
  - ch_PP-OCRv4_rec_infer.onnx (~10.4 MB) — 文字识别
  来源：RapidOCR / PaddleOCR v4，Apache 2.0 许可证
"""

from .engine import OCREngine, recognize_image, SUPPORTED_IMAGE_SUFFIXES
from .results import OCRBox, OCRResult

__all__ = [
    "OCREngine",
    "recognize_image",
    "OCRBox",
    "OCRResult",
    "SUPPORTED_IMAGE_SUFFIXES",
]
