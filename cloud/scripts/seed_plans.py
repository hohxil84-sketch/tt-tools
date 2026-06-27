"""
一次性脚本：确保 plans 表存在默认套餐。

用法：
  cd cloud
  python scripts/seed_plans.py

幂等操作 — 已存在的同名套餐不会被覆盖。
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

# 确保项目根目录在 sys.path 中
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
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
                os.environ.setdefault(key.strip(), val.strip())


async def main():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/tt_tools")
    engine = create_async_engine(db_url, echo=False)

    # 确保至少存在免费套餐、标准套餐、专业套餐三个默认套餐
    default_plans = [
        ("免费套餐", 10, {}),
        ("标准套餐", 500, {"ai_copy_cloud": True}),
        ("专业套餐", 2000, {"ai_copy_cloud": True, "ai_render_cloud": True}),
    ]

    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        for name, monthly_grant, features in default_plans:
            result = await conn.execute(
                text("SELECT id FROM plans WHERE name = :name"),
                {"name": name},
            )
            if result.fetchone():
                print(f"  [已存在] {name}")
            else:
                await conn.execute(
                    text(
                        "INSERT INTO plans (id, name, monthly_grant, enabled_features_json, status, created_at, updated_at) "
                        "VALUES (:id, :name, :mg, :feat::jsonb, 'active', :ts, :ts)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "mg": monthly_grant,
                        "feat": '{}' if not features else str(features).replace("'", '"'),
                        "ts": now,
                    },
                )
                print(f"  [新增] {name}")

    await engine.dispose()
    print("\n默认套餐检查完成。")


if __name__ == "__main__":
    asyncio.run(main())
