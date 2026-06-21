# NOTES.md - local-worker-resize-image

## 设计备注

图片改尺寸本地实现，支持常见尺寸、比例、导出策略。

## 选型记录

### 候选方案

1. **Pillow (PIL)** — Python 图像处理标准库
   - 许可证：HPND（历史许可，非常宽松）
   - 优点：纯 Python（C 扩展），无需 GPU，支持所有常见格式，API 简单清晰，项目其他模块已广泛使用
   - 缺点：不支持高级图像处理（如内容感知缩放）
   - 推荐：✅ 推荐

2. **OpenCV (cv2)** — 计算机视觉库
   - 许可证：Apache 2.0
   - 优点：功能强大，支持 GPU 加速
   - 缺点：体积大（~40MB），对简单 resize 过于重量级
   - 推荐：❌ 不推荐（过度设计）

3. **ImageMagick (Wand/PythonMagick)** — 外部命令行工具
   - 许可证：Apache 2.0
   - 优点：功能丰富，支持数百种格式
   - 缺点：需要额外安装 ImageMagick 系统软件，增加部署复杂度
   - 推荐：❌ 不推荐（增加外部依赖）

### 最终选择

**Pillow** — 轻量、纯 Python、功能完全满足需求，与项目其他模块一致。

### 不依赖

- 不依赖 GPU
- 不依赖 ML 模型
- 不依赖云端 API
- 纯本地图像处理，CPU-only

## 架构设计

- `specifications.py`：纯数据层，定义枚举、常量、数据类、预设尺寸
- `processor.py`：核心业务层，ImageResizer 类实现所有缩放和导出逻辑
- `__init__.py`：公共接口层，对外暴露稳定 API
