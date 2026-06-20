"""
cloud-app-shell 基础中间件模块。

提供：
1. 请求追踪 ID 中间件：确保每个请求带有 X-Request-ID 头。
2. CORS 中间件：根据配置允许跨域来源。
3. 统一错误处理：将未捕获异常转换为符合 shared-contract/openapi/common.yaml 的 ErrorResponse 格式。

统一响应结构要求：{ success, data, error, request_id }
"""
from __future__ import annotations

import sys
import os
import uuid
import traceback

# cloud/app-shell 目录名含连字符，无法用 Python 点号导入，故将本目录加入 sys.path
_parent_dir = os.path.dirname(os.path.abspath(__file__))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

import config
from config import settings


# ---- 常量：统一响应头 ----
REQUEST_ID_HEADER = "X-Request-ID"


def setup_middleware(app: FastAPI) -> None:
    """按正确顺序注册所有基础中间件。

    注册顺序（从外到内）：
    1. 错误处理中间件 —— 最外层兜底捕获所有未处理异常
    2. CORS 中间件 —— 处理跨域
    3. Request ID 中间件 —— 生成和传递请求追踪 ID
    """
    # 1. 异常处理中间件：最外层兜底捕获，生成统一错误响应
    app.add_middleware(BaseHTTPMiddleware, dispatch=_error_handler_dispatch)

    # 2. CORS：允许桌面客户端跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. 请求追踪 ID
    app.add_middleware(BaseHTTPMiddleware, dispatch=_request_id_dispatch)

    # 4. 注册 FastAPI 级异常处理器（捕获校验、HTTP 等特定异常）
    _register_fastapi_handlers(app)


# ---- 请求追踪 ID ----

async def _request_id_dispatch(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    """如果请求头没有 X-Request-ID 则生成一个，并将其添加到响应头中。"""
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
    # 注入到 request.state，供下游业务使用
    request.state.request_id = request_id
    response = await call_next(request)
    # 确保响应也包含追踪 ID
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


# ---- 统一错误处理中间件（最外层） ----

async def _error_handler_dispatch(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    """最外层异常捕获中间件，将未处理异常转换为统一错误响应格式。

    该中间件位于中间件栈最外层，确保任何未被下层捕获的异常都能
    被转换为符合 common.yaml ErrorResponse 格式的 JSON 响应。
    """
    try:
        return await call_next(request)
    except Exception as exc:
        # 尝试获取已生成的 request_id，否则重新生成
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        # 仅 debug 模式输出完整 traceback
        if settings.debug:
            traceback.print_exc()

        # 根据异常类型确定状态码和错误码
        if isinstance(exc, ValueError):
            status_code = 400
            error_code = "VALIDATION_ERROR"
        else:
            status_code = 500
            error_code = "UNKNOWN_ERROR"

        message = f"服务内部异常: {str(exc)}" if settings.debug else "服务内部异常，请稍后重试"

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": error_code,
                    "message": message,
                },
                "request_id": request_id,
            },
        )


# ---- FastAPI 级异常处理器（补充） ----

def _register_fastapi_handlers(app: FastAPI) -> None:
    """注册 FastAPI 级异常处理器，处理中间件无法覆盖的特定场景。"""

    @app.exception_handler(ValueError)
    async def validation_handler(request: Request, exc: ValueError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "data": None,
                "error": {"code": "VALIDATION_ERROR", "message": str(exc)},
                "request_id": request_id,
            },
        )
