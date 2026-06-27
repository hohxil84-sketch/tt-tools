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
    """统计每个功能码被多少个 active 套餐引用。

    遍历所有 active 套餐的 enabled_features_json，统计每个 key 的出现次数。
    """
    counts: dict[str, int] = {}
    try:
        pl = Base.metadata.tables.get("plans")
        if pl is None:
            return counts
        result = await db.execute(
            select(pl.c.enabled_features_json).where(pl.c.status == "active")
        )
        for row in result.all():
            features = _parse_json(row[0])
            for key in features:
                counts[key] = counts.get(key, 0) + 1
    except Exception:
        pass  # 统计失败不影响主流程
    return counts


async def list_feature_codes(db: AsyncSession, limit=20, offset=0, category: Optional[str]=None) -> FeatureCodeListData:
    limit = max(1, min(limit, MAX_LIMIT)); offset = max(0, offset)
    q = select(FeatureCode)
    if category: q = q.where(FeatureCode.category == category)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(FeatureCode.code).offset(offset).limit(limit))).scalars().all()

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
    fc = (await db.execute(select(FeatureCode).where(FeatureCode.id == fc_id))).scalar_one_or_none()
    if not fc: raise AppError(code="FEATURE_CODE_NOT_FOUND", message="功能码不存在", status_code=404)
    # 检查是否有活跃套餐引用了此功能码
    pl = Base.metadata.tables.get("plans")
    if pl is not None:
        result = await db.execute(
            text("SELECT name FROM plans WHERE status = 'active' AND enabled_features_json::text LIKE :pattern"),
            {"pattern": f'%"' + fc.code + '"%'},
        )
        ref_plans = [row[0] for row in result.all()]
        if ref_plans:
            raise AppError(
                code="FEATURE_CODE_IN_USE",
                message=f"功能码 '{fc.code}' 被以下套餐引用，无法删除：{', '.join(ref_plans)}",
                status_code=409,
            )
    await db.delete(fc); await db.flush()
    return {"deleted": True}

def _to_detail(fc: FeatureCode) -> FeatureCodeDetail:
    return FeatureCodeDetail(id=fc.id, code=fc.code, name=fc.name, category=fc.category, description=fc.description, is_active=fc.is_active, created_at=_fmt_ts(fc.created_at))
