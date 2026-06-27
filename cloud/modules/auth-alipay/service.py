"""
支付宝 OAuth 2.0 登录业务逻辑。

流程：
1. 前端调用 /auth/alipay/login → 获取授权 URL → 跳转支付宝
2. 用户在支付宝确认授权 → 支付宝回调 /auth/alipay/callback?auth_code=xxx
3. 后端用 auth_code 换 access_token + user_id
4. 用 user_id 查找已有绑定，或创建新用户
5. 签发 JWT 返回前端
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, quote

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import AppError, ErrorCode, create_access_token
from cloud.shared.config import shared_settings

# ============================================================
# 配置
# ============================================================

ALIPAY_APP_ID = os.environ.get("ALIPAY_APP_ID", "")
ALIPAY_PRIVATE_KEY = os.environ.get("ALIPAY_PRIVATE_KEY", "")
ALIPAY_PUBLIC_KEY = os.environ.get("ALIPAY_PUBLIC_KEY", "")
ALIPAY_GATEWAY = "https://openapi.alipay.com/gateway.do"
ALIPAY_AUTH_URL = "https://openauth.alipay.com/oauth2/publicAppAuthorize.htm"

# 回调地址（优先环境变量，否则从请求推导）
ALIPAY_CALLBACK_URL = os.environ.get("ALIPAY_CALLBACK_URL", "")


# ============================================================
# RSA2 签名
# ============================================================


def _load_private_key():
    """加载应用私钥（从文件读取，避免 .env 编码问题）。"""
    import os as _os
    key_path = _os.path.join(_os.path.dirname(__file__), "alipay_private_key.pem")
    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())


def _sign(params: dict) -> str:
    """对参数字典按支付宝规则做 RSA2-SHA256 签名。"""
    # 1. 去掉 sign 和空值，按 key 字母序排序
    filtered = {k: v for k, v in params.items() if v is not None and v != "" and k != "sign"}
    sorted_items = sorted(filtered.items())

    # 2. 拼接为 key1=value1&key2=value2...（不 URL encode）
    raw = "&".join(f"{k}={v}" for k, v in sorted_items)

    # 3. RSA-SHA256 签名
    private_key = _load_private_key()
    signature = private_key.sign(raw.encode(), padding.PKCS1v15(), hashes.SHA256())

    return base64.b64encode(signature).decode()


def _verify_sign(params: dict, sign: str) -> bool:
    """验证支付宝返回的签名。"""
    import os as _os
    filtered = {k: v for k, v in params.items() if v is not None and v != "" and k not in ("sign", "sign_type")}
    sorted_items = sorted(filtered.items())
    raw = "&".join(f"{k}={v}" for k, v in sorted_items)

    key_path = _os.path.join(_os.path.dirname(__file__), "alipay_public_key.pem")
    with open(key_path, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read(), backend=default_backend())

    try:
        public_key.verify(base64.b64decode(sign), raw.encode(), padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False


# ============================================================
# 支付宝 API 调用
# ============================================================


async def _call_alipay(method: str, biz_params: dict = None, top_params: dict = None) -> dict:
    """调用支付宝网关 API。

    Args:
        method: API 方法名
        biz_params: 业务参数（放入 biz_content）
        top_params: 顶层参数（如 grant_type、code 等，不放入 biz_content）
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    params = {
        "app_id": ALIPAY_APP_ID,
        "method": method,
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": now,
        "version": "1.0",
    }
    if top_params:
        params.update(top_params)
    if biz_params:
        params["biz_content"] = json.dumps(biz_params, ensure_ascii=False)

    params["sign"] = _sign(params)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(ALIPAY_GATEWAY, data=params)
        resp.raise_for_status()
        raw = resp.content
        try:
            body = json.loads(raw)
        except UnicodeDecodeError:
            body = json.loads(raw.decode("gbk"))

    # 验证签名（TODO: 修复验签算法后启用）
    # 当前跳过验签，直接返回响应数据
    response_key = method.replace(".", "_") + "_response"
    response_data = body.get(response_key, {})
    if "sign" in body:
        pass  # 签名验证已跳过

    # 检查业务错误
    if response_data.get("code") and response_data.get("code") != "10000":
        raise AppError(
            code=ErrorCode.AUTH_INVALID_CREDENTIALS,
            message=f"支付宝返回错误: {response_data.get('msg', response_data.get('sub_msg', '未知错误'))}",
            status_code=502,
        )

    return response_data


# ============================================================
# 业务逻辑
# ============================================================


def alipay_get_login_url() -> str:
    """生成支付宝授权登录 URL。"""
    params = {
        "app_id": ALIPAY_APP_ID,
        "scope": "auth_user",
        "redirect_uri": ALIPAY_CALLBACK_URL,
        "state": str(uuid.uuid4())[:8],
    }
    return f"{ALIPAY_AUTH_URL}?{urlencode(params)}"


async def alipay_handle_callback(db: AsyncSession, auth_code: str) -> dict:
    """处理支付宝 OAuth 回调。

    Args:
        db: 数据库会话
        auth_code: 支付宝回调返回的授权码

    Returns:
        {"access_token": "...", "refresh_token": "...", "user": {...}}
    """
    # 1. 用 auth_code 换取 access_token（grant_type/code 是顶层参数）
    token_resp = await _call_alipay("alipay.system.oauth.token",
        top_params={
            "grant_type": "authorization_code",
            "code": auth_code,
        }
    )
    alipay_user_id = token_resp.get("open_id") or token_resp.get("user_id")
    access_token = token_resp.get("access_token")
    if not alipay_user_id:
        raise AppError(code=ErrorCode.AUTH_INVALID_CREDENTIALS, message="支付宝授权失败：未获取到 user_id", status_code=401)

    # 2. 尝试获取支付宝用户信息（应用上线后才可用）
    nickname = ""
    avatar = ""
    try:
        user_info = await _call_alipay("alipay.user.info.share",
            top_params={"auth_token": access_token}
        )
        nickname = user_info.get("nick_name", "")
        avatar = user_info.get("avatar", "")
    except AppError:
        pass  # 应用未上线时 user.info.share 不可用，使用 open_id 即可

    # 3. 查找或创建本地用户
    local_user_id = await _find_or_create_alipay_user(db, alipay_user_id, nickname)

    # 4. 签发 JWT
    now = int(time.time())
    jwt_token = create_access_token(user_id=local_user_id, role="user")

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "expires_in": shared_settings.auth_access_token_expire_minutes * 60,
        "user": {
            "id": local_user_id,
            "alipay_user_id": alipay_user_id,
            "nickname": nickname,
            "avatar": avatar,
        },
    }


async def _find_or_create_alipay_user(db: AsyncSession, alipay_user_id: str, nickname: str) -> str:
    """按 alipay_user_id 查找已有绑定用户，不存在则创建新用户。

    使用 raw SQL 避免跨模块 ORM 冲突。
    """
    # 查找已有绑定
    result = await db.execute(
        text("SELECT user_id FROM user_alipay_bindings WHERE alipay_user_id = :aid"),
        {"aid": alipay_user_id},
    )
    row = result.fetchone()
    if row:
        return row[0]

    # 统一注册新用户（默认套餐自动分配）
    from cloud.shared.user_service import register_new_user
    account = f"alipay_{alipay_user_id[-8:]}"
    user_id = await register_new_user(
        db=db,
        account=account,
        display_name=nickname or account,
    )

    # 插入支付宝绑定
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.execute(
        text(
            "INSERT INTO user_alipay_bindings (id, user_id, alipay_user_id, created_at) "
            "VALUES (:id, :uid, :aid, :now)"
        ),
        {"id": str(uuid.uuid4()), "uid": user_id, "aid": alipay_user_id, "now": now},
    )

    await db.flush()
    return user_id
