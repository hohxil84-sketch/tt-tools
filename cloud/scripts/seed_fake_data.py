"""
假数据填充脚本 - 为每个表插入至少 10 条记录。

运行方式:
    cd d:\\TT Tools
    python cloud/scripts/seed_fake_data.py

依赖: .env 中 APP_DATABASE_URL 已正确配置。
"""
from __future__ import annotations

import os
import sys
import uuid
import random
from datetime import datetime, timezone, timedelta

# 确保项目根目录在 sys.path 中
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 加载 .env
_dotenv_path = os.path.join(_project_root, ".env")
if os.path.exists(_dotenv_path):
    with open(_dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                if key not in os.environ:
                    os.environ[key] = val

# 预加载所有 ORM 模型到 Base.metadata（按依赖顺序）
import importlib.util as _iu

def _load_models(module_path_parts, alias):
    """通过 importlib 加载模型文件，确保表注册到 Base.metadata。"""
    file_path = os.path.join(_project_root, *module_path_parts)
    dir_path = os.path.join(_project_root, *module_path_parts[:-1])
    _orig_path = list(sys.path)
    sys.path.insert(0, dir_path)
    _saved = {}
    for _k in ("models", "service", "schemas", "router"):
        if _k in sys.modules:
            _saved[_k] = sys.modules.pop(_k)
    try:
        spec = _iu.spec_from_file_location(alias, file_path)
        mod = _iu.module_from_spec(spec)
        sys.modules[alias] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        for _k in ("models", "service", "schemas", "router"):
            sys.modules.pop(_k, None)
        for _k, _v in _saved.items():
            sys.modules[_k] = _v
        sys.path.clear()
        sys.path.extend(_orig_path)

print("[1/3] 加载 ORM 模型...")

# 按依赖顺序加载
_auth_models = _load_models(
    ["cloud", "modules", "auth-device", "models.py"], "auth_device_models"
)
User = _auth_models.User
Device = _auth_models.Device
AuthSession = _auth_models.AuthSession

_credits_models = _load_models(
    ["cloud", "modules", "credits-billing", "models.py"], "credits_billing_models"
)
Plan = _credits_models.Plan
CreditAccount = _credits_models.CreditAccount
CreditLedger = _credits_models.CreditLedger
UsageEvent = _credits_models.UsageEvent

_order_models = _load_models(
    ["cloud", "modules", "orders_recharge", "models.py"], "orders_recharge_models"
)
Order = _order_models.Order

_provider_models = _load_models(
    ["cloud", "modules", "provider-log", "models.py"], "provider_log_models"
)
ProviderCallLog = _provider_models.ProviderCallLog

_risk_mod = _load_models(
    ["cloud", "admin", "modules", "admin-ops", "models.py"], "admin_ops_models"
)
RiskLog = _risk_mod.RiskLog

print("   -> 模型加载完成")

# --- 数据库连接 ---
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from cloud.shared.database import Base

_database_url = os.environ.get("APP_DATABASE_URL", "")
if not _database_url:
    print("ERROR: APP_DATABASE_URL 未配置! 请在 .env 中设置.")
    sys.exit(1)

_host_info = _database_url.split("@")[-1] if "@" in _database_url else _database_url
print(f"[2/3] 连接数据库: {_host_info}")

_engine = create_async_engine(_database_url, echo=False)
_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _days_ago(n: int) -> datetime:
    return (_now() - timedelta(days=n))


def _rand_str(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


async def seed_all():
    """创建表并插入假数据。"""
    # 1. 创建所有表
    print("[3/3] 创建表并插入假数据...")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("   -> 表创建/确认完成")

    async with _session_factory() as session:
        # ========== 1. users (10 + 1 admin) ==========
        print("   [users] 插入中...")
        user_ids = [_rand_str("user-") for _ in range(10)]
        users = [
            User(
                id=user_ids[i],
                account=f"user{i+1:02d}@alphoria.com",
                password_hash="$2b$12$" + uuid.uuid4().hex[:53],
                display_name=f"测试用户{i+1:02d}",
                role="user" if i < 8 else "admin",
                status="active" if i < 9 else "blocked",
                plan_code=["free", "free", "standard", "standard", "pro", "free", "standard", "pro", "free", "standard"][i],
                created_at=_days_ago(30 - i * 2),
                updated_at=_now(),
            )
            for i in range(10)
        ]
        import bcrypt
        admin_pw = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()
        users.append(User(
            id="admin-seed-001",
            account="admin@alphoria.com",
            password_hash=admin_pw,
            display_name="系统管理员",
            role="admin",
            status="active",
            plan_code="pro",
            created_at=_days_ago(60),
            updated_at=_now(),
        ))
        session.add_all(users)
        await session.flush()
        print(f"   [users] -> {len(users)} 条 (含 admin@alphoria.com / admin)")

        # ========== 2. devices (10) ==========
        print("   [devices] 插入中...")
        device_names = ["前台", "设计", "老板", "后台", "笔记本", "工作站", "门店A", "门店B", "门店C", "服务器"]
        device_ids = [_rand_str("dev-") for _ in range(10)]
        devices = [
            Device(
                id=device_ids[i],
                user_id=user_ids[i],
                device_fingerprint_hash=_rand_str("fp-"),
                device_name=f"电脑-{device_names[i]}",
                client_version="0.1.0",
                status="active" if i < 9 else "blocked",
                bound_at=_days_ago(28 - i * 2),
                last_seen_at=_now() if i < 9 else _days_ago(10),
                created_at=_days_ago(28 - i * 2),
                updated_at=_now(),
            )
            for i in range(10)
        ]
        session.add_all(devices)
        await session.flush()
        print(f"   [devices] -> {len(devices)} 条")

        # ========== 3. plans (10) ==========
        print("   [plans] 插入中...")
        plan_ids = [_rand_str("plan-") for _ in range(10)]
        plan_data = [
            ("free", "免费套餐", 10, {"resize_image_local_paid": {"daily_limit": 3}}, "active"),
            ("standard", "标准套餐", 500, {"ai_copy_cloud": True, "resize_image_local_paid": {"daily_limit": 10}}, "active"),
            ("pro", "专业套餐", 2000, {"ai_copy_cloud": True, "ai_render_cloud": True, "ai_image_tools_cloud": True}, "active"),
            ("enterprise", "企业套餐", 10000, {"ai_copy_cloud": True, "ai_render_cloud": True, "ai_image_tools_cloud": True, "priority_queue": True}, "active"),
            ("starter", "入门套餐", 50, {"ai_copy_cloud": True}, "active"),
            ("designer", "设计师套餐", 800, {"ai_render_cloud": True, "ai_image_tools_cloud": True}, "active"),
            ("basic_v2", "基础版 v2", 30, {"ai_copy_cloud": True, "resize_image_local_paid": {"daily_limit": 5}}, "disabled"),
            ("trial", "试用套餐", 5, {"resize_image_local_paid": {"daily_limit": 1}}, "active"),
            ("premium_old", "高级版(旧)", 1500, {"ai_copy_cloud": True, "ai_render_cloud": True}, "disabled"),
            ("reseller", "经销商套餐", 3000, {"ai_copy_cloud": True, "ai_render_cloud": True, "ai_image_tools_cloud": True, "reseller_panel": True}, "active"),
        ]
        plans = [
            Plan(
                id=plan_ids[i],
                code=plan_data[i][0],
                name=plan_data[i][1],
                monthly_grant=plan_data[i][2],
                enabled_features_json=plan_data[i][3],
                status=plan_data[i][4],
                created_at=_days_ago(90 - i * 7),
                updated_at=_now(),
            )
            for i in range(10)
        ]
        session.add_all(plans)
        await session.flush()
        print(f"   [plans] -> {len(plans)} 条")

        # ========== 4. credit_accounts (10) ==========
        print("   [credit_accounts] 插入中...")
        plan_codes = ["free", "standard", "pro", "enterprise", "starter", "designer", "free", "standard", "pro", "free"]
        grants = [10, 500, 2000, 10000, 50, 800, 10, 500, 2000, 10]
        acct_ids = [_rand_str("acct-") for _ in range(10)]
        accounts = [
            CreditAccount(
                id=acct_ids[i],
                user_id=user_ids[i],
                plan_code=plan_codes[i],
                balance=random.randint(5, 5000),
                monthly_grant=grants[i],
                period_start=_days_ago(30),
                period_end=_days_ago(-30),
                status="active" if i < 9 else "frozen",
                created_at=_days_ago(30 - i),
                updated_at=_now(),
            )
            for i in range(10)
        ]
        session.add_all(accounts)
        await session.flush()
        print(f"   [credit_accounts] -> {len(accounts)} 条")

        # ========== 5. orders (10) ==========
        print("   [orders] 插入中...")
        order_ids = [_rand_str("ord-") for _ in range(10)]
        order_types = ["plan", "credits", "plan", "credits", "credits", "plan", "credits", "plan", "credits", "plan"]
        products = ["standard", "credits_100", "pro", "credits_500", "credits_2000", "standard", "credits_100", "enterprise", "credits_500", "designer"]
        amounts_cents = [2900, 1000, 9900, 5000, 20000, 2900, 1000, 49900, 5000, 9900]
        credit_amounts = [None, 100, None, 500, 2000, None, 100, None, 500, None]
        order_statuses = ["paid", "paid", "pending", "paid", "paid", "closed", "paid", "paid", "refunded", "pending"]
        orders = [
            Order(
                id=order_ids[i],
                user_id=user_ids[i],
                order_no=f"ORD-{_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                order_type=order_types[i],
                product_code=products[i],
                amount_cents=amounts_cents[i],
                credit_amount=credit_amounts[i],
                currency="CNY",
                status=order_statuses[i],
                paid_at=_days_ago(14 - i) if order_statuses[i] in ("paid", "refunded") else None,
                created_at=_days_ago(14 - i),
                updated_at=_now(),
            )
            for i in range(10)
        ]
        session.add_all(orders)
        await session.flush()
        print(f"   [orders] -> {len(orders)} 条")

        # ========== 6. credit_ledger (10) ==========
        print("   [credit_ledger] 插入中...")
        ledger_ids = [_rand_str("led-") for _ in range(10)]
        change_types = ["grant", "consume", "grant", "consume", "recharge", "grant", "consume", "adjust", "grant", "consume"]
        amts = [500, -50, 2000, -120, 100, 10, -30, 200, 500, -80]
        bal_afters = [500, 450, 2450, 2330, 2430, 2440, 2410, 2610, 3110, 3030]
        sources = ["system", "provider_call", "system", "provider_call", "order", "system", "provider_call", "admin", "system", "provider_call"]
        descs = [
            "月度赠送 500 额度", "AI Copy 消耗 50 额度", "月度赠送 2000 额度",
            "AI Render 消耗 120 额度", "充值 100 额度", "月度赠送 10 额度",
            "AI 图片工具消耗 30 额度", "管理员手动调整 +200", "月度赠送 500 额度",
            "AI Copy 消耗 80 额度",
        ]
        ledgers = [
            CreditLedger(
                id=ledger_ids[i],
                user_id=user_ids[i],
                account_id=acct_ids[i],
                change_type=change_types[i],
                amount=amts[i],
                balance_after=bal_afters[i],
                source_type=sources[i],
                source_id=order_ids[i] if sources[i] == "order" else None,
                description=descs[i],
                created_at=_days_ago(13 - i),
            )
            for i in range(10)
        ]
        session.add_all(ledgers)
        await session.flush()
        print(f"   [credit_ledger] -> {len(ledgers)} 条")

        # ========== 7. provider_call_log (10) ==========
        print("   [provider_call_log] 插入中...")
        pcl_ids = [_rand_str("pcl-") for _ in range(10)]
        features = ["ai_copy_cloud", "ai_render_cloud", "ai_copy_cloud", "ai_image_tools_cloud",
                     "ai_copy_cloud", "ai_render_cloud", "ai_copy_cloud", "ai_image_tools_cloud",
                     "ai_render_cloud", "ai_copy_cloud"]
        providers = ["deepseek", "openai", "deepseek", "doubao", "deepseek",
                      "openai", "deepseek", "doubao", "openai", "deepseek"]
        models = ["deepseek-chat", "gpt-4o", "deepseek-chat", "doubao-vision-pro",
                   "deepseek-chat", "gpt-4o", "deepseek-chat", "doubao-vision-pro",
                   "gpt-4o", "deepseek-chat"]
        pcl_statuses = ["success", "success", "failed", "success", "success",
                        "success", "timeout", "success", "failed", "success"]
        error_codes = [None, None, "PROVIDER_RATE_LIMITED", None, None,
                       None, "PROVIDER_TIMEOUT", None, "CONTENT_FILTERED", None]
        input_toks = [120, 300, 80, 200, 150, 400, 60, 250, 350, 100]
        output_toks = [80, 200, 0, 150, 100, 250, 0, 180, 0, 70]
        credits = [1, 3, 0, 2, 1, 4, 0, 3, 0, 1]
        latencies = [800, 2500, 300, 1500, 950, 3200, 30000, 1800, 500, 750]

        pcls = [
            ProviderCallLog(
                id=pcl_ids[i],
                request_id=_rand_str("req-"),
                user_id=user_ids[i],
                device_id=device_ids[i],
                feature=features[i],
                provider=providers[i],
                model=models[i],
                status=pcl_statuses[i],
                error_code=error_codes[i],
                input_tokens=input_toks[i],
                output_tokens=output_toks[i],
                total_tokens=input_toks[i] + output_toks[i],
                estimated_cost=round((input_toks[i] + output_toks[i]) * 0.00001, 6),
                credits_charged=credits[i],
                latency_ms=latencies[i],
                created_at=_days_ago(7 - i // 2),
            )
            for i in range(10)
        ]
        session.add_all(pcls)
        await session.flush()
        print(f"   [provider_call_log] -> {len(pcls)} 条")

        # ========== 8. risk_logs (10) ==========
        print("   [risk_logs] 插入中...")
        risk_ids = [_rand_str("risk-") for _ in range(10)]
        risk_types = ["suspicious_login", "rate_limit", "abnormal_usage", "suspicious_login",
                       "rate_limit", "credits_exhausted", "suspicious_login", "abnormal_usage",
                       "api_abuse", "credits_exhausted"]
        severities = ["medium", "low", "high", "medium", "low", "medium", "high", "high", "high", "low"]
        details = [
            {"ip": "203.0.113.1", "reason": "异地登录"},
            {"endpoint": "/api/v1/ai/copy/generate", "count": 120},
            {"reason": "疑似恶意扫描", "paths": ["/admin", "/.env", "/wp-admin"]},
            {"ip": "198.51.100.5", "reason": "非常用设备"},
            {"endpoint": "/api/v1/ai/render/generate", "count": 200},
            {"user_id": "user-005", "reason": "额度耗尽，连续请求"},
            {"ip": "192.0.2.100", "reason": "新地域登录"},
            {"reason": "短时间内大量失败请求", "fail_count": 45},
            {"endpoint": "/api/v1/auth/login", "count": 500, "reason": "暴力破解嫌疑"},
            {"user_id": "user-010", "reason": "额度耗尽，尝试切换设备"},
        ]
        risks = [
            RiskLog(
                id=risk_ids[i],
                user_id=user_ids[i],
                device_id=device_ids[i] if i % 2 == 0 else None,
                risk_type=risk_types[i],
                severity=severities[i],
                details_json=details[i],
                created_at=_days_ago(10 - i),
            )
            for i in range(10)
        ]
        session.add_all(risks)
        await session.flush()
        print(f"   [risk_logs] -> {len(risks)} 条")

        # ========== 9. auth_sessions (10) ==========
        print("   [auth_sessions] 插入中...")
        session_ids = [_rand_str("sess-") for _ in range(10)]
        auth_sessions = [
            AuthSession(
                id=session_ids[i],
                user_id=user_ids[i],
                device_id=device_ids[i],
                refresh_token_hash=_rand_str("rt-"),
                status="active" if i < 8 else "expired",
                expires_at=_now() + timedelta(days=30 if i < 8 else -1),
                created_at=_days_ago(5 - i // 2),
            )
            for i in range(10)
        ]
        session.add_all(auth_sessions)
        await session.flush()
        print(f"   [auth_sessions] -> {len(auth_sessions)} 条")

        # ========== 10. usage_events (10) ==========
        print("   [usage_events] 插入中...")
        ue_ids = [_rand_str("ue-") for _ in range(10)]
        ue_types = ["local_start", "local_success", "cloud_success", "local_start",
                     "local_success", "cloud_success", "entitlement_granted", "local_start",
                     "local_success", "cloud_success"]
        ue_features = ["ai_copy_cloud", "resize_image_local_paid", "ai_render_cloud", "ai_copy_cloud",
                        "resize_image_local_paid", "ai_image_tools_cloud", "ai_copy_cloud", "ai_copy_cloud",
                        "resize_image_local_paid", "ai_render_cloud"]
        ues = [
            UsageEvent(
                id=ue_ids[i],
                user_id=user_ids[i],
                device_id=device_ids[i] if i % 3 != 0 else None,
                feature=ue_features[i],
                event_type=ue_types[i],
                request_id=_rand_str("req-") if "cloud" in ue_types[i] else None,
                metadata_json={"source": "seed_script", "batch": 1},
                created_at=_days_ago(6 - i // 2),
            )
            for i in range(10)
        ]
        session.add_all(ues)
        await session.flush()
        print(f"   [usage_events] -> {len(ues)} 条")

        # ========== 提交 ==========
        await session.commit()

        print("")
        print("=" * 55)
        print("  假数据插入完成!")
        print("=" * 55)
        print(f"  users:              {len(users):>4} 条 (admin@alphoria.com / admin)")
        print(f"  devices:            {len(devices):>4} 条")
        print(f"  plans:              {len(plans):>4} 条")
        print(f"  credit_accounts:    {len(accounts):>4} 条")
        print(f"  orders:             {len(orders):>4} 条")
        print(f"  credit_ledger:      {len(ledgers):>4} 条")
        print(f"  provider_call_log:  {len(pcls):>4} 条")
        print(f"  risk_logs:          {len(risks):>4} 条")
        print(f"  auth_sessions:      {len(auth_sessions):>4} 条")
        print(f"  usage_events:       {len(ues):>4} 条")
        print("=" * 55)


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_all())
