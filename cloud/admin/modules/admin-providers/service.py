"""
admin-providers 业务逻辑层。
"""
from __future__ import annotations
from typing import Optional
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from cloud.shared import AppError
from models import Provider
from schemas import ProviderItem, ProviderDetail, ProviderListData

MAX_LIMIT = 100


def _fmt_ts(dt) -> str:
    if dt is None: return ""
    if dt.tzinfo is None: return dt.isoformat() + "Z"
    return dt.isoformat()


async def _reload_router(db: AsyncSession) -> None:
    """Provider 变更后刷新全局 Router（热更新）。

    使用独立的数据库会话来加载 Provider，避免与原 CRUD 事务冲突。
    router.load_from_db 直接从数据库重读 Provider 配置，不需要刷新模块导入缓存。
    """
    import logging
    _log = logging.getLogger("admin-providers")
    try:
        import sys, os
        _pr_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "modules", "provider-runtime")
        if _pr_dir not in sys.path:
            sys.path.insert(0, _pr_dir)
        from registry import get_global_router
        router = get_global_router()
        await router.load_from_db(db)
        _log.info("Router 热更新完成")
    except Exception as e:
        _log.warning("Router 热更新失败（不影响 CRUD）: %s", e)


async def list_providers(db: AsyncSession, limit: int = 20, offset: int = 0, order: str = "desc") -> ProviderListData:
    limit = max(1, min(limit, MAX_LIMIT)); offset = max(0, offset)
    base = select(Provider).where(Provider.is_enabled == True)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await db.execute(base.order_by(Provider.created_at.desc() if order == "desc" else Provider.created_at.asc()).offset(offset).limit(limit))).scalars().all()
    items = [ProviderItem(id=r.id, name=r.name, provider_type=r.provider_type, is_enabled=r.is_enabled, priority=r.priority, created_at=_fmt_ts(r.created_at)) for r in rows]
    return ProviderListData(items=items, total=total, limit=limit, offset=offset)


async def create_provider(db: AsyncSession, name: str, provider_type: str, **kwargs) -> ProviderDetail:
    existing = (await db.execute(select(Provider).where(Provider.name == name))).scalar_one_or_none()
    if existing: raise AppError(code="PROVIDER_EXISTS", message=f"Provider '{name}' 已存在", status_code=409)
    p = Provider(name=name, provider_type=provider_type, **{k: v for k, v in kwargs.items() if v is not None})
    db.add(p); await db.flush(); await db.refresh(p)
    await _reload_router(db)
    return _to_detail(p)


async def get_provider_detail(db: AsyncSession, provider_id: str) -> ProviderDetail:
    p = (await db.execute(select(Provider).where(Provider.id == provider_id))).scalar_one_or_none()
    if not p: raise AppError(code="PROVIDER_NOT_FOUND", message="Provider 不存在", status_code=404)
    return _to_detail(p)


async def update_provider(db: AsyncSession, provider_id: str, **kwargs) -> ProviderDetail:
    p = (await db.execute(select(Provider).where(Provider.id == provider_id))).scalar_one_or_none()
    if not p: raise AppError(code="PROVIDER_NOT_FOUND", message="Provider 不存在", status_code=404)
    for k, v in kwargs.items():
        if v is not None and hasattr(p, k): setattr(p, k, v)
    # 用数据库 NOW() 更新，避免客户端时区偏差
    await db.execute(text("UPDATE providers SET updated_at = NOW() WHERE id = :id"), {"id": provider_id})
    await db.flush(); await db.refresh(p)
    await _reload_router(db)
    return _to_detail(p)


async def delete_provider(db: AsyncSession, provider_id: str) -> dict:
    """软删除 Provider。

    将 Provider 设为禁用（is_enabled=False），保留配置记录。

    Args:
        db: 数据库异步会话
        provider_id: Provider ID

    Returns:
        {"deleted": True}

    Raises:
        AppError: Provider 不存在时抛出 404
    """
    p = (await db.execute(select(Provider).where(Provider.id == provider_id))).scalar_one_or_none()
    if not p: raise AppError(code="PROVIDER_NOT_FOUND", message="Provider 不存在", status_code=404)
    p.is_enabled = False
    await db.flush()
    await _reload_router(db)
    return {"deleted": True}


def _to_detail(p: Provider) -> ProviderDetail:
    return ProviderDetail(
        id=p.id, name=p.name, provider_type=p.provider_type,
        api_key_encrypted=p.api_key_encrypted, base_url=p.base_url,
        is_enabled=p.is_enabled,
        priority=p.priority,
        created_at=_fmt_ts(p.created_at),
        updated_at=_fmt_ts(p.updated_at),
    )
