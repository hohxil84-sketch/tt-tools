"""
cloud-shared request_id 依赖模块测试。

验证：get_request_id 依赖从 request.state 正确提取 request_id。
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, Depends
from httpx import AsyncClient, ASGITransport

from cloud.shared.request_id import get_request_id


# -- 测试路由 --
from fastapi import APIRouter

_rid_router = APIRouter()


@_rid_router.get("/my-request-id")
async def my_request_id(rid: str = Depends(get_request_id)) -> dict:
    """返回当前请求的 request_id。"""
    return {"request_id": rid}


@pytest.fixture
def rid_app() -> FastAPI:
    """创建带 request_id 注入中间件和测试路由的 FastAPI 应用。"""
    app = FastAPI(debug=False)

    # 模拟 cloud-app-shell 中间件
    @app.middleware("http")
    async def _inject_request_id(request, call_next):
        import uuid
        request.state.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    app.include_router(_rid_router)
    return app


import pytest_asyncio


@pytest_asyncio.fixture
async def rid_client(rid_app: FastAPI) -> AsyncClient:
    """创建异步测试客户端。"""
    transport = ASGITransport(app=rid_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestGetRequestId:
    """get_request_id 依赖测试。"""

    @pytest.mark.asyncio
    async def test_returns_middleware_injected_id(self, rid_client: AsyncClient) -> None:
        """get_request_id 应返回中间件注入的 request_id。"""
        response = await rid_client.get("/my-request-id")
        assert response.status_code == 200
        body = response.json()
        assert "request_id" in body
        assert len(body["request_id"]) == 36  # UUID 格式
        assert body["request_id"].count("-") == 4

    @pytest.mark.asyncio
    async def test_preserves_custom_request_id(self, rid_client: AsyncClient) -> None:
        """自定义 X-Request-ID 应被保留。"""
        custom_id = "custom-req-id-12345"
        response = await rid_client.get(
            "/my-request-id", headers={"X-Request-ID": custom_id}
        )
        body = response.json()
        assert body["request_id"] == custom_id

    @pytest.mark.asyncio
    async def test_fallback_when_no_middleware(self) -> None:
        """极端情况：中间件未注入 request_id 时，依赖应生成兜底值。"""
        app = FastAPI(debug=False)

        @app.get("/no-middleware")
        async def handler(rid: str = Depends(get_request_id)):
            return {"request_id": rid}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/no-middleware")
            body = response.json()
            assert len(body["request_id"]) == 36  # 兜底生成的 UUID
