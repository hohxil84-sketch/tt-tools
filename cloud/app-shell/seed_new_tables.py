"""
种子脚本：为新模块表插入测试数据。
用法：从项目根目录运行 python cloud/app-shell/seed_new_tables.py
"""
import sys, os
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 加载 .env 文件（确保环境变量就位）
_env_path = os.path.join(_project_root, ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
                if _k and _k not in os.environ:
                    os.environ[_k] = _v

import asyncio
import uuid
from datetime import datetime, timezone, timedelta

# 预加载所有 ORM 模型到 Base.metadata（必须先于 init_db 调用）
import importlib.util
_model_dirs = [
    'cloud/modules/auth-device',
    'cloud/modules/credits-billing',
    'cloud/modules/provider-runtime',
    'cloud/modules/provider-log',
    'cloud/modules/ai-render',
    'cloud/modules/ai-image-tools',
    'cloud/modules/orders_recharge',
    'cloud/admin/modules/admin-ops',
    'cloud/admin/modules/admin-audit',
    'cloud/admin/modules/admin-providers',
    'cloud/admin/modules/admin-feature-codes',
    'cloud/admin/modules/admin-roles',
]
for _d in _model_dirs:
    _mpath = os.path.join(_project_root, _d, 'models.py')
    if not os.path.exists(_mpath):
        continue
    _mname = _d.replace('/', '_').replace('-', '_') + '_models'
    _spec = importlib.util.spec_from_file_location(_mname, _mpath)
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules[_mname] = _mod
        _spec.loader.exec_module(_mod)

from sqlalchemy import text
from cloud.shared.database import init_db, _get_engine
from sqlalchemy.ext.asyncio import AsyncSession

ADMIN_ID = "admin-seed-0000-0000-000000000001"
_now = lambda: datetime.now(timezone.utc).replace(tzinfo=None)


async def seed():
    await init_db()
    engine = _get_engine()

    async with AsyncSession(engine) as db:
        # ============================================================
        # 1. admin_audit_logs — 10 条审计日志
        # ============================================================
        actions = [
            ("create", "user", "创建用户 zhangsan@tt.com"),
            ("update", "user", "更新用户 lisi@tt.com 展示名称"),
            ("delete", "device", "删除设备 dev-old-001"),
            ("status_change", "user", "封禁用户 wangwu@tt.com"),
            ("create", "plan", "创建套餐 enterprise"),
            ("update", "plan", "更新套餐 pro 月赠额度为 2000"),
            ("adjust", "credits", "手动赠送用户 test@tt.com 500 额度"),
            ("refund", "order", "退款订单 ORD-20260625-abc12345"),
            ("cancel", "order", "取消订单 ORD-20260626-def67890"),
            ("status_change", "device", "解封设备 dev-002"),
        ]
        for i, (action, target_type, summary) in enumerate(actions):
            await db.execute(text(
                "INSERT INTO admin_audit_logs (id, admin_user_id, admin_account, action, target_type, target_id, summary, details_json, ip_address, created_at) "
                "VALUES (:id, :uid, :acct, :action, :ttype, :tid, :summary, :details, :ip, :ts)"
            ), {
                "id": str(uuid.uuid4()),
                "uid": ADMIN_ID,
                "acct": "admin@tttools.com",
                "action": action,
                "ttype": target_type,
                "tid": str(uuid.uuid4())[:8],
                "summary": summary,
                "details": '{"operator": "admin", "result": "success"}',
                "ip": f"192.168.1.{10+i}",
                "ts": _now() - timedelta(hours=i * 3),
            })
        print("[OK] admin_audit_logs: 10 rows")

        # ============================================================
        # 2. providers — 10 条 Provider 配置
        # ============================================================
        provider_data = [
            ("deepseek-main", "deepseek", "https://api.deepseek.com", '{"text":"deepseek-chat","vision":"deepseek-vl"}', True),
            ("doubao-text", "doubao", "https://ark.cn-beijing.volces.com", '{"text":"doubao-pro-32k"}', True),
            ("doubao-image", "doubao", "https://ark.cn-beijing.volces.com", '{"image":"doubao-seedream-3"}', True),
            ("openai-gpt4", "openai", "https://api.openai.com", '{"text":"gpt-4o"}', False),
            ("openai-dalle", "openai", "https://api.openai.com", '{"image":"dall-e-3"}', False),
            ("moonshot-kimi", "moonshot", "https://api.moonshot.cn", '{"text":"moonshot-v1-8k"}', True),
            ("zhipu-glm", "zhipu", "https://open.bigmodel.cn", '{"text":"glm-4-flash"}', True),
            ("qwen-tongyi", "qwen", "https://dashscope.aliyuncs.com", '{"text":"qwen-max"}', True),
            ("baidu-ernie", "baidu", "https://aip.baidubce.com", '{"text":"ernie-4.0-8k"}', False),
            ("mock-test", "mock", "http://localhost:9999", '{"text":"mock-model"}', True),
        ]
        for i, (name, ptype, url, models, enabled) in enumerate(provider_data):
            await db.execute(text(
                "INSERT INTO providers (id, name, provider_type, api_key_encrypted, base_url, models_json, is_enabled, created_at, updated_at) "
                "VALUES (:id, :name, :ptype, :key, :url, :models, :enabled, :ts, :ts)"
            ), {
                "id": str(uuid.uuid4()),
                "name": name,
                "ptype": ptype,
                "key": f"sk-encrypted-{name}-{uuid.uuid4().hex[:8]}",
                "url": url,
                "models": models,
                "enabled": enabled,
                "ts": _now() - timedelta(days=i),
            })
        print("[OK] providers: 10 rows")

        # ============================================================
        # 3. feature_codes — 10 条功能码
        # ============================================================
        fc_data = [
            ("ai_copy_cloud", "AI 文案生成", "cloud_ai", "云端 AI 生成营销文案"),
            ("ai_render_cloud", "AI 效果图生成", "cloud_ai", "云端 AI 生成产品效果图"),
            ("upscale_image_cloud", "AI 高清修复", "cloud_ai", "云端 AI 提升图片分辨率"),
            ("vectorize_image_cloud", "AI 转矢量", "cloud_ai", "云端 AI 图片转矢量图"),
            ("ai_edit_image_cloud", "AI 智能改图", "cloud_ai", "云端 AI 智能编辑图片"),
            ("remove_bg_cloud", "云端高级抠图", "cloud_ai", "云端 AI 高级背景移除"),
            ("ocr_cloud", "云端高级 OCR", "cloud_ai", "云端 AI 高精度文字识别"),
            ("resize_image_local_paid", "图片改尺寸", "local_paid", "本地批量图片尺寸调整"),
            ("pdf_image_convert_local_paid", "PDF/图片互转", "local_paid", "本地 PDF 与图片格式互转"),
            ("ocr_local", "本地 OCR", "local_free", "本地免费文字识别"),
        ]
        for code, name, cat, desc in fc_data:
            await db.execute(text(
                "INSERT INTO feature_codes (id, code, name, category, description, is_active, created_at) "
                "VALUES (:id, :code, :name, :cat, :desc, :active, :ts)"
            ), {
                "id": str(uuid.uuid4()),
                "code": code,
                "name": name,
                "cat": cat,
                "desc": desc,
                "active": True,
                "ts": _now(),
            })
        print("[OK] feature_codes: 10 rows")

        # ============================================================
        # 4. roles — 5 条角色
        # ============================================================
        role_data = [
            ("admin", "超级管理员", "拥有系统全部权限", True),
            ("operator", "运营专员", "用户管理、订单管理、额度管理", False),
            ("auditor", "审计员", "查看审计日志和操作记录", False),
            ("finance", "财务专员", "订单管理、额度调整、退款操作", False),
            ("viewer", "只读观察员", "查看所有数据，不可修改", False),
        ]
        role_ids = {}
        for code, name, desc, is_sys in role_data:
            rid = str(uuid.uuid4())
            role_ids[code] = rid
            await db.execute(text(
                "INSERT INTO roles (id, name, code, description, is_system, created_at) "
                "VALUES (:id, :name, :code, :desc, :is_sys, :ts)"
            ), {"id": rid, "name": name, "code": code, "desc": desc, "is_sys": is_sys, "ts": _now()})
        print("[OK] roles: 5 rows")

        # ============================================================
        # 5. permissions — 27 条权限（完整 RBAC 权限集）
        # ============================================================
        perm_data = [
            # 仪表盘
            ("dashboard.read", "查看仪表盘", "dashboard", "read"),
            # 用户管理
            ("users.read", "查看用户", "users", "read"),
            ("users.create", "创建用户", "users", "create"),
            ("users.update", "编辑用户", "users", "update"),
            ("users.delete", "删除用户", "users", "delete"),
            ("users.manage", "管理用户状态", "users", "manage"),
            # 设备管理
            ("devices.read", "查看设备", "devices", "read"),
            ("devices.manage", "管理设备", "devices", "manage"),
            # 订单管理
            ("orders.read", "查看订单", "orders", "read"),
            ("orders.refund", "退款订单", "orders", "manage"),
            ("orders.cancel", "取消订单", "orders", "manage"),
            # 套餐管理
            ("plans.read", "查看套餐", "plans", "read"),
            ("plans.manage", "管理套餐", "plans", "manage"),
            # 额度管理
            ("credits.read", "查看额度", "credits", "read"),
            ("credits.adjust", "调整额度", "credits", "manage"),
            # Provider 管理
            ("providers.read", "查看 Provider", "providers", "read"),
            ("providers.manage", "管理 Provider", "providers", "manage"),
            # 功能码管理
            ("features.read", "查看功能码", "features", "read"),
            ("features.manage", "管理功能码", "features", "manage"),
            # 角色权限管理
            ("roles.read", "查看角色权限", "roles", "read"),
            ("roles.manage", "管理角色权限", "roles", "manage"),
            # 审计日志
            ("audit.read", "查看审计日志", "audit", "read"),
            # 运维管理
            ("ops.read", "查看运维数据", "ops", "read"),
            ("ops.manage", "管理运维配置", "ops", "manage"),
            # 批量操作
            ("batch.manage", "批量操作", "batch", "manage"),
            # 数据导出
            ("export.read", "导出数据", "export", "read"),
        ]
        perm_ids = {}
        for code, name, res, act in perm_data:
            pid = str(uuid.uuid4())
            perm_ids[code] = pid
            await db.execute(text(
                "INSERT INTO permissions (id, code, name, resource, action, description, created_at) "
                "VALUES (:id, :code, :name, :res, :act, :desc, :ts)"
            ), {"id": pid, "code": code, "name": name, "res": res, "act": act, "desc": f"允许{act}操作{res}", "ts": _now()})
        print("[OK] permissions: 27 rows")

        # ============================================================
        # 6. role_permissions — 关联角色和权限
        # ============================================================
        role_perm_map = {
            "admin": list(perm_ids.keys()),  # admin 拥有全部权限
            "operator": ["dashboard.read", "users.read", "users.create", "users.update", "users.manage",
                        "devices.read", "orders.read", "credits.read", "ops.read", "export.read"],
            "auditor": ["dashboard.read", "audit.read", "users.read", "devices.read",
                       "orders.read", "credits.read", "ops.read", "export.read",
                       "providers.read", "features.read", "roles.read"],
            "finance": ["dashboard.read", "orders.read", "orders.refund", "orders.cancel",
                       "credits.read", "credits.adjust", "users.read", "export.read"],
            "viewer": ["dashboard.read", "users.read", "devices.read", "orders.read", "plans.read",
                      "credits.read", "ops.read", "export.read",
                      "providers.read", "features.read", "roles.read", "audit.read"],
        }
        count = 0
        for role_code, perm_codes in role_perm_map.items():
            rid = role_ids[role_code]
            for pcode in perm_codes:
                pid = perm_ids[pcode]
                await db.execute(text(
                    "INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid) "
                    "ON CONFLICT DO NOTHING"
                ), {"rid": rid, "pid": pid})
                count += 1
        print(f"[OK] role_permissions: {count} rows")

        await db.commit()
        print("\nAll seed data inserted!")


if __name__ == "__main__":
    asyncio.run(seed())
