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
