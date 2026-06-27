"""
cloud-shared 审计日志中间件（纯 ASGI 实现）。

自动记录所有 /api/v1/admin/* 写操作到 admin_audit_logs 表。
使用纯 ASGI 中间件而非 BaseHTTPMiddleware，避免请求体读取问题。
"""
from __future__ import annotations

import json
import logging
import traceback
from typing import Optional

from starlette.types import ASGIApp, Receive, Scope, Send, Message

logger = logging.getLogger("audit")


# ============================================================
# 路径解析工具
# ============================================================

def _infer_action(method: str, path: str) -> str:
    method = method.upper()
    pl = path.lower()
    if method == "POST":
        if "batch" in pl: return "batch"
        if "adjust" in pl: return "adjust"
        if "refund" in pl: return "refund"
        if "cancel" in pl: return "cancel"
        if "status" in pl or "reset-password" in pl: return "status_change"
        return "create"
    if method in ("PATCH", "PUT"):
        if "status" in pl: return "status_change"
        return "update"
    if method == "DELETE":
        return "delete"
    return method.lower()


def _infer_target_type(path: str) -> str:
    pl = path.lower()
    if "/users" in pl: return "user"
    if "/devices" in pl: return "device"
    if "/orders" in pl: return "order"
    if "/plans" in pl: return "plan"
    if "/credits" in pl: return "credits"
    if "/feature-flags" in pl or "/features" in pl: return "feature_flag"
    if "/providers" in pl: return "provider"
    if "/audit-logs" in pl: return "audit_log"
    if "/roles" in pl or "/permissions" in pl: return "role"
    if "/feature-codes" in pl: return "feature_code"
    return "other"


def _extract_target_id(path: str) -> Optional[str]:
    import re
    parts = path.rstrip("/").split("/")
    uuid_pat = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    for part in reversed(parts):
        if uuid_pat.match(part):
            return part
    return None


_ACTION_LABELS = {
    "create": "创建", "update": "更新", "delete": "删除",
    "status_change": "修改状态", "adjust": "调整额度",
    "refund": "退款", "cancel": "取消", "batch": "批量操作",
}
_TARGET_LABELS = {
    "user": "用户", "device": "设备", "order": "订单",
    "plan": "套餐", "credits": "额度", "feature_flag": "功能开关",
    "provider": "Provider", "audit_log": "审计日志",
    "role": "角色权限", "feature_code": "功能码",
}


class AuditMiddleware:
    """纯 ASGI 审计中间件。

    不继承 BaseHTTPMiddleware，直接实现 ASGI 协议，
    避免请求体读取和上下文切换问题。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # 只处理 HTTP 请求
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")

        # 判断是否需要审计
        should_audit = (
            path.startswith("/api/v1/admin/")
            and method in ("POST", "PATCH", "PUT", "DELETE")
            and not path.startswith("/api/v1/admin/auth/")
        )

        if not should_audit:
            await self.app(scope, receive, send)
            return

        # 解析基本信息（不读 body，避免消费请求体）
        admin_user_id = ""
        admin_account = "unknown"
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"authorization":
                auth_str = header_value.decode("utf-8", errors="ignore")
                if auth_str.startswith("Bearer "):
                    try:
                        from cloud.shared.auth import decode_token
                        token_data = decode_token(auth_str[7:])
                        admin_user_id = token_data.user_id
                    except Exception as e:
                        logger.warning(f"Audit JWT decode failed: {e}")
                break

        action = _infer_action(method, path)
        target_type = _infer_target_type(path)
        target_id = _extract_target_id(path)

        # 获取 IP
        ip_address = None
        for hname, hval in scope.get("headers", []):
            if hname == b"x-forwarded-for":
                ip_address = hval.decode("utf-8", errors="ignore").split(",")[0].strip()
                break
        if not ip_address:
            client = scope.get("client")
            if client:
                ip_address = client[0]

        # 收集响应状态码
        response_status = 200

        async def _send_wrapper(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status", 200)
            await send(message)

        # 执行实际请求
        try:
            await self.app(scope, receive, _send_wrapper)
        except Exception:
            raise
        finally:
            # 请求完成后写入审计日志
            if admin_user_id:
                try:
                    await _write_audit_entry(
                        admin_user_id=admin_user_id,
                        action=action,
                        target_type=target_type,
                        target_id=target_id,
                        response_status=response_status,
                        ip_address=ip_address,
                    )
                except Exception:
                    logger.error(f"Audit write failed:\n{traceback.format_exc()}")


async def _write_audit_entry(
    admin_user_id: str,
    action: str,
    target_type: str,
    target_id: Optional[str],
    response_status: int,
    ip_address: Optional[str],
) -> None:
    """异步写入一条审计日志到数据库。"""
    import uuid
    from datetime import datetime, timezone

    try:
        from cloud.shared.database import _get_engine
        engine = _get_engine()
        if engine is None:
            logger.warning("Audit: no database engine available")
            return
    except Exception as e:
        logger.warning(f"Audit: failed to get engine: {e}")
        return

    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import text

        log_id = str(uuid.uuid4())

        # 查询管理员账号
        admin_account = "unknown"
        async with AsyncSession(engine) as session:
            try:
                user_result = await session.execute(
                    text("SELECT account FROM users WHERE id = :uid"),
                    {"uid": admin_user_id},
                )
                user_row = user_result.first()
                if user_row:
                    admin_account = user_row[0]
            except Exception:
                pass

            result_text = "成功" if 200 <= response_status < 300 else f"失败({response_status})"
            action_label = _ACTION_LABELS.get(action, action)
            target_label = _TARGET_LABELS.get(target_type, target_type)
            summary = f"{action_label}{target_label} {result_text}"

            # 使用数据库 NOW() 而非 Python datetime，避免客户端/服务端时区偏差
            await session.execute(
                text(
                    "INSERT INTO admin_audit_logs "
                    "(id, admin_user_id, admin_account, action, target_type, "
                    "target_id, summary, details_json, ip_address, created_at) "
                    "VALUES (:id, :uid, :account, :action, :target_type, "
                    ":target_id, :summary, :details, :ip, NOW())"
                ),
                {
                    "id": log_id,
                    "uid": admin_user_id,
                    "account": admin_account,
                    "action": action,
                    "target_type": target_type,
                    "target_id": target_id,
                    "summary": summary,
                    "details": json.dumps({"method": action, "status": response_status}),
                    "ip": ip_address,
                },
            )
            await session.commit()
            logger.info(f"Audit: {summary} by {admin_account}")
    except Exception:
        logger.error(f"Audit DB write failed:\n{traceback.format_exc()}")
