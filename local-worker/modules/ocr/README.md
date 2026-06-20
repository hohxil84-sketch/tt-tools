# local-worker-ocr

OCR 本地识别实现，基于 RapidOCR (ONNX Runtime) / PaddleOCR v4 模型。

- 所属端：local-worker
- 类型：免费功能
- 分支：`feature/local-ocr`
- 状态：`DEVELOPMENT_COMPLETE`
- 引擎：RapidOCR 1.4.4 (ONNX Runtime)
- 模型：ch_PP-OCRv4_det + ch_ppocr_mobile_v2.0_cls + ch_PP-OCRv4_rec
- 测试：29/29 通过

## 快速开始

```python
from modules.ocr import OCREngine, recognize_image

# 便捷函数
result = recognize_image("path/to/image.png")
print(result.total_text)

# 引擎实例（批量/自定义参数）
with OCREngine(text_score=0.6) as engine:
    result = engine.recognize("path/to/image.png")
    print(f"识别 {result.line_count} 行, 置信度 {result.avg_score:.3f}")
```
