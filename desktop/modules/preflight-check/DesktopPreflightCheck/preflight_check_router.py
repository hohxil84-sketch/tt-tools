"""
desktop/modules/preflight-check/preflight_check_router.py — 印前检查路由脚本

通过 stdin/stdout JSON 协议与桌面端 LocalRuntimeClient 通信。
接收检查请求，调用 local-worker PreflightChecker，返回结构化报告。

协议格式：
  请求（stdin，每行一个 JSON）：{"action": "...", "data": {...}, "request_id": "..."}
  响应（stdout，每行一个 JSON）：{"success": true, "data": {...}, "error": null, "request_id": "..."}

支持的动作：
  - ping: 健康检查
  - check: 单文件印前检查
  - check_batch: 批量文件印前检查
  - shutdown: 关闭进程

用法：由 LocalRuntimeClient 自动调用，不直接运行。
"""

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# 将 local-worker 根目录添加到 Python 路径，确保可以导入核心模块
_LOCAL_WORKER_ROOT = Path(r"D:\TT Tools\local-worker")
if str(_LOCAL_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(_LOCAL_WORKER_ROOT))

# 将 local-worker 模块目录加入路径（用于直接导入 preflight-check 模块）
_LOCAL_WORKER_MODULES = _LOCAL_WORKER_ROOT / "modules" / "preflight-check"
if str(_LOCAL_WORKER_MODULES) not in sys.path:
    sys.path.insert(0, str(_LOCAL_WORKER_MODULES))

from checker import PreflightChecker


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
    """健康检查：返回检查器状态和检查项信息。"""
    checker = PreflightChecker()
    send_response(
        success=True,
        data={
            "checker": "PreflightChecker",
            "status": "available",
            "check_items": [
                "file_format", "dimensions", "dpi", "color_mode",
                "transparency", "low_resolution", "file_size"
            ],
            "supported_formats": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"],
        },
        request_id=request_id,
    )


def handle_check(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理单文件印前检查请求。

    期望 data 包含：
        - file_path: str (必填) 待检查的图像文件路径

    返回：PreflightReport.to_dict() 序列化的完整检查报告。
    """
    file_path = data.get("file_path")
    if not file_path:
        send_response(success=False, error="缺少必填参数 file_path", request_id=request_id)
        return

    if not Path(file_path).is_file():
        send_response(
            success=False,
            error=f"文件不存在: {file_path}",
            request_id=request_id,
        )
        return

    try:
        checker = PreflightChecker()
        report = checker.check(file_path)
        report_dict = report.to_dict()
        send_response(
            success=True,
            data=report_dict,
            request_id=request_id,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"印前检查失败: {str(e)}",
            request_id=request_id,
        )


def handle_check_batch(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理批量文件印前检查请求。

    期望 data 包含：
        - file_paths: List[str] (必填) 待检查的图像文件路径列表

    返回：每个文件的检查报告列表。
    """
    file_paths = data.get("file_paths")
    if not file_paths:
        send_response(success=False, error="缺少必填参数 file_paths", request_id=request_id)
        return

    results = []
    checker = PreflightChecker()

    for fp in file_paths:
        if not Path(fp).is_file():
            results.append({
                "error": f"文件不存在: {fp}",
                "file_path": fp,
                "success": False,
            })
            continue

        try:
            report = checker.check(fp)
            report_dict = report.to_dict()
            report_dict["success"] = True
            results.append(report_dict)
        except Exception as e:
            results.append({
                "error": f"检查失败: {str(e)}",
                "file_path": fp,
                "success": False,
            })

    send_response(
        success=True,
        data={"results": results, "total": len(results)},
        request_id=request_id,
    )


# 动作映射表
ACTION_HANDLERS = {
    "ping": handle_ping,
    "check": handle_check,
    "check_batch": handle_check_batch,
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
            send_response(success=True, data={"message": "PreflightCheck worker 已关闭"}, request_id=request_id)
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
