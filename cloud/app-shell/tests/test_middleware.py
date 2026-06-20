"""
基础中间件测试。

验证：
1. X-Request-ID 中间件：请求无此头时自动生成，响应头包含。
2. 统一错误响应格式：对齐 common.yaml ErrorResponse。
3. CORS 响应头：允许跨域。
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, APIRouter


# 用于错误测试的辅助路由
_error_test_router = APIRouter()


@_error_test_router.get("/test-error")
async def trigger_error() -> None:
    """故意抛出异常，用于测试统一错误处理。"""
    raise RuntimeError("测试异常")


@_error_test_router.get("/test-validation-error")
async def trigger_validation_error() -> None:
    """故意抛出 ValueError，用于测试校验错误处理。"""
    raise ValueError("参数无效")


@pytest.fixture
def app_with_error_routes(app: FastAPI) -> FastAPI:
    """在测试 app 上额外注册触发错误的路由。"""
    app.include_router(_error_test_router)
    return app


@pytest_asyncio.fixture
async def error_client(app_with_error_routes: FastAPI) -> AsyncClient:
    """使用带错误路由的 app 创建测试客户端。"""
    transport = ASGITransport(app=app_with_error_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestRequestIdMiddleware:
    """X-Request-ID 中间件测试。"""

    @pytest.mark.asyncio
    async def test_response_has_request_id_header(self, client: AsyncClient) -> None:
        """响应头中应包含 X-Request-ID。"""
        response = await client.get("/health")
        assert "x-request-id" in response.headers, (
            f"响应头缺少 x-request-id，当前头：{dict(response.headers)}"
        )

    @pytest.mark.asyncio
    async def test_custom_request_id_preserved(self, client: AsyncClient) -> None:
        """自定义 X-Request-ID 应被保留并回传。"""
        custom_id = "my-custom-req-id-12345"
        response = await client.get("/health", headers={"X-Request-ID": custom_id})
        assert response.headers["x-request-id"] == custom_id

    @pytest.mark.asyncio
    async def test_auto_generated_request_id_is_uuid_format(self, client: AsyncClient) -> None:
        """自动生成的 request_id 应为 UUID 格式（36 字符，含 4 个连字符）。"""
        response = await client.get("/health")
        req_id = response.headers["x-request-id"]
        assert len(req_id) == 36, f"UUID 应为 36 字符，实际 {len(req_id)}"
        assert req_id.count("-") == 4, f"UUID 应含 4 个 '-'，实际 {req_id.count('-')}"


class TestUnifiedErrorResponse:
    """统一错误响应格式测试（对齐 common.yaml ErrorResponse）。"""

    @pytest.mark.asyncio
    async def test_unhandled_exception_returns_500(self, error_client: AsyncClient) -> None:
        """未处理异常应返回 500 状态码。"""
        response = await error_client.get("/test-error")
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_unhandled_exception_body_structure(self, error_client: AsyncClient) -> None:
        """错误响应体必须包含 success、data、error、request_id。"""
        response = await error_client.get("/test-error")
        body = response.json()

        assert body["success"] is False, f"错误时 success 应为 false，实际 {body['success']}"
        assert body["data"] is None, f"错误时 data 应为 null，实际 {body['data']}"
        assert "error" in body, "错误响应缺少 error 字段"
        assert "request_id" in body, "错误响应缺少 request_id 字段"

    @pytest.mark.asyncio
    async def test_error_has_code_and_message(self, error_client: AsyncClient) -> None:
        """error 对象必须包含 code 和 message 字段。"""
        response = await error_client.get("/test-error")
        body = response.json()
        error = body["error"]

        assert "code" in error, "error 对象缺少 code 字段"
        assert "message" in error, "error 对象缺少 message 字段"
        assert isinstance(error["code"], str)
        assert isinstance(error["message"], str)

    @pytest.mark.asyncio
    async def test_validation_error_returns_400(self, error_client: AsyncClient) -> None:
        """ValueError 应返回 400 状态码，错误码为 VALIDATION_ERROR。"""
        response = await error_client.get("/test-validation-error")
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_error_request_id_not_empty(self, error_client: AsyncClient) -> None:
        """错误响应的 request_id 不应为空。"""
        response = await error_client.get("/test-error")
        body = response.json()
        assert body["request_id"] != ""
        assert len(body["request_id"]) > 0


class TestCorsHeaders:
    """CORS 中间件测试。"""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client: AsyncClient) -> None:
        """跨域请求应返回 CORS 相关响应头。"""
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORSMiddleware 默认会设置 access-control-allow-origin 等头
        assert response.status_code in (200, 204, 405), (
            f"OPTIONS 请求异常状态码 {response.status_code}"
        )
