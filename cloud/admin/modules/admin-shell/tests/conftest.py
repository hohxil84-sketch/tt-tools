"""
admin-shell test fixtures.

Creates test FastAPI app with dependency overrides to isolate admin-shell endpoints
without requiring a real database or full auth-device login flow.

The get_db dependency is overridden to return None, which causes
get_dashboard_stats to return placeholder values (0 for all stats).
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
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, HTTPException

from cloud.shared import (
    TokenData,
    require_admin,
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
    """Override require_admin: return admin identity."""
    return ADMIN_TOKEN_DATA


async def _override_user_forbidden() -> TokenData:
    """Override require_admin: simulate normal user rejected (403)."""
    raise HTTPException(
        status_code=403,
        detail={
            "code": "PERMISSION_DENIED",
            "message": "需要管理员权限",
        },
    )


async def _override_db_none():
    """Override get_db: return None so dashboard uses placeholder values."""
    return None


# ============================================================
# Test fixtures
# ============================================================


@pytest_asyncio.fixture
def app():
    """Create FastAPI test app with admin-shell routes.

    Overrides both require_admin (-> admin) and get_db (-> None).
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

    # Register admin-shell routes
    app.include_router(admin_router, prefix="/api/v1")

    return app


@pytest_asyncio.fixture
async def admin_client(app: FastAPI) -> AsyncClient:
    """Async HTTP test client (admin privileges)."""
    app.dependency_overrides[require_admin] = _override_admin
    app.dependency_overrides[get_db] = _override_db_none

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def user_client(app: FastAPI) -> AsyncClient:
    """Async HTTP test client (normal user -> expected 403)."""
    app.dependency_overrides[require_admin] = _override_user_forbidden
    app.dependency_overrides[get_db] = _override_db_none

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def no_auth_client(app: FastAPI) -> AsyncClient:
    """Async HTTP test client (no auth -> expected 401).

    No dependency override for require_admin — the original OAuth2PasswordBearer
    dependency fires, sees no token, and require_auth raises 401.
    """
    app.dependency_overrides[get_db] = _override_db_none

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
