"""
desktop/modules/format-convert/format_convert_router.py — 格式转换/压缩/裁剪/旋转操作路由脚本

通过 stdin/stdout JSON 协议与桌面端 LocalRuntimeClient 通信。
接收图片处理请求，调用 local-worker format-convert 引擎，返回结构化结果。

协议格式：
  请求（stdin，每行一个 JSON）：{"action": "...", "data": {...}, "request_id": "..."}
  响应（stdout，每行一个 JSON）：{"success": true, "data": {...}, "error": null, "request_id": "..."}

支持的动作：
  - ping:               健康检查，返回引擎信息和支持的格式
  - convert_format:     格式转换（PNG/JPEG/BMP/TIFF/WEBP/GIF/ICO 互转）
  - compress:           图片压缩（有损/无损）
  - crop:               矩形区域裁剪 / 锚点裁剪
  - rotate:             直角旋转 / 任意角度旋转
  - supported_formats:  列出支持的输入输出格式
  - get_image_info:     获取图片文件基本信息
  - shutdown:           关闭进程

用法：由 LocalRuntimeClient 自动调用，不直接运行。
"""

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---- 关键：在导入任何 worker 模块之前，将 stdout 重定向到 stderr ----
# local-worker/shared/logging 在初始化时会向 stdout 写入一行日志，
# 这会破坏 stdin/stdout JSON 通信协议。重定向后所有非 JSON 输出走 stderr，
# 只有 send_response() 的 JSON 响应走 stdout（协议要求的通道）。
_real_stdout = sys.stdout  # 保留真实 stdout 引用，用于 send_response
sys.stdout = sys.stderr    # 将所有 print/logging 输出重定向到 stderr

# 将 local-worker 根目录添加到 Python 路径，确保可以导入核心模块
# format_convert_router.py → DesktopFormatConvert → format-convert → modules → desktop → TT Tools
_LOCAL_WORKER_ROOT = Path(r"D:\TT Tools\local-worker")

# format-convert 目录包含连字符，不能直接通过 "import modules.format-convert" 导入
# 将其父目录加入路径后，可直接导入模块内的文件
_FORMAT_CONVERT_DIR = _LOCAL_WORKER_ROOT / "modules" / "format-convert"
if str(_FORMAT_CONVERT_DIR) not in sys.path:
    sys.path.insert(0, str(_FORMAT_CONVERT_DIR))

# 将 local-worker/ 目录加入路径，确保 shared.* 导入可用
if str(_LOCAL_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(_LOCAL_WORKER_ROOT))

from processor import FormatConverter
from specifications import (
    ConvertFormat,
    CropAnchor,
    FormatConvertParams,
    CompressParams,
    CropParams,
    RotateParams,
    OperationResult,
    FORMAT_SUFFIX_MAP,
    SUPPORTED_INPUT_SUFFIXES,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_PNG_COMPRESS_LEVEL,
    DEFAULT_WEBP_QUALITY,
    MAX_OUTPUT_DIMENSION,
)


# ---- 全局处理器实例（进程级单例） ----
_converter = FormatConverter()

# ---- 格式名到枚举的映射 ----
_FORMAT_NAME_MAP: Dict[str, ConvertFormat] = {
    f.value: f for f in ConvertFormat
}


def send_response(
    success: bool,
    data: Any = None,
    error: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """将响应以单行 JSON 写入真实 stdout 并立即刷新。

    桌面端通过 stdout 读取响应，必须每行一个完整 JSON。
    """
    response = {
        "success": success,
        "data": data,
        "error": error,
        "request_id": request_id,
    }
    _real_stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    _real_stdout.flush()


def _parse_output_path(data: Dict[str, Any]) -> Optional[str]:
    """解析并校验 output_path 参数。

    C4: 校验外部传入路径——扩展名必须属于支持格式，父目录必须已存在。
    返回校验通过的 output_path，或 None。
    """
    output_path = data.get("output_path")
    if output_path:
        output_path = str(output_path)
        out_suffix = Path(output_path).suffix.lower()
        valid_suffixes = [v for v in FORMAT_SUFFIX_MAP.values()]
        if out_suffix and out_suffix not in valid_suffixes:
            send_response(
                success=False,
                error=f"不支持的输出文件扩展名: {out_suffix}，支持: {valid_suffixes}",
            )
            return None
        out_parent = Path(output_path).parent
        if not out_parent.is_dir():
            send_response(
                success=False,
                error=f"输出目录不存在: {out_parent}",
            )
            return None
    return output_path


def _result_to_response(result: OperationResult, output_path: Optional[str]) -> Dict[str, Any]:
    """将 OperationResult 转为 JSON 可序列化的响应字典。

    不包含二进制 output_data——图片已通过文件保存，C# 侧读取文件路径即可。
    """
    return {
        "output_path": str(output_path) if output_path else None,
        "source_path": result.source_path,
        "source_width": result.source_width,
        "source_height": result.source_height,
        "output_width": result.output_width,
        "output_height": result.output_height,
        "output_format": result.output_format,
        "output_size": result.output_size,
        "compression_ratio": round(result.compression_ratio, 4),
        "warnings": result.warnings,
        "elapsed_ms": round(result.elapsed_ms, 2),
    }


def handle_ping(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """健康检查：返回引擎信息和支持的格式列表。"""
    formats = FormatConverter.supported_formats()
    send_response(
        success=True,
        data={
            "engine": "Pillow (纯本地图像处理)",
            "status": "available",
            "supported_input": formats.get("input", []),
            "supported_output": formats.get("output", []),
            "max_output_dimension": MAX_OUTPUT_DIMENSION,
        },
        request_id=request_id,
    )


def handle_supported_formats(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """列出所有支持的输入输出格式及后缀映射。"""
    formats = FormatConverter.supported_formats()
    send_response(
        success=True,
        data=formats,
        request_id=request_id,
    )


def handle_get_image_info(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """获取图片文件的基本信息（不执行转换）。"""
    input_path = data.get("input_path")
    if not input_path:
        send_response(success=False, error="缺少必填参数 input_path", request_id=request_id)
        return

    input_path = str(input_path)
    if not Path(input_path).is_file():
        send_response(
            success=False,
            error=f"图片文件不存在: {input_path}",
            request_id=request_id,
        )
        return

    try:
        info = FormatConverter.get_image_info(input_path)
        send_response(
            success=True,
            data=info,
            request_id=request_id,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"获取图片信息失败: {str(e)}",
            request_id=request_id,
        )


def handle_convert_format(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理格式转换请求。

    期望 data 包含：
        - input_path: str (必填) 输入图像文件路径
        - target_format: str (可选) 目标格式，默认 "original" (保持原格式)
        - quality: int (可选) JPEG/WEBP 质量 (1-100)，默认 85
        - png_compress: int (可选) PNG 压缩级别 (0-9)，默认 6
        - webp_quality: int (可选) WEBP 质量 (1-100)，默认 85
        - preserve_alpha: bool (可选) 是否保留透明通道，默认 True
        - output_path: str (可选) 输出文件路径
    """
    input_path = data.get("input_path")
    if not input_path:
        send_response(success=False, error="缺少必填参数 input_path", request_id=request_id)
        return

    input_path = str(input_path)
    if not Path(input_path).is_file():
        send_response(
            success=False,
            error=f"图片文件不存在: {input_path}",
            request_id=request_id,
        )
        return

    # 解析 output_path
    output_path = _parse_output_path(data)
    if output_path is None and "output_path" in data:
        return  # 解析出错时已发送错误响应

    # 自动生成输出路径
    if not output_path:
        input_file = Path(input_path)
        target_format_str = str(data.get("target_format", "original")).lower()
        if target_format_str != "original" and target_format_str in FORMAT_SUFFIX_MAP:
            # 换个格式：用 FORMAT_SUFFIX_MAP 获取后缀
            out_format = _FORMAT_NAME_MAP.get(target_format_str)
            out_suffix = FORMAT_SUFFIX_MAP.get(out_format, input_file.suffix)
        else:
            out_suffix = input_file.suffix
        output_path = str(
            input_file.parent / f"{input_file.stem}_converted{out_suffix}"
        )

    # 解析目标格式
    target_format_str = str(data.get("target_format", "original")).lower()
    try:
        target_format = ConvertFormat(target_format_str)
    except ValueError:
        send_response(
            success=False,
            error=f"不支持的目标格式: {target_format_str}，支持: {[f.value for f in ConvertFormat]}",
            request_id=request_id,
        )
        return

    try:
        result = _converter.convert_format(
            image=input_path,
            target_format=target_format,
            quality=int(data.get("quality", DEFAULT_JPEG_QUALITY)),
            png_compress=int(data.get("png_compress", DEFAULT_PNG_COMPRESS_LEVEL)),
            webp_quality=int(data.get("webp_quality", DEFAULT_WEBP_QUALITY)),
            preserve_alpha=bool(data.get("preserve_alpha", True)),
            output_path=str(output_path),
        )

        if not result.success:
            send_response(
                success=False,
                error=result.error_message or "格式转换失败",
                request_id=request_id,
            )
            return

        response_data = _result_to_response(result, output_path)
        send_response(success=True, data=response_data, request_id=request_id)

    except Exception as e:
        send_response(
            success=False,
            error=f"格式转换失败: {str(e)}",
            request_id=request_id,
        )


def handle_compress(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理图片压缩请求。

    期望 data 包含：
        - input_path: str (必填) 输入图像文件路径
        - quality: int (可选) 有损格式质量 (1-100)，默认 75
        - target_format: str (可选) 目标格式，默认 "original"
        - png_compress: int (可选) PNG 压缩级别 (0-9)，默认 9
        - max_size_bytes: int (可选) 目标最大文件大小
        - output_path: str (可选) 输出文件路径
    """
    input_path = data.get("input_path")
    if not input_path:
        send_response(success=False, error="缺少必填参数 input_path", request_id=request_id)
        return

    input_path = str(input_path)
    if not Path(input_path).is_file():
        send_response(
            success=False,
            error=f"图片文件不存在: {input_path}",
            request_id=request_id,
        )
        return

    # 解析 output_path
    output_path = _parse_output_path(data)
    if output_path is None and "output_path" in data:
        return

    if not output_path:
        input_file = Path(input_path)
        output_path = str(
            input_file.parent / f"{input_file.stem}_compressed{input_file.suffix}"
        )

    # 解析目标格式
    target_format_str = str(data.get("target_format", "original")).lower()
    try:
        target_format = ConvertFormat(target_format_str)
    except ValueError:
        send_response(
            success=False,
            error=f"不支持的目标格式: {target_format_str}",
            request_id=request_id,
        )
        return

    # 解析 max_size_bytes
    max_size_bytes = data.get("max_size_bytes")
    if max_size_bytes is not None:
        max_size_bytes = int(max_size_bytes)

    try:
        result = _converter.compress(
            image=input_path,
            quality=int(data.get("quality", 75)),
            target_format=target_format,
            png_compress=int(data.get("png_compress", 9)),
            max_size_bytes=max_size_bytes,
            output_path=str(output_path),
        )

        if not result.success:
            send_response(
                success=False,
                error=result.error_message or "压缩失败",
                request_id=request_id,
            )
            return

        response_data = _result_to_response(result, output_path)
        send_response(success=True, data=response_data, request_id=request_id)

    except Exception as e:
        send_response(
            success=False,
            error=f"压缩失败: {str(e)}",
            request_id=request_id,
        )


def handle_crop(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理图片裁剪请求。

    支持两种模式：
    1. 坐标裁剪：指定 left/top/width/height
    2. 锚点裁剪：指定 width/height + anchor

    期望 data 包含：
        - input_path: str (必填) 输入图像文件路径
        - left: int (可选，坐标模式) 裁剪左边界，默认 0
        - top: int (可选，坐标模式) 裁剪上边界，默认 0
        - width: int (必填) 裁剪宽度
        - height: int (必填) 裁剪高度
        - anchor: str (可选，锚点模式) 对齐方式: center/top_left/top_right/bottom_left/bottom_right
        - output_path: str (可选) 输出文件路径
    """
    input_path = data.get("input_path")
    if not input_path:
        send_response(success=False, error="缺少必填参数 input_path", request_id=request_id)
        return

    input_path = str(input_path)
    if not Path(input_path).is_file():
        send_response(
            success=False,
            error=f"图片文件不存在: {input_path}",
            request_id=request_id,
        )
        return

    # 校验 width 和 height
    width = data.get("width")
    height = data.get("height")
    if not width or not height:
        send_response(
            success=False,
            error="缺少必填参数 width 和 height",
            request_id=request_id,
        )
        return

    width = int(width)
    height = int(height)

    # 解析 output_path
    output_path = _parse_output_path(data)
    if output_path is None and "output_path" in data:
        return

    if not output_path:
        input_file = Path(input_path)
        output_path = str(
            input_file.parent / f"{input_file.stem}_cropped{input_file.suffix}"
        )

    # 判断使用哪种裁剪模式
    anchor_str = data.get("anchor")
    anchor = None
    if anchor_str:
        try:
            anchor = CropAnchor(str(anchor_str).lower())
        except ValueError:
            send_response(
                success=False,
                error=f"不支持的锚点: {anchor_str}，支持: {[a.value for a in CropAnchor]}",
                request_id=request_id,
            )
            return

    try:
        if anchor:
            # 锚点模式：使用 crop_by_anchor
            result = _converter.crop_by_anchor(
                image=input_path,
                width=width,
                height=height,
                anchor=anchor,
                output_path=str(output_path),
            )
        else:
            # 坐标模式：使用 crop
            left = int(data.get("left", 0))
            top_val = int(data.get("top", 0))
            result = _converter.crop(
                image=input_path,
                left=left,
                top=top_val,
                width=width,
                height=height,
                output_path=str(output_path),
            )

        if not result.success:
            send_response(
                success=False,
                error=result.error_message or "裁剪失败",
                request_id=request_id,
            )
            return

        response_data = _result_to_response(result, output_path)
        send_response(success=True, data=response_data, request_id=request_id)

    except Exception as e:
        send_response(
            success=False,
            error=f"裁剪失败: {str(e)}",
            request_id=request_id,
        )


def handle_rotate(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理图片旋转请求。

    期望 data 包含：
        - input_path: str (必填) 输入图像文件路径
        - angle: float (必填) 旋转角度（正数为顺时针）
        - expand: bool (可选) 是否扩展画布，默认 True
        - fillcolor_r: int (可选) 填充颜色 R 分量，默认 255
        - fillcolor_g: int (可选) 填充颜色 G 分量，默认 255
        - fillcolor_b: int (可选) 填充颜色 B 分量，默认 255
        - output_path: str (可选) 输出文件路径
    """
    input_path = data.get("input_path")
    if not input_path:
        send_response(success=False, error="缺少必填参数 input_path", request_id=request_id)
        return

    input_path = str(input_path)
    if not Path(input_path).is_file():
        send_response(
            success=False,
            error=f"图片文件不存在: {input_path}",
            request_id=request_id,
        )
        return

    angle = data.get("angle")
    if angle is None:
        send_response(
            success=False,
            error="缺少必填参数 angle",
            request_id=request_id,
        )
        return

    # 解析 output_path
    output_path = _parse_output_path(data)
    if output_path is None and "output_path" in data:
        return

    if not output_path:
        input_file = Path(input_path)
        output_path = str(
            input_file.parent / f"{input_file.stem}_rotated{input_file.suffix}"
        )

    # 解析填充颜色
    fillcolor = (
        int(data.get("fillcolor_r", 255)),
        int(data.get("fillcolor_g", 255)),
        int(data.get("fillcolor_b", 255)),
    )

    try:
        result = _converter.rotate(
            image=input_path,
            angle=float(angle),
            expand=bool(data.get("expand", True)),
            fillcolor=fillcolor,
            output_path=str(output_path),
        )

        if not result.success:
            send_response(
                success=False,
                error=result.error_message or "旋转失败",
                request_id=request_id,
            )
            return

        response_data = _result_to_response(result, output_path)
        send_response(success=True, data=response_data, request_id=request_id)

    except Exception as e:
        send_response(
            success=False,
            error=f"旋转失败: {str(e)}",
            request_id=request_id,
        )


# 动作映射表
ACTION_HANDLERS = {
    "ping": handle_ping,
    "convert_format": handle_convert_format,
    "compress": handle_compress,
    "crop": handle_crop,
    "rotate": handle_rotate,
    "supported_formats": handle_supported_formats,
    "get_image_info": handle_get_image_info,
}


def main() -> None:
    """主循环：逐行读取 stdin JSON 请求，分发到对应处理器，输出响应。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            send_response(success=False, error=f"JSON 解析失败: {str(e)}")
            continue

        action = request.get("action")
        request_id = request.get("request_id")
        data = request.get("data", {})

        if action == "shutdown":
            send_response(
                success=True,
                data={"message": "格式转换 worker 已关闭"},
                request_id=request_id,
            )
            break

        handler = ACTION_HANDLERS.get(action)
        if handler is None:
            send_response(
                success=False,
                error=f"未知操作: {action}，支持的操作: {list(ACTION_HANDLERS.keys())}",
                request_id=request_id,
            )
            continue

        try:
            handler(data, request_id)
        except Exception as e:
            send_response(
                success=False,
                error=f"处理器异常: {str(e)}",
                request_id=request_id,
            )


if __name__ == "__main__":
    main()
