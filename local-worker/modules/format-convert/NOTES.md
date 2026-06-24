# NOTES.md - local-worker-format-convert

## 设计备注

格式转换、压缩、裁剪、旋转本地实现。基于 Pillow 提供纯本地、离线的图像处理能力。

## 选型记录

- **推荐方案**：Pillow (PIL) 12.2.0
- **许可证**：HPND（Historical Permission Notice and Disclaimer）
- **下载地址**：https://pypi.org/project/Pillow/
- **优点**：纯 Python 图像处理库，无需 GPU，无需 ML 模型，支持几乎所有图片格式的读写和基本操作
- **是否需要 GPU**：否
- **是否有 CPU fallback**：纯 CPU 运行

## 功能覆盖

### 格式转换
- 支持 7 种目标格式：PNG、JPEG、BMP、TIFF、WEBP、GIF、ICO
- 输入支持：PNG、JPEG、BMP、TIFF、WEBP、GIF、ICO
- 透明通道处理：RGBA 转 JPEG 时自动合成白色背景

### 压缩
- 有损压缩：JPEG/WEBP 通过 quality 控制
- 无损压缩：PNG 通过 compress_level 控制
- 迭代质量压缩：指定 max_size_bytes 时通过二分法逼近目标文件大小

### 裁剪
- 矩形区域裁剪：指定 left/top/width/height
- 锚点裁剪：CENTER / TOP_LEFT / TOP_RIGHT / BOTTOM_LEFT / BOTTOM_RIGHT
- 居中裁剪便捷方法

### 旋转
- 直角旋转：90°/180°/270°，使用 transpose 无损方法
- 任意角度：支持 0-360° 任意角度，BICUBIC 插值
- 画布扩展：expand=True 时画布变大以容纳完整图像
- 自定义填充色：fillcolor RGB 元组

## 不依赖

- 不依赖 GPU
- 不依赖 ML 模型
- 不调用云端 API
- 不涉及 AI
