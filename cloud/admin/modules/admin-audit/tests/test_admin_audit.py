"""
admin-audit 模块测试。
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text


@pytest.mark.asyncio
async def test_write_and_list_audit_logs(db_session, admin_token_data):
    """测试写入审计日志并查询列表。"""
    from service import write_audit_log, list_audit_logs

    # 写入测试日志
    log = await write_audit_log(
        db=db_session,
        admin_user_id=admin_token_data.user_id,
        admin_account="admin@test.com",
        action="update",
        target_type="user",
        target_id="test-user-id",
        summary="更新用户 test-user 的状态为 blocked",
        details_json={"status": "blocked"},
        ip_address="127.0.0.1",
    )
    assert log.id is not None
    assert log.action == "update"

    # 查询列表
    result = await list_audit_logs(db=db_session, limit=10, offset=0)
    assert result.total >= 1
    assert len(result.items) >= 1


@pytest.mark.asyncio
async def test_list_audit_logs_with_filters(db_session, admin_token_data):
    """测试审计日志筛选。"""
    from service import write_audit_log, list_audit_logs

    # 写入不同类型日志
    await write_audit_log(
        db=db_session,
        admin_user_id=admin_token_data.user_id,
        admin_account="admin@test.com",
        action="create",
        target_type="plan",
        summary="创建套餐 basic",
    )
    await write_audit_log(
        db=db_session,
        admin_user_id=admin_token_data.user_id,
        admin_account="admin@test.com",
        action="delete",
        target_type="user",
        summary="删除用户 old-user",
    )

    # 按操作类型筛选
    result = await list_audit_logs(db=db_session, action="create")
    assert result.total >= 1
    for item in result.items:
        assert item.action == "create"

    # 按目标类型筛选
    result = await list_audit_logs(db=db_session, target_type="user")
    assert result.total >= 1


@pytest.mark.asyncio
async def test_get_audit_log_detail(db_session, admin_token_data):
    """测试审计日志详情查询。"""
    from service import write_audit_log, get_audit_log_detail

    log = await write_audit_log(
        db=db_session,
        admin_user_id=admin_token_data.user_id,
        admin_account="admin@test.com",
        action="status_change",
        target_type="device",
        target_id="dev-001",
        summary="封禁设备 dev-001",
        details_json={"old_status": "active", "new_status": "blocked"},
        ip_address="192.168.1.1",
    )

    detail = await get_audit_log_detail(db=db_session, log_id=log.id)
    assert detail.id == log.id
    assert detail.action == "status_change"
    assert detail.target_id == "dev-001"
    assert detail.details_json == {"old_status": "active", "new_status": "blocked"}


@pytest.mark.asyncio
async def test_get_audit_log_not_found(db_session, admin_token_data):
    """测试查询不存在的审计日志返回 404。"""
    from service import get_audit_log_detail
    from cloud.shared import AppError

    with pytest.raises(AppError) as exc:
        await get_audit_log_detail(db=db_session, log_id="non-existent-id")
    assert exc.value.status_code == 404


# -- 测试依赖注入夹具（在模块级 conftest 或 test 文件内） --

@pytest.fixture
def admin_token_data():
    """模拟管理员 JWT TokenData。"""
    from cloud.shared.auth import TokenData
    return TokenData(
        user_id="admin-test-uuid",
        device_id=None,
        role="admin",
        plan_code="free",
    )


@pytest_asyncio.fixture
async def db_session():
    """创建测试用数据库会话。"""
    from cloud.shared.database import init_db, _get_engine
    from sqlalchemy.ext.asyncio import AsyncSession

    # 初始化内存数据库
    await init_db()

    engine = _get_engine()
    async with engine.begin() as conn:
        # 创建测试表
        await conn.run_sync(_create_test_tables)

    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()


def _create_test_tables(connection):
    """创建测试所需的表结构。"""
    from sqlalchemy import (
        Column, String, DateTime, JSON, Integer, Index, MetaData, Table, Text,
    )

    # 使用原始 SQL 创建测试表（避免 ORM 模型冲突）
    pass  # 由 cloud.shared.database.init_db 自动处理
