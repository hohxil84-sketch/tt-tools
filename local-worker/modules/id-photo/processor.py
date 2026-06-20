"""
local-worker/modules/id-photo/processor — 证件照换底色核心处理器

实现：
  - 背景区域检测（基于边缘采样颜色分析）
  - 人物前景遮罩生成（颜色阈值 + GrabCut 混合策略）
  - 背景色替换
  - 证件照规格缩放裁剪

算法策略：
  1. 对输入图像自动检测背景色（采样四角和边缘像素）。
  2. 如果背景为接近纯色，使用颜色距离阈值生成遮罩。
  3. 如果背景复杂或不均匀，回退到 GrabCut 分割。
  4. 遮罩边缘使用高斯模糊羽化，避免生硬过渡。
  5. 替换为目标底色。
  6. 按目标规格等比缩放并居中裁剪。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import cv2  # type: ignore
import numpy as np

from specifications import (
    BackgroundColor,
    PhotoSpec,
    get_background_color,
    get_spec,
)

# 模块日志
logger = logging.getLogger(__name__)


# ---- 处理结果 ----

@dataclass
class IdPhotoResult:
    """证件照换底色处理结果。"""

    # 输出图像数据（BGR 格式 numpy 数组）
    image: np.ndarray

    # 输出图像像素尺寸
    width_px: int
    height_px: int

    # 使用的规格
    spec: PhotoSpec

    # 目标背景色
    background_color: BackgroundColor

    # 检测到的原始背景色（可能为 None）
    detected_background: Optional[BackgroundColor] = None

    # 处理元信息
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---- 背景检测 ----

# 背景采样区域比例（从图像边缘向内的比例）
_BACKGROUND_SAMPLE_MARGIN_RATIO = 0.05
# 采样带宽度（像素）
_MIN_SAMPLE_WIDTH = 5
# 纯色背景判定阈值（颜色标准差低于此值视为纯色）
_PURE_BACKGROUND_STD_THRESHOLD = 30.0
# 颜色距离阈值（用于前景/背景分类）
_COLOR_DISTANCE_THRESHOLD = 45.0


def _sample_edge_pixels(
    image: np.ndarray,
    margin_ratio: float = _BACKGROUND_SAMPLE_MARGIN_RATIO,
    min_width: int = _MIN_SAMPLE_WIDTH,
) -> np.ndarray:
    """从图像四边边缘采样像素，用于背景色检测。

    参数：
        image: BGR 图像 (H, W, 3)。
        margin_ratio: 边缘采样比例。
        min_width: 最小采样宽度（像素）。

    返回：
        采样像素数组 (N, 3)，BGR 格式。
    """
    h, w = image.shape[:2]
    margin = max(int(min(h, w) * margin_ratio), min_width)

    samples = []

    # 上边缘
    if margin <= h:
        samples.append(image[:margin, :, :].reshape(-1, 3))
    # 下边缘
    if margin <= h:
        samples.append(image[h - margin : h, :, :].reshape(-1, 3))
    # 左边缘
    if margin <= w:
        samples.append(image[:, :margin, :].reshape(-1, 3))
    # 右边缘
    if margin <= w:
        samples.append(image[:, w - margin : w, :].reshape(-1, 3))

    if not samples:
        # 图像太小，使用四个角
        corners = [
            image[0, 0, :],
            image[0, -1, :],
            image[-1, 0, :],
            image[-1, -1, :],
        ]
        return np.array(corners, dtype=np.float32)

    return np.vstack(samples).astype(np.float32)


def detect_background_color(
    image: np.ndarray,
    std_threshold: float = _PURE_BACKGROUND_STD_THRESHOLD,
) -> Tuple[Optional[BackgroundColor], bool]:
    """检测图像的背景色。

    通过采样图像四边边缘像素，分析其颜色均值和标准差，
    判断是否为接近纯色的背景。

    参数：
        image: BGR 图像。
        std_threshold: 颜色标准差阈值，低于此值判定为纯色背景。

    返回：
        (BackgroundColor, is_solid) 元组。
        - BackgroundColor: 检测到的背景色，可能为 None。
        - is_solid: 是否为纯色背景（True 表示可用颜色阈值做分割）。
    """
    samples = _sample_edge_pixels(image)
    if len(samples) == 0:
        return None, False

    mean_bgr = np.mean(samples, axis=0)
    std_bgr = np.std(samples, axis=0)
    avg_std = float(np.mean(std_bgr))

    # 是否纯色背景
    is_solid = avg_std < std_threshold

    # 转为整数 RGB
    b, g, r = int(round(mean_bgr[0])), int(round(mean_bgr[1])), int(round(mean_bgr[2]))
    # 限制在 0-255
    r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))

    bg_color = BackgroundColor(
        name="检测背景色",
        r=r,
        g=g,
        b=b,
    )

    return bg_color, is_solid


# ---- 前景遮罩生成 ----


def _create_color_mask(
    image: np.ndarray,
    background_bgr: Tuple[int, int, int],
    distance_threshold: float = _COLOR_DISTANCE_THRESHOLD,
) -> np.ndarray:
    """基于颜色距离阈值创建前景遮罩。

    计算每个像素与背景色的欧几里得距离，距离大于阈值的视为前景。

    参数：
        image: BGR 图像。
        background_bgr: 背景色 BGR 值。
        distance_threshold: 距离阈值。

    返回：
        二值遮罩 (H, W)，255=前景，0=背景。
    """
    # 将背景色转为与图像相同的 float 类型
    bg = np.array(background_bgr, dtype=np.float32).reshape(1, 1, 3)

    # 计算每个像素与背景色的欧几里得距离
    image_float = image.astype(np.float32)
    distance = np.sqrt(np.sum((image_float - bg) ** 2, axis=2))

    # 距离大于阈值的为前景（人物）
    raw_mask = (distance > distance_threshold).astype(np.uint8) * 255

    # 形态学后处理：闭合小孔洞、去除噪点
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    # 先闭运算：连接人物区域的断裂
    mask = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, kernel_small)
    # 再开运算：去除孤立噪点
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_medium)

    return mask


def _create_grabcut_mask(image: np.ndarray) -> np.ndarray:
    """使用 GrabCut 算法创建前景遮罩。

    适用于背景复杂的照片。自动以图像中心区域作为初始前景。

    参数：
        image: BGR 图像。

    返回：
        二值遮罩 (H, W)，255=前景，0=背景。
    """
    h, w = image.shape[:2]

    # 创建初始掩码
    mask = np.zeros((h, w), dtype=np.uint8)

    # 初始化背景/前景模型
    bgd_model = np.zeros((1, 65), dtype=np.float64)
    fgd_model = np.zeros((1, 65), dtype=np.float64)

    # 定义初始前景矩形：图像中心 60% 区域（假设人物在中间）
    margin_x = int(w * 0.15)
    margin_y = int(h * 0.05)
    rect = (
        margin_x,
        margin_y,
        w - 2 * margin_x,
        h - 2 * margin_y,
    )

    # 确保 rect 有效
    if rect[2] <= 0 or rect[3] <= 0:
        # 图像太小，使用整张图
        rect = (1, 1, w - 2, h - 2)

    try:
        # 执行 GrabCut（5 次迭代）
        cv2.grabCut(
            image,
            mask,
            rect,
            bgd_model,
            fgd_model,
            5,
            cv2.GC_INIT_WITH_RECT,
        )
    except cv2.error:
        # GrabCut 失败时回退到全图作为前景
        return np.full((h, w), 255, dtype=np.uint8)

    # 提取前景区域（GC_FGD=1, GC_PR_FGD=3）
    fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(
        np.uint8
    )

    # 形态学后处理
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

    return fg_mask


def create_foreground_mask(
    image: np.ndarray,
    background_bgr: Optional[Tuple[int, int, int]] = None,
    is_solid_background: bool = False,
) -> np.ndarray:
    """创建前景（人物）遮罩。

    策略：
      - 如果是纯色背景且提供了背景色，优先使用颜色距离法（更快更准）。
      - 否则使用 GrabCut 分割。

    参数：
        image: BGR 图像。
        background_bgr: 检测到的背景色 BGR 值。
        is_solid_background: 是否为纯色背景。

    返回：
        二值遮罩 (H, W)，255=前景（人物），0=背景。
    """
    h, w = image.shape[:2]

    if is_solid_background and background_bgr is not None:
        # 纯色背景：使用颜色距离法
        logger.info("使用颜色距离法生成遮罩（纯色背景检测）")
        mask = _create_color_mask(image, background_bgr)

        # 检查遮罩质量：如果前景占比过大（>90%）或过小（<1%），
        # 可能颜色检测不准，回退到 GrabCut
        fg_ratio = np.count_nonzero(mask) / (h * w)
        if fg_ratio > 0.90 or fg_ratio < 0.01:
            logger.info(
                "颜色遮罩质量不佳（前景占比=%.1f%%），回退到 GrabCut",
                fg_ratio * 100,
            )
            mask = _create_grabcut_mask(image)
    else:
        # 复杂背景：使用 GrabCut
        logger.info("使用 GrabCut 分割生成遮罩（非纯色背景）")
        mask = _create_grabcut_mask(image)

    return mask


def _refine_mask_edge(
    mask: np.ndarray,
    blur_kernel_size: int = 5,
) -> np.ndarray:
    """对遮罩边缘进行羽化处理。

    使用高斯模糊软化遮罩边缘，避免背景替换后出现生硬的锯齿过渡。

    参数：
        mask: 二值遮罩 (H, W)，值为 0 或 255。
        blur_kernel_size: 高斯核大小，必须为奇数。

    返回：
        羽化后的遮罩 (H, W)，值域 [0, 255]。
    """
    if blur_kernel_size % 2 == 0:
        blur_kernel_size += 1  # 确保为奇数

    # 高斯模糊
    blurred = cv2.GaussianBlur(mask.astype(np.float32), (blur_kernel_size, blur_kernel_size), 0)
    return blurred


# ---- 背景替换 ----

def replace_background(
    image: np.ndarray,
    foreground_mask: np.ndarray,
    new_background_bgr: Tuple[int, int, int],
    edge_feather: bool = True,
    feather_kernel_size: int = 5,
) -> np.ndarray:
    """将图像背景替换为新颜色。

    参数：
        image: 原始 BGR 图像。
        foreground_mask: 前景遮罩，值域 [0, 255]。
        new_background_bgr: 目标背景色 BGR 值。
        edge_feather: 是否进行边缘羽化。
        feather_kernel_size: 羽化核大小。

    返回：
        换底后的 BGR 图像。
    """
    h, w = image.shape[:2]

    # 创建新背景图
    new_bg = np.full((h, w, 3), new_background_bgr, dtype=np.uint8)

    if edge_feather:
        # 羽化遮罩并归一化到 [0, 1]
        alpha = _refine_mask_edge(foreground_mask, feather_kernel_size) / 255.0
    else:
        # 直接归一化
        alpha = foreground_mask.astype(np.float32) / 255.0

    # 扩展为 3 通道
    alpha_3ch = np.stack([alpha, alpha, alpha], axis=2)

    # Alpha 混合：result = foreground * alpha + background * (1 - alpha)
    image_float = image.astype(np.float32)
    new_bg_float = new_bg.astype(np.float32)

    result = image_float * alpha_3ch + new_bg_float * (1.0 - alpha_3ch)

    return np.clip(result, 0, 255).astype(np.uint8)


# ---- 规格缩放 ----

def resize_to_spec(
    image: np.ndarray,
    spec: PhotoSpec,
    maintain_aspect: bool = True,
) -> np.ndarray:
    """将图像缩放到目标证件照规格。

    保持宽高比缩放并居中裁剪。

    参数：
        image: 输入 BGR 图像。
        spec: 目标 PhotoSpec。
        maintain_aspect: 是否保持宽高比（默认 True）。

    返回：
        缩放裁剪后的图像。
    """
    target_w = spec.width_px
    target_h = spec.height_px
    h, w = image.shape[:2]

    if not maintain_aspect:
        # 直接拉伸
        return cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

    # 等比缩放并居中裁剪
    # 计算缩放比例
    scale_w = target_w / w
    scale_h = target_h / h

    if scale_w > scale_h:
        # 以宽度为基准缩放，高度裁剪
        new_w = target_w
        new_h = int(h * scale_w)
    else:
        # 以高度为基准缩放，宽度裁剪
        new_h = target_h
        new_w = int(w * scale_h)

    # 等比缩放
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    # 居中裁剪
    start_x = (new_w - target_w) // 2
    start_y = (new_h - target_h) // 2
    # 确保裁剪区域在图像内
    start_x = max(0, start_x)
    start_y = max(0, start_y)
    end_x = start_x + target_w
    end_y = start_y + target_h

    cropped = resized[start_y:end_y, start_x:end_x]

    # 如果裁剪后尺寸不够（极端情况），补边
    if cropped.shape[0] != target_h or cropped.shape[1] != target_w:
        result = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        ch = min(cropped.shape[0], target_h)
        cw = min(cropped.shape[1], target_w)
        dy = (target_h - ch) // 2
        dx = (target_w - cw) // 2
        result[dy : dy + ch, dx : dx + cw] = cropped[:ch, :cw]
        return result

    return cropped


# ---- 完整处理流程 ----

def process_id_photo(
    image: np.ndarray,
    background: str = "white",
    spec_name: str = "1寸",
    dpi: int = 300,
    auto_detect_background: bool = True,
    edge_feather: bool = True,
) -> IdPhotoResult:
    """证件照换底色完整流程。

    流程：
      1. 自动检测原图背景色（如果启用）。
      2. 生成前景（人物）遮罩。
      3. 替换为新底色。
      4. 缩放裁剪到目标规格。

    参数：
        image: 输入 BGR 图像（numpy 数组，shape=(H,W,3)）。
        background: 目标底色名称，如 "white"、"red"、"blue"。
        spec_name: 目标规格名称，如 "1寸"、"2寸"。
        dpi: 目标 DPI，默认 300。
        auto_detect_background: 是否自动检测原图背景色。
        edge_feather: 是否边缘羽化。

    返回：
        IdPhotoResult 对象，包含输出图像和元信息。

    异常：
        ValueError: 参数无效。
    """
    # 校验输入
    if image is None or len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError("输入图像必须为 3 通道 BGR 格式")

    # 获取目标规格
    spec = get_spec(spec_name, dpi=dpi)

    # 获取目标底色
    target_bg = get_background_color(background)

    metadata: Dict[str, Any] = {
        "spec_name": spec.name,
        "spec_size_mm": spec.size_mm,
        "spec_size_px": spec.size_px,
        "target_background": target_bg.name,
    }

    # ---- 第1步：检测原图背景色 ----
    detected_bg: Optional[BackgroundColor] = None
    is_solid = False
    if auto_detect_background:
        detected_bg, is_solid = detect_background_color(image)
        if detected_bg:
            metadata["detected_background_rgb"] = detected_bg.to_rgb()
            metadata["detected_background_hex"] = detected_bg.to_hex()
            metadata["is_solid_background"] = is_solid
            logger.info(
                "背景检测完成：RGB=%s, 纯色=%s",
                detected_bg.to_rgb(),
                is_solid,
            )

    # ---- 第2步：生成前景遮罩 ----
    bg_bgr = detected_bg.to_bgr() if detected_bg else None
    mask = create_foreground_mask(
        image,
        background_bgr=bg_bgr,
        is_solid_background=is_solid,
    )
    metadata["mask_method"] = "color_distance" if is_solid and bg_bgr else "grabcut"

    # ---- 第3步：替换背景 ----
    result_image = replace_background(
        image,
        mask,
        target_bg.to_bgr(),
        edge_feather=edge_feather,
    )

    # ---- 第4步：缩放裁剪 ----
    result_image = resize_to_spec(result_image, spec, maintain_aspect=True)
    metadata["output_size_px"] = (result_image.shape[1], result_image.shape[0])

    logger.info(
        "证件照处理完成：规格=%s, 底色=%s, 尺寸=%s",
        spec.name,
        target_bg.name,
        (result_image.shape[1], result_image.shape[0]),
    )

    return IdPhotoResult(
        image=result_image,
        width_px=result_image.shape[1],
        height_px=result_image.shape[0],
        spec=spec,
        background_color=target_bg,
        detected_background=detected_bg,
        metadata=metadata,
    )


def process_id_photo_from_path(
    input_path: str,
    output_path: str,
    background: str = "white",
    spec_name: str = "1寸",
    dpi: int = 300,
    auto_detect_background: bool = True,
    edge_feather: bool = True,
) -> IdPhotoResult:
    """从文件路径读取图像，处理后保存到输出路径。

    参数：
        input_path: 输入图像文件路径。
        output_path: 输出图像文件路径。
        background: 目标底色名称。
        spec_name: 目标规格名称。
        dpi: 目标 DPI。
        auto_detect_background: 是否自动检测原图背景色。
        edge_feather: 是否边缘羽化。

    返回：
        IdPhotoResult 对象。
    """
    # 读取图像（cv2.imread 返回 BGR 格式）
    image = cv2.imread(input_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"无法读取图像文件: {input_path}")

    result = process_id_photo(
        image=image,
        background=background,
        spec_name=spec_name,
        dpi=dpi,
        auto_detect_background=auto_detect_background,
        edge_feather=edge_feather,
    )

    # 保存结果
    success = cv2.imwrite(output_path, result.image)
    if not success:
        raise IOError(f"无法写入输出文件: {output_path}")

    logger.info("输出已保存到: %s", output_path)
    return result
