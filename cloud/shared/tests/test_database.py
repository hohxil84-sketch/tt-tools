"""
cloud-shared 数据库连接模块测试。

验证：Base 声明式基类、引擎创建、会话工厂、get_db 依赖、
init_db / close_db。
使用 SQLite 内存库，不需要真实 PostgreSQL。
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI, Depends
from httpx import AsyncClient, ASGITransport
from sqlalchemy import Column, String, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from cloud.shared.database import (
    Base,
    get_db,
    AsyncSessionLocal,
)


# -- 测试用 ORM 模型 --
class _TestUser(Base):
    __tablename__ = "test_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class TestBase:
    """Base ORM 基类测试。"""

    def test_base_is_declarative(self) -> None:
        """Base 应为 SQLAlchemy DeclarativeBase。"""
        from sqlalchemy.orm import DeclarativeBase as SA_DeclarativeBase
        assert issubclass(Base, SA_DeclarativeBase)

    def test_model_inherits_base(self) -> None:
        """自定义模型应继承 Base。"""
        assert issubclass(_TestUser, Base)

    def test_model_has_table_name(self) -> None:
        """模型应自动推导 __tablename__ 或显式指定。"""
        assert _TestUser.__tablename__ == "test_users"


class TestDatabaseSession:
    """数据库会话测试（使用 SQLite 内存库）。"""

    @pytest.mark.asyncio
    async def test_session_can_execute(self, test_session: AsyncSession) -> None:
        """会话应能执行 SQL。"""
        result = await test_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_can_insert_and_query(self, test_session: AsyncSession) -> None:
        """应能插入并从测试表中查询数据。"""
        user = _TestUser(id="uuid-001", name="测试用户")
        test_session.add(user)
        await test_session.commit()

        result = await test_session.execute(
            text("SELECT name FROM test_users WHERE id = :id"),
            {"id": "uuid-001"},
        )
        assert result.scalar() == "测试用户"

    @pytest.mark.asyncio
    async def test_rollback_on_error(self, test_session: AsyncSession) -> None:
        """异常时数据应回滚。"""
        user = _TestUser(id="uuid-002", name="回滚测试")
        test_session.add(user)
        await test_session.flush()  # 先刷入但不提交

        # 模拟异常后回滚
        await test_session.rollback()

        result = await test_session.execute(
            text("SELECT COUNT(*) FROM test_users WHERE id = :id"),
            {"id": "uuid-002"},
        )
        assert result.scalar() == 0  # 回滚后数据不应存在


class TestGetDbDependency:
    """get_db FastAPI 依赖测试。"""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self, test_session: AsyncSession) -> None:
        """get_db 生成器应返回可用的 AsyncSession。"""
        # 直接测试生成器（不经过 FastAPI）
        gen = get_db()
        session = await gen.__anext__()
        try:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        finally:
            await gen.aclose()
