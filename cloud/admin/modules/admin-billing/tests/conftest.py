"""
admin-billing 测试夹具。

提供测试用 FastAPI 应用、异步 HTTP 客户端、以及 SQLite 内存数据库。
测试数据库通过 SQLAlchemy aiosqlite 实现，无需外部 PostgreSQL。

跨模块模型预加载：
在导入 admin-billing 路由之前，将 credits-billing、orders-recharge 和
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

# 将 admin-billing 模块目录加入 sys.path
_ADMIN_BILLING_DIR = os.path.join(
    _PROJECT_ROOT, "cloud", "admin", "modules", "admin-billing"
)
for _key in list(sys.modules.keys()):
    if _key in ("router", "service", "schemas", "models") or _key.startswith(
        ("router.", "service.", "schemas.", "models.")
    ):
        del sys.modules[_key]
if _ADMIN_BILLING_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_BILLING_DIR)

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

# ============================================================
# 跨模块模型预加载
# ============================================================

# 1. 加载 credits-billing 的模型（Plan, CreditAccount, CreditLedger）
_cb_models_path = os.path.join(
    _PROJECT_ROOT, "cloud", "modules", "credits-billing", "models.py"
)
# 使用 importlib 加载
import importlib.util as _iu

# 保存当前 sys.modules 中可能冲突的键
_saved_modules = {}
for _k in ("models", "service", "schemas", "router"):
    if _k in sys.modules:
        _saved_modules[_k] = sys.modules.pop(_k)

# 将 credits-billing 目录加入 sys.path
_cb_dir = os.path.join(_PROJECT_ROOT, "cloud", "modules", "credits-billing")
_orig_path = list(sys.path)
if _cb_dir in sys.path:
    sys.path.remove(_cb_dir)
sys.path.insert(0, _cb_dir)

try:
    _spec = _iu.spec_from_file_location("credits_billing_models", _cb_models_path)
    _cb_mod = _iu.module_from_spec(_spec)
    sys.modules["credits_billing_models"] = _cb_mod
    _spec.loader.exec_module(_cb_mod)
finally:
    # 恢复
    for _k in ("models", "service", "schemas", "router"):
        sys.modules.pop(_k, None)
    for _k, _v in _saved_modules.items():
        sys.modules[_k] = _v
    sys.path.clear()
    sys.path.extend(_orig_path)

# 2. 加载 orders_recharge 的模型（Order）
_or_path = os.path.join(
    _PROJECT_ROOT, "cloud", "modules", "orders_recharge", "models.py"
)
_saved_modules2 = {}
for _k in ("models", "service", "schemas", "router"):
    if _k in sys.modules:
        _saved_modules2[_k] = sys.modules.pop(_k)

_or_dir = os.path.join(_PROJECT_ROOT, "cloud", "modules", "orders_recharge")
_orig_path2 = list(sys.path)
if _or_dir in sys.path:
    sys.path.remove(_or_dir)
sys.path.insert(0, _or_dir)

try:
    _spec2 = _iu.spec_from_file_location("orders_recharge_models", _or_path)
    _or_mod = _iu.module_from_spec(_spec2)
    sys.modules["orders_recharge_models"] = _or_mod
    _spec2.loader.exec_module(_or_mod)
finally:
    for _k in ("models", "service", "schemas", "router"):
        sys.modules.pop(_k, None)
    for _k, _v in _saved_modules2.items():
        sys.modules[_k] = _v
    sys.path.clear()
    sys.path.extend(_orig_path2)

# 3. 加载 admin-users 的模型（User）
_au_models_path = os.path.join(
    _PROJECT_ROOT, "cloud", "admin", "modules", "admin-users", "models.py"
)
_saved_modules3 = {}
for _k in ("models", "service", "schemas", "router"):
    if _k in sys.modules:
        _saved_modules3[_k] = sys.modules.pop(_k)

_au_dir = os.path.join(_PROJECT_ROOT, "cloud", "admin", "modules", "admin-users")
_orig_path3 = list(sys.path)
if _au_dir in sys.path:
    sys.path.remove(_au_dir)
sys.path.insert(0, _au_dir)

try:
    _spec3 = _iu.spec_from_file_location("admin_users_models", _au_models_path)
    _au_mod = _iu.module_from_spec(_spec3)
    sys.modules["admin_users_models"] = _au_mod
    _spec3.loader.exec_module(_au_mod)
finally:
    for _k in ("models", "service", "schemas", "router"):
        sys.modules.pop(_k, None)
    for _k, _v in _saved_modules3.items():
        sys.modules[_k] = _v
    sys.path.clear()
    sys.path.extend(_orig_path3)

# 4. 清理模块缓存，确保 admin-billing 的 router/service/schemas 重新导入
for _key in list(sys.modules.keys()):
    if _key in ("router", "service", "schemas", "models") or _key.startswith(
        ("router.", "service.", "schemas.", "models.")
    ):
        del sys.modules[_key]

# 获取模型类的引用（用于种子数据）
Plan = _cb_mod.Plan
CreditAccount = _cb_mod.CreditAccount
CreditLedger = _cb_mod.CreditLedger
Order = _or_mod.Order
User = _au_mod.UserAdmin

# 导入 admin-billing 路由
from router import router as admin_billing_router  # noqa: E402


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
    """填充测试数据：套餐、用户、额度账户、流水、订单。"""
    from datetime import datetime, timezone

    def _now():
        return datetime.now(timezone.utc).replace(tzinfo=None)

    async with session_factory() as session:
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
            status="blocked",
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

        # === 额度账户数据 ===
        acct1 = CreditAccount(
            id="acct-001",
            user_id="user-001",
            plan_code="standard",
            balance=450,
            monthly_grant=500,
            period_start=_now(),
            period_end=_now(),
            status="active",
            created_at=_now(),
            updated_at=_now(),
        )
        acct2 = CreditAccount(
            id="acct-002",
            user_id="user-002",
            plan_code="free",
            balance=5,
            monthly_grant=10,
            period_start=_now(),
            period_end=_now(),
            status="active",
            created_at=_now(),
            updated_at=_now(),
        )
        acct3 = CreditAccount(
            id="acct-003",
            user_id="admin-001",
            plan_code="pro",
            balance=2000,
            monthly_grant=2000,
            period_start=_now(),
            period_end=_now(),
            status="active",
            created_at=_now(),
            updated_at=_now(),
        )
        session.add_all([acct1, acct2, acct3])

        # === 额度流水数据 ===
        ledger1 = CreditLedger(
            id="ledger-001",
            user_id="user-001",
            account_id="acct-001",
            change_type="grant",
            amount=500,
            balance_after=500,
            source_type="system",
            description="月度赠送 500 额度",
            created_at=_now(),
        )
        ledger2 = CreditLedger(
            id="ledger-002",
            user_id="user-001",
            account_id="acct-001",
            change_type="consume",
            amount=-50,
            balance_after=450,
            source_type="provider_call",
            description="AI Copy 消耗 50 额度",
            created_at=_now(),
        )
        session.add_all([ledger1, ledger2])

        # === 订单数据 ===
        order1 = Order(
            id="order-001",
            user_id="user-001",
            order_no="ORD-20260624-a1b2c3d4",
            order_type="credits",
            product_code="credits_100",
            amount_cents=1000,
            credit_amount=100,
            currency="CNY",
            status="pending",
            created_at=_now(),
            updated_at=_now(),
        )
        order2 = Order(
            id="order-002",
            user_id="user-002",
            order_no="ORD-20260624-e5f6g7h8",
            order_type="plan",
            product_code="standard",
            amount_cents=2900,
            credit_amount=None,
            currency="CNY",
            status="paid",
            paid_at=_now(),
            created_at=_now(),
            updated_at=_now(),
        )
        session.add_all([order1, order2])

        await session.commit()


# ============================================================
# 测试 FastAPI 应用
# ============================================================


@pytest_asyncio.fixture
async def app(db_engine, _db_session_factory):
    """创建带 admin-billing 路由和数据库的 FastAPI 测试应用。

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

    # 注册 admin-billing 路由
    app.include_router(admin_billing_router, prefix="/api/v1")

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
    app.dependency_overrides[require_admin] = _override_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

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
