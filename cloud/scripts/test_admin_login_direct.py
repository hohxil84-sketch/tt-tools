"""直接测试 admin-shell login_admin 函数，打印完整 traceback"""
import sys, os, traceback
os.environ['APP_DATABASE_URL'] = 'sqlite+aiosqlite:///d:/TT Tools/data/tt_tools.db'
sys.path.insert(0, 'd:/TT Tools')

# 模拟 main.py lifespan 中的预加载
import importlib.util

_auth_device_dir = os.path.abspath(os.path.join('d:/TT Tools', 'cloud', 'modules', 'auth-device'))
if _auth_device_dir not in sys.path:
    sys.path.insert(0, _auth_device_dir)
_models_path = os.path.join(_auth_device_dir, 'models.py')
if os.path.exists(_models_path) and 'auth_device_models' not in sys.modules:
    spec = importlib.util.spec_from_file_location('auth_device_models', _models_path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules['auth_device_models'] = mod
        sys.modules.setdefault('models', mod)
        spec.loader.exec_module(mod)
        print('auth-device models loaded')

# init db
import asyncio
from cloud.shared.database import init_db, _get_session_factory

async def test():
    await init_db()
    factory = _get_session_factory()
    async with factory() as session:
        # 导入 admin-shell 的 login_admin
        from cloud.admin.modules.admin_shell.service import login_admin
        result = await login_admin(
            session,
            account='admin@tt-tools.com',
            password='admin123',
            device_fingerprint='test123',
        )
        print(f'Login OK! token={result.access_token[:30]}...')

try:
    asyncio.run(test())
except Exception:
    traceback.print_exc()
