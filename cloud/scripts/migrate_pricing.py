"""一键迁移脚本：创建定价相关新表 + 已有表加字段 + 种子数据。"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://postgres:123456@localhost:5432/tttools"


async def migrate():
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        # === 已有表加字段 ===
        for sql, desc in [
            ("ALTER TABLE plans ADD COLUMN IF NOT EXISTS plan_tier VARCHAR(20) DEFAULT ''", "plans +plan_tier"),
            ("ALTER TABLE plans ADD COLUMN IF NOT EXISTS price_cents INTEGER DEFAULT 0", "plans +price_cents"),
            ("ALTER TABLE provider_call_log ADD COLUMN IF NOT EXISTS estimated_credits_before INTEGER", "provider_call_log +estimated_credits_before"),
            ("ALTER TABLE provider_call_log ADD COLUMN IF NOT EXISTS estimated_latency_ms INTEGER", "provider_call_log +estimated_latency_ms"),
            ("ALTER TABLE ai_tasks ADD COLUMN IF NOT EXISTS estimated_credits_before INTEGER", "ai_tasks +estimated_credits_before"),
            ("ALTER TABLE ai_tasks ADD COLUMN IF NOT EXISTS estimated_latency_ms INTEGER", "ai_tasks +estimated_latency_ms"),
        ]:
            await conn.execute(text(sql))
            print(f"OK: {desc}")

        # === 新表创建 ===
        # provider_model_pricing
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS provider_model_pricing (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                provider_name VARCHAR(50) NOT NULL,
                model_name VARCHAR(100) NOT NULL,
                input_price DECIMAL(18,6) NOT NULL DEFAULT 0,
                output_price DECIMAL(18,6) NOT NULL DEFAULT 0,
                currency VARCHAR(10) DEFAULT 'CNY',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(provider_name, model_name)
            )
        """))
        print("OK: provider_model_pricing")

        # feature_pricing
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS feature_pricing (
                feature_code VARCHAR(100) PRIMARY KEY,
                min_credits INTEGER NOT NULL DEFAULT 1,
                default_max_tokens INTEGER NOT NULL DEFAULT 2048,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        print("OK: feature_pricing")

        # system_config
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_config (
                key VARCHAR(100) PRIMARY KEY,
                value VARCHAR(500) NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        print("OK: system_config")

        # provider_latency_stats
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS provider_latency_stats (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                provider_name VARCHAR(50) NOT NULL,
                model_name VARCHAR(100) NOT NULL,
                capability VARCHAR(50) NOT NULL,
                p50_latency_ms INTEGER NOT NULL DEFAULT 0,
                p95_latency_ms INTEGER NOT NULL DEFAULT 0,
                sample_count INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(provider_name, model_name, capability)
            )
        """))
        print("OK: provider_latency_stats")

        # credit_packages
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS credit_packages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                product_code VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                credit_amount INTEGER NOT NULL,
                price_cents INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        print("OK: credit_packages")

        # === 种子数据 ===
        # 模型定价
        models = [
            ("deepseek", "deepseek-chat", 1.0, 2.0),
            ("deepseek", "deepseek-v4-flash", 1.0, 2.0),
            ("deepseek", "deepseek-v4-pro", 4.0, 16.0),
            ("deepseek", "deepseek-reasoner", 4.0, 16.0),
            ("openai", "gpt-4o", 18.31, 73.24),
            ("openai", "gpt-4o-mini", 1.10, 4.39),
            ("openai", "gpt-4-turbo", 73.24, 219.72),
            ("anthropic", "claude-3-opus", 109.86, 549.30),
            ("anthropic", "claude-3-sonnet", 21.97, 109.86),
            ("anthropic", "claude-3-haiku", 1.83, 9.15),
            ("doubao", "doubao-text-default", 1.0, 2.0),
            ("doubao", "doubao-image-default", 0.0, 0.0),
            ("__default__", "__default__", 1.0, 2.0),
        ]
        for pn, mn, ip, op in models:
            await conn.execute(text("""
                INSERT INTO provider_model_pricing (id, provider_name, model_name, input_price, output_price, currency, is_active, created_at, updated_at)
                VALUES (gen_random_uuid(), :pn, :mn, :ip, :op, 'CNY', TRUE, NOW(), NOW())
                ON CONFLICT (provider_name, model_name) DO UPDATE SET
                input_price = EXCLUDED.input_price, output_price = EXCLUDED.output_price, updated_at = NOW()
            """), {"pn": pn, "mn": mn, "ip": ip, "op": op})
        print(f"OK: seeded {len(models)} model pricings")

        # 功能定价
        features = [
            ("ai_copy_cloud", 2), ("ai_render_cloud", 3),
            ("upscale_image_cloud", 3), ("vectorize_image_cloud", 3),
            ("ai_edit_image_cloud", 5), ("remove_bg_cloud", 2), ("ocr_cloud", 2),
        ]
        for fc, mc in features:
            await conn.execute(text("""
                INSERT INTO feature_pricing (feature_code, min_credits, default_max_tokens, updated_at)
                VALUES (:fc, :mc, 2048, NOW())
                ON CONFLICT (feature_code) DO UPDATE SET min_credits = EXCLUDED.min_credits, updated_at = NOW()
            """), {"fc": fc, "mc": mc})
        print(f"OK: seeded {len(features)} feature pricings")

        # 汇率
        await conn.execute(text("""
            INSERT INTO system_config (key, value, updated_at) VALUES ('credits_exchange_rate', '10', NOW())
            ON CONFLICT (key) DO NOTHING
        """))
        print("OK: credits_exchange_rate = 10")

        # 充值套餐
        packages = [
            ("credits_100", "100点额度包", 100, 1000, 1),
            ("credits_500", "500点超值包", 500, 4000, 2),
            ("credits_2000", "2000点特惠包", 2000, 15000, 3),
        ]
        for pc, nm, ca, pr, so in packages:
            await conn.execute(text("""
                INSERT INTO credit_packages (id, product_code, name, credit_amount, price_cents, sort_order, is_active, created_at, updated_at)
                VALUES (gen_random_uuid(), :pc, :nm, :ca, :pr, :so, TRUE, NOW(), NOW())
                ON CONFLICT (product_code) DO UPDATE SET
                name = EXCLUDED.name, credit_amount = EXCLUDED.credit_amount, price_cents = EXCLUDED.price_cents, updated_at = NOW()
            """), {"pc": pc, "nm": nm, "ca": ca, "pr": pr, "so": so})
        print(f"OK: seeded {len(packages)} credit packages")

        # 已有 plans 数据迁移
        await conn.execute(text("UPDATE plans SET plan_tier = 'free' WHERE monthly_grant <= 10 AND plan_tier = ''"))
        await conn.execute(text("UPDATE plans SET plan_tier = 'standard' WHERE monthly_grant > 10 AND monthly_grant <= 1000 AND plan_tier = ''"))
        await conn.execute(text("UPDATE plans SET plan_tier = 'pro' WHERE monthly_grant > 1000 AND plan_tier = ''"))
        await conn.execute(text("UPDATE plans SET price_cents = 2900 WHERE plan_tier = 'standard' AND price_cents = 0"))
        await conn.execute(text("UPDATE plans SET price_cents = 9900 WHERE plan_tier = 'pro' AND price_cents = 0"))
        print("OK: plans data migrated")

    await engine.dispose()
    print("\nAll done! 请重启服务。")


asyncio.run(migrate())
