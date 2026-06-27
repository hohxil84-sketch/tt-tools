"""
cloud-shared 鉴权依赖模块测试。

验证：JWT 签发/校验、TokenData 模型、require_auth / require_admin / optional_auth 依赖。
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI, Depends, APIRouter
from httpx import AsyncClient, ASGITransport

from cloud.shared.auth import (
    TokenData,
    create_access_token,
    decode_token,
    require_auth,
    require_admin,
    optional_auth,
)
from cloud.shared.config import shared_settings
from cloud.shared.errors import ErrorCode

# -- 测试路由 --
_auth_router = APIRouter()


@_auth_router.get("/me")
async def get_me(user: TokenData = Depends(require_auth)) -> dict:
    """需登录：返回当前用户信息。"""
    return {
        "user_id": user.user_id,
        "role": user.role,
        "plan_id": user.plan_id,
    }


@_auth_router.get("/admin-only")
async def admin_endpoint(user: TokenData = Depends(require_admin)) -> dict:
    """管理员专用。"""
    return {"admin": True, "user_id": user.user_id}


@_auth_router.get("/optional")
async def optional_endpoint(user: TokenData | None = Depends(optional_auth)) -> dict:
    """可选登录。"""
    return {"logged_in": user is not None, "user_id": user.user_id if user else None}


@pytest.fixture
def auth_app() -> FastAPI:
    """创建带鉴权依赖和测试路由的 FastAPI 应用。"""
    app = FastAPI(debug=False)

    # 注入 request_id 模拟中间件
    @app.middleware("http")
    async def _inject_request_id(request, call_next):
        import uuid
        request.state.request_id = str(uuid.uuid4())
        return await call_next(request)

    app.include_router(_auth_router)
    return app


@pytest_asyncio.fixture
async def auth_client(auth_app: FastAPI) -> AsyncClient:
    """创建异步测试客户端。"""
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ============================================================
# TokenData
# ============================================================

class TestTokenData:
    """TokenData 模型测试。"""

    def test_create_minimal(self) -> None:
        """最简 TokenData（仅 user_id 必填）。"""
        td = TokenData(user_id="uuid-001")
        assert td.user_id == "uuid-001"
        assert td.device_id is None
        assert td.role == "user"
        assert td.plan_id is None

    def test_create_full(self) -> None:
        """完整 TokenData。"""
        td = TokenData(
            user_id="uuid-002",
            device_id="dev-001",
            role="admin",
            plan_id="plan-pro",
        )
        assert td.device_id == "dev-001"
        assert td.role == "admin"
        assert td.plan_id == "plan-pro"


# ============================================================
# JWT 工具函数
# ============================================================

class TestJwtCreateAndDecode:
    """JWT 签发和校验端到端测试。"""

    def test_create_and_decode_access_token(self) -> None:
        """签发 token 后解码，应返回一致的 TokenData。"""
        token = create_access_token(
            user_id="user-abc",
            device_id="dev-xyz",
            role="user",
            plan_id="plan-standard",
        )
        data = decode_token(token)
        assert data.user_id == "user-abc"
        assert data.device_id == "dev-xyz"
        assert data.role == "user"
        assert data.plan_id == "plan-standard"

    def test_token_is_string(self) -> None:
        """签发的 token 应为字符串。"""
        token = create_access_token(user_id="u1")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_invalid_token_raises(self) -> None:
        """解码无效 token 应抛出异常。"""
        from jose import JWTError as JoseJWTError
        with pytest.raises(JoseJWTError):
            decode_token("invalid-token-string")

    def test_create_token_with_defaults(self) -> None:
        """默认 role 和 plan_id 应为 user / None。"""
        token = create_access_token(user_id="u-default")
        data = decode_token(token)
        assert data.role == "user"
        assert data.plan_id is None
        assert data.device_id is None


# ============================================================
# FastAPI 鉴权依赖
# ============================================================

class TestRequireAuth:
    """require_auth 依赖测试。"""

    @pytest.mark.asyncio
    async def test_no_token_returns_401(self, auth_client: AsyncClient) -> None:
        """无 token 时应返回 401。"""
        response = await auth_client.get("/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, auth_client: AsyncClient) -> None:
        """无效 token 应返回 401。"""
        response = await auth_client.get(
            "/me", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_info(self, auth_client: AsyncClient) -> None:
        """有效 token 应返回用户信息。"""
        token = create_access_token(
            user_id="test-user-id",
            role="user",
            plan_id="plan-standard",
        )
        response = await auth_client.get(
            "/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == "test-user-id"
        assert body["role"] == "user"
        assert body["plan_id"] == "plan-standard"


class TestRequireAdmin:
    """require_admin 依赖测试。"""

    @pytest.mark.asyncio
    async def test_user_role_returns_403(self, auth_client: AsyncClient) -> None:
        """普通用户访问管理员接口应返回 403。"""
        token = create_access_token(user_id="user-001", role="user")
        response = await auth_client.get(
            "/admin-only", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_role_returns_200(self, auth_client: AsyncClient) -> None:
        """管理员访问管理员接口应返回 200。"""
        token = create_access_token(user_id="admin-001", role="admin")
        response = await auth_client.get(
            "/admin-only", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["admin"] is True


class TestOptionalAuth:
    """optional_auth 依赖测试。"""

    @pytest.mark.asyncio
    async def test_no_token_returns_none(self, auth_client: AsyncClient) -> None:
        """无 token 时 logged_in=False。"""
        response = await auth_client.get("/optional")
        assert response.status_code == 200
        body = response.json()
        assert body["logged_in"] is False
        assert body["user_id"] is None

    @pytest.mark.asyncio
    async def test_with_token_returns_user(self, auth_client: AsyncClient) -> None:
        """有 token 时 logged_in=True，返回 user_id。"""
        token = create_access_token(user_id="opt-user")
        response = await auth_client.get(
            "/optional", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["logged_in"] is True
        assert body["user_id"] == "opt-user"

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self, auth_client: AsyncClient) -> None:
        """无效 token 时 logged_in=False（不抛异常）。"""
        response = await auth_client.get(
            "/optional", headers={"Authorization": "Bearer bad_token"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["logged_in"] is False
