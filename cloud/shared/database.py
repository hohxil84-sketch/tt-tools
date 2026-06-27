"""
cloud-shared 数据库连接模块。

基于 SQLAlchemy 2.0 异步风格，使用 asyncpg 驱动连接 PostgreSQL。
提供异步引擎、会话工厂、ORM 基类、以及 FastAPI 依赖注入 get_db()。

数据库表定义对齐 cloud/DATABASE_SCHEMA.md。
"""
from __future__ import annotations

from typing import Any, AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import shared_settings


# -- 惰性初始化（避免导入时连接数据库） --
_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _get_engine() -> AsyncEngine:
    """获取或创建数据库异步引擎（惰性初始化，首次调用时创建）。"""
    global _engine
    if _engine is None:
        url = shared_settings.database_url
        if not url:
            raise RuntimeError(
                "APP_DATABASE_URL 未配置，拒绝使用内存 SQLite 运行。"
                "请在 .env 或启动脚本中设置，例如："
                "APP_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/tttools"
            )
        # 连接池参数仅对 PostgreSQL 有效，SQLite 不支持
        if url.startswith("postgresql") or url.startswith("asyncpg"):
            _engine = create_async_engine(
                url,
                echo=False,
                pool_size=shared_settings.database_pool_size,
                max_overflow=shared_settings.database_max_overflow,
                connect_args={
                    "timeout": 10,
                    "command_timeout": 30,
                    "server_settings": {"timezone": "utc"},
                },
            )
        else:
            _engine = create_async_engine(url, echo=False)
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取或创建异步会话工厂（惰性初始化）。"""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


# 模块级惰性属性：通过 __getattr__ 延迟创建
def __getattr__(name: str) -> Any:
    if name == "engine":
        return _get_engine()
    if name == "AsyncSessionLocal":
        return _get_session_factory()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# -- ORM 基类 --
class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类，所有数据库表模型继承自此。"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：获取异步数据库会话。

    使用示例：
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(...)
            return result

    会话在请求结束后自动关闭，异常时自动回滚。
    """
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库：创建所有 ORM 模型对应表（仅开发环境使用）。

    生产环境应使用 Alembic 迁移。
    该函数在 FastAPI lifespan startup 阶段调用。
    """
    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库引擎，释放连接池资源。

    该函数在 FastAPI lifespan shutdown 阶段调用。
    """
    global _engine, _async_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    _async_session_factory = None
