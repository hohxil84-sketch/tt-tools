"""
admin-export 业务逻辑层。

使用 Python csv 模块生成 CSV，通过 StreamingResponse 流式返回。
"""
from __future__ import annotations

import csv
import io
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse


async def export_users_csv(db: AsyncSession, status: Optional[str] = None) -> StreamingResponse:
    """导出用户列表为 CSV。"""
    where = ""
    params = {}
    if status:
        where = "WHERE status = :status"
        params["status"] = status

    result = await db.execute(
        text(f"SELECT id, account, display_name, role, status, plan_code, created_at FROM users {where} ORDER BY created_at"),
        params,
    )
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "账号", "展示名称", "角色", "状态", "套餐", "创建时间"])
    for row in rows:
        writer.writerow(list(row))

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users_export.csv"},
    )


async def export_orders_csv(
    db: AsyncSession, status: Optional[str] = None, order_type: Optional[str] = None,
) -> StreamingResponse:
    """导出订单列表为 CSV。"""
    conditions = []
    params = {}
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if order_type:
        conditions.append("order_type = :otype")
        params["otype"] = order_type
    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    result = await db.execute(
        text(f"SELECT id, order_no, order_type, product_code, amount_cents, credit_amount, currency, status, paid_at, user_id, created_at FROM orders {where} ORDER BY created_at DESC"),
        params,
    )
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "订单号", "类型", "产品", "金额(分)", "额度", "币种", "状态", "支付时间", "用户ID", "创建时间"])
    for row in rows:
        writer.writerow(list(row))

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders_export.csv"},
    )


async def export_credits_ledger_csv(
    db: AsyncSession, user_id: Optional[str] = None, change_type: Optional[str] = None,
) -> StreamingResponse:
    """导出额度流水为 CSV。"""
    conditions = []
    params = {}
    if user_id:
        conditions.append("user_id = :uid")
        params["uid"] = user_id
    if change_type:
        conditions.append("change_type = :ctype")
        params["ctype"] = change_type
    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    result = await db.execute(
        text(f"SELECT id, user_id, account_id, change_type, amount, balance_after, source_type, source_id, description, created_at FROM credit_ledger {where} ORDER BY created_at DESC LIMIT 10000"),
        params,
    )
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "用户ID", "账户ID", "变化类型", "金额", "变化后余额", "来源类型", "来源ID", "说明", "创建时间"])
    for row in rows:
        writer.writerow(list(row))

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=credits_ledger_export.csv"},
    )


async def export_provider_call_logs_csv(
    db: AsyncSession, feature: Optional[str] = None, provider: Optional[str] = None,
) -> StreamingResponse:
    """导出 Provider 调用记录为 CSV。"""
    conditions = []
    params = {}
    if feature:
        conditions.append("feature = :feature")
        params["feature"] = feature
    if provider:
        conditions.append("provider = :provider")
        params["provider"] = provider
    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    result = await db.execute(
        text(f"SELECT id, request_id, user_id, feature, provider, model, status, error_code, input_tokens, output_tokens, total_tokens, estimated_cost, credits_charged, latency_ms, created_at FROM provider_call_log {where} ORDER BY created_at DESC LIMIT 10000"),
        params,
    )
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "请求ID", "用户ID", "功能码", "Provider", "模型", "状态", "错误码", "输入Token", "输出Token", "总Token", "估算成本", "扣除额度", "延迟(ms)", "创建时间"])
    for row in rows:
        writer.writerow(list(row))

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=provider_call_logs_export.csv"},
    )
