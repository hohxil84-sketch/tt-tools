"""
local-worker/shared — 本地 worker 公共层

提供进程协议、模型加载、文件 IO、错误结构、日志和 CPU/GPU 能力检测。
"""

from .errors import AppError, ErrorCode
from .runtime import detect_cpu_info, detect_gpu_info, get_runtime_info
from .model_registry import ModelRegistry, ModelInfo
from .file_io import (
    read_file_bytes,
    write_file_bytes,
    get_file_info,
    ensure_directory,
    list_files,
)
from .logging import setup_logging, get_logger

__all__ = [
    # errors
    "AppError",
    "ErrorCode",
    # runtime
    "detect_cpu_info",
    "detect_gpu_info",
    "get_runtime_info",
    # model_registry
    "ModelRegistry",
    "ModelInfo",
    # file_io
    "read_file_bytes",
    "write_file_bytes",
    "get_file_info",
    "ensure_directory",
    "list_files",
    # logging
    "setup_logging",
    "get_logger",
]
