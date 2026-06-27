"""
cloud-ai-image-tools 测试夹具。

提供测试用 FastAPI 应用、异步 HTTP 客户端、测试数据库等共享资源。
使用 SQLite 内存数据库，无需真实 PostgreSQL。

跨模块导入说明：
    本模块依赖 auth-device（User 模型）、credits-billing（Plan/CreditAccount 模型）、
    provider-runtime（MockProvider/ProviderRouter）、provider-log（ProviderCallLog 模型）。
    由于各模块目录名含连字符且有同名文件（models.py），需要仔细管理 sys.path
    和 sys.modules 避免模块名冲突（对齐 ai-render 测试的导入模式）。
"""
from __future__ import annotations

import sys
import os

# ============================================================
# 路径设置
# ============================================================

_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 各模块目录路径
_AI_IMAGE_TOOLS_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "ai-image-tools")
_AUTH_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "auth-device")
_CREDITS_BILLING_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "credits-billing")
_PROVIDER_LOG_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "provider-log")
_PROVIDER_RUNTIME_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "provider-runtime")


def _clean_modules(*names: str):
    """从 sys.modules 中移除指定模块及其子模块。"""
    for key in list(sys.modules.keys()):
        if key in names or any(key.startswith(n + ".") for n in names):
            del sys.modules[key]


# ============================================================
# 步骤 1: 从 auth-device 加载 User / Device / AuthSession 模型
# ============================================================

_clean_modules("models", "schemas", "service")

_ip = _AUTH_DIR
if _ip in sys.path:
    sys.path.remove(_ip)
sys.path.insert(0, _ip)

from models import User, Device, AuthSession  # noqa: E402

sys.path.pop(0)  # 移除 _AUTH_DIR
_clean_modules("models", "schemas", "service")

# ============================================================
# 步骤 2: 从 credits-billing 加载 Plan / CreditAccount 等模型
# ============================================================

_ip = _CREDITS_BILLING_DIR
if _ip in sys.path:
    sys.path.remove(_ip)
sys.path.insert(0, _ip)

from models import Plan, CreditAccount, CreditLedger, UsageEvent  # noqa: E402
from service import seed_plans, get_or_create_credit_account  # noqa: E402

sys.path.pop(0)  # 移除 _CREDITS_BILLING_DIR
_clean_modules("models", "schemas", "service")

# ============================================================
# 步骤 3: 从 provider-log 加载 ProviderCallLog 模型
# ============================================================

_ip = _PROVIDER_LOG_DIR
if _ip in sys.path:
    sys.path.remove(_ip)
sys.path.insert(0, _ip)

from models import ProviderCallLog  # noqa: E402

sys.path.pop(0)
_clean_modules("models", "schemas", "service")

# ============================================================
# 步骤 3b: 从 ai-image-tools 加载 AiTask 模型（确保 Base.metadata 创建 ai_tasks 表）
# ============================================================

_ip = _AI_IMAGE_TOOLS_DIR
if _ip in sys.path:
    sys.path.remove(_ip)
sys.path.insert(0, _ip)

from models import AiTask  # noqa: E402

sys.path.pop(0)
_clean_modules("models", "schemas", "service")

# ============================================================
# 步骤 4: 设置 ai-image-tools 模块目录到 sys.path（用于 router 导入）
# ============================================================

if _AI_IMAGE_TOOLS_DIR not in sys.path:
    sys.path.insert(0, _AI_IMAGE_TOOLS_DIR)

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


# ============================================================
# 测试夹具
# ============================================================

import pytest
import pytest_asyncio


@pytest.fixture(autouse=True)
def _use_mock_provider_runtime(monkeypatch):
    monkeypatch.setenv("IMAGE_TOOLS_PROVIDER", "mock")
    monkeypatch.setenv("AI_IMAGE_PROVIDER", "mock")
    monkeypatch.setenv("DEEPSEEK_ENABLED", "false")
    monkeypatch.setenv("DOUBAO_ENABLED", "false")
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from cloud.shared.database import Base
from cloud.shared import get_db


# SQLite 内存数据库 URL（测试用）
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


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

    覆盖 get_db 依赖，注入测试数据库会话工厂。
    注册 ai-image-tools 路由。
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

    # 注册 ai-image-tools 路由
    from router import router  # noqa: E402
    app.include_router(router, prefix="/api/v1")

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


@pytest_asyncio.fixture
async def seed_plans_fixture(db_session: AsyncSession):
    """初始化套餐种子数据。"""
    return await seed_plans(db_session)


@pytest_asyncio.fixture
async def standard_user(db_session: AsyncSession, seed_plans_fixture):
    """创建一个标准套餐测试用户。

    密码为 "test123"，已 bcrypt 哈希。
    标准套餐的各 AI 图片子功能已启用。
    """
    user = User(
        account="standard@example.com",
        password_hash=hash_password("test123"),
        display_name="标准用户",
        role="user",
        status="active",
        plan_code="standard",
    )
    db_session.add(user)
    await db_session.flush()

    # 创建额度账户
    account = await get_or_create_credit_account(db_session, user.id, "standard")
    await db_session.flush()

    return user


@pytest_asyncio.fixture
async def free_user(db_session: AsyncSession, seed_plans_fixture):
    """创建一个免费套餐测试用户。

    免费套餐的各 AI 图片子功能未启用，应返回权限错误。
    """
    user = User(
        account="free@example.com",
        password_hash=hash_password("test123"),
        display_name="免费用户",
        role="user",
        status="active",
        plan_code="free",
    )
    db_session.add(user)
    await db_session.flush()

    # 创建额度账户
    account = await get_or_create_credit_account(db_session, user.id, "free")
    await db_session.flush()

    return user


@pytest_asyncio.fixture
async def pro_user(db_session: AsyncSession, seed_plans_fixture):
    """创建一个专业套餐测试用户。"""
    user = User(
        account="pro@example.com",
        password_hash=hash_password("test123"),
        display_name="专业用户",
        role="user",
        status="active",
        plan_code="pro",
    )
    db_session.add(user)
    await db_session.flush()

    # 创建额度账户
    account = await get_or_create_credit_account(db_session, user.id, "pro")
    await db_session.flush()

    return user


@pytest_asyncio.fixture
async def standard_auth_headers(standard_user):
    """生成标准套餐用户的有效 Bearer Token 请求头。"""
    from cloud.shared import create_access_token
    token = create_access_token(
        user_id=standard_user.id,
        device_id=None,
        role=standard_user.role,
        plan_code=standard_user.plan_code,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def free_auth_headers(free_user):
    """生成免费套餐用户的有效 Bearer Token 请求头。"""
    from cloud.shared import create_access_token
    token = create_access_token(
        user_id=free_user.id,
        device_id=None,
        role=free_user.role,
        plan_code=free_user.plan_code,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def pro_auth_headers(pro_user):
    """生成专业套餐用户的有效 Bearer Token 请求头。"""
    from cloud.shared import create_access_token
    token = create_access_token(
        user_id=pro_user.id,
        device_id=None,
        role=pro_user.role,
        plan_code=pro_user.plan_code,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def low_balance_user(db_session: AsyncSession, seed_plans_fixture):
    """创建一个额度为 0 的标准套餐测试用户（用于测试额度不足）。"""
    user = User(
        account="lowbalance@example.com",
        password_hash=hash_password("test123"),
        display_name="额度不足用户",
        role="user",
        status="active",
        plan_code="standard",
    )
    db_session.add(user)
    await db_session.flush()

    # 创建额度账户但手动清零（模拟额度用完的场景）
    account = await get_or_create_credit_account(db_session, user.id, "standard")
    account.balance = 0
    await db_session.flush()

    return user


@pytest_asyncio.fixture
async def low_balance_auth_headers(low_balance_user):
    """生成额度不足用户的有效 Bearer Token 请求头。"""
    from cloud.shared import create_access_token
    token = create_access_token(
        user_id=low_balance_user.id,
        device_id=None,
        role=low_balance_user.role,
        plan_code=low_balance_user.plan_code,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
def valid_upscale_request():
    """构造一个有效的高清修复请求。"""
    return {
        "feature": "upscale_image_cloud",
        "input_file_ids": [
            "11111111-1111-1111-1111-111111111111",
        ],
        "options": {"target_width": 3840, "target_height": 2160},
        "client_request_id": "test_client_req_upscale_001",
    }


@pytest_asyncio.fixture
def valid_vectorize_request():
    """构造一个有效的转矢量请求。"""
    return {
        "feature": "vectorize_image_cloud",
        "input_file_ids": [
            "22222222-2222-2222-2222-222222222222",
        ],
        "options": {"output_format": "svg", "color_layers": 8},
        "client_request_id": "test_client_req_vectorize_001",
    }


@pytest_asyncio.fixture
def valid_ai_edit_request():
    """构造一个有效的 AI 改图请求。"""
    return {
        "feature": "ai_edit_image_cloud",
        "input_file_ids": [
            "33333333-3333-3333-3333-333333333333",
        ],
        "options": {"edit_prompt": "增强画质，提高对比度"},
        "client_request_id": "test_client_req_ai_edit_001",
    }


@pytest_asyncio.fixture
def valid_remove_bg_request():
    """构造一个有效的高级抠图请求。"""
    return {
        "feature": "remove_bg_cloud",
        "input_file_ids": [
            "44444444-4444-4444-4444-444444444444",
        ],
        "client_request_id": "test_client_req_remove_bg_001",
    }


@pytest_asyncio.fixture
def valid_ocr_request():
    """构造一个有效的高级 OCR 请求。"""
    return {
        "feature": "ocr_cloud",
        "input_file_ids": [
            "55555555-5555-5555-5555-555555555555",
        ],
        "options": {"language": "zh", "enable_layout_analysis": True},
        "client_request_id": "test_client_req_ocr_001",
    }


@pytest_asyncio.fixture
def minimal_request():
    """构造最小必填字段的图片 AI 请求（仅必填字段）。"""
    return {
        "feature": "remove_bg_cloud",
        "input_file_ids": ["11111111-1111-1111-1111-111111111111"],
        "client_request_id": "test_client_req_minimal",
    }


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession, seed_plans_fixture):
    """创建另一个标准套餐用户（用于测试跨用户任务隔离）。"""
    user = User(
        account="other@example.com",
        password_hash=hash_password("test123"),
        display_name="其他用户",
        role="user",
        status="active",
        plan_code="standard",
    )
    db_session.add(user)
    await db_session.flush()

    account = await get_or_create_credit_account(db_session, user.id, "standard")
    await db_session.flush()

    return user


@pytest_asyncio.fixture
async def other_auth_headers(other_user):
    """生成另一个用户的 Bearer Token 请求头。"""
    from cloud.shared import create_access_token
    token = create_access_token(
        user_id=other_user.id,
        device_id=None,
        role=other_user.role,
        plan_code=other_user.plan_code,
    )
    return {"Authorization": f"Bearer {token}"}
