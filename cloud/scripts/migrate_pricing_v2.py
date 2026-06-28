"""v2 迁移：provider_model_pricing 关联 providers 表"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://postgres:123456@localhost:5432/tttools"


async def migrate():
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        # 1. 加 provider_id 列
        await conn.execute(text(
            "ALTER TABLE provider_model_pricing ADD COLUMN IF NOT EXISTS provider_id VARCHAR(36)"
        ))
        print("OK: +provider_id")

        # 2. 从 providers 表匹配 name → id
        await conn.execute(text("""
            UPDATE provider_model_pricing pmp
            SET provider_id = p.id
            FROM providers p
            WHERE pmp.provider_id IS NULL AND pmp.provider_name = p.name
        """))
        print("OK: migrated provider_name → provider_id")

        # 3. 未匹配到的（如 __default__）用 UUID 生成
        import uuid
        result = await conn.execute(text(
            "SELECT id, provider_name FROM provider_model_pricing WHERE provider_id IS NULL"
        ))
        for row in result.all():
            new_id = str(uuid.uuid4())
            await conn.execute(text(
                "UPDATE provider_model_pricing SET provider_id = :nid WHERE id = :oid"
            ), {"nid": new_id, "oid": row[0]})
            # 如果 providers 表里没有，创建一个占位
            await conn.execute(text("""
                INSERT INTO providers (id, name, provider_type, is_enabled, priority, created_at, updated_at)
                VALUES (:id, :name, '__legacy__', FALSE, 0, NOW(), NOW())
                ON CONFLICT (name) DO NOTHING
            """), {"id": new_id, "name": row[1]})
        print("OK: orphan rows assigned")

        # 4. 删除旧唯一约束，创建新的
        await conn.execute(text(
            "ALTER TABLE provider_model_pricing DROP CONSTRAINT IF EXISTS idx_pmp_provider_model"
        ))
        await conn.execute(text(
            "ALTER TABLE provider_model_pricing DROP CONSTRAINT IF EXISTS provider_model_pricing_provider_name_model_name_key"
        ))
        # 设 NOT NULL
        await conn.execute(text(
            "ALTER TABLE provider_model_pricing ALTER COLUMN provider_id SET NOT NULL"
        ))
        # 新唯一约束
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_pmp_provider_model_v2 ON provider_model_pricing (provider_id, model_name)"
        ))
        print("OK: new unique constraint")

        # 5. provider_name 列保留（兼容过渡期），后续版本删除
        print("OK: provider_name kept for backward compat")

    await engine.dispose()
    # FK 约束
    await conn.execute(text("""
        ALTER TABLE provider_model_pricing ADD CONSTRAINT IF NOT EXISTS fk_pmp_provider
        FOREIGN KEY (provider_id) REFERENCES providers(id)
    """))
    print("OK: FK provider_model_pricing → providers")

    await conn.execute(text("""
        ALTER TABLE feature_pricing ADD CONSTRAINT IF NOT EXISTS fk_fp_feature_code
        FOREIGN KEY (feature_code) REFERENCES feature_codes(code)
    """))
    print("OK: FK feature_pricing → feature_codes")

    print("\nMigration v2 complete! 请重启服务。")


asyncio.run(migrate())
