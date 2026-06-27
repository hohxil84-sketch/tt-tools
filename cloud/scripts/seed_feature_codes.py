"""
一次性脚本：将所有功能码同步到 feature_codes 表。

用法：
  cd cloud
  python scripts/seed_feature_codes.py

幂等操作 — 已存在的 code 不会被覆盖。
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
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text

    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/tt_tools")
    engine = create_async_engine(db_url, echo=False)

    # 全部 13 个功能码（与系统中套餐使用的功能开关对齐）
    all_features = [
        # 云端 AI
        ("ai_copy_cloud", "AI 文案生成", "cloud_ai", "云端 AI 生成营销文案"),
        ("ai_render_cloud", "AI 效果图生成", "cloud_ai", "云端 AI 生成产品效果图"),
        ("ai_image_tools_cloud", "AI 高级图片", "cloud_ai", "云端 AI 高级图片处理（已拆分，保留兼容）"),
        ("upscale_image_cloud", "AI 高清修复", "cloud_ai", "云端 AI 提升图片分辨率"),
        ("vectorize_image_cloud", "AI 转矢量", "cloud_ai", "云端 AI 图片转矢量图"),
        ("ai_edit_image_cloud", "AI 智能改图", "cloud_ai", "云端 AI 智能编辑图片"),
        ("remove_bg_cloud", "AI 高级抠图", "cloud_ai", "云端 AI 高级背景移除"),
        ("ocr_cloud", "AI 高级 OCR", "cloud_ai", "云端 AI 高精度文字识别"),
        ("priority_queue", "优先队列", "cloud_ai", "请求优先处理，降低排队延迟"),
        ("reseller_panel", "经销商面板", "cloud_ai", "经销商管理面板访问权限"),
        # 本地付费
        ("resize_image_local_paid", "图片改尺寸", "local_paid", "本地批量图片尺寸调整"),
        ("pdf_image_convert_local_paid", "PDF/图片互转", "local_paid", "本地 PDF 与图片格式互转"),
        # 本地免费
        ("ocr_local", "本地 OCR", "local_free", "本地免费文字识别"),
    ]

    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        inserted = 0
        for code, name, cat, desc in all_features:
            result = await conn.execute(
                text("SELECT id FROM feature_codes WHERE code = :code"),
                {"code": code},
            )
            existing = result.fetchone()
            if existing:
                # 已存在则更新名称和描述
                await conn.execute(
                    text("UPDATE feature_codes SET name = :name, category = :cat, description = :desc WHERE code = :code"),
                    {"code": code, "name": name, "cat": cat, "desc": desc},
                )
                print(f"  [更新] {code} → {name}")
            else:
                await conn.execute(
                    text(
                        "INSERT INTO feature_codes (id, code, name, category, description, is_active, created_at) "
                        "VALUES (:id, :code, :name, :cat, :desc, TRUE, :ts)"
                    ),
                    {"id": str(uuid.uuid4()), "code": code, "name": name, "cat": cat, "desc": desc, "ts": now},
                )
                inserted += 1
                print(f"  [新增] {code} → {name}")

    await engine.dispose()
    print(f"\n完成: 新增 {inserted} 条，总计 {len(all_features)} 条功能码已同步到数据库。")


if __name__ == "__main__":
    asyncio.run(main())
