"""
cloud-provider-log 业务逻辑层。

提供 Provider 调用日志的写入和查询功能。

关键规则（对齐 DATABASE_SCHEMA.md 写入边界）：
    - provider_call_log 只能由本模块写入。
    - raw_usage_json 和 raw_meta_json 仅服务端保存，不返回给客户端。
    - 查询接口只返回脱敏后的字段。

写入时机（标准云端 AI 调用链）：
    provider-runtime -> 返回 ProviderResult
    -> provider-log 写入调用日志
    -> credits-billing 扣费
    -> 返回统一响应
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import ErrorCode, AppError

from models import ProviderCallLog
from schemas import (
    WriteProviderCallLogRequest,
    ProviderCallLogItem,
    ProviderCallLogListData,
)


# ============================================================
# Provider 调用日志写入
# ============================================================


async def write_provider_call_log(
    db: AsyncSession,
    *,
    user_id: str,
    feature: str,
    req: WriteProviderCallLogRequest,
    device_id: Optional[str] = None,
) -> ProviderCallLog:
    """写入一条 Provider 调用日志。

    由 provider-runtime 或上层 AI 模块调用。
    调用链：API endpoint -> provider-runtime -> provider-log -> credits-billing。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID（来自 JWT TokenData）
        feature: 功能码（如 ai_copy_cloud）
        req: Provider 调用日志写入请求（包含 provider、model、token 用量等）
        device_id: 设备 ID（可选，来自 JWT TokenData）

    Returns:
        写入的 ProviderCallLog ORM 对象

    Raises:
        AppError: request_id 重复（幂等保护）
    """
    # 幂等检查：同一 request_id 不能重复写入
    existing = await db.execute(
        select(ProviderCallLog).where(ProviderCallLog.request_id == req.request_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"调用日志已存在：request_id={req.request_id}",
            status_code=409,
        )

    # 构造 ORM 对象
    log_entry = ProviderCallLog(
        request_id=req.request_id,
        user_id=user_id,
        device_id=device_id,
        feature=feature,
        provider=req.provider,
        model=req.model,
        status=req.status,
        error_code=req.error_code,
        input_tokens=req.input_tokens,
        output_tokens=req.output_tokens,
        total_tokens=req.total_tokens,
        reasoning_tokens=req.reasoning_tokens,
        cached_tokens=req.cached_tokens,
        image_count=req.image_count,
        estimated_cost=req.estimated_cost,
        credits_charged=req.credits_charged,
        latency_ms=req.latency_ms,
        raw_usage_json=req.raw_usage_json,
        raw_meta_json=req.raw_meta_json,
        # created_at 由 ORM default 自动填充
    )

    db.add(log_entry)
    await db.flush()

    # 异步更新 Provider 耗时统计（仅成功调用）
    if req.status == "success" and req.latency_ms is not None and req.latency_ms > 0:
        await _update_latency_stats_async(
            db,
            provider_name=req.provider,
            model_name=req.model,
            capability=_guess_capability(feature),
            latency_ms=req.latency_ms,
        )

    return log_entry


# ============================================================
# Provider 调用日志查询
# ============================================================


async def list_provider_call_logs(
    db: AsyncSession,
    *,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    feature: Optional[str] = None,
    status: Optional[str] = None,
    provider: Optional[str] = None,
) -> ProviderCallLogListData:
    """查询当前用户的 Provider 调用日志（分页 + 筛选）。

    返回字段不包含 raw_usage_json、raw_meta_json、reasoning_tokens、
    cached_tokens、image_count 等仅服务端使用的敏感字段。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID（来自 JWT TokenData）
        limit: 每页条数（默认 50，最大 100）
        offset: 分页偏移量
        feature: 可选，按功能码筛选（如 ai_copy_cloud）
        status: 可选，按调用状态筛选（success / failed / timeout）
        provider: 可选，按 Provider 名称筛选（如 openai、deepseek）

    Returns:
        ProviderCallLogListData（含 items、total、limit、offset）
    """
    # 限制最大每页条数
    limit = min(limit, 100)
    limit = max(limit, 1)

    # 构建查询条件（只查询当前用户的数据）
    conditions = [ProviderCallLog.user_id == user_id]
    if feature:
        conditions.append(ProviderCallLog.feature == feature)
    if status:
        conditions.append(ProviderCallLog.status == status)
    if provider:
        conditions.append(ProviderCallLog.provider == provider)

    where_clause = and_(*conditions)

    # 查询总记录数
    count_result = await db.execute(
        select(func.count()).select_from(ProviderCallLog).where(where_clause)
    )
    total = count_result.scalar()

    # 查询分页数据（按创建时间倒序，最新的在前）
    result = await db.execute(
        select(ProviderCallLog)
        .where(where_clause)
        .order_by(ProviderCallLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    entries = result.scalars().all()

    # 转换为响应 DTO（过滤掉仅服务端字段）
    items = [
        ProviderCallLogItem(
            id=e.id,
            request_id=e.request_id,
            feature=e.feature,
            provider=e.provider,
            model=e.model,
            status=e.status,
            error_code=e.error_code,
            input_tokens=e.input_tokens,
            output_tokens=e.output_tokens,
            total_tokens=e.total_tokens,
            estimated_cost=float(e.estimated_cost),
            credits_charged=e.credits_charged,
            latency_ms=e.latency_ms,
            created_at=e.created_at,
        )
        for e in entries
    ]

    return ProviderCallLogListData(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ============================================================
# Provider 耗时统计更新（供预估接口使用）
# ============================================================


def _guess_capability(feature: str) -> str:
    """根据功能码推测 capability 类型。

    用于 provider_latency_stats 表的 capability 字段。
    """
    image_features = {
        "ai_render_cloud", "upscale_image_cloud", "vectorize_image_cloud",
        "ai_edit_image_cloud", "remove_bg_cloud",
    }
    ocr_features = {"ocr_cloud"}
    if feature in image_features:
        return "image_generation"
    if feature in ocr_features:
        return "image_edit"
    return "text"


async def _update_latency_stats_async(
    db: AsyncSession,
    provider_name: str,
    model_name: str,
    capability: str,
    latency_ms: int,
) -> None:
    """异步更新 provider_latency_stats 表。

    基于最近 1000 条成功调用的滑动窗口，计算 p50 和 p95 耗时。
    使用 raw SQL 避免 ORM 跨模块冲突。

    Args:
        db: 数据库异步会话
        provider_name: Provider 名称
        model_name: 模型名称
        capability: text / image_generation / image_edit
        latency_ms: 本次调用的耗时（毫秒）
    """
    # 查询最近 1000 条成功调用的耗时（含本次）
    result = await db.execute(
        text(
            "SELECT latency_ms FROM provider_call_log "
            "WHERE provider = :pn AND model = :mn AND status = 'success' "
            "AND latency_ms IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 1000"
        ),
        {"pn": provider_name, "mn": model_name},
    )
    rows = result.all()
    latencies = sorted([row[0] for row in rows if row[0] is not None])

    if not latencies:
        return

    n = len(latencies)
    p50 = latencies[n // 2]
    p95 = latencies[min(int(n * 0.95), n - 1)]

    # UPSERT: 使用 PostgreSQL ON CONFLICT / SQLite INSERT OR REPLACE
    # 兼容两种数据库，先尝试 UPDATE，rowcount=0 则 INSERT
    update_result = await db.execute(
        text(
            "UPDATE provider_latency_stats SET "
            "p50_latency_ms = :p50, p95_latency_ms = :p95, sample_count = :cnt, "
            "updated_at = :now "
            "WHERE provider_name = :pn AND model_name = :mn AND capability = :cap"
        ),
        {
            "p50": p50, "p95": p95, "cnt": n,
            "now": datetime.now(timezone.utc),
            "pn": provider_name, "mn": model_name, "cap": capability,
        },
    )
    if update_result.rowcount == 0:
        import uuid as _uuid
        await db.execute(
            text(
                "INSERT INTO provider_latency_stats "
                "(id, provider_name, model_name, capability, "
                " p50_latency_ms, p95_latency_ms, sample_count, updated_at) "
                "VALUES (:id, :pn, :mn, :cap, :p50, :p95, :cnt, :now)"
            ),
            {
                "id": str(_uuid.uuid4()),
                "pn": provider_name, "mn": model_name, "cap": capability,
                "p50": p50, "p95": p95, "cnt": n,
                "now": datetime.now(timezone.utc),
            },
        )

    await db.flush()
