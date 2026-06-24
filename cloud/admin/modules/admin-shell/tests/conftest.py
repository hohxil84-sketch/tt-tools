"""
admin-shell 测试夹具。

提供测试用 FastAPI 应用和异步 HTTP 客户端。
使用依赖覆盖（dependency_overrides）隔离测试 admin-shell 端点，
不依赖 auth-device 的完整登录流程。

admin-shell 模块目录加入 sys.path，对齐 cloud/app-shell/main.py 的导入方式。
"""
from __future__ import annotations

import sys
import os

# 将项目根目录加入 sys.path，使 cloud.shared.* 可导入
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 将 admin-shell 模块目录加入 sys.path（目录含连字符，需直接导入）
_ADMIN_SHELL_DIR = os.path.join(
    _PROJECT_ROOT, "cloud", "admin", "modules", "admin-shell"
)
# 清理可能冲突的模块缓存（避免与其他模块的 router/service/schemas 冲突）
for _key in list(sys.modules.keys()):
    if _key in ("router", "service", "schemas") or _key.startswith("router."):
        del sys.modules[_key]
if _ADMIN_SHELL_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_SHELL_DIR)

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, HTTPException

from cloud.shared import (
    TokenData,
    require_admin,
    ErrorCode,
)

# 直接从 admin-shell 模块目录导入（已在 sys.path 中）
from router import router as admin_router  # noqa: E402


# ============================================================
# 测试用户身份
# ============================================================

# 模拟管理员身份
ADMIN_TOKEN_DATA = TokenData(
    user_id="admin-uuid-001",
    device_id="admin-device-001",
    role="admin",
    plan_code="pro",
)

# 模拟普通用户身份
USER_TOKEN_DATA = TokenData(
    user_id="user-uuid-001",
    device_id="user-device-001",
    role="user",
    plan_code="free",
)


# ============================================================
# 依赖覆盖函数
# ============================================================


async def _override_admin() -> TokenData:
    """覆盖 require_admin：返回管理员身份。"""
    return ADMIN_TOKEN_DATA


async def _override_user_forbidden() -> TokenData:
    """覆盖 require_admin：模拟普通用户被拒绝（403）。

    require_admin 依赖检测到 role != "admin" 时会抛出 HTTPException(403)。
    本函数直接模拟该行为，不返回 TokenData。
    """
    raise HTTPException(
        status_code=403,
        detail={
            "code": "PERMISSION_DENIED",
            "message": "需要管理员权限",
        },
    )


# ============================================================
# 测试夹具
# ============================================================


@pytest_asyncio.fixture
def app():
    """创建带 admin-shell 路由的 FastAPI 测试应用。

    覆盖 require_admin 依赖为管理员身份（默认）。
    """
    app = FastAPI(debug=False)

    # 模拟 cloud-app-shell 中间件的 request_id 注入
    @app.middleware("http")
    async def _inject_request_id(request, call_next):
        import uuid

        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    # 注册 admin-shell 路由
    app.include_router(admin_router, prefix="/api/v1")

    return app


@pytest_asyncio.fixture
async def admin_client(app: FastAPI) -> AsyncClient:
    """创建异步 HTTP 测试客户端（默认管理员权限）。"""
    # 覆盖 require_admin → 返回管理员身份
    app.dependency_overrides[require_admin] = _override_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # 清理覆盖
    app.dependency_overrides.pop(require_admin, None)


@pytest_asyncio.fixture
async def user_client(app: FastAPI) -> AsyncClient:
    """创建异步 HTTP 测试客户端（普通用户权限 → 预期 403）。"""
    # 覆盖 require_admin → 模拟普通用户被拒绝
    app.dependency_overrides[require_admin] = _override_user_forbidden

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # 清理覆盖
    app.dependency_overrides.pop(require_admin, None)


@pytest_asyncio.fixture
async def no_auth_client(app: FastAPI) -> AsyncClient:
    """创建异步 HTTP 测试客户端（无鉴权 → 预期 401）。

    不覆盖 require_admin，让原始的 OAuth2PasswordBearer 依赖生效，
    由于没有 token，oauth2_scheme 返回 None，require_auth 抛出 401。
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
