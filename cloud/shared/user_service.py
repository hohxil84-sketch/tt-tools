"""
统一用户注册服务。

所有自主注册渠道（支付宝、微信、手机号等）调用统一的 register_new_user()，
确保用户创建、默认套餐分配、额度账户初始化逻辑一致且可扩展。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def register_new_user(
    db: AsyncSession,
    account: str,
    display_name: str = "",
    role: str = "user",
    password_hash: str = "",
    profile_json: dict = None,
) -> str:
    """统一注册新用户。

    自动查找默认套餐并分配额度账户。此后台手动创建用户不调用此函数
    （后台可选择套餐）。

    Args:
        db: 数据库会话
        account: 登录账号（如 alipay_xxx、wechat_xxx、phone_xxx）
        display_name: 展示名称
        role: 用户角色，默认 user
        password_hash: 密码哈希，第三方登录可为空

    Returns:
        新用户的 user_id (UUID)
    """
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 1. 查找默认套餐
    plan_result = await db.execute(
        text(
            "SELECT id, monthly_grant, expire_days FROM plans "
            "WHERE is_default = true AND status = 'active' LIMIT 1"
        )
    )
    plan_row = plan_result.fetchone()
    plan_id = plan_row[0] if plan_row else None
    plan_mg = plan_row[1] if plan_row else 0
    plan_exp = plan_row[2] if plan_row else 0

    # 2. 创建用户记录
    import json as _json
    await db.execute(
        text(
            "INSERT INTO users (id, account, password_hash, display_name, role, "
            "status, plan_id, profile_json, created_at, updated_at) "
            "VALUES (:id, :account, :pw, :dn, :role, 'active', :plan_id, "
            ":profile::jsonb, :now, :now)"
        ),
        {
            "id": user_id,
            "account": account,
            "pw": password_hash,
            "dn": display_name or account,
            "role": role,
            "plan_id": plan_id,
            "profile": _json.dumps(profile_json) if profile_json else None,
            "now": now,
        },
    )

    # 3. 有默认套餐则创建额度账户
    if plan_id:
        acct_id = str(uuid.uuid4())
        period_start = now
        if plan_exp > 0:
            period_end = now + timedelta(days=plan_exp)
        else:
            period_end = now.replace(year=now.year + 100)

        await db.execute(
            text(
                "INSERT INTO credit_accounts (id, user_id, plan_id, balance, "
                "monthly_grant, period_start, period_end, status, created_at, updated_at) "
                "VALUES (:id, :uid, :pid, :bal, :mg, :ps, :pe, 'active', :now, :now)"
            ),
            {
                "id": acct_id, "uid": user_id, "pid": plan_id,
                "bal": plan_mg, "mg": plan_mg,
                "ps": period_start, "pe": period_end, "now": now,
            },
        )

        if plan_mg > 0:
            await db.execute(
                text(
                    "INSERT INTO credit_ledger (id, user_id, account_id, change_type, "
                    "amount, balance_after, source_type, description, created_at) "
                    "VALUES (:id, :uid, :aid, 'grant', :amt, :ba, 'system', :desc, :now)"
                ),
                {
                    "id": str(uuid.uuid4()), "uid": user_id, "aid": acct_id,
                    "amt": plan_mg, "ba": plan_mg,
                    "desc": "新用户注册，默认套餐赠送额度", "now": now,
                },
            )

    await db.flush()
    return user_id
