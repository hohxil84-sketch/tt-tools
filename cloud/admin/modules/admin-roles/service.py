"""
admin-roles 业务逻辑层。
"""
from __future__ import annotations
from typing import Optional
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from cloud.shared import AppError
from models import Role, Permission, role_permissions, user_roles
from schemas import *  # noqa: F403

MAX_LIMIT = 100


def _fmt_ts(dt) -> str:
    if dt is None: return ""
    if dt.tzinfo is None: return dt.isoformat() + "Z"
    return dt.isoformat()


# ============================================================
# 角色 CRUD
# ============================================================

async def list_roles(db: AsyncSession, limit=20, offset=0) -> RoleListData:
    limit = max(1, min(limit, MAX_LIMIT)); offset = max(0, offset)
    total = (await db.execute(select(func.count()).select_from(Role))).scalar_one()
    rows = (await db.execute(select(Role).order_by(Role.name).offset(offset).limit(limit))).scalars().all()
    items = [RoleItem(id=r.id, name=r.name, code=r.code, is_system=r.is_system, created_at=_fmt_ts(r.created_at)) for r in rows]
    return RoleListData(items=items, total=total, limit=limit, offset=offset)


async def create_role(db: AsyncSession, name: str, code: str, description=None) -> RoleDetail:
    ex = (await db.execute(select(Role).where(Role.code == code))).scalar_one_or_none()
    if ex: raise AppError(code="ROLE_EXISTS", message=f"角色代码 '{code}' 已存在", status_code=409)
    r = Role(name=name, code=code, description=description)
    db.add(r); await db.flush()
    return _to_detail(r)


async def get_role_detail(db: AsyncSession, role_id: str) -> RoleDetail:
    r = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if not r: raise AppError(code="ROLE_NOT_FOUND", message="角色不存在", status_code=404)
    return _to_detail(r)


async def update_role(db: AsyncSession, role_id: str, **kwargs) -> RoleDetail:
    r = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if not r: raise AppError(code="ROLE_NOT_FOUND", message="角色不存在", status_code=404)
    for k, v in kwargs.items():
        if v is not None and hasattr(r, k): setattr(r, k, v)
    await db.flush()
    return _to_detail(r)


async def delete_role(db: AsyncSession, role_id: str) -> dict:
    r = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if not r: raise AppError(code="ROLE_NOT_FOUND", message="角色不存在", status_code=404)
    if r.is_system: raise AppError(code="ROLE_IS_SYSTEM", message="系统内置角色不可删除", status_code=400)
    await db.delete(r); await db.flush()
    return {"deleted": True}


# ============================================================
# 权限查询
# ============================================================

async def list_permissions(db: AsyncSession) -> PermissionListData:
    rows = (await db.execute(select(Permission).order_by(Permission.resource, Permission.action))).scalars().all()
    items = [PermissionItem(id=r.id, code=r.code, name=r.name, resource=r.resource, action=r.action) for r in rows]
    return PermissionListData(items=items)


# ============================================================
# 角色-权限关联
# ============================================================

async def assign_permissions_to_role(db: AsyncSession, role_id: str, permission_ids: list[str]) -> RoleDetail:
    r = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if not r: raise AppError(code="ROLE_NOT_FOUND", message="角色不存在", status_code=404)
    await db.execute(text("DELETE FROM role_permissions WHERE role_id = :rid"), {"rid": role_id})
    for pid in permission_ids:
        await db.execute(text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid)"), {"rid": role_id, "pid": pid})
    await db.flush()
    # 重新加载
    await db.refresh(r)
    return _to_detail(r)


# ============================================================
# 用户-角色关联
# ============================================================

async def get_user_roles(db: AsyncSession, user_id: str) -> list[UserRoleItem]:
    result = await db.execute(
        text("SELECT r.id, r.name, r.code, r.is_system FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = :uid"),
        {"uid": user_id},
    )
    rows = result.all()
    return [UserRoleItem(id=r[0], name=r[1], code=r[2], is_system=r[3]) for r in rows]


async def assign_roles_to_user(db: AsyncSession, user_id: str, role_ids: list[str]) -> list[UserRoleItem]:
    # 验证用户存在
    user = (await db.execute(text("SELECT id FROM users WHERE id = :uid"), {"uid": user_id})).first()
    if not user: raise AppError(code="USER_NOT_FOUND", message="用户不存在", status_code=404)
    await db.execute(text("DELETE FROM user_roles WHERE user_id = :uid"), {"uid": user_id})
    for rid in role_ids:
        await db.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (:uid, :rid)"), {"uid": user_id, "rid": rid})
    await db.flush()
    return await get_user_roles(db, user_id)


# ============================================================
# 权限检查（供中间件使用）
# ============================================================

async def user_has_permission(db: AsyncSession, user_id: str, permission_code: str) -> bool:
    """检查用户是否拥有指定权限。"""
    result = await db.execute(
        text("SELECT 1 FROM user_roles ur JOIN role_permissions rp ON ur.role_id = rp.role_id JOIN permissions p ON rp.permission_id = p.id WHERE ur.user_id = :uid AND p.code = :pcode LIMIT 1"),
        {"uid": user_id, "pcode": permission_code},
    )
    return result.first() is not None


def _to_detail(r: Role) -> RoleDetail:
    perms = [PermissionItem(id=p.id, code=p.code, name=p.name, resource=p.resource, action=p.action) for p in (r.permissions or [])]
    return RoleDetail(id=r.id, name=r.name, code=r.code, description=r.description, is_system=r.is_system, created_at=_fmt_ts(r.created_at), permissions=perms)
