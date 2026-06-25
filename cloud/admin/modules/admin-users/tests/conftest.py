"""
admin-users 测试夹具。

提供测试用 FastAPI 应用、异步 HTTP 客户端、以及 SQLite 内存数据库。
测试数据库通过 SQLAlchemy aiosqlite 实现，无需外部 PostgreSQL。

测试路径覆盖：
- admin_client：管理员权限 → 预期 200
- user_client：普通用户权限 → 预期 403
- no_auth_client：无鉴权 → 预期 401
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

# 将 admin-users 模块目录加入 sys.path（目录含连字符，需直接导入）
_ADMIN_USERS_DIR = os.path.join(
    _PROJECT_ROOT, "cloud", "admin", "modules", "admin-users"
)
# 清理可能冲突的模块缓存
for _key in list(sys.modules.keys()):
    if _key in ("router", "service", "schemas", "models") or _key.startswith(
        ("router.", "service.", "schemas.", "models.")
    ):
        del sys.modules[_key]
if _ADMIN_USERS_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_USERS_DIR)

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, HTTPException
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from cloud.shared import (
    TokenData,
    require_admin,
    get_db,
    Base,
)

# 在注册 models 中的 ORM 模型后才创建表
# models 的导入必须在 Base.metadata.create_all 之前完成
from models import UserAdmin, DeviceAdmin  # noqa: E402

# 直接从 admin-users 模块目录导入路由
from router import router as admin_users_router  # noqa: E402


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
    """覆盖 require_admin：模拟普通用户被拒绝（403）。"""
    raise HTTPException(
        status_code=403,
        detail={
            "code": "PERMISSION_DENIED",
            "message": "需要管理员权限",
        },
    )


# ============================================================
# 测试数据库引擎（模块级别，共享连接池）
# ============================================================


@pytest.fixture(scope="session")
def db_engine():
    """创建测试数据库引擎（SQLite 内存，session 级别共享）。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    return engine


@pytest.fixture(scope="session")
def _db_session_factory(db_engine):
    """创建异步会话工厂（session 级别）。"""
    return async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# ============================================================
# 测试表初始化和数据填充
# ============================================================


async def _reset_database(engine):
    """重置数据库：先删除所有表，再重新创建，确保测试隔离。"""
    async with engine.begin() as conn:
        # 先删除所有表（CASCADE 确保依赖关系正确）
        await conn.run_sync(Base.metadata.drop_all)
        # 再重新创建
        await conn.run_sync(Base.metadata.create_all)


async def _seed_test_data(session_factory) -> None:
    """填充测试数据：3 个用户，每个用户 1-2 台设备。"""
    import uuid
    from datetime import datetime, timezone

    def _now():
        return datetime.now(timezone.utc).replace(tzinfo=None)

    async with session_factory() as session:
        # 用户 1：正常活跃用户
        user1 = UserAdmin(
            id="user-001",
            account="alice@example.com",
            password_hash="hash1",
            display_name="Alice",
            role="user",
            status="active",
            plan_code="standard",
            created_at=_now(),
            updated_at=_now(),
        )
        # 用户 2：被封禁用户
        user2 = UserAdmin(
            id="user-002",
            account="bob@example.com",
            password_hash="hash2",
            display_name="Bob",
            role="user",
            status="blocked",
            plan_code="free",
            created_at=_now(),
            updated_at=_now(),
        )
        # 用户 3：管理员
        user3 = UserAdmin(
            id="admin-001",
            account="admin@tt-tools.com",
            password_hash="hash3",
            display_name="管理员",
            role="admin",
            status="active",
            plan_code="pro",
            created_at=_now(),
            updated_at=_now(),
        )
        session.add_all([user1, user2, user3])

        # 设备数据
        device1 = DeviceAdmin(
            id="device-001",
            user_id="user-001",
            device_fingerprint_hash="fp_hash_1",
            device_name="Alice-PC",
            client_version="0.1.0",
            status="active",
            bound_at=_now(),
            last_seen_at=_now(),
            created_at=_now(),
            updated_at=_now(),
        )
        device2 = DeviceAdmin(
            id="device-002",
            user_id="user-001",
            device_fingerprint_hash="fp_hash_2",
            device_name="Alice-Laptop",
            client_version="0.1.0",
            status="active",
            bound_at=_now(),
            last_seen_at=_now(),
            created_at=_now(),
            updated_at=_now(),
        )
        device3 = DeviceAdmin(
            id="device-003",
            user_id="user-002",
            device_fingerprint_hash="fp_hash_3",
            device_name="Bob-PC",
            client_version="0.1.0",
            status="blocked",
            bound_at=_now(),
            last_seen_at=_now(),
            created_at=_now(),
            updated_at=_now(),
        )
        # 用户 3（管理员）没有设备
        session.add_all([device1, device2, device3])
        await session.commit()


# ============================================================
# 测试 FastAPI 应用
# ============================================================


@pytest_asyncio.fixture
async def app(db_engine, _db_session_factory):
    """创建带 admin-users 路由和数据库的 FastAPI 测试应用。

    每次测试前重建表结构和种子数据，确保测试隔离。
    """
    # 重置数据库（删除旧表 → 重建新表 → 填充种子数据）
    await _reset_database(db_engine)
    # 填充测试数据
    await _seed_test_data(_db_session_factory)

    app = FastAPI(debug=False)

    # 模拟 cloud-app-shell 中间件的 request_id 注入
    @app.middleware("http")
    async def _inject_request_id(request, call_next):
        import uuid

        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    # 注册 admin-users 路由
    app.include_router(admin_users_router, prefix="/api/v1")

    # 覆盖 get_db → 使用测试数据库会话
    async def _override_get_db():
        async with _db_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _override_get_db

    return app


# ============================================================
# 测试客户端
# ============================================================


@pytest_asyncio.fixture
async def admin_client(app: FastAPI) -> AsyncClient:
    """创建异步 HTTP 测试客户端（管理员权限）。"""
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
    app.dependency_overrides[require_admin] = _override_user_forbidden

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.pop(require_admin, None)


@pytest_asyncio.fixture
async def no_auth_client(app: FastAPI) -> AsyncClient:
    """创建异步 HTTP 测试客户端（无鉴权 → 预期 401）。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
