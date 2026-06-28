"""
admin-feature-codes 业务逻辑层。
"""
from __future__ import annotations
import json
from typing import Optional
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from cloud.shared import AppError
from cloud.shared.database import Base
from models import FeatureCode
from schemas import FeatureCodeItem, FeatureCodeDetail, FeatureCodeListData

MAX_LIMIT = 100

def _fmt_ts(dt) -> str:
    if dt is None: return ""
    if dt.tzinfo is None: return dt.isoformat() + "Z"
    return dt.isoformat()


def _parse_json(raw) -> dict:
    """安全解析 JSON 字段，兼容 SQLite TEXT 和 PostgreSQL JSONB。"""
    if raw is None: return {}
    if isinstance(raw, dict): return raw
    if isinstance(raw, str):
        try: return json.loads(raw)
        except (json.JSONDecodeError, TypeError): return {}
    return {}


async def _get_feature_plan_counts(db: AsyncSession) -> dict[str, int]:
    """统计每个功能码被多少个 active 套餐引用（只计 truthy 值）。"""
    counts: dict[str, int] = {}
    try:
        pl = Base.metadata.tables.get("plans")
        if pl is None:
            return counts
        result = await db.execute(
            select(pl.c.id, pl.c.enabled_features_json).where(pl.c.status == "active")
        )
        for row in result.all():
            features = _parse_json(row[1])
            for key, val in features.items():
                if val:  # 只计数 truthy 值（true / 含 daily_limit 的对象）
                    counts[key] = counts.get(key, 0) + 1
    except Exception:
        pass
    return counts


async def get_feature_plans(db: AsyncSession, fc_id: str) -> list[dict]:
    """查询功能码关联的套餐列表（详情用）。

    遍历所有 active 套餐，检查 enabled_features_json 中是否包含该功能码（truthy 值），
    返回套餐名称、月赠额度、是否启用。
    """
    fc = (await db.execute(select(FeatureCode).where(FeatureCode.id == fc_id))).scalar_one_or_none()
    if not fc:
        raise AppError(code="FEATURE_CODE_NOT_FOUND", message="功能码不存在", status_code=404)

    plans: list[dict] = []
    try:
        pl = Base.metadata.tables.get("plans")
        if pl is None:
            return plans
        result = await db.execute(
            select(pl.c.id, pl.c.name, pl.c.monthly_grant, pl.c.status, pl.c.enabled_features_json)
        )
        for row in result.all():
            features = _parse_json(row[4])
            val = features.get(fc.code)
            if val:  # truthy 才算关联
                plans.append({
                    "id": row[0],
                    "name": row[1],
                    "monthly_grant": row[2] or 0,
                    "status": row[3],
                })
    except Exception:
        pass
    return plans


async def list_feature_codes(db: AsyncSession, limit=20, offset=0, category: Optional[str]=None, order: str = "desc") -> FeatureCodeListData:
    limit = max(1, min(limit, MAX_LIMIT)); offset = max(0, offset)
    q = select(FeatureCode)
    if category: q = q.where(FeatureCode.category == category)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(FeatureCode.created_at.desc() if order == "desc" else FeatureCode.created_at.asc()).offset(offset).limit(limit))).scalars().all()

    # 批量统计每个功能码被多少套餐引用
    plan_counts = await _get_feature_plan_counts(db)

    items = [FeatureCodeItem(
        id=r.id, code=r.code, name=r.name, category=r.category,
        is_active=r.is_active, plan_count=plan_counts.get(r.code, 0),
        created_at=_fmt_ts(r.created_at),
    ) for r in rows]
    return FeatureCodeListData(items=items, total=total, limit=limit, offset=offset)

async def create_feature_code(db: AsyncSession, code: str, name: str, category="cloud_ai", description=None) -> FeatureCodeDetail:
    ex = (await db.execute(select(FeatureCode).where(FeatureCode.code == code))).scalar_one_or_none()
    if ex: raise AppError(code="FEATURE_CODE_EXISTS", message=f"功能码 '{code}' 已存在", status_code=409)
    fc = FeatureCode(code=code, name=name, category=category, description=description)
    db.add(fc); await db.flush(); await db.refresh(fc)
    return _to_detail(fc)

async def get_feature_code_detail(db: AsyncSession, fc_id: str) -> FeatureCodeDetail:
    fc = (await db.execute(select(FeatureCode).where(FeatureCode.id == fc_id))).scalar_one_or_none()
    if not fc: raise AppError(code="FEATURE_CODE_NOT_FOUND", message="功能码不存在", status_code=404)
    return _to_detail(fc)

async def update_feature_code(db: AsyncSession, fc_id: str, **kwargs) -> FeatureCodeDetail:
    fc = (await db.execute(select(FeatureCode).where(FeatureCode.id == fc_id))).scalar_one_or_none()
    if not fc: raise AppError(code="FEATURE_CODE_NOT_FOUND", message="功能码不存在", status_code=404)
    for k, v in kwargs.items():
        if v is not None and hasattr(fc, k): setattr(fc, k, v)
    await db.flush(); await db.refresh(fc)
    return _to_detail(fc)

async def delete_feature_code(db: AsyncSession, fc_id: str) -> dict:
    """软删除功能码。

    将功能码设为停用（is_active=False），保留功能码记录及套餐关联。

    Args:
        db: 数据库异步会话
        fc_id: 功能码 ID

    Returns:
        {"deleted": True}

    Raises:
        AppError: 功能码不存在时抛出 404
    """
    fc = (await db.execute(select(FeatureCode).where(FeatureCode.id == fc_id))).scalar_one_or_none()
    if not fc: raise AppError(code="FEATURE_CODE_NOT_FOUND", message="功能码不存在", status_code=404)
    fc.is_active = False
    await db.flush()
    return {"deleted": True}

def _to_detail(fc: FeatureCode) -> FeatureCodeDetail:
    return FeatureCodeDetail(id=fc.id, code=fc.code, name=fc.name, category=fc.category, description=fc.description, is_active=fc.is_active, created_at=_fmt_ts(fc.created_at))
