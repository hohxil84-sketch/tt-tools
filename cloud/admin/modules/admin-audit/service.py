"""
admin-audit 业务逻辑层。

提供审计日志的写入和查询功能。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import AdminAuditLog
from schemas import AuditLogItem, AuditLogDetail, AuditLogListData


def _fmt_ts(dt) -> str:
    """将数据库时间转为 ISO 8601 UTC 字符串（JavaScript 可正确解析）。"""
    if dt is None:
        return ""
    # 如果是 naive datetime（数据库常见），加 Z 标记为 UTC
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    # 如果已带时区，转为 UTC 后格式化
    return dt.isoformat()


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def write_audit_log(
    db: AsyncSession,
    admin_user_id: str,
    admin_account: str,
    action: str,
    target_type: str,
    target_id: Optional[str] = None,
    summary: str = "",
    details_json: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> AdminAuditLog:
    """写入一条审计日志。

    由审计中间件在后台写操作完成后调用。

    Args:
        db: 数据库异步会话
        admin_user_id: 操作管理员 ID（来自 JWT）
        admin_account: 操作管理员账号
        action: 操作类型（create / update / delete / status_change / adjust / refund / cancel）
        target_type: 目标资源类型（user / device / order / plan / credits / feature_flag / provider）
        target_id: 目标资源 ID
        summary: 操作摘要（中文）
        details_json: 操作详情（请求体等）
        ip_address: 请求来源 IP

    Returns:
        创建的 AdminAuditLog 记录
    """
    log = AdminAuditLog(
        id=str(uuid.uuid4()),
        admin_user_id=admin_user_id,
        admin_account=admin_account,
        action=action,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        details_json=details_json or {},
        ip_address=ip_address,
        # created_at 由数据库 server_default=NOW() 自动生成
    )
    db.add(log)
    await db.flush()
    return log


async def list_audit_logs(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    admin_user_id: Optional[str] = None,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
) -> AuditLogListData:
    """查询审计日志列表（分页+多条件筛选）。

    Args:
        db: 数据库异步会话
        limit: 每页条数（默认 20，最大 100）
        offset: 偏移量
        admin_user_id: 按操作管理员 ID 筛选
        action: 按操作类型筛选
        target_type: 按目标资源类型筛选
        target_id: 按目标资源 ID 筛选

    Returns:
        AuditLogListData（含 items, total, limit, offset）
    """
    # 构建查询条件
    conditions = []
    params = {}
    if admin_user_id:
        conditions.append("admin_user_id = :admin_user_id")
        params["admin_user_id"] = admin_user_id
    if action:
        conditions.append("action = :action")
        params["action"] = action
    if target_type:
        conditions.append("target_type = :target_type")
        params["target_type"] = target_type
    if target_id:
        conditions.append("target_id = :target_id")
        params["target_id"] = target_id

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # 查询总数
    count_sql = f"SELECT COUNT(*) FROM admin_audit_logs {where_clause}"
    count_result = await db.execute(text(count_sql), params)
    total = count_result.scalar_one()

    # 查询列表
    query_sql = (
        f"SELECT id, admin_user_id, admin_account, admin_display_name, action, target_type, "
        f"target_id, summary, ip_address, created_at "
        f"FROM admin_audit_logs {where_clause} "
        f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    )
    params["limit"] = limit
    params["offset"] = offset
    result = await db.execute(text(query_sql), params)
    rows = result.all()

    items = [
        AuditLogItem(
            id=row[0],
            admin_user_id=row[1],
            admin_account=row[2],
            admin_display_name=row[3],
            action=row[4],
            target_type=row[5],
            target_id=row[6],
            summary=row[7],
            ip_address=row[8],
            created_at=_fmt_ts(row[9]),
        )
        for row in rows
    ]

    return AuditLogListData(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_audit_log_detail(
    db: AsyncSession,
    log_id: str,
) -> AuditLogDetail:
    """查询审计日志详情。

    Args:
        db: 数据库异步会话
        log_id: 审计日志 ID

    Returns:
        AuditLogDetail（含完整操作数据）

    Raises:
        AppError: 日志不存在
    """
    from cloud.shared import AppError, ErrorCode

    result = await db.execute(
        text(
            "SELECT id, admin_user_id, admin_account, admin_display_name, action, target_type, "
            "target_id, summary, details_json, ip_address, created_at "
            "FROM admin_audit_logs WHERE id = :log_id"
        ),
        {"log_id": log_id},
    )
    row = result.first()
    if row is None:
        raise AppError(
            code="AUDIT_LOG_NOT_FOUND",
            message="审计日志不存在",
            status_code=404,
        )

    return AuditLogDetail(
        id=row[0],
        admin_user_id=row[1],
        admin_account=row[2],
        admin_display_name=row[3],
        action=row[4],
        target_type=row[5],
        target_id=row[6],
        summary=row[7],
        details_json=row[8] if row[8] else None,
        ip_address=row[9],
        created_at=_fmt_ts(row[10]),
    )
