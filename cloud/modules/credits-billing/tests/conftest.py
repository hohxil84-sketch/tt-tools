"""
cloud-credits-billing 测试夹具。

提供测试用 FastAPI 应用、异步 HTTP 客户端、测试数据库等共享资源。
使用 SQLite 内存数据库，无需真实 PostgreSQL。

由于 auth-device 和 credits-billing 目录下都有 models.py，
需要谨慎管理 sys.path 和 sys.modules 避免模块名冲突。
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
_MODULE_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "credits-billing")
_AUTH_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "auth-device")

# ---- 步骤 1: 从 auth-device 加载 User 模型 ----
# 将 auth-device 目录临时放在 sys.path 最前面
if _AUTH_DIR in sys.path:
    sys.path.remove(_AUTH_DIR)
sys.path.insert(0, _AUTH_DIR)

# 导入 auth-device 的 User 模型（会注册 users 表到 Base.metadata）
from models import User, Device, AuthSession  # noqa: E402

# 清理：移除 auth-device 目录，清除 models 缓存
sys.path.pop(0)  # 移除 _AUTH_DIR
if "models" in sys.modules:
    del sys.modules["models"]

# ---- 步骤 2: 从 credits-billing 加载模型 ----
if _MODULE_DIR in sys.path:
    sys.path.remove(_MODULE_DIR)
sys.path.insert(0, _MODULE_DIR)

from models import Plan, CreditAccount, CreditLedger, UsageEvent  # noqa: E402, F401

# 注意：sys.path[0] 现在是 _MODULE_DIR，后续 `from router import router` 等会正确解析

# ---- 密码哈希工具（内联，避免导入 auth-device service.py 的依赖冲突） ----
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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

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
        # 手动创建跨模块的表（这些表的 ORM 不在本模块中，但 raw SQL 查询会用到）
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS feature_codes ("
            " id VARCHAR(36) PRIMARY KEY, code VARCHAR(100) UNIQUE NOT NULL,"
            " name VARCHAR(100) NOT NULL, category VARCHAR(50) NOT NULL,"
            " description TEXT, is_active BOOLEAN NOT NULL DEFAULT TRUE,"
            " created_at TIMESTAMP)"
        ))
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS provider_model_pricing ("
            " id VARCHAR(36) PRIMARY KEY, provider_name VARCHAR(50) NOT NULL,"
            " model_name VARCHAR(100) NOT NULL, input_price DECIMAL(18,6) NOT NULL DEFAULT 0,"
            " output_price DECIMAL(18,6) NOT NULL DEFAULT 0, currency VARCHAR(10) DEFAULT 'CNY',"
            " is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP, updated_at TIMESTAMP,"
            " UNIQUE(provider_name, model_name))"
        ))
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS feature_pricing ("
            " feature_code VARCHAR(100) PRIMARY KEY, min_credits INT NOT NULL DEFAULT 1,"
            " default_max_tokens INT NOT NULL DEFAULT 2048, updated_at TIMESTAMP)"
        ))
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS system_config ("
            " key VARCHAR(100) PRIMARY KEY, value VARCHAR(500) NOT NULL, updated_at TIMESTAMP)"
        ))
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS provider_latency_stats ("
            " id VARCHAR(36) PRIMARY KEY, provider_name VARCHAR(50) NOT NULL,"
            " model_name VARCHAR(100) NOT NULL, capability VARCHAR(50) NOT NULL,"
            " p50_latency_ms INT NOT NULL DEFAULT 0, p95_latency_ms INT NOT NULL DEFAULT 0,"
            " sample_count INT NOT NULL DEFAULT 0, updated_at TIMESTAMP,"
            " UNIQUE(provider_name, model_name, capability))"
        ))
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS credit_packages ("
            " id VARCHAR(36) PRIMARY KEY, product_code VARCHAR(50) UNIQUE NOT NULL,"
            " name VARCHAR(100) NOT NULL, credit_amount INT NOT NULL,"
            " price_cents INT NOT NULL, is_active BOOLEAN DEFAULT TRUE,"
            " sort_order INT DEFAULT 0, created_at TIMESTAMP, updated_at TIMESTAMP)"
        ))

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
    注册 credits-billing 路由。
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

    # 注册 credits-billing 路由
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
async def seed_plans(db_session: AsyncSession):
    """初始化套餐种子数据。"""
    from service import seed_plans  # noqa: E402
    return await seed_plans(db_session)


@pytest_asyncio.fixture
async def seed_pricing_tables(db_session: AsyncSession):
    """初始化定价相关表的种子数据。"""
    import uuid as _uuid
    from datetime import datetime, timezone as _tz

    now = datetime.now(_tz.utc)

    # 功能码
    features = [
        ("ai_copy_cloud", "AI 文案生成", "cloud_ai", True),
        ("ai_render_cloud", "AI 效果图生成", "cloud_ai", True),
        ("upscale_image_cloud", "AI 高清修复", "cloud_ai", True),
        ("vectorize_image_cloud", "AI 转矢量", "cloud_ai", True),
        ("ai_edit_image_cloud", "AI 智能改图", "cloud_ai", True),
        ("remove_bg_cloud", "云端高级抠图", "cloud_ai", True),
        ("ocr_cloud", "云端高级 OCR", "cloud_ai", True),
        ("resize_image_local_paid", "图片改尺寸", "local_paid", True),
        ("pdf_image_convert_local_paid", "PDF/图片互转", "local_paid", True),
        ("ocr_local", "本地 OCR", "local_free", True),
    ]
    for code, name, cat, active in features:
        await db_session.execute(
            text("INSERT OR IGNORE INTO feature_codes (id, code, name, category, is_active, created_at) "
                 "VALUES (:id, :code, :name, :cat, :active, :now)"),
            {"id": str(_uuid.uuid4()), "code": code, "name": name, "cat": cat, "active": active, "now": now},
        )

    # 模型定价
    pricing = [
        ("deepseek", "deepseek-chat", 1.0, 2.0),
        ("__default__", "__default__", 1.0, 2.0),
    ]
    for pn, mn, ip, op in pricing:
        await db_session.execute(
            text("INSERT OR IGNORE INTO provider_model_pricing "
                 "(id, provider_name, model_name, input_price, output_price, is_active, created_at, updated_at) "
                 "VALUES (:id, :pn, :mn, :ip, :op, TRUE, :now, :now)"),
            {"id": str(_uuid.uuid4()), "pn": pn, "mn": mn, "ip": ip, "op": op, "now": now},
        )

    # 功能定价
    fp_data = [
        ("ai_copy_cloud", 2), ("ai_render_cloud", 3),
        ("upscale_image_cloud", 3), ("vectorize_image_cloud", 3),
        ("ai_edit_image_cloud", 5), ("remove_bg_cloud", 2), ("ocr_cloud", 2),
    ]
    for fc_code, mc in fp_data:
        await db_session.execute(
            text("INSERT OR IGNORE INTO feature_pricing (feature_code, min_credits, default_max_tokens, updated_at) "
                 "VALUES (:fc, :mc, 2048, :now)"),
            {"fc": fc_code, "mc": mc, "now": now},
        )

    # 汇率
    await db_session.execute(
        text("INSERT OR IGNORE INTO system_config (key, value, updated_at) VALUES ('credits_exchange_rate', '10', :now)"),
        {"now": now},
    )

    await db_session.flush()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, seed_plans, seed_pricing_tables):
    """创建一个测试用户（标准套餐）并返回 ORM 对象。

    密码为 "test123"，已 bcrypt 哈希。
    """
    user = User(
        account="test@example.com",
        password_hash=hash_password("test123"),
        display_name="测试用户",
        role="user",
        status="active",
        plan_id=None,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def free_user(db_session: AsyncSession, seed_plans):
    """创建一个免费套餐测试用户。"""
    user = User(
        account="free@example.com",
        password_hash=hash_password("test123"),
        display_name="免费用户",
        role="user",
        status="active",
        plan_id=None,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def pro_user(db_session: AsyncSession, seed_plans):
    """创建一个专业套餐测试用户。"""
    user = User(
        account="pro@example.com",
        password_hash=hash_password("test123"),
        display_name="专业用户",
        role="user",
        status="active",
        plan_id=None,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_credit_account(db_session: AsyncSession, test_user, seed_plans):
    """为测试用户创建额度账户。"""
    from service import get_or_create_credit_account  # noqa: E402
    account = await get_or_create_credit_account(db_session, test_user.id, "standard")
    await db_session.flush()
    return account


@pytest_asyncio.fixture
async def free_credit_account(db_session: AsyncSession, free_user, seed_plans):
    """为免费用户创建额度账户。"""
    from service import get_or_create_credit_account  # noqa: E402
    account = await get_or_create_credit_account(db_session, free_user.id, "free")
    await db_session.flush()
    return account


@pytest_asyncio.fixture
async def auth_headers(test_user, test_credit_account):
    """生成测试用户的有效 Bearer Token 请求头。

    直接使用 cloud-shared 的 JWT 签发（不经过登录流程），方便测试。
    """
    from cloud.shared import create_access_token
    token = create_access_token(
        user_id=test_user.id,
        device_id=None,
        role=test_user.role,
        plan_id=None,
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
        plan_id=None,
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
        plan_id=None,
    )
    return {"Authorization": f"Bearer {token}"}
