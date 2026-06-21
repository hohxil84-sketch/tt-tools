"""
desktop/modules/resize-image/resize_image_router.py — 图片改尺寸操作路由脚本

通过 stdin/stdout JSON 协议与桌面端 LocalRuntimeClient 通信。
接收改尺寸处理请求，调用 local-worker resize-image 引擎，返回结构化结果。

协议格式：
  请求（stdin，每行一个 JSON）：{"action": "...", "data": {...}, "request_id": "..."}
  响应（stdout，每行一个 JSON）：{"success": true, "data": {...}, "error": null, "request_id": "..."}

支持的动作：
  - ping: 健康检查，返回引擎信息、模式列表、格式列表、预设数量
  - resize: 执行图片改尺寸
  - list_presets: 列出所有预设尺寸
  - shutdown: 关闭进程

用法：由 LocalRuntimeClient 自动调用，不直接运行。
"""

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---- 关键：在导入任何 worker 模块之前，将 stdout 重定向到 stderr ----
# local-worker/shared/logging 在初始化时会向 stdout 写入一行日志，
# 这会破坏 stdin/stdout JSON 通信协议。重定向后所有非 JSON 输出走 stderr，
# 只有 send_response() 的 JSON 响应走 stdout（协议要求的通道）。
# 保存原始 stdout 文件描述符用于 JSON 响应。
_real_stdout = sys.stdout  # 保留真实 stdout 引用，用于 send_response
sys.stdout = sys.stderr    # 将所有 print/logging 输出重定向到 stderr

# 将 local-worker 根目录添加到 Python 路径，确保可以导入核心模块
# 从当前文件向上 5 级到达项目根目录 (D:\TT Tools)
# resize_image_router.py → DesktopResizeImage → resize-image → modules → desktop → TT Tools
_LOCAL_WORKER_ROOT = Path(__file__).resolve().parents[4] / "local-worker"

# resize-image 目录包含连字符，不能直接通过 "import modules.resize-image" 导入
# 将其父目录加入路径后，可直接导入模块内的文件
_RESIZE_IMAGE_DIR = _LOCAL_WORKER_ROOT / "modules" / "resize-image"
if str(_RESIZE_IMAGE_DIR) not in sys.path:
    sys.path.insert(0, str(_RESIZE_IMAGE_DIR))

# 将 local-worker/ 目录加入路径，确保 shared.* 导入可用
if str(_LOCAL_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(_LOCAL_WORKER_ROOT))

from processor import ImageResizer
from specifications import (
    ResizeMode,
    ResampleFilter,
    OutputFormat,
    ResizeParams,
    ResizeResult,
    PRINT_PRESETS,
    SUPPORTED_INPUT_SUFFIXES,
    FORMAT_SUFFIX_MAP,
    MAX_OUTPUT_DIMENSION,
)


# ---- 全局处理器实例（进程级单例） ----
_resizer = ImageResizer()


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


def handle_ping(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """健康检查：返回引擎信息、可用模式和格式。"""
    send_response(
        success=True,
        data={
            "engine": "Pillow (纯本地图像处理)",
            "status": "available",
            "supported_modes": _resizer.supported_modes(),
            "supported_filters": _resizer.supported_filters(),
            "supported_formats": SUPPORTED_INPUT_SUFFIXES,
            "output_formats": [f.value for f in OutputFormat],
            "preset_count": len(PRINT_PRESETS),
            "max_output_dimension": MAX_OUTPUT_DIMENSION,
        },
        request_id=request_id,
    )


def handle_list_presets(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """列出所有可用预设尺寸，含中文描述。"""
    try:
        presets = _resizer.list_presets()
        send_response(
            success=True,
            data={
                "presets": presets,
                "count": len(presets),
            },
            request_id=request_id,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"获取预设列表失败: {str(e)}",
            request_id=request_id,
        )


def handle_resize(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理图片改尺寸请求。

    期望 data 包含：
        - input_path: str (必填) 输入图像文件路径
        - output_path: str (可选) 输出图像文件路径，为空时自动生成
        - mode: str (可选) 改尺寸模式，默认 "fit"
        - width: int (可选) 目标宽度
        - height: int (可选) 目标高度
        - scale_percent: float (可选) 缩放百分比
        - short_side: int (可选) 短边约束
        - long_side: int (可选) 长边约束
        - target_dpi: int (可选) 目标 DPI
        - resample: str (可选) 重采样滤镜，默认 "lanczos"
        - keep_aspect: bool (可选) 是否保持宽高比
        - output_format: str (可选) 输出格式，默认 "original"
        - jpeg_quality: int (可选) JPEG 质量，默认 92
        - png_compress_level: int (可选) PNG 压缩级别，默认 6
        - webp_quality: int (可选) WEBP 质量，默认 85
        - dpi: list[float, float] (可选) 输出 DPI
        - preset: str (可选) 预设名称（优先级高于 mode+尺寸参数）

    返回：处理元数据，含输出路径、尺寸、格式等信息。
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

    # ---- 处理 output_path（C4: 校验外部传入路径） ----
    output_path = data.get("output_path")
    if output_path:
        output_path = str(output_path)
        # 校验扩展名属于支持格式
        out_suffix = Path(output_path).suffix.lower()
        valid_suffixes = [v for v in FORMAT_SUFFIX_MAP.values()]
        if out_suffix and out_suffix not in valid_suffixes:
            send_response(
                success=False,
                error=f"不支持的输出文件扩展名: {out_suffix}，支持: {valid_suffixes}",
                request_id=request_id,
            )
            return
        # 校验父目录存在（不自动创建，避免目录遍历风险）
        out_parent = Path(output_path).parent
        if not out_parent.is_dir():
            send_response(
                success=False,
                error=f"输出目录不存在: {out_parent}",
                request_id=request_id,
            )
            return
    else:
        # 自动生成输出路径: {input_dir}/{input_stem}_resized.{ext}
        input_file = Path(input_path)
        out_suffix = input_file.suffix.lower()
        if out_suffix not in SUPPORTED_INPUT_SUFFIXES:
            out_suffix = ".png"  # fallback
        output_path = str(
            input_file.parent / f"{input_file.stem}_resized{out_suffix}"
        )

    # ---- 解析参数 ----
    mode_str = str(data.get("mode", "fit")).lower()

    # 处理 preset（优先级最高）
    preset = data.get("preset")

    # 构建 ResizeParams
    try:
        # 解析重采样滤镜
        resample_str = str(data.get("resample", "lanczos")).lower()
        try:
            resample = ResampleFilter(resample_str)
        except ValueError:
            send_response(
                success=False,
                error=f"不支持的重采样滤镜: {resample_str}，支持: {_resizer.supported_filters()}",
                request_id=request_id,
            )
            return

        # 解析输出格式
        output_format_str = str(data.get("output_format", "original")).lower()
        try:
            output_format = OutputFormat(output_format_str)
        except ValueError:
            send_response(
                success=False,
                error=f"不支持的输出格式: {output_format_str}",
                request_id=request_id,
            )
            return

        # 解析 DPI
        dpi_data = data.get("dpi")
        dpi_tuple = None
        if dpi_data and isinstance(dpi_data, list) and len(dpi_data) == 2:
            dpi_tuple = (float(dpi_data[0]), float(dpi_data[1]))

        # 构建参数对象
        params = ResizeParams(
            mode=ResizeMode(mode_str) if mode_str in [m.value for m in ResizeMode] else ResizeMode.FIT,
            width=data.get("width") if data.get("width") is not None else None,
            height=data.get("height") if data.get("height") is not None else None,
            scale_percent=float(data.get("scale_percent", 100.0)),
            short_side=data.get("short_side") if data.get("short_side") is not None else None,
            long_side=data.get("long_side") if data.get("long_side") is not None else None,
            target_dpi=data.get("target_dpi") if data.get("target_dpi") is not None else None,
            resample=resample,
            keep_aspect=bool(data.get("keep_aspect", True)),
            output_format=output_format,
            jpeg_quality=int(data.get("jpeg_quality", 92)),
            png_compress_level=int(data.get("png_compress_level", 6)),
            webp_quality=int(data.get("webp_quality", 85)),
            dpi=dpi_tuple,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"参数解析失败: {str(e)}",
            request_id=request_id,
        )
        return

    # ---- 执行缩放 ----
    try:
        result = _resizer.resize(
            image=str(input_path),
            params=params,
            preset=preset,
            output_path=str(output_path),
        )

        if not result.success:
            send_response(
                success=False,
                error=result.error_message or "改尺寸处理失败",
                request_id=request_id,
            )
            return

        # 构建响应数据（不含二进制 output_data，由文件路径替代）
        response_data = {
            "output_path": str(output_path),
            "input_path": str(input_path),
            "source_width": result.source_width,
            "source_height": result.source_height,
            "output_width": result.output_width,
            "output_height": result.output_height,
            "mode": result.mode.value if result.mode else mode_str,
            "scale_ratio": round(result.scale_ratio, 6),
            "output_format": result.output_format,
            "output_size": result.output_size,
            "dpi": list(result.dpi) if result.dpi else None,
            "warnings": result.warnings,
            "elapsed_ms": round(result.elapsed_ms, 2),
            "preset": preset,
        }

        send_response(
            success=True,
            data=response_data,
            request_id=request_id,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"改尺寸处理失败: {str(e)}",
            request_id=request_id,
        )


# 动作映射表
ACTION_HANDLERS = {
    "ping": handle_ping,
    "resize": handle_resize,
    "list_presets": handle_list_presets,
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
                data={"message": "改尺寸 worker 已关闭"},
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
