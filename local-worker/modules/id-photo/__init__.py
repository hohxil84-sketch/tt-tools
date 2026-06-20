"""
local-worker/modules/id-photo — 证件照换底色

本地免费功能（功能码: id_photo_local）。

提供：
  - 自动背景色检测（边缘采样分析）
  - 人物前景遮罩生成（颜色阈值法 + GrabCut 混合策略）
  - 背景色替换（支持边缘羽化）
  - 证件照规格缩放裁剪（1寸、2寸、小1寸、小2寸等）

使用示例：
    from local_worker.modules.id_photo import (
        process_id_photo,
        process_id_photo_from_path,
        list_specs,
        list_background_colors,
    )

    # 完整处理
    result = process_id_photo(
        image,
        background="red",
        spec_name="1寸",
    )

    # 从文件处理
    result = process_id_photo_from_path(
        "input.jpg",
        "output.jpg",
        background="blue",
        spec_name="2寸",
    )
"""

from processor import (
    IdPhotoResult,
    create_foreground_mask,
    detect_background_color,
    process_id_photo,
    process_id_photo_from_path,
    replace_background,
    resize_to_spec,
)
from specifications import (
    BackgroundColor,
    PhotoSpec,
    get_background_color,
    get_spec,
    list_background_colors,
    list_specs,
)

__all__ = [
    # 完整流程
    "process_id_photo",
    "process_id_photo_from_path",
    # 结果类型
    "IdPhotoResult",
    # 规格
    "PhotoSpec",
    "get_spec",
    "list_specs",
    # 底色
    "BackgroundColor",
    "get_background_color",
    "list_background_colors",
    # 底层 API（用于自定义流程）
    "detect_background_color",
    "create_foreground_mask",
    "replace_background",
    "resize_to_spec",
]
