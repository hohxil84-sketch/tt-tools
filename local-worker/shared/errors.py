"""
local-worker/shared/errors — 统一错误结构和错误码

对齐 shared-contract/openapi/common.yaml 的 ErrorDetail schema：
  - code: string        # 错误码
  - message: string     # 错误描述
  - details: object     # 附加详情（可选）
"""

import uuid
from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """统一错误码枚举。

    本地 worker 错误码前缀使用 LOCAL_，与云端错误码区分。
    对齐 shared-contract/API_INDEX.md 中全局统一的错误码体系。
    """

    # ---- 通用 ----
    UNKNOWN = "LOCAL_UNKNOWN"
    INTERNAL = "LOCAL_INTERNAL"
    INVALID_ARGUMENT = "LOCAL_INVALID_ARGUMENT"
    NOT_IMPLEMENTED = "LOCAL_NOT_IMPLEMENTED"

    # ---- 运行时 ----
    RUNTIME_CPU_UNSUPPORTED = "LOCAL_RUNTIME_CPU_UNSUPPORTED"
    RUNTIME_GPU_UNAVAILABLE = "LOCAL_RUNTIME_GPU_UNAVAILABLE"
    RUNTIME_GPU_FALLBACK_CPU = "LOCAL_RUNTIME_GPU_FALLBACK_CPU"

    # ---- 文件 IO ----
    FILE_NOT_FOUND = "LOCAL_FILE_NOT_FOUND"
    FILE_READ_ERROR = "LOCAL_FILE_READ_ERROR"
    FILE_WRITE_ERROR = "LOCAL_FILE_WRITE_ERROR"
    FILE_UNSUPPORTED_FORMAT = "LOCAL_FILE_UNSUPPORTED_FORMAT"
    FILE_TOO_LARGE = "LOCAL_FILE_TOO_LARGE"

    # ---- 模型 ----
    MODEL_NOT_FOUND = "LOCAL_MODEL_NOT_FOUND"
    MODEL_LOAD_FAILED = "LOCAL_MODEL_LOAD_FAILED"
    MODEL_INFERENCE_FAILED = "LOCAL_MODEL_INFERENCE_FAILED"
    MODEL_NOT_REGISTERED = "LOCAL_MODEL_NOT_REGISTERED"

    # ---- 进程协议 ----
    PROTOCOL_TIMEOUT = "LOCAL_PROTOCOL_TIMEOUT"
    PROTOCOL_INVALID_MESSAGE = "LOCAL_PROTOCOL_INVALID_MESSAGE"
    PROTOCOL_CONNECTION_LOST = "LOCAL_PROTOCOL_CONNECTION_LOST"

    # ---- 任务 ----
    TASK_CANCELLED = "LOCAL_TASK_CANCELLED"
    TASK_FAILED = "LOCAL_TASK_FAILED"


class AppError(Exception):
    """统一错误类，对齐 OpenAPI ErrorDetail 结构。

    用法：
        raise AppError(
            ErrorCode.FILE_NOT_FOUND,
            "未找到输入文件",
            details={"path": "/tmp/input.png"},
        )
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        # request_id 用于链路追踪，对齐 OpenAPI ApiResponse 的 request_id
        self.request_id = request_id or str(uuid.uuid4())
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """转为字典，用于序列化或跨进程传输。"""
        result: Dict[str, Any] = {
            "success": False,
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
            },
            "data": None,
            "request_id": self.request_id,
        }
        return result

    def __repr__(self) -> str:
        return (
            f"AppError(code={self.code.value!r}, message={self.message!r}, "
            f"request_id={self.request_id!r})"
        )
