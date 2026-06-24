"""
desktop/modules/pdf-image-convert/pdf_image_convert_router.py — PDF/图片互转操作路由脚本

通过 stdin/stdout JSON 协议与桌面端 LocalRuntimeClient 通信。
接收 PDF/图片互转处理请求，调用 local-worker pdf-image-convert 引擎，返回结构化结果。

协议格式：
  请求（stdin，每行一个 JSON）：{"action": "...", "data": {...}, "request_id": "..."}
  响应（stdout，每行一个 JSON）：{"success": true, "data": {...}, "error": null, "request_id": "..."}

支持的动作：
  - ping: 健康检查，返回引擎信息和支持的格式
  - pdf_to_images: PDF 转图片
  - images_to_pdf: 图片转 PDF
  - list_formats: 列出支持的输入输出格式
  - shutdown: 关闭进程

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
# 从当前文件向上 5 级到达项目根目录 (D:\TT Tools)
# pdf_image_convert_router.py → DesktopPdfImageConvert → pdf-image-convert → modules → desktop → TT Tools
_LOCAL_WORKER_ROOT = Path(r"D:\TT Tools\local-worker")

# pdf-image-convert 目录包含连字符，不能直接通过 "import modules.pdf-image-convert" 导入
# 将其父目录加入路径后，可直接导入模块内的文件
_PDF_IMAGE_CONVERT_DIR = _LOCAL_WORKER_ROOT / "modules" / "pdf-image-convert"
if str(_PDF_IMAGE_CONVERT_DIR) not in sys.path:
    sys.path.insert(0, str(_PDF_IMAGE_CONVERT_DIR))

# 将 local-worker/ 目录加入路径，确保 shared.* 导入可用
if str(_LOCAL_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(_LOCAL_WORKER_ROOT))

from processor import PdfImageConverter
from specifications import (
    ConvertDirection,
    OutputFormat,
    ConvertParams,
    SUPPORTED_IMAGE_INPUT_SUFFIXES,
    SUPPORTED_PDF_SUFFIX,
    FORMAT_SUFFIX_MAP,
    DEFAULT_PDF_RENDER_DPI,
    DEFAULT_JPEG_QUALITY,
    MAX_OUTPUT_DIMENSION,
    MAX_PDF_PAGES,
    MAX_IMAGES_COUNT,
)

# ---- 全局处理器实例（进程级单例） ----
_converter = PdfImageConverter()


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
    """健康检查：返回引擎信息和支持格式。"""
    formats = PdfImageConverter.supported_formats()
    send_response(
        success=True,
        data={
            "engine": "PyMuPDF + Pillow (纯本地 PDF/图片互转)",
            "status": "available",
            "pdf_input": formats.get("pdf_input", [SUPPORTED_PDF_SUFFIX]),
            "image_input": formats.get("image_input", SUPPORTED_IMAGE_INPUT_SUFFIXES),
            "image_output": formats.get("image_output", ["png", "jpeg"]),
            "output_format_suffixes": {
                k.value: v for k, v in FORMAT_SUFFIX_MAP.items()
            },
            "default_dpi": DEFAULT_PDF_RENDER_DPI,
            "max_output_dimension": MAX_OUTPUT_DIMENSION,
            "max_pdf_pages": MAX_PDF_PAGES,
            "max_images_count": MAX_IMAGES_COUNT,
        },
        request_id=request_id,
    )


def handle_list_formats(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """列出支持的输入输出格式。"""
    formats = PdfImageConverter.supported_formats()
    send_response(
        success=True,
        data={
            "pdf_input": formats.get("pdf_input", [SUPPORTED_PDF_SUFFIX]),
            "image_input": formats.get("image_input", SUPPORTED_IMAGE_INPUT_SUFFIXES),
            "image_output": formats.get("image_output", ["png", "jpeg"]),
            "output_suffix_map": {
                k.value: v for k, v in FORMAT_SUFFIX_MAP.items()
            },
        },
        request_id=request_id,
    )


def handle_pdf_to_images(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理 PDF 转图片请求。

    期望 data 包含：
        - input_path: str (必填) PDF 文件路径
        - output_dir: str (可选) 输出目录，不为空时每页图片保存到该目录
        - dpi: int (可选) 渲染 DPI，默认 200
        - output_format: str (可选) 输出格式 "png" 或 "jpeg"，默认 "png"
        - jpeg_quality: int (可选) JPEG 质量，默认 92
        - page_range: [int, int] (可选) 页码范围 1-based，包含两端
        - page_limit: int (可选) 最多转换页数

    返回：每页图片的元数据（不含二进制 data——通过文件保存）。
    """
    input_path = data.get("input_path")
    if not input_path:
        send_response(success=False, error="缺少必填参数 input_path", request_id=request_id)
        return

    input_path = str(input_path)
    if not Path(input_path).is_file():
        send_response(
            success=False,
            error=f"PDF 文件不存在: {input_path}",
            request_id=request_id,
        )
        return

    # 校验扩展名
    suffix = Path(input_path).suffix.lower()
    if suffix != SUPPORTED_PDF_SUFFIX:
        send_response(
            success=False,
            error=f"不支持的文件格式: {suffix}，仅支持 PDF 文件",
            request_id=request_id,
        )
        return

    # 解析输出目录
    output_dir = data.get("output_dir")
    if output_dir:
        output_dir = str(output_dir)
        output_dir_path = Path(output_dir)
        if output_dir_path.exists() and not output_dir_path.is_dir():
            send_response(
                success=False,
                error=f"输出路径必须为目录: {output_dir}",
                request_id=request_id,
            )
            return
    else:
        output_dir = None

    # 解析输出格式
    output_format_str = str(data.get("output_format", "png")).lower()
    try:
        output_format = OutputFormat(output_format_str)
    except ValueError:
        send_response(
            success=False,
            error=f"不支持的输出格式: {output_format_str}，支持: png, jpeg",
            request_id=request_id,
        )
        return

    # 解析 DPI
    dpi = int(data.get("dpi", DEFAULT_PDF_RENDER_DPI))
    if dpi < 72 or dpi > 600:
        dpi = DEFAULT_PDF_RENDER_DPI

    # 解析 JPEG 质量
    jpeg_quality = int(data.get("jpeg_quality", DEFAULT_JPEG_QUALITY))

    # 解析页码范围
    page_range: Optional[Tuple[int, int]] = None
    pr = data.get("page_range")
    if pr and isinstance(pr, list) and len(pr) == 2:
        page_range = (int(pr[0]), int(pr[1]))

    # 解析页面限制
    page_limit = data.get("page_limit")
    if page_limit is not None:
        page_limit = int(page_limit)

    # 构建参数并执行转换
    try:
        params = ConvertParams(
            direction=ConvertDirection.PDF_TO_IMAGES,
            output_format=output_format,
            dpi=dpi,
            jpeg_quality=jpeg_quality,
            page_range=page_range,
            page_limit=page_limit,
        )

        result = _converter.convert(
            source=input_path,
            params=params,
            output_path=output_dir,
        )

        # 构建响应数据（pages 中不含二进制 data，体积过大跨进程传输无意义）
        response_data = {
            "input_path": str(input_path),
            "direction": "pdf_to_images",
            "source_format": result.source_format,
            "total_pages": result.total_pages,
            "output_pages": result.output_pages,
            "output_format": result.output_format,
            "output_size": result.output_size,
            "output_dir": output_dir,
            "pages": [p.to_dict() for p in result.pages],
            "warnings": result.warnings,
            "elapsed_ms": result.elapsed_ms,
        }

        send_response(
            success=True,
            data=response_data,
            request_id=request_id,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"PDF 转图片失败: {str(e)}",
            request_id=request_id,
        )


def handle_images_to_pdf(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理图片转 PDF 请求。

    期望 data 包含：
        - input_paths: [str] (必填) 图片文件路径列表
        - output_path: str (可选) 输出 PDF 文件路径，为空时自动生成

    返回：合并后 PDF 的元数据（不含二进制 data——通过文件保存）。
    """
    input_paths = data.get("input_paths")
    if not input_paths:
        send_response(success=False, error="缺少必填参数 input_paths", request_id=request_id)
        return

    if not isinstance(input_paths, list):
        send_response(
            success=False,
            error=f"input_paths 必须是字符串列表，收到: {type(input_paths).__name__}",
            request_id=request_id,
        )
        return

    if len(input_paths) == 0:
        send_response(success=False, error="图片路径列表不能为空", request_id=request_id)
        return

    # 校验所有文件存在且为支持的图片格式
    for idx, path in enumerate(input_paths):
        path_str = str(path)
        if not Path(path_str).is_file():
            send_response(
                success=False,
                error=f"第 {idx + 1} 张图片不存在: {path_str}",
                request_id=request_id,
            )
            return
        suffix = Path(path_str).suffix.lower()
        if suffix not in SUPPORTED_IMAGE_INPUT_SUFFIXES:
            send_response(
                success=False,
                error=f"第 {idx + 1} 张图片格式不支持: {suffix}，支持: {SUPPORTED_IMAGE_INPUT_SUFFIXES}",
                request_id=request_id,
            )
            return

    # 处理输出路径
    output_path = data.get("output_path")
    if output_path:
        output_path = str(output_path)
        # 校验输出父目录存在
        out_parent = Path(output_path).parent
        if not out_parent.is_dir():
            send_response(
                success=False,
                error=f"输出目录不存在: {out_parent}",
                request_id=request_id,
            )
            return
    else:
        # 自动生成输出路径: 第一张图片同目录/{第一张图片名}_merged.pdf
        first_img = Path(str(input_paths[0]))
        output_path = str(first_img.parent / f"{first_img.stem}_merged.pdf")

    # 执行图片转 PDF
    try:
        result = _converter.convert(
            source=input_paths,
            params=ConvertParams(direction=ConvertDirection.IMAGES_TO_PDF),
            output_path=output_path,
        )

        response_data = {
            "input_paths": [str(p) for p in input_paths],
            "output_path": str(output_path),
            "direction": "images_to_pdf",
            "source_format": result.source_format,
            "total_pages": result.total_pages,
            "output_pages": result.output_pages,
            "output_format": result.output_format,
            "output_size": result.output_size,
            "pages": [p.to_dict() for p in result.pages],
            "warnings": result.warnings,
            "elapsed_ms": result.elapsed_ms,
        }

        send_response(
            success=True,
            data=response_data,
            request_id=request_id,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"图片转 PDF 失败: {str(e)}",
            request_id=request_id,
        )


# 动作映射表
ACTION_HANDLERS = {
    "ping": handle_ping,
    "pdf_to_images": handle_pdf_to_images,
    "images_to_pdf": handle_images_to_pdf,
    "list_formats": handle_list_formats,
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
                data={"message": "PDF/图片互转 worker 已关闭"},
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
