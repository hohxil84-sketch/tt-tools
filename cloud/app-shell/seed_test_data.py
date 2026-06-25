"""
测试数据种子脚本。
用法：从项目根目录执行:
    cd D:/TT Tools
    set APP_DATABASE_URL=sqlite+aiosqlite:///./tttools_dev.db
    python cloud/app-shell/seed_test_data.py

创建：
- 3 个套餐：free / standard / pro（均启用 ai_image_tools_cloud）
- 2 个测试账号：
  - 账号 A：test_paid@tttools.com / test123（standard 套餐，100 额度）
  - 账号 B：test_free@tttools.com / test123（free 套餐，0 额度）
"""
import asyncio
import json
import sys
import os
import uuid
from datetime import datetime, timezone

# 确保项目根目录在 path 中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 加载 .env 文件（如果存在）
env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                if key and value and key not in os.environ:
                    os.environ[key] = value

import bcrypt
import importlib.util
from sqlalchemy import text

# 先预加载所有 ORM 模型（与 init_tables.py 相同逻辑）
model_dirs = [
    'cloud/modules/auth-device',
    'cloud/modules/credits-billing',
    'cloud/modules/provider-runtime',
    'cloud/modules/provider-log',
    'cloud/modules/ai-render',
    'cloud/modules/ai-image-tools',
    'cloud/modules/orders_recharge',
]
for d in model_dirs:
    path = os.path.join(project_root, d, 'models.py')
    if not os.path.exists(path):
        print(f'SKIP (not found): {path}')
        continue
    name = d.replace('/', '_').replace('-', '_') + '_models'
    spec = importlib.util.spec_from_file_location(name, path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        print(f'Loaded: {name}')

from cloud.shared.database import init_db, _get_engine, _get_session_factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def seed():
    # 初始化数据库（创建表）
    await init_db()
    print("数据库表已初始化")

    async with _get_session_factory()() as session:
        # ---- 1. 创建套餐 ----
        plans = [
            {
                "id": str(uuid.uuid4()),
                "code": "free",
                "name": "免费套餐",
                "monthly_grant": 0,
                # AI 功能全部关闭（与 credits-billing 默认种子数据对齐）
                "enabled_features_json": json.dumps({
                    "ocr_local": True,
                    "remove_bg_local": True,
                    "id_photo_local": True,
                    "preflight_check_local": True,
                    "format_convert_local": True,
                    "resize_image_local_paid": {"daily_limit": 3},
                    "pdf_image_convert_local_paid": {"daily_limit": 2},
                    "ai_copy_cloud": False,
                    "ai_render_cloud": False,
                    "ai_image_tools_cloud": False,
                }),
                "status": "active",
            },
            {
                "id": str(uuid.uuid4()),
                "code": "standard",
                "name": "标准套餐",
                "monthly_grant": 100,
                # AI 功能全开，包含所有子功能码（与 credits-billing 默认种子数据对齐）
                "enabled_features_json": json.dumps({
                    "resize_image_local_paid": True,
                    "pdf_image_convert_local_paid": True,
                    "ai_copy_cloud": True,
                    "ai_render_cloud": True,
                    "ai_image_tools_cloud": True,
                    "upscale_image_cloud": True,
                    "vectorize_image_cloud": True,
                    "ai_edit_image_cloud": True,
                    "remove_bg_cloud": True,
                    "ocr_cloud": True,
                }),
                "status": "active",
            },
            {
                "id": str(uuid.uuid4()),
                "code": "pro",
                "name": "专业套餐",
                "monthly_grant": 500,
                "enabled_features_json": json.dumps({
                    "resize_image_local_paid": True,
                    "pdf_image_convert_local_paid": True,
                    "ai_copy_cloud": True,
                    "ai_render_cloud": True,
                    "ai_image_tools_cloud": True,
                    "upscale_image_cloud": True,
                    "vectorize_image_cloud": True,
                    "ai_edit_image_cloud": True,
                    "remove_bg_cloud": True,
                    "ocr_cloud": True,
                }),
                "status": "active",
            },
        ]

        for p in plans:
            now = _utcnow()
            # 检查是否已存在
            result = await session.execute(
                text("SELECT id FROM plans WHERE code = :code"),
                {"code": p["code"]},
            )
            if result.fetchone() is None:
                await session.execute(
                    text(
                        "INSERT INTO plans (id, code, name, monthly_grant, enabled_features_json, status, created_at, updated_at) "
                        "VALUES (:id, :code, :name, :mg, :efj, :status, :now, :now)"
                    ),
                    {
                        "id": p["id"],
                        "code": p["code"],
                        "name": p["name"],
                        "mg": p["monthly_grant"],
                        "efj": p["enabled_features_json"],
                        "status": p["status"],
                        "now": now,
                    },
                )
                print(f"套餐已创建: {p['code']} ({p['name']})")
            else:
                print(f"套餐已存在，跳过: {p['code']}")

        await session.commit()

        # ---- 2. 创建测试用户 ----
        password = "test123"
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        test_users = [
            {
                "id": str(uuid.uuid4()),
                "account": "test_paid@tttools.com",
                "display_name": "付费测试用户",
                "role": "user",
                "plan_code": "standard",
                "balance": 100,
            },
            {
                "id": str(uuid.uuid4()),
                "account": "test_free@tttools.com",
                "display_name": "免费测试用户",
                "role": "user",
                "plan_code": "free",
                "balance": 0,
            },
        ]

        for u in test_users:
            # 检查是否已存在
            result = await session.execute(
                text("SELECT id FROM users WHERE account = :account"),
                {"account": u["account"]},
            )
            if result.fetchone() is not None:
                print(f"用户已存在，跳过: {u['account']}")
                continue

            now = _utcnow()
            await session.execute(
                text(
                    "INSERT INTO users (id, account, password_hash, display_name, role, status, plan_code, created_at, updated_at) "
                    "VALUES (:id, :account, :ph, :dn, :role, 'active', :pc, :now, :now)"
                ),
                {
                    "id": u["id"],
                    "account": u["account"],
                    "ph": password_hash,
                    "dn": u["display_name"],
                    "role": u["role"],
                    "pc": u["plan_code"],
                    "now": now,
                },
            )
            print(f"用户已创建: {u['account']} (密码: {password})")

            # 创建额度账户
            if u["balance"] > 0:
                account_id = str(uuid.uuid4())
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if now.month == 12:
                    period_end = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    period_end = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)

                await session.execute(
                    text(
                        "INSERT INTO credit_accounts "
                        "(id, user_id, plan_code, balance, monthly_grant, period_start, period_end, status, created_at, updated_at) "
                        "VALUES (:id, :uid, :pc, :bal, :mg, :ps, :pe, 'active', :now, :now)"
                    ),
                    {
                        "id": account_id,
                        "uid": u["id"],
                        "pc": u["plan_code"],
                        "bal": u["balance"],
                        "mg": 100,
                        "ps": period_start,
                        "pe": period_end,
                        "now": now,
                    },
                )

                # 写入初始赠送流水
                await session.execute(
                    text(
                        "INSERT INTO credit_ledger "
                        "(id, user_id, account_id, change_type, amount, balance_after, source_type, description, created_at) "
                        "VALUES (:id, :uid, :aid, 'grant', :amt, :ba, 'system', :desc, :now)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "uid": u["id"],
                        "aid": account_id,
                        "amt": u["balance"],
                        "ba": u["balance"],
                        "desc": f"测试账号初始赠送额度 ({u['plan_code']} 套餐)",
                        "now": now,
                    },
                )
                print(f"  额度账户已创建: 余额 {u['balance']}")

        await session.commit()

    print("\n===== 测试数据种子完成 =====")
    print("账号 A (付费): test_paid@tttools.com / test123")
    print("  套餐: standard, 额度: 100")
    print("账号 B (免费): test_free@tttools.com / test123")
    print("  套餐: free, 额度: 0 (无 AI 图片工具权限)")
    print(f"\n数据库文件: {os.path.join(project_root, 'tttools_dev.db')}")


if __name__ == "__main__":
    asyncio.run(seed())
