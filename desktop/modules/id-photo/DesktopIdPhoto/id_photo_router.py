"""
desktop/modules/id-photo/id_photo_router.py — 证件照换底色路由脚本

通过 stdin/stdout JSON 协议与桌面端 LocalRuntimeClient 通信。
接收证件照处理请求，调用 local-worker id-photo 引擎，返回结构化结果。

协议格式：
  请求（stdin，每行一个 JSON）：{"action": "...", "data": {...}, "request_id": "..."}
  响应（stdout，每行一个 JSON）：{"success": true, "data": {...}, "error": null, "request_id": "..."}

支持的动作：
  - ping: 健康检查
  - process_id_photo: 证件照换底色处理
  - list_specs: 列出所有可用规格
  - list_background_colors: 列出所有可用底色
  - shutdown: 关闭进程

用法：由 LocalRuntimeClient 自动调用，不直接运行。
"""

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# 将 local-worker 根目录添加到 Python 路径，确保可以导入核心模块
# 从当前文件向上 4 级到达项目根目录 (TT Tools)
_LOCAL_WORKER_ROOT = Path(__file__).resolve().parents[4] / "local-worker"

# id-photo 目录包含连字符，不能直接通过 "import modules.id-photo" 导入
# 将其父目录加入路径后，可直接导入模块内的文件
_ID_PHOTO_DIR = _LOCAL_WORKER_ROOT / "modules" / "id-photo"
if str(_ID_PHOTO_DIR) not in sys.path:
    sys.path.insert(0, str(_ID_PHOTO_DIR))

from specifications import (
    list_specs,
    list_background_colors,
)
from processor import process_id_photo_from_path



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
    specs = list_specs()
    colors = list_background_colors()
    send_response(
        success=True,
        data={
            "engine": "OpenCV ID Photo Processor",
            "status": "available",
            "supported_formats": [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"],
            "spec_count": len(specs),
            "color_count": len(colors),
        },
        request_id=request_id,
    )


def handle_list_specs(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """列出所有可用的证件照规格。

    可选参数：
        - dpi: int (可选) 目标 DPI，默认 300。

    返回：规格列表，每个规格包含名称、尺寸（mm 和 px）、DPI。
    """
    dpi = int(data.get("dpi", 300))
    try:
        specs = list_specs(dpi=dpi)
        specs_data = [
            {
                "name": s.name,
                "width_mm": s.width_mm,
                "height_mm": s.height_mm,
                "width_px": s.width_px,
                "height_px": s.height_px,
                "dpi": s.dpi,
            }
            for s in specs
        ]
        send_response(
            success=True,
            data={"specs": specs_data, "count": len(specs_data)},
            request_id=request_id,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"获取规格列表失败: {str(e)}",
            request_id=request_id,
        )


def handle_list_background_colors(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """列出所有可用的背景色。

    返回：背景色列表，每个颜色包含名称、RGB 值、十六进制和 BGR 值。
    """
    try:
        colors = list_background_colors()
        colors_data = [
            {
                "name": c.name,
                "r": c.r,
                "g": c.g,
                "b": c.b,
                "hex": c.to_hex(),
                "bgr": list(c.to_bgr()),
            }
            for c in colors
        ]
        send_response(
            success=True,
            data={"colors": colors_data, "count": len(colors_data)},
            request_id=request_id,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"获取底色列表失败: {str(e)}",
            request_id=request_id,
        )


def handle_process_id_photo(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理证件照换底色请求。

    期望 data 包含：
        - input_path: str (必填) 输入图像文件路径
        - output_path: str (可选) 输出文件路径，为空时自动生成到同一目录
        - background: str (可选) 目标底色名称，默认 "white"
        - spec_name: str (可选) 目标规格名称，默认 "1寸"
        - dpi: int (可选) 目标 DPI，默认 300
        - auto_detect_background: bool (可选) 是否自动检测原图背景色，默认 true
        - edge_feather: bool (可选) 是否边缘羽化，默认 true

    返回：处理结果，包含输出路径、尺寸、规格信息、底色信息、元数据。
    """
    input_path = data.get("input_path")
    if not input_path:
        send_response(success=False, error="缺少必填参数 input_path", request_id=request_id)
        return

    if not Path(input_path).is_file():
        send_response(
            success=False,
            error=f"图片文件不存在: {input_path}",
            request_id=request_id,
        )
        return

    # 解析可选参数
    background = str(data.get("background", "white"))
    spec_name = str(data.get("spec_name", "1寸"))
    dpi = int(data.get("dpi", 300))
    auto_detect_background = bool(data.get("auto_detect_background", True))
    edge_feather = bool(data.get("edge_feather", True))

    # 生成输出路径（如果未指定）
    output_path = data.get("output_path")
    if not output_path:
        input_file = Path(input_path)
        output_path = str(
            input_file.parent / f"{input_file.stem}_id_photo{input_file.suffix}"
        )

    try:
        # 调用 local-worker id-photo 引擎
        result = process_id_photo_from_path(
            input_path=input_path,
            output_path=output_path,
            background=background,
            spec_name=spec_name,
            dpi=dpi,
            auto_detect_background=auto_detect_background,
            edge_feather=edge_feather,
        )

        # 构建响应数据
        response_data = {
            "output_path": output_path,
            "input_path": input_path,
            "width_px": result.width_px,
            "height_px": result.height_px,
            "spec": {
                "name": result.spec.name,
                "width_mm": result.spec.width_mm,
                "height_mm": result.spec.height_mm,
                "width_px": result.spec.width_px,
                "height_px": result.spec.height_px,
                "dpi": result.spec.dpi,
            },
            "background_color": {
                "name": result.background_color.name,
                "r": result.background_color.r,
                "g": result.background_color.g,
                "b": result.background_color.b,
                "hex": result.background_color.to_hex(),
            },
            "detected_background": (
                {
                    "name": result.detected_background.name,
                    "r": result.detected_background.r,
                    "g": result.detected_background.g,
                    "b": result.detected_background.b,
                    "hex": result.detected_background.to_hex(),
                }
                if result.detected_background
                else None
            ),
            "metadata": result.metadata,
        }

        send_response(
            success=True,
            data=response_data,
            request_id=request_id,
        )
    except ValueError as e:
        send_response(
            success=False,
            error=f"参数错误: {str(e)}",
            request_id=request_id,
        )
    except IOError as e:
        send_response(
            success=False,
            error=f"文件写入失败: {str(e)}",
            request_id=request_id,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"证件照处理失败: {str(e)}",
            request_id=request_id,
        )


# 动作映射表
ACTION_HANDLERS = {
    "ping": handle_ping,
    "process_id_photo": handle_process_id_photo,
    "list_specs": handle_list_specs,
    "list_background_colors": handle_list_background_colors,
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
            send_response(success=True, data={"message": "证件照 worker 已关闭"}, request_id=request_id)
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
