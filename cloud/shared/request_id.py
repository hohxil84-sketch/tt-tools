"""
cloud-shared request_id 依赖模块。

提供 FastAPI 依赖函数，从 request.state 提取由 cloud-app-shell 中间件注入的
X-Request-ID，供业务模块直接使用。
"""
from __future__ import annotations

from fastapi import Request


def get_request_id(request: Request) -> str:
    """FastAPI 依赖：获取当前请求的追踪 ID。

    该 ID 由 cloud-app-shell 的 _request_id_dispatch 中间件注入到
    request.state.request_id。如果没有（极少情况），生成一个应急值。

    使用示例：
        @router.get("/something")
        async def handler(request_id: str = Depends(get_request_id)):
            ...
    """
    rid = getattr(request.state, "request_id", None)
    if rid is None:
        # 极端兜底：中间件未执行时
        import uuid
        rid = str(uuid.uuid4())
        request.state.request_id = rid
    return rid
