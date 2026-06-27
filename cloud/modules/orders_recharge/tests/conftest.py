"""
cloud-orders-recharge 测试夹具。

提供测试用 FastAPI 应用、异步 HTTP 客户端、测试数据库等共享资源。
使用 SQLite 内存数据库，无需真实 PostgreSQL。

需要加载的模型（跨模块）：
- auth-device: User, Device, AuthSession
- credits-billing: Plan, CreditAccount, CreditLedger, UsageEvent
- orders_recharge: Order

注意：由于各模块目录使用中划线命名，无法用 Python 点号导入，
必须通过 sys.path 插入和 sys.modules 清理来隔离模块名冲突。
"""
from __future__ import annotations

import sys
import os

# 将项目根目录加入 sys.path，使 cloud.shared.* 可导入
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 目录路径
_ORDERS_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "orders_recharge")
_AUTH_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "auth-device")
_CREDITS_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "credits-billing")

# ---- 步骤 1: 加载 auth-device 的 User 模型 ----
if _AUTH_DIR in sys.path:
    sys.path.remove(_AUTH_DIR)
sys.path.insert(0, _AUTH_DIR)
from models import User, Device, AuthSession  # noqa: E402
sys.path.pop(0)
if "models" in sys.modules:
    del sys.modules["models"]

# ---- 步骤 2: 加载 credits-billing 的模型 ----
# 保存为独立模块名 "credits_billing_models"，避免与 orders_recharge 的 models 冲突
if _CREDITS_DIR in sys.path:
    sys.path.remove(_CREDITS_DIR)
sys.path.insert(0, _CREDITS_DIR)
from models import Plan, CreditAccount, CreditLedger, UsageEvent  # noqa: E402, F401
sys.path.pop(0)
# 将 models 模块保存为 credits_billing_models，供 service.py 的 _get_grant_credits() 使用
if "models" in sys.modules:
    sys.modules["credits_billing_models"] = sys.modules.pop("models")

# ---- 步骤 3: 加载 orders_recharge 的模型并保持 sys.path ----
if _ORDERS_DIR in sys.path:
    sys.path.remove(_ORDERS_DIR)
sys.path.insert(0, _ORDERS_DIR)
from models import Order  # noqa: E402, F401
# _ORDERS_DIR 保持在 sys.path[0]，后续 fixture 中的 router 导入会正确解析


# ============================================================
# 密码哈希工具
# ============================================================

import bcrypt


def hash_password(plain_password: str) -> str:
    """对明文密码做 bcrypt 哈希。"""
    return bcrypt.hashpw(
        plain_password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from cloud.shared.database import Base
from cloud.shared import get_db


# SQLite 内存数据库 URL（测试用）
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def _clear_module(name: str):
    """从 sys.modules 中移除指定模块名及其所有子模块。"""
    prefix = name + "."
    for _key in list(sys.modules.keys()):
        if _key == name or _key.startswith(prefix):
            del sys.modules[_key]


# ============================================================
# Fixtures
# ============================================================


@pytest_asyncio.fixture
async def test_engine():
    """创建测试用 SQLite 异步引擎，自动建表后返回，测试结束释放。"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine):
    """创建测试用异步会话工厂。"""
    factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    return factory


@pytest_asyncio.fixture
def app(test_session_factory):
    """创建带测试数据库和路由的 FastAPI 应用。

    只注册 orders-recharge 路由（被测模块）。
    confirm_order 通过 importlib 直接调用 grant_credits，不需要 credits-billing 路由。
    使用 importlib 按绝对路径加载 router，完全避开 sys.path 冲突。
    """
    import importlib.util

    app = FastAPI(debug=False)

    # 模拟 cloud-app-shell 中间件的 request_id 注入
    @app.middleware("http")
    async def _inject_request_id(request, call_next):
        import uuid
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    # 覆盖 get_db 依赖，使用测试数据库
    async def _override_get_db():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _override_get_db

    # 显式确保 sys.path[0] 指向 orders_recharge 目录
    # （避免被其他 fixture 的 sys.path 操作污染）
    if _ORDERS_DIR in sys.path:
        sys.path.remove(_ORDERS_DIR)
    sys.path.insert(0, _ORDERS_DIR)

    # 清理可能缓存的 router/schemas/service 模块，确保从 orders_recharge 加载
    for _name in ("router", "schemas", "service"):
        if _name in sys.modules:
            del sys.modules[_name]

    # 使用 importlib 按绝对路径加载 router.py
    _router_path = os.path.join(_ORDERS_DIR, "router.py")
    _spec = importlib.util.spec_from_file_location("orders_recharge_router", _router_path)
    _router_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_router_mod)
    app.include_router(_router_mod.router, prefix="/api/v1")

    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncClient:
    """创建异步 HTTP 测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def db_session(app, test_session_factory):
    """获取一个独立的测试数据库会话，用于准备测试数据。"""
    async with test_session_factory() as session:
        yield session
        await session.commit()


# ============================================================
# 测试数据夹具
# ============================================================


def _switch_to_credits():
    """临时切换到 credits-billing 目录以导入其 service。

    操作：
    1. 将 _CREDITS_DIR 插入 sys.path[0]
    2. 将 sys.modules["models"] 临时替换为 credits_billing_models
    3. 清除 service 缓存（确保从 _CREDITS_DIR 重新导入）
    4. 返回 (原始 sys.path, 原始 models) 用于恢复
    """
    _orig_path = list(sys.path)
    if _CREDITS_DIR in sys.path:
        sys.path.remove(_CREDITS_DIR)
    sys.path.insert(0, _CREDITS_DIR)

    # 保存当前 models 模块（可能是 orders_recharge 的），临时切换为 credits_billing_models
    _orig_models = sys.modules.pop("models", None)
    if "credits_billing_models" in sys.modules:
        sys.modules["models"] = sys.modules["credits_billing_models"]

    # 清除 service/schemas 缓存
    for _name in ("service", "schemas"):
        if _name in sys.modules:
            del sys.modules[_name]

    return _orig_path, _orig_models


def _restore_path(orig_path: list, orig_models=None):
    """恢复 sys.path 到原始状态，并恢复 models 模块。

    ORDERS_DIR 保持在位置 0。清除 service/schemas 缓存以确保下次从正确目录导入。
    """
    sys.path.clear()
    sys.path.extend([_ORDERS_DIR] + [p for p in orig_path if p != _ORDERS_DIR])

    # 恢复 models 模块
    sys.modules.pop("models", None)
    if orig_models is not None:
        sys.modules["models"] = orig_models

    # 清除 service/schemas 缓存，确保下次导入从 orders_recharge 解析
    for _name in ("service", "schemas"):
        if _name in sys.modules:
            del sys.modules[_name]


@pytest_asyncio.fixture
async def seed_plans(db_session: AsyncSession):
    """初始化套餐种子数据。"""
    _orig_path, _orig_models = _switch_to_credits()
    from service import seed_plans  # noqa: E402
    result = await seed_plans(db_session)
    _restore_path(_orig_path, _orig_models)
    return result


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, seed_plans):
    """创建一个测试用户（标准套餐）。"""
    user = User(
        account="test@example.com",
        password_hash=hash_password("test123"),
        display_name="测试用户",
        role="user",
        status="active",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def user_b(db_session: AsyncSession, seed_plans):
    """创建另一个测试用户（用户 B，用于跨用户隔离测试）。"""
    user = User(
        account="userb@example.com",
        password_hash=hash_password("test123"),
        display_name="用户B",
        role="user",
        status="active",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_credit_account(db_session: AsyncSession, test_user, seed_plans):
    """为测试用户创建额度账户。"""
    _orig_path, _orig_models = _switch_to_credits()
    from service import get_or_create_credit_account  # noqa: E402
    account = await get_or_create_credit_account(db_session, test_user.id, "standard")
    await db_session.flush()
    _restore_path(_orig_path, _orig_models)
    return account


@pytest_asyncio.fixture
async def user_b_credit_account(db_session: AsyncSession, user_b, seed_plans):
    """为用户 B 创建额度账户。"""
    _orig_path, _orig_models = _switch_to_credits()
    from service import get_or_create_credit_account  # noqa: E402
    account = await get_or_create_credit_account(db_session, user_b.id, "free")
    await db_session.flush()
    _restore_path(_orig_path, _orig_models)
    return account


@pytest_asyncio.fixture
async def auth_headers(test_user, test_credit_account):
    """生成测试用户的有效 Bearer Token 请求头。"""
    from cloud.shared import create_access_token
    token = create_access_token(
        user_id=test_user.id,
        device_id=None,
        role=test_user.role,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user_b_auth_headers(user_b, user_b_credit_account):
    """生成用户 B 的有效 Bearer Token 请求头。"""
    from cloud.shared import create_access_token
    token = create_access_token(
        user_id=user_b.id,
        device_id=None,
        role=user_b.role,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def pending_credits_order(db_session: AsyncSession, test_user, seed_plans, test_credit_account):
    """创建一个 pending 状态的 credits 订单（测试用）。"""
    from service import create_order  # noqa: E402
    order_data = await create_order(
        db_session,
        user_id=test_user.id,
        order_type="credits",
        product_code="credits_100",
        client_request_id="test_req_pending",
    )
    await db_session.flush()
    return order_data


@pytest_asyncio.fixture
async def pending_plan_order(db_session: AsyncSession, test_user, seed_plans, test_credit_account):
    """创建一个 pending 状态的 plan 订单（测试用）。"""
    from service import create_order  # noqa: E402
    order_data = await create_order(
        db_session,
        user_id=test_user.id,
        order_type="plan",
        product_code="pro",
        client_request_id="test_req_plan",
    )
    await db_session.flush()
    return order_data
