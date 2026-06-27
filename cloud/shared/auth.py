"""
cloud-shared 鉴权依赖模块（骨架）。

提供 Bearer Token 校验和 FastAPI 鉴权依赖。
当前为骨架实现：JWT 签发/校验逻辑可用，但用户查询、设备检查等真实
逻辑留给 cloud/modules/auth-device 模块实现。

对齐 shared-contract/openapi/common.yaml securitySchemes.BearerAuth：
  Authorization: Bearer <access_token>

Token 载荷字段对齐 API_INDEX.md 客户端不得提交字段规则。
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from .config import shared_settings
from .database import get_db

# -- OAuth2 密码流（FastAPI 标准） --
# tokenUrl 指向登录接口，用于自动生成的 OpenAPI 文档
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class TokenData(BaseModel):
    """JWT 令牌解析后的载荷数据。

    客户端不得在请求中提交这些字段——由服务端根据鉴权结果自行决定。
    """
    user_id: str = Field(..., description="用户 ID（UUID）")
    device_id: Optional[str] = Field(default=None, description="设备 ID（UUID）")
    role: str = Field(default="user", description="用户角色")
    plan_code: str = Field(default="free", description="当前套餐编码")


# ============================================================
# JWT 工具函数
# ============================================================

def create_access_token(
    user_id: str,
    device_id: Optional[str] = None,
    role: str = "user",
    plan_code: str = "free",
) -> str:
    """签发短期 access_token。

    Args:
        user_id: 用户 UUID
        device_id: 设备 UUID（可选）
        role: 用户角色
        plan_code: 套餐编码

    Returns:
        JWT 字符串
    """
    from datetime import datetime, timedelta, timezone

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=shared_settings.auth_access_token_expire_minutes
    )
    payload = {
        "sub": user_id,
        "device_id": device_id,
        "role": role,
        "plan_code": plan_code,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(
        payload,
        shared_settings.auth_secret_key,
        algorithm=shared_settings.auth_algorithm,
    )


def decode_token(token: str) -> TokenData:
    """解码并校验 JWT token，返回 TokenData。

    Args:
        token: JWT 字符串（不含 "Bearer " 前缀）

    Returns:
        解析后的 TokenData

    Raises:
        JWTError: token 无效或已过期
    """
    payload = jwt.decode(
        token,
        shared_settings.auth_secret_key,
        algorithms=[shared_settings.auth_algorithm],
    )
    # 校验 token 类型
    if payload.get("type") != "access":
        raise JWTError("Token 类型不正确")

    user_id = payload.get("sub")
    if not user_id:
        raise JWTError("Token 缺少 sub 字段")

    return TokenData(
        user_id=user_id,
        device_id=payload.get("device_id"),
        role=payload.get("role", "user"),
        plan_code=payload.get("plan_code", "free"),
    )


# ============================================================
# FastAPI 鉴权依赖
# ============================================================

async def require_auth(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> TokenData:
    """FastAPI 依赖：要求请求携带有效 Bearer Token。

    如果 token 缺失或无效，抛出 401 错误。
    使用示例：
        @router.get("/me")
        async def get_me(current_user: TokenData = Depends(require_auth)):
            ...
    """
    if token is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_REQUIRED",
                "message": "请先登录",
                "request_id": getattr(request.state, "request_id", ""),
            },
        )

    try:
        return decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_TOKEN_EXPIRED",
                "message": "登录已过期，请重新登录",
                "request_id": getattr(request.state, "request_id", ""),
            },
        )


async def require_admin(
    current_user: TokenData = Depends(require_auth),
) -> TokenData:
    """FastAPI 依赖：要求当前用户为管理员。

    在 require_auth 基础上增加角色检查。
    保留此函数用于向后兼容；新代码应优先使用 require_permission()。
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PERMISSION_DENIED",
                "message": "需要管理员权限",
                "request_id": "",
            },
        )
    return current_user


def require_permission(permission_code: str):
    """FastAPI 依赖工厂：要求当前用户拥有指定权限。

    检查逻辑（按优先级）：
    1. 先通过 RBAC 表（user_roles → role_permissions → permissions）检查
    2. 如果用户 role=admin 且在 user_roles 表中无任何记录，视为超级管理员放行
    3. 否则拒绝访问

    使用示例：
        @router.get("/users")
        async def list_users(
            current_user: TokenData = Depends(require_permission("users.read")),
        ):
            ...

    Args:
        permission_code: 权限码，如 "users.read"、"orders.refund"

    Returns:
        异步依赖函数，返回 TokenData
    """
    async def _check(
        current_user: TokenData = Depends(require_auth),
        db=Depends(get_db),
    ) -> TokenData:
        from sqlalchemy import text as sql_text

        # 1. 快速路径：非管理员直接拒绝（管理后台仅限管理员访问）
        if current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "PERMISSION_DENIED",
                    "message": f"需要权限：{permission_code}",
                    "request_id": "",
                },
            )

        # 2. 查询该用户是否已分配 RBAC 角色
        role_count_result = await db.execute(
            sql_text("SELECT COUNT(*) FROM user_roles WHERE user_id = :uid"),
            {"uid": current_user.user_id},
        )
        has_rbac = role_count_result.scalar_one() > 0

        if not has_rbac:
            # 向后兼容：admin 且无 RBAC 记录 → 超级管理员，直接放行
            return current_user

        # 3. 有 RBAC 记录 → 严格检查具体权限
        result = await db.execute(
            sql_text(
                "SELECT 1 FROM user_roles ur "
                "JOIN role_permissions rp ON ur.role_id = rp.role_id "
                "JOIN permissions p ON rp.permission_id = p.id "
                "WHERE ur.user_id = :uid AND p.code = :pcode LIMIT 1"
            ),
            {"uid": current_user.user_id, "pcode": permission_code},
        )
        if result.first() is not None:
            return current_user

        # 4. 无此权限
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PERMISSION_DENIED",
                "message": f"需要权限：{permission_code}",
                "request_id": "",
            },
        )

    return _check


async def get_user_permissions(db, user_id: str) -> list[str]:
    """查询用户拥有的所有权限码列表。

    用于登录响应和前端菜单过滤。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID

    Returns:
        权限码字符串列表，如 ["users.read", "users.create", ...]
    """
    from sqlalchemy import text as sql_text

    result = await db.execute(
        sql_text(
            "SELECT DISTINCT p.code FROM user_roles ur "
            "JOIN role_permissions rp ON ur.role_id = rp.role_id "
            "JOIN permissions p ON rp.permission_id = p.id "
            "WHERE ur.user_id = :uid ORDER BY p.code"
        ),
        {"uid": user_id},
    )
    perms = [row[0] for row in result.all()]
    if perms:
        return perms

    # 如果用户没有 RBAC 记录但是 admin，返回全部权限
    role_count_result = await db.execute(
        sql_text("SELECT COUNT(*) FROM user_roles WHERE user_id = :uid"),
        {"uid": user_id},
    )
    has_rbac = role_count_result.scalar_one() > 0

    if not has_rbac:
        # 检查 users 表的 role 字段
        user_result = await db.execute(
            sql_text("SELECT role FROM users WHERE id = :uid"),
            {"uid": user_id},
        )
        user_row = user_result.first()
        if user_row and user_row[0] == "admin":
            # 返回系统中所有权限码（admin 无 RBAC 记录 = 超级管理员）
            all_perms = await db.execute(
                sql_text("SELECT code FROM permissions ORDER BY code")
            )
            return [row[0] for row in all_perms.all()]

    return perms


async def optional_auth(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[TokenData]:
    """FastAPI 依赖：可选鉴权——有 token 则解析，无 token 返回 None。

    用于同时支持登录/未登录用户的接口。
    """
    if token is None:
        return None
    try:
        return decode_token(token)
    except JWTError:
        return None
