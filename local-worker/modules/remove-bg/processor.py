"""
local-worker/modules/remove-bg/processor — 智能抠图核心处理器

实现：
  - 背景去除（使用 rembg / ONNX Runtime）
  - 多种模型支持（u2net、u2netp、isnet-general-use 等）
  - Alpha Matting 后处理优化
  - 前景/背景分离
  - 纯色背景合成

技术选型：rembg (MIT License)
  - 基于 ONNX Runtime 推理，无需 PyTorch
  - 支持 CPU-only 运行，无需 GPU
  - 内置 u2net / u2netp / isnet-general-use 等多种模型
  - ONNX 模型自动下载到用户缓存目录，首次使用联网

算法流程：
  1. 加载 rembg 模型（ONNX Runtime 推理）
  2. 输入图像预处理（resize 到模型输入尺寸）
  3. 推理生成 Alpha 遮罩
  4. （可选）Alpha Matting 精细化边缘
  5. 合成 RGBA 输出（原图前景 + Alpha 通道）
  6. （可选）合成纯色背景
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# 模块日志
logger = logging.getLogger(__name__)

# 支持的模型名称列表
SUPPORTED_MODELS = [
    "u2net",            # 默认模型，质量最佳，~168 MB
    "u2netp",           # 轻量模型，速度快，~16 MB
    "u2net_human_seg",  # 人像专用分割模型
    "isnet-general-use",# ISNet 通用模型，较新架构
    "silueta",          # 轻量级模型，适合简单场景
]

# 默认模型
DEFAULT_MODEL = "u2net"


# ---- 处理结果 ----

@dataclass
class RemoveBgResult:
    """智能抠图处理结果。"""

    # 输出图像数据（RGBA 格式，shape=(H,W,4)，dtype=uint8）
    # Alpha 通道中 255=前景（保留），0=背景（移除）
    image: np.ndarray

    # 原始图像尺寸（像素）
    input_width: int
    input_height: int

    # 输出图像尺寸（像素）
    output_width: int
    output_height: int

    # 使用的模型名称
    model: str

    # 只含 Alpha 遮罩（H,W），值域 [0, 255]
    alpha_mask: Optional[np.ndarray] = None

    # 处理元信息
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---- 模型管理 ----

# 全局模型缓存：避免每次调用重新加载模型
_model_cache: Dict[str, Any] = {}
# 全局 Session 缓存：rembg 的 Session 对象


def _get_session(model_name: str = DEFAULT_MODEL) -> Any:
    """获取或创建 rembg Session。

    Session 会被缓存到模块级字典中，避免重复加载模型（模型加载耗时较长）。

    参数：
        model_name: 模型名称。

    返回：
        rembg.Session 实例。

    异常：
        ImportError: rembg 未安装。
        ValueError: 模型名称无效。
    """
    if model_name not in SUPPORTED_MODELS:
        raise ValueError(
            f"不支持的模型名称: {model_name}，支持: {SUPPORTED_MODELS}"
        )

    if model_name not in _model_cache:
        # 延迟导入：只在第一次使用时加载 rembg
        try:
            from rembg import new_session  # type: ignore
        except ImportError:
            raise ImportError(
                "rembg 未安装。请运行: pip install rembg"
            )
        logger.info("正在加载抠图模型: %s ...", model_name)
        _model_cache[model_name] = new_session(model_name)
        logger.info("抠图模型加载完成: %s", model_name)

    return _model_cache[model_name]


def clear_model_cache(model_name: Optional[str] = None) -> None:
    """清除模型缓存，释放内存。

    参数：
        model_name: 指定清除的模型名称，None 表示清除全部。
    """
    global _model_cache
    if model_name:
        _model_cache.pop(model_name, None)
        logger.info("已清除模型缓存: %s", model_name)
    else:
        _model_cache.clear()
        logger.info("已清除全部模型缓存")


# ---- 抠图核心 ----

def remove_background(
    image: np.ndarray,
    model_name: str = DEFAULT_MODEL,
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
    only_mask: bool = False,
) -> RemoveBgResult:
    """去除图像背景，返回带透明通道的结果。

    这是抠图的主要入口函数。

    参数：
        image: 输入图像（BGR 格式，shape=(H,W,3) 或 RGBA shape=(H,W,4)）。
        model_name: 模型名称，默认 "u2net"。
        alpha_matting: 是否启用 Alpha Matting 精细化边缘（耗时更多但质量更好）。
        alpha_matting_foreground_threshold: Alpha Matting 前景阈值。
        alpha_matting_background_threshold: Alpha Matting 背景阈值。
        alpha_matting_erode_size: Alpha Matting 腐蚀核大小。
        only_mask: 是否只返回 Alpha 遮罩（不从原图提取前景）。

    返回：
        RemoveBgResult 对象，包含 RGBA 图像和元信息。

    异常：
        ValueError: 输入无效或模型名称无效。
        ImportError: rembg 未安装。
    """
    # 校验输入
    if image is None or len(image.shape) not in (2, 3):
        raise ValueError(
            f"输入图像格式无效，需要 2D（灰度）或 3D（BGR/RGBA）数组，"
            f"实际 shape={getattr(image, 'shape', None)}"
        )

    # 仅支持 3 通道或 4 通道图像
    if len(image.shape) == 3 and image.shape[2] not in (1, 3, 4):
        raise ValueError(
            f"输入图像通道数无效: {image.shape[2]}，支持 1（灰度）、3（BGR）或 4（RGBA）"
        )

    input_h, input_w = image.shape[:2]

    # 获取模型 session
    session = _get_session(model_name)

    # 准备输入数据（rembg 接受 PIL Image 或 numpy array）
    # rembg 内部使用 PIL 读取，可直接传 numpy array

    metadata: Dict[str, Any] = {
        "model": model_name,
        "input_size": (input_w, input_h),
        "alpha_matting": alpha_matting,
    }

    # 调用 rembg 推理
    from rembg import remove as rembg_remove  # type: ignore

    # 将 numpy array 转为 rembg 可处理的格式
    # rembg.remove 接受 numpy array, bytes, PIL Image 或文件路径
    logger.info(
        "开始抠图推理: 尺寸=%dx%d, 模型=%s, alpha_matting=%s",
        input_w, input_h, model_name, alpha_matting,
    )

    try:
        # rembg.remove 返回 PIL Image (RGBA)
        from PIL import Image  # type: ignore

        # 如果图像是 BGR，转为 RGB（PIL 期望 RGB）
        if len(image.shape) == 3 and image.shape[2] == 3:
            # BGR -> RGB
            # 注意：如果是 OpenCV 读取的 BGR，需要转换
            rgb_image = image[:, :, ::-1]  # BGR to RGB
        else:
            rgb_image = image

        # 转为 PIL Image 传入 rembg
        pil_input = Image.fromarray(rgb_image)

        pil_output = rembg_remove(
            pil_input,
            session=session,
            alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=alpha_matting_background_threshold,
            alpha_matting_erode_size=alpha_matting_erode_size,
            only_mask=only_mask,
        )

        # pil_output 是 RGBA PIL Image 或灰度遮罩（only_mask=True）
        output_array = np.array(pil_output)

    except Exception as e:
        logger.error("抠图推理失败: %s", e)
        raise RuntimeError(f"抠图推理失败: {e}") from e

    output_h, output_w = output_array.shape[:2]

    # 提取 Alpha 遮罩
    if only_mask:
        # 输出已经是灰度遮罩
        alpha_mask = output_array
        # 创建 RGBA 前景图（原图 + 遮罩）
        if len(image.shape) == 3 and image.shape[2] == 3:
            rgba = np.dstack([image[:, :, ::-1], alpha_mask])
        else:
            # 灰度或 RGBA 原图
            if len(image.shape) == 2:
                rgba = np.dstack([np.stack([image]*3, axis=2), alpha_mask])
            else:
                rgba = np.dstack([image[:, :, :3], alpha_mask])
    else:
        # 输出是 RGBA
        if output_array.shape[2] == 4:
            alpha_mask = output_array[:, :, 3]
            rgba = output_array
        else:
            # 意外格式，尝试处理
            alpha_mask = np.full((output_h, output_w), 255, dtype=np.uint8)
            rgba = np.dstack([output_array[:, :, :3], alpha_mask])

    logger.info(
        "抠图完成: 输入=%dx%d, 输出=%dx%d, 前景占比=%.1f%%",
        input_w, input_h, output_w, output_h,
        np.count_nonzero(alpha_mask > 128) / (output_w * output_h) * 100,
    )

    return RemoveBgResult(
        image=rgba,
        input_width=input_w,
        input_height=input_h,
        output_width=output_w,
        output_height=output_h,
        model=model_name,
        alpha_mask=alpha_mask,
        metadata=metadata,
    )


# ---- 纯色背景合成 ----

def composite_on_color(
    result: RemoveBgResult,
    color: Tuple[int, int, int] = (255, 255, 255),
) -> np.ndarray:
    """将抠图结果合成到纯色背景上。

    参数：
        result: remove_background 返回的 RemoveBgResult。
        color: 背景色 RGB 元组，默认白色 (255, 255, 255)。

    返回：
        BGR 格式 numpy 数组（3 通道），可直接用 cv2.imwrite 保存。
    """
    h, w = result.image.shape[:2]
    rgba = result.image.astype(np.float32)

    # 归一化 Alpha 通道到 [0, 1]
    if rgba.shape[2] == 4:
        alpha = rgba[:, :, 3:4] / 255.0
    else:
        alpha = np.ones((h, w, 1), dtype=np.float32)

    rgb = rgba[:, :, :3]

    # 创建背景
    bg = np.full((h, w, 3), color, dtype=np.float32)

    # Alpha 混合：result = foreground * alpha + background * (1 - alpha)
    composited = rgb * alpha + bg * (1.0 - alpha)

    # 输出 BGR 格式
    bgr = composited[:, :, ::-1]  # RGB -> BGR

    return np.clip(bgr, 0, 255).astype(np.uint8)


# ---- 文件路径 API ----

def remove_background_from_path(
    input_path: str,
    output_path: str,
    model_name: str = DEFAULT_MODEL,
    alpha_matting: bool = False,
    output_rgba: bool = True,
    composite_color: Optional[Tuple[int, int, int]] = None,
) -> RemoveBgResult:
    """从文件读取图像，去除背景后保存。

    支持透明 PNG（RGBA）或合并到纯色背景后保存。

    参数：
        input_path: 输入图像文件路径（支持 PNG/JPG/BMP/WEBP 等）。
        output_path: 输出图像文件路径。
        model_name: 模型名称。
        alpha_matting: 是否启用 Alpha Matting 精细化边缘。
        output_rgba: 是否输出带透明通道的 PNG。如果为 False 且未指定 composite_color，
                     默认使用白色背景合成。
        composite_color: 合成背景色 RGB 元组。如果指定，输出会合成为不透明图像。

    返回：
        RemoveBgResult 对象。
    """
    import cv2  # type: ignore

    # 读取图像（cv2.imread 返回 BGR 格式）
    image = cv2.imread(input_path, cv2.IMREAD_COLOR)
    if image is None:
        # 尝试用 PIL 读取（支持更多格式）
        from PIL import Image
        pil_img = Image.open(input_path)
        if pil_img.mode == "RGBA":
            image = np.array(pil_img.convert("RGBA"))
        else:
            image = np.array(pil_img.convert("RGB"))
            # PIL RGB -> OpenCV BGR
            image = image[:, :, ::-1]

    if image is None or image.size == 0:
        raise ValueError(f"无法读取图像文件: {input_path}")

    result = remove_background(
        image=image,
        model_name=model_name,
        alpha_matting=alpha_matting,
    )

    # 决定输出格式
    if composite_color is not None:
        # 合成到纯色背景
        output_image = composite_on_color(result, composite_color)
        # 用 OpenCV 保存（BGR）
        cv2.imwrite(output_path, output_image)
    elif output_rgba:
        # 保存 RGBA PNG
        # PIL 保存 RGBA
        from PIL import Image
        rgba = result.image
        pil_out = Image.fromarray(rgba, mode="RGBA")
        pil_out.save(output_path, format="PNG")
    else:
        # 默认白色背景合成
        bgr_output = composite_on_color(result, (255, 255, 255))
        cv2.imwrite(output_path, bgr_output)

    logger.info("抠图结果已保存: %s", output_path)
    return result


# ---- 工具函数 ----

def list_supported_models() -> List[str]:
    """列出所有支持的模型名称。"""
    return list(SUPPORTED_MODELS)


def is_model_available(model_name: str) -> bool:
    """检查指定模型名称是否支持。"""
    return model_name in SUPPORTED_MODELS
