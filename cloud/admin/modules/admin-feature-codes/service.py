"""
admin-feature-codes 业务逻辑层。
"""
from __future__ import annotations
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from cloud.shared import AppError
from models import FeatureCode
from schemas import FeatureCodeItem, FeatureCodeDetail, FeatureCodeListData

MAX_LIMIT = 100

def _fmt_ts(dt) -> str:
    if dt is None: return ""
    if dt.tzinfo is None: return dt.isoformat() + "Z"
    return dt.isoformat()

async def list_feature_codes(db: AsyncSession, limit=20, offset=0, category: Optional[str]=None) -> FeatureCodeListData:
    limit = max(1, min(limit, MAX_LIMIT)); offset = max(0, offset)
    q = select(FeatureCode)
    if category: q = q.where(FeatureCode.category == category)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(FeatureCode.code).offset(offset).limit(limit))).scalars().all()
    items = [FeatureCodeItem(id=r.id, code=r.code, name=r.name, category=r.category, is_active=r.is_active, created_at=_fmt_ts(r.created_at)) for r in rows]
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
    await db.delete(fc); await db.flush()
    return {"deleted": True}

def _to_detail(fc: FeatureCode) -> FeatureCodeDetail:
    return FeatureCodeDetail(id=fc.id, code=fc.code, name=fc.name, category=fc.category, description=fc.description, is_active=fc.is_active, created_at=_fmt_ts(fc.created_at))
