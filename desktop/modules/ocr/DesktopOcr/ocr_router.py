"""
desktop/modules/ocr/ocr_router.py — OCR 操作路由脚本

通过 stdin/stdout JSON 协议与桌面端 LocalRuntimeClient 通信。
接收识别请求，调用 local-worker OCR 引擎，返回结构化结果。

协议格式：
  请求（stdin，每行一个 JSON）：{"action": "...", "data": {...}, "request_id": "..."}
  响应（stdout，每行一个 JSON）：{"success": true, "data": {...}, "error": null, "request_id": "..."}

支持的动作：
  - ping: 健康检查
  - recognize: 单张图片 OCR 识别
  - recognize_batch: 批量图片 OCR 识别
  - shutdown: 关闭进程

用法：由 LocalRuntimeClient 自动调用，不直接运行。
"""

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# 强制 stdin/stdout 使用 UTF-8 编码，对齐 C# 端 LocalRuntimeClient 的编码设置。
# 不加此行，Windows 上 Python 默认使用 GBK/cp936，会导致中文字符乱码。
sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")

# 将 local-worker 根目录添加到 Python 路径，确保可以导入核心模块
_LOCAL_WORKER_ROOT = Path(r"D:\TT Tools\local-worker")
if str(_LOCAL_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(_LOCAL_WORKER_ROOT))

from modules.ocr import OCREngine, recognize_image, OCRResult


def send_response(
    success: bool,
    data: Any = None,
    error: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """将响应以单行 JSON 写入 stdout 并立即刷新。

    桌面端通过 stdout 读取响应，必须每行一个完整 JSON。
    """
    response = {
        "success": success,
        "data": data,
        "error": error,
        "request_id": request_id,
    }
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle_ping(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """健康检查：返回引擎可用性和版本信息。"""
    send_response(
        success=True,
        data={
            "engine": "RapidOCR",
            "status": "available",
            "supported_formats": [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"],
        },
        request_id=request_id,
    )


def handle_recognize(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理单张图片 OCR 识别请求。

    期望 data 包含：
        - file_path: str (必填) 图片文件路径
        - text_score: float (可选) 识别置信度阈值，默认 0.5
        - use_dml: bool (可选) 是否使用 DirectML GPU 加速，默认 false

    返回：OCRResult.to_dict() 序列化的结构化识别结果。
    """
    file_path = data.get("file_path")
    if not file_path:
        send_response(success=False, error="缺少必填参数 file_path", request_id=request_id)
        return

    if not Path(file_path).is_file():
        send_response(
            success=False,
            error=f"图片文件不存在: {file_path}",
            request_id=request_id,
        )
        return

    text_score = float(data.get("text_score", 0.5))
    use_dml = bool(data.get("use_dml", False))

    try:
        engine = OCREngine(text_score=text_score, use_dml=use_dml)
        result = engine.recognize(file_path)
        engine.close()

        # 转为字典并修复 total_text：用换行符拼接，保留原始排版
        result_dict = result.to_dict()
        if result.text_lines:
            result_dict["total_text"] = "\n".join(
                line.text for line in result.text_lines
            )
        send_response(
            success=True,
            data=result_dict,
            request_id=request_id,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"OCR 识别失败: {str(e)}",
            request_id=request_id,
        )


def handle_recognize_batch(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理批量图片 OCR 识别请求。

    期望 data 包含：
        - file_paths: List[str] (必填) 图片文件路径列表
        - text_score: float (可选) 识别置信度阈值，默认 0.5
        - use_dml: bool (可选) 是否使用 DirectML GPU 加速，默认 false

    返回：List[OCRResult.to_dict()] 序列化的结果列表。
    """
    file_paths = data.get("file_paths")
    if not file_paths:
        send_response(success=False, error="缺少必填参数 file_paths", request_id=request_id)
        return

    text_score = float(data.get("text_score", 0.5))
    use_dml = bool(data.get("use_dml", False))

    results = []
    engine = OCREngine(text_score=text_score, use_dml=use_dml)

    try:
        for fp in file_paths:
            if not Path(fp).is_file():
                results.append({
                    "error": f"文件不存在: {fp}",
                    "file_path": fp,
                    "success": False,
                })
                continue

            try:
                result = engine.recognize(fp)
                result_dict = result.to_dict()
                # 用换行符拼接，保留原始排版格式
                if result.text_lines:
                    result_dict["total_text"] = "\n".join(
                        line.text for line in result.text_lines
                    )
                result_dict["success"] = True
                result_dict["file_path"] = fp
                results.append(result_dict)
            except Exception as e:
                results.append({
                    "error": f"识别失败: {str(e)}",
                    "file_path": fp,
                    "success": False,
                })
    finally:
        engine.close()

    send_response(
        success=True,
        data={"results": results, "total": len(results)},
        request_id=request_id,
    )


# 动作映射表
ACTION_HANDLERS = {
    "ping": handle_ping,
    "recognize": handle_recognize,
    "recognize_batch": handle_recognize_batch,
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
            send_response(success=True, data={"message": "OCR worker 已关闭"}, request_id=request_id)
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
