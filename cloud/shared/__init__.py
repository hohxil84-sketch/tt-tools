"""
cloud-shared 公共层统一导出。

本模块是 cloud/shared 的唯一公共接口，所有业务模块通过它访问公共能力。
"""
from __future__ import annotations

from typing import Any

# -- 配置 --
from .config import SharedSettings, shared_settings

# -- 数据库（engine / AsyncSessionLocal 用 __getattr__ 惰性导入，避免触发连接） --
from .database import (
    Base,
    close_db,
    get_db,
    init_db,
)

# -- 错误处理 --
from .errors import (
    ApiResponse,
    AppError,
    ErrorCode,
    ErrorDetail,
    error_response,
    success_response,
)

# -- 请求追踪 ID --
from .request_id import get_request_id

# -- 日志 --
from .logging_config import get_logger, setup_logging

# -- 鉴权 --
from .auth import (
    TokenData,
    create_access_token,
    decode_token,
    get_user_permissions,
    oauth2_scheme,
    optional_auth,
    require_admin,
    require_auth,
    require_permission,
)

# -- 权限 --
from .permissions import check_credits_enough, check_entitlement


# 惰性导入 engine 和 AsyncSessionLocal（访问时才触发数据库引擎创建）
def __getattr__(name: str) -> Any:
    if name in ("engine", "AsyncSessionLocal"):
        from . import database
        return getattr(database, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # config
    "SharedSettings",
    "shared_settings",
    # database
    "engine",
    "AsyncSessionLocal",
    "Base",
    "get_db",
    "init_db",
    "close_db",
    # errors
    "ErrorCode",
    "ErrorDetail",
    "ApiResponse",
    "AppError",
    "error_response",
    "success_response",
    # request_id
    "get_request_id",
    # logging
    "setup_logging",
    "get_logger",
    # auth
    "TokenData",
    "create_access_token",
    "decode_token",
    "get_user_permissions",
    "oauth2_scheme",
    "require_auth",
    "require_admin",
    "require_permission",
    "optional_auth",
    # permissions
    "check_entitlement",
    "check_credits_enough",
]
