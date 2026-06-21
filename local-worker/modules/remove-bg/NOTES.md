# NOTES.md - local-worker-remove-bg

## 设计备注

智能抠图本地实现，基于 rembg + ONNX Runtime。

## 选型记录

### 候选方案

| 方案 | 许可证 | 模型大小 | 依赖 | GPU 需求 | 优点 | 缺点 |
|------|--------|----------|------|----------|------|------|
| **rembg** | MIT | u2net: 168MB, u2netp: 4.4MB | ONNX Runtime | 否（CPU 支持） | 轻量、API 简洁、纯 ONNX 推理、不依赖 PyTorch | 模型固定，不可微调 |
| SAM (Segment Anything) | Apache 2.0 | ~2.4GB | PyTorch | 推荐 | 通用分割能力极强 | 体积大、需 PyTorch、太"重" |
| MODNet | Apache 2.0 | ~25MB | PyTorch / ONNX | 否 | 专为人像优化、边缘精细 | 非人像场景效果一般 |
| BackgroundRemover | MIT | ~168MB | PyTorch | 否 | 基于 U²-Net | 需 PyTorch |

### 最终选择：rembg

选择理由：
1. MIT 许可证，商用友好
2. 基于 ONNX Runtime，不依赖 PyTorch，部署轻量
3. 提供多模型选择（u2net/u2netp/u2net_human_seg/isnet/silueta）
4. API 简洁（`rembg.remove()`），上手快
5. CPU-only 运行完全可用
6. 社区活跃（16k+ GitHub stars）

### 模型说明

- **u2net**（默认，168MB）：U²-Net 显著性目标检测模型，通用性最佳，适合各类图片。
- **u2netp**（轻量，4.4MB）：u2net 的小型版，速度更快，适合简单场景。

### 参考链接

- rembg GitHub: https://github.com/danielgatis/rembg
- 模型下载: https://github.com/danielgatis/rembg/releases
