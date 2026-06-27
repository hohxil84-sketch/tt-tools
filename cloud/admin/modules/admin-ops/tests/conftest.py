"""
admin-ops 测试夹具。

提供测试用 FastAPI 应用、异步 HTTP 客户端、以及 SQLite 内存数据库。
测试数据库通过 SQLAlchemy aiosqlite 实现，无需外部 PostgreSQL。

跨模块模型预加载：
在导入 admin-ops 路由之前，将 provider-log、credits-billing 和
admin-users 的 ORM 模型预加载到 sys.modules 的别名键下。
service.py 通过 _load_module_models() 惰性加载这些模型。

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

# 将 admin-ops 模块目录加入 sys.path
_ADMIN_OPS_DIR = os.path.join(
    _PROJECT_ROOT, "cloud", "admin", "modules", "admin-ops"
)
for _key in list(sys.modules.keys()):
    if _key in ("router", "service", "schemas", "models") or _key.startswith(
        ("router.", "service.", "schemas.", "models.")
    ):
        del sys.modules[_key]
if _ADMIN_OPS_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_OPS_DIR)

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
    require_auth,
    get_db,
    Base,
)

# ============================================================
# 跨模块模型预加载
# ============================================================

import importlib.util as _iu


def _load_module_file(module_path_parts, alias, dir_name):
    """通过 importlib 加载跨模块模型文件。

    加载前后会保存和恢复 sys.modules 和 sys.path，
    避免与 admin-ops 的 models/schemas/service/router 模块冲突。
    """
    file_path = os.path.join(_PROJECT_ROOT, *module_path_parts)
    dir_path = os.path.join(_PROJECT_ROOT, *module_path_parts[:-1])

    _saved = {}
    for _k in ("models", "service", "schemas", "router"):
        if _k in sys.modules:
            _saved[_k] = sys.modules.pop(_k)

    _orig_path = list(sys.path)
    if dir_path in sys.path:
        sys.path.remove(dir_path)
    sys.path.insert(0, dir_path)

    try:
        spec = _iu.spec_from_file_location(alias, file_path)
        mod = _iu.module_from_spec(spec)
        sys.modules[alias] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        for _k in ("models", "service", "schemas", "router"):
            sys.modules.pop(_k, None)
        for _k, _v in _saved.items():
            sys.modules[_k] = _v
        sys.path.clear()
        sys.path.extend(_orig_path)


# 1. 加载 provider-log 模型（ProviderCallLog）
_pl_mod = _load_module_file(
    ["cloud", "modules", "provider-log", "models.py"],
    "provider_log_models",
    "provider-log",
)

# 2. 加载 credits-billing 模型（Plan）
_cb_mod = _load_module_file(
    ["cloud", "modules", "credits-billing", "models.py"],
    "credits_billing_models",
    "credits-billing",
)

# 3. 加载 admin-users 模型（User）
_au_mod = _load_module_file(
    ["cloud", "admin", "modules", "admin-users", "models.py"],
    "admin_users_models",
    "admin-users",
)

# 3.5 加载 admin-roles 模型（require_permission 需要 user_roles 表）
_ar_mod = _load_module_file(
    ["cloud", "admin", "modules", "admin-roles", "models.py"],
    "admin_roles_models",
    "admin-roles",
)

# 4. 清理模块缓存，确保 admin-ops 的 router/service/schemas/models 重新导入
for _key in list(sys.modules.keys()):
    if _key in ("router", "service", "schemas", "models") or _key.startswith(
        ("router.", "service.", "schemas.", "models.")
    ):
        del sys.modules[_key]

# 获取模型类的引用（用于种子数据）
ProviderCallLog = _pl_mod.ProviderCallLog
Plan = _cb_mod.Plan
User = _au_mod.UserAdmin

# 导入 admin-ops 路由和 RiskLog 模型
from models import RiskLog  # noqa: E402
from router import router as admin_ops_router  # noqa: E402


# ============================================================
# 测试用户身份
# ============================================================

ADMIN_TOKEN_DATA = TokenData(
    user_id="admin-uuid-001",
    device_id="admin-device-001",
    role="admin",
    plan_code="pro",
)

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
    """覆盖 require_auth：返回管理员身份。"""
    return ADMIN_TOKEN_DATA


async def _override_user() -> TokenData:
    """覆盖 require_auth：返回普通用户身份。

    require_permission 会检查 role != admin，自动返回 403。
    """
    return USER_TOKEN_DATA


# ============================================================
# 测试数据库引擎
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
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def _seed_test_data(session_factory) -> None:
    """填充测试数据：用户、套餐、Provider 调用日志、风控日志。"""
    from datetime import datetime, timezone

    def _now():
        return datetime.now(timezone.utc).replace(tzinfo=None)

    async with session_factory() as session:
        # === 用户数据 ===
        user1 = User(
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
        user2 = User(
            id="user-002",
            account="bob@example.com",
            password_hash="hash2",
            display_name="Bob",
            role="user",
            status="active",
            plan_code="free",
            created_at=_now(),
            updated_at=_now(),
        )
        user3 = User(
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

        # === 套餐数据 ===
        plan_free = Plan(
            id="plan-free",
            code="free",
            name="免费套餐",
            monthly_grant=10,
            enabled_features_json={
                "resize_image_local_paid": {"daily_limit": 3},
            },
            status="active",
            created_at=_now(),
            updated_at=_now(),
        )
        plan_standard = Plan(
            id="plan-standard",
            code="standard",
            name="标准套餐",
            monthly_grant=500,
            enabled_features_json={
                "ai_copy_cloud": True,
            },
            status="active",
            created_at=_now(),
            updated_at=_now(),
        )
        plan_pro = Plan(
            id="plan-pro",
            code="pro",
            name="专业套餐",
            monthly_grant=2000,
            enabled_features_json={
                "ai_copy_cloud": True,
                "ai_render_cloud": True,
            },
            status="active",
            created_at=_now(),
            updated_at=_now(),
        )
        session.add_all([plan_free, plan_standard, plan_pro])

        # === Provider 调用日志数据 ===
        pcl1 = ProviderCallLog(
            id="pcl-001",
            request_id="req-001",
            user_id="user-001",
            feature="ai_copy_cloud",
            provider="deepseek",
            model="deepseek-chat",
            status="success",
            input_tokens=100,
            output_tokens=80,
            total_tokens=180,
            estimated_cost=0.001,
            credits_charged=1,
            latency_ms=1200,
            created_at=_now(),
        )
        pcl2 = ProviderCallLog(
            id="pcl-002",
            request_id="req-002",
            user_id="user-001",
            feature="ai_render_cloud",
            provider="openai",
            model="gpt-4o",
            status="success",
            input_tokens=200,
            output_tokens=150,
            total_tokens=350,
            estimated_cost=0.003,
            credits_charged=3,
            latency_ms=3000,
            created_at=_now(),
        )
        pcl3 = ProviderCallLog(
            id="pcl-003",
            request_id="req-003",
            user_id="user-002",
            feature="ai_copy_cloud",
            provider="deepseek",
            model="deepseek-chat",
            status="failed",
            error_code="PROVIDER_TIMEOUT",
            input_tokens=50,
            output_tokens=0,
            total_tokens=50,
            estimated_cost=0.0,
            credits_charged=0,
            latency_ms=None,
            created_at=_now(),
        )
        session.add_all([pcl1, pcl2, pcl3])

        # === 风控日志数据 ===
        risk1 = RiskLog(
            id="risk-001",
            user_id="user-001",
            risk_type="suspicious_login",
            severity="medium",
            details_json={"ip": "203.0.113.1", "reason": "异地登录"},
            created_at=_now(),
        )
        risk2 = RiskLog(
            id="risk-002",
            user_id="user-002",
            risk_type="rate_limit",
            severity="low",
            details_json={"endpoint": "/api/v1/ai/copy/generate", "count": 120},
            created_at=_now(),
        )
        risk3 = RiskLog(
            id="risk-003",
            user_id=None,
            risk_type="abnormal_usage",
            severity="high",
            details_json={"reason": "疑似恶意扫描"},
            created_at=_now(),
        )
        session.add_all([risk1, risk2, risk3])

        await session.commit()


# ============================================================
# 测试 FastAPI 应用
# ============================================================


@pytest_asyncio.fixture
async def app(db_engine, _db_session_factory):
    """创建带 admin-ops 路由和数据库的 FastAPI 测试应用。

    每次测试前重建表结构和种子数据，确保测试隔离。
    """
    await _reset_database(db_engine)
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

    # 注册 admin-ops 路由
    app.include_router(admin_ops_router, prefix="/api/v1")

    # 覆盖 get_db → 使用测试数据库会话
    # 请求结束时自动提交，模拟真实 FastAPI 请求生命周期中的事务提交
    async def _override_get_db():
        async with _db_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _override_get_db

    return app


# ============================================================
# 测试客户端
# ============================================================


@pytest_asyncio.fixture
async def admin_client(app: FastAPI) -> AsyncClient:
    """创建异步 HTTP 测试客户端（管理员权限）。

    覆盖 require_auth（require_permission 通过 Depends(require_auth) 链式调用）。
    """
    app.dependency_overrides[require_auth] = _override_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.pop(require_auth, None)


@pytest_asyncio.fixture
async def user_client(app: FastAPI) -> AsyncClient:
    """创建异步 HTTP 测试客户端（普通用户权限 → 预期 403）。"""
    app.dependency_overrides[require_auth] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.pop(require_auth, None)


@pytest_asyncio.fixture
async def no_auth_client(app: FastAPI) -> AsyncClient:
    """创建异步 HTTP 测试客户端（无鉴权 → 预期 401）。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
