"""
local-worker/modules/remove-bg — 智能抠图

本地免费功能（功能码: remove_bg_local）。

基于 rembg (MIT License) + ONNX Runtime 实现，无需 GPU 即可运行。

提供：
  - remove_background() — 去除图像背景（numpy 数组输入）
  - remove_background_from_path() — 去除图像背景（文件路径输入）
  - composite_on_color() — 抠图结果合成到纯色背景
  - list_supported_models() — 列出支持的模型
  - clear_model_cache() — 清除模型缓存释放内存

支持的模型：
  - u2net：默认模型，质量最佳，~168 MB
  - u2netp：轻量模型，速度快，~16 MB
  - u2net_human_seg：人像专用分割
  - isnet-general-use：ISNet 通用模型
  - silueta：极轻量模型

使用示例：
    from local_worker.modules.remove_bg import (
        remove_background,
        remove_background_from_path,
        list_supported_models,
    )

    # numpy 数组方式
    import cv2
    image = cv2.imread("input.jpg")
    result = remove_background(image, model_name="u2net")

    # 文件路径方式
    result = remove_background_from_path(
        "input.jpg",
        "output.png",
        model_name="u2netp",
        output_rgba=True,
    )

    # 合成到纯色背景
    from local_worker.modules.remove_bg import composite_on_color
    composited = composite_on_color(result, color=(255, 255, 255))
    cv2.imwrite("output_white_bg.jpg", composited)
"""

from processor import (
    RemoveBgResult,
    clear_model_cache,
    composite_on_color,
    is_model_available,
    list_supported_models,
    remove_background,
    remove_background_from_path,
)

__all__ = [
    # 主要 API
    "remove_background",
    "remove_background_from_path",
    # 结果类型
    "RemoveBgResult",
    # 辅助工具
    "composite_on_color",
    "list_supported_models",
    "is_model_available",
    "clear_model_cache",
]
