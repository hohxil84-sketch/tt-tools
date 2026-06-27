"""
admin-shell test fixtures.

Creates test FastAPI app with dependency overrides to isolate admin-shell endpoints
without requiring a real database or full auth-device login flow.

对 require_auth 做依赖覆盖（require_permission 内部通过 Depends(require_auth) 链式调用），
对 get_db 提供 MagicMock 以支持 RBAC 权限表的 SQL 查询。
"""
from __future__ import annotations

import sys
import os

# Add project root to sys.path so cloud.shared.* is importable
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Add admin-shell module directory to sys.path (directory name has hyphens)
_ADMIN_SHELL_DIR = os.path.join(
    _PROJECT_ROOT, "cloud", "admin", "modules", "admin-shell"
)
# Clear conflicting module caches to avoid cross-module router/service/schemas conflicts
for _key in list(sys.modules.keys()):
    if _key in ("router", "service", "schemas") or _key.startswith("router."):
        del sys.modules[_key]
if _ADMIN_SHELL_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_SHELL_DIR)

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, HTTPException

from cloud.shared import (
    TokenData,
    require_auth,
    ErrorCode,
)

# Import from admin-shell module directory (already in sys.path)
from router import router as admin_router  # noqa: E402
from cloud.shared.database import get_db  # noqa: E402


# ============================================================
# Test user identities
# ============================================================

# Simulated admin identity
ADMIN_TOKEN_DATA = TokenData(
    user_id="admin-uuid-001",
    device_id="admin-device-001",
    role="admin",
    plan_code="pro",
)

# Simulated normal user identity
USER_TOKEN_DATA = TokenData(
    user_id="user-uuid-001",
    device_id="user-device-001",
    role="user",
    plan_code="free",
)


# ============================================================
# Dependency override functions
# ============================================================

async def _override_admin() -> TokenData:
    """Override require_auth: return admin identity."""
    return ADMIN_TOKEN_DATA


async def _override_user() -> TokenData:
    """Override require_auth: return normal user identity (will be rejected by require_permission)."""
    return USER_TOKEN_DATA


def _make_mock_db() -> MagicMock:
    """创建一个模拟的数据库会话，支持 RBAC 权限查询。

    require_permission 内部执行两条 SQL：
    1. SELECT COUNT(*) FROM user_roles WHERE user_id = :uid
    2. SELECT 1 FROM user_roles ... JOIN permissions ... WHERE p.code = :pcode

    返回空结果（count=0），触发 admin 向后兼容放行。
    """
    mock_db = MagicMock()

    async def mock_execute(query, params=None):
        mock_result = MagicMock()
        sql_str = str(query)

        if "COUNT(*)" in sql_str and "user_roles" in sql_str:
            # RBAC 角色计数查询 → 返回 0（无 RBAC 记录，admin 向后兼容）
            mock_result.scalar_one.return_value = 0
        elif "SELECT 1 FROM user_roles" in sql_str:
            # RBAC 权限检查 → 返回空（无匹配权限）
            mock_result.first.return_value = None
        elif "SELECT DISTINCT p.code FROM user_roles" in sql_str or "SELECT code FROM permissions" in sql_str:
            # get_user_permissions → 返回空权限列表（admin 向后兼容）
            mock_result.all.return_value = []
        elif "SELECT role" in sql_str and "COUNT(*)" in sql_str and "user_roles" in sql_str:
            # get_user_permissions 中的角色计数查询 → 返回空
            mock_result.first.return_value = None
        elif "SELECT role FROM users WHERE id" in sql_str:
            # get_user_permissions 中的 users 表查询 → 返回 admin
            mock_row = MagicMock()
            mock_row.__getitem__ = lambda s, i: "admin" if i == 0 else None
            mock_result.first.return_value = ("admin",)
        elif "SELECT COUNT(*) FROM users" in sql_str:
            # 仪表盘统计 → 返回 0
            mock_result.scalar_one.return_value = 0
        elif "SELECT COUNT(*)" in sql_str and "orders" in sql_str:
            # 仪表盘订单统计 → 返回 (0, 0)
            mock_result.one.return_value = (0, 0)
        elif "SELECT COUNT(*) FROM devices" in sql_str:
            # 仪表盘设备统计 → 返回 0
            mock_result.scalar_one.return_value = 0
        else:
            # 其他查询 → 返回空
            mock_result.scalar_one.return_value = 0
            mock_result.first.return_value = None
            mock_result.scalars.return_value.all.return_value = []
            mock_result.all.return_value = []
            mock_result.one.return_value = (0, 0)

        return mock_result

    mock_db.execute = mock_execute
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_db.close = AsyncMock()

    return mock_db


async def _override_db_mock():
    """Override get_db: 返回 Mock 数据库会话（支持 RBAC 查询）。"""
    return _make_mock_db()


# ============================================================
# Test fixtures
# ============================================================

@pytest_asyncio.fixture
def app():
    """Create FastAPI test app with admin-shell routes.

    Overrides both require_auth (-> admin) and get_db (-> mock).
    """
    app = FastAPI(debug=False)

    # Simulate cloud-app-shell middleware for request_id injection
    @app.middleware("http")
    async def _inject_request_id(request, call_next):
        import uuid

        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    # Register admin-shell routes（prefix 对齐 main.py 中的 /api/v1/admin）
    app.include_router(admin_router, prefix="/api/v1/admin")

    return app


@pytest_asyncio.fixture
async def admin_client(app: FastAPI) -> AsyncClient:
    """Async HTTP test client (admin privileges)."""
    # 覆盖 require_auth（require_permission 通过 Depends(require_auth) 链式调用）
    app.dependency_overrides[require_auth] = _override_admin
    # 覆盖 get_db（require_permission 内部查询 RBAC 表）
    app.dependency_overrides[get_db] = _override_db_mock

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.pop(require_auth, None)
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def user_client(app: FastAPI) -> AsyncClient:
    """Async HTTP test client (normal user -> expected 403).

    require_auth 返回普通用户身份，require_permission 检查 role != admin 直接返回 403。
    """
    app.dependency_overrides[require_auth] = _override_user
    app.dependency_overrides[get_db] = _override_db_mock

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.pop(require_auth, None)
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def no_auth_client(app: FastAPI) -> AsyncClient:
    """Async HTTP test client (no auth -> expected 401).

    No dependency override for require_auth — the original OAuth2PasswordBearer
    dependency fires, sees no token, and require_auth raises 401.
    """
    app.dependency_overrides[get_db] = _override_db_mock

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
