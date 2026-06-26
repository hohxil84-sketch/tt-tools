"""
desktop/modules/remove-bg/remove_bg_router.py — 智能抠图操作路由脚本

通过 stdin/stdout JSON 协议与桌面端 LocalRuntimeClient 通信。
接收抠图处理请求，调用 local-worker remove-bg 引擎，返回结构化结果。

协议格式：
  请求（stdin，每行一个 JSON）：{"action": "...", "data": {...}, "request_id": "..."}
  响应（stdout，每行一个 JSON）：{"success": true, "data": {...}, "error": null, "request_id": "..."}

支持的动作：
  - ping: 健康检查
  - remove_background: 去除图像背景
  - list_models: 列出所有支持的抠图模型
  - shutdown: 关闭进程

用法：由 LocalRuntimeClient 自动调用，不直接运行。
"""

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# 将 local-worker 根目录添加到 Python 路径，确保可以导入核心模块
# 从当前文件向上 5 级到达项目根目录 (TT Tools)
_LOCAL_WORKER_ROOT = Path(r"D:\TT Tools\local-worker")

# remove-bg 目录包含连字符，不能直接通过 "import modules.remove-bg" 导入
# 将其父目录加入路径后，可直接导入模块内的文件
_REMOVE_BG_DIR = _LOCAL_WORKER_ROOT / "modules" / "remove-bg"
if str(_REMOVE_BG_DIR) not in sys.path:
    sys.path.insert(0, str(_REMOVE_BG_DIR))

from processor import (
    remove_background,
    remove_background_from_path,
    composite_on_color,
    list_supported_models,
    is_model_available,
    clear_model_cache,
    SUPPORTED_MODELS,
    DEFAULT_MODEL,
)

# 本地模型目录（与安装包一起分发，优先从本地加载 .onnx 文件）
# 目录位于此脚本同级目录下的 remove_bg_models/ 中
_MODELS_DIR = str(Path(__file__).parent / "remove_bg_models")
if Path(_MODELS_DIR).is_dir():
    _LOCAL_MODELS_AVAILABLE = True
else:
    _LOCAL_MODELS_AVAILABLE = False
    _MODELS_DIR = None


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
    """健康检查：返回引擎可用性、版本信息和模型列表。"""
    models = list_supported_models()
    send_response(
        success=True,
        data={
            "engine": "rembg (ONNX Runtime + u2net)",
            "status": "available",
            "default_model": DEFAULT_MODEL,
            "supported_models": models,
            "model_count": len(models),
            "supported_formats": [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"],
        },
        request_id=request_id,
    )


def handle_list_models(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """列出所有支持的抠图模型及其描述信息。

    返回：模型名称列表和默认模型。
    """
    try:
        models = list_supported_models()
        # 模型描述映射
        model_descriptions = {
            "u2net": "默认模型，质量最佳，约 168 MB",
            "u2netp": "轻量模型，速度快，约 4.4 MB",
            "u2net_human_seg": "人像专用分割模型",
            "isnet-general-use": "ISNet 通用模型，较新架构",
            "silueta": "轻量级模型，适合简单场景",
        }
        models_data = [
            {
                "name": m,
                "description": model_descriptions.get(m, ""),
            }
            for m in models
        ]
        send_response(
            success=True,
            data={
                "models": models_data,
                "default_model": DEFAULT_MODEL,
                "count": len(models_data),
            },
            request_id=request_id,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"获取模型列表失败: {str(e)}",
            request_id=request_id,
        )


def handle_remove_background(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """处理智能抠图请求。

    期望 data 包含：
        - input_path: str (必填) 输入图像文件路径
        - output_path: str (可选) 输出图像文件路径，为空时自动生成
        - model_name: str (可选) 模型名称，默认 "u2net"
        - alpha_matting: bool (可选) 是否启用 Alpha Matting 精细化边缘，默认 false
        - output_rgba: bool (可选) 是否输出 RGBA 透明 PNG，默认 true
        - composite_color: List[int] (可选) RGB 纯色背景合成，如 [255,255,255] 白色
        - only_mask: bool (可选) 是否只返回 Alpha 遮罩，默认 false

    返回：处理结果，包含输出路径、图像尺寸、模型名称和元信息。
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
    model_name = str(data.get("model_name", DEFAULT_MODEL))
    alpha_matting = bool(data.get("alpha_matting", False))
    output_rgba = bool(data.get("output_rgba", True))
    only_mask = bool(data.get("only_mask", False))
    composite_color = data.get("composite_color")

    # 校验模型名称
    if not is_model_available(model_name):
        send_response(
            success=False,
            error=f"不支持的模型名称: {model_name}，支持: {list_supported_models()}",
            request_id=request_id,
        )
        return

    # 处理 composite_color 参数
    composite_color_tuple = None
    if composite_color and isinstance(composite_color, list) and len(composite_color) == 3:
        composite_color_tuple = tuple(int(c) for c in composite_color)

    # 生成输出路径（如果未指定）
    output_path = data.get("output_path")
    if not output_path:
        input_file = Path(input_path)
        ext = ".png" if output_rgba else ".jpg"
        output_path = str(
            input_file.parent / f"{input_file.stem}_remove_bg{ext}"
        )

    try:
        # 调用 local-worker remove-bg 引擎
        # 优先使用安装包自带的本地模型，避免用户首次使用时联网下载
        result = remove_background_from_path(
            input_path=str(input_path),
            output_path=str(output_path),
            model_name=model_name,
            alpha_matting=alpha_matting,
            output_rgba=output_rgba,
            composite_color=composite_color_tuple,
            models_dir=_MODELS_DIR,
        )

        # 构建响应数据
        response_data = {
            "output_path": str(output_path),
            "input_path": str(input_path),
            "output_width": result.output_width,
            "output_height": result.output_height,
            "input_width": result.input_width,
            "input_height": result.input_height,
            "model": result.model,
            "alpha_matting": alpha_matting,
            "output_rgba": output_rgba,
            "composite_color": list(composite_color_tuple) if composite_color_tuple else None,
            "has_alpha_mask": result.alpha_mask is not None,
            # Alpha 遮罩前景占比（用于 UI 预览展示）
            "foreground_ratio": (
                float((result.alpha_mask > 128).sum() / result.alpha_mask.size)
                if result.alpha_mask is not None
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
    except ImportError as e:
        send_response(
            success=False,
            error=f"依赖缺失: {str(e)}",
            request_id=request_id,
        )
    except Exception as e:
        send_response(
            success=False,
            error=f"抠图处理失败: {str(e)}",
            request_id=request_id,
        )


def handle_clear_cache(data: Dict[str, Any], request_id: Optional[str]) -> None:
    """清除模型缓存，释放内存。

    可选参数：
        - model_name: str (可选) 指定清除的模型名称，不传则清除全部缓存。
    """
    model_name = data.get("model_name") if data else None
    try:
        clear_model_cache(model_name)
        if model_name:
            send_response(
                success=True,
                data={"message": f"已清除模型缓存: {model_name}"},
                request_id=request_id,
            )
        else:
            send_response(
                success=True,
                data={"message": "已清除全部模型缓存"},
                request_id=request_id,
            )
    except Exception as e:
        send_response(
            success=False,
            error=f"清除缓存失败: {str(e)}",
            request_id=request_id,
        )


# 动作映射表
ACTION_HANDLERS = {
    "ping": handle_ping,
    "remove_background": handle_remove_background,
    "list_models": handle_list_models,
    "clear_cache": handle_clear_cache,
}


def main() -> None:
    """主循环：逐行读取 stdin JSON 请求，分发到对应处理器，输出响应。"""
    # 强制 stdout/stderr 使用 UTF-8 编码，避免 Windows 管道中文乱码
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

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
            send_response(success=True, data={"message": "抠图 worker 已关闭"}, request_id=request_id)
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
