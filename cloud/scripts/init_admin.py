"""
一次性脚本：创建 SQLite 数据库文件并初始化管理员账号。

用法：
    cd "d:\TT Tools"
    D:\localPath\venvs\cloud-app-shell\Scripts\python.exe cloud/scripts/init_admin.py

创建的管理员账号：
    用户名：admin@tt-tools.com
    密码：admin123
"""
import sys
import os
import asyncio
import importlib.util

# 确保项目根目录在 path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)

# 设置持久化数据库路径（避免重启丢数据）
db_dir = os.path.join(_project_root, "data")
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, "tt_tools.db")
os.environ["APP_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"

from sqlalchemy import select
from cloud.shared.database import Base, _get_engine, _get_session_factory, init_db


# -- 使用 importlib 加载含连字符目录的 models 模块 --
def _load_module_file(module_name: str, file_path: str):
    """从指定文件路径加载 Python 模块。"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块: {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(module_name, mod)
    spec.loader.exec_module(mod)
    return mod


# 加载所有 models.py（使用 importlib 避免连字符问题）
# 注意：users 表被 auth-device 和 admin-users 共享定义，只加载前者
# ai_tasks 表被 ai-render 和 ai-image-tools 共享定义，只加载前者
_model_files = [
    ("auth_device.models", "cloud/modules/auth-device/models.py"),
    ("credits_billing.models", "cloud/modules/credits-billing/models.py"),
    ("provider_log.models", "cloud/modules/provider-log/models.py"),
    ("ai_render.models", "cloud/modules/ai-render/models.py"),
    ("orders_recharge.models", "cloud/modules/orders-recharge/models.py"),
    ("admin_ops.models", "cloud/admin/modules/admin-ops/models.py"),
]

for mod_name, rel_path in _model_files:
    full_path = os.path.join(_project_root, rel_path)
    if os.path.exists(full_path):
        try:
            _load_module_file(mod_name, full_path)
            print(f"  loaded: {rel_path}")
        except Exception as e:
            print(f"  skip {rel_path}: {e}")

# 加载 auth-device 的 service 模块（需要 hash_password）
# 需要将 auth-device 目录加入 sys.path，因为 service.py 内部用 "from models import ..."
_auth_device_dir = os.path.join(_project_root, "cloud", "modules", "auth-device")
if _auth_device_dir not in sys.path:
    sys.path.insert(0, _auth_device_dir)
# 确保 models 模块在 sys.modules 中以 "models" 名称可用（避免重复加载）
if "models" not in sys.modules:
    sys.modules["models"] = sys.modules["auth_device.models"]
_auth_device_service_path = os.path.join(_auth_device_dir, "service.py")
_auth_device_service = _load_module_file("auth_device.service", _auth_device_service_path)
hash_password = _auth_device_service.hash_password

# 获取 User 模型
User = sys.modules["auth_device.models"].User


async def create_admin_user():
    """创建管理员账号。"""
    # 确保所有表已创建
    await init_db()
    print(f"\n数据库路径: {db_path}")

    factory = _get_session_factory()
    async with factory() as session:
        # 检查是否已存在
        result = await session.execute(
            select(User).where(User.account == "admin@tt-tools.com")
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"管理员账号已存在: {existing.account} (id={existing.id})")
            print("无需重复创建。")
            return

        admin = User(
            account="admin@tt-tools.com",
            password_hash=hash_password("admin123"),
            display_name="管理员",
            role="admin",
            status="active",
            plan_id=None,
        )
        session.add(admin)
        await session.commit()
        print(f"管理员账号已创建:")
        print(f"  账号: admin@tt-tools.com")
        print(f"  密码: admin123")
        print(f"  角色: admin")
        print(f"  ID: {admin.id}")

    # 关闭引擎
    engine = _get_engine()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin_user())
