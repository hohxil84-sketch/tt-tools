"""测试登录功能，查看详细错误。"""
import sys, os, traceback
sys.path.insert(0, 'd:/TT Tools')
os.environ['APP_DATABASE_URL'] = 'sqlite+aiosqlite:///d:/TT Tools/data/tt_tools.db'

import asyncio
from cloud.shared.database import _get_engine, _get_session_factory, init_db

async def test():
    # 预加载模型
    import importlib.util
    def load_mod(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules.setdefault(name, mod)
        spec.loader.exec_module(mod)
        return mod

    auth_dir = 'd:/TT Tools/cloud/modules/auth-device'
    if auth_dir not in sys.path:
        sys.path.insert(0, auth_dir)
    load_mod('auth_device_models', f'{auth_dir}/models.py')
    sys.modules['models'] = sys.modules['auth_device_models']
    load_mod('auth_device_service', f'{auth_dir}/service.py')
    load_mod('auth_device_schemas', f'{auth_dir}/schemas.py')

    await init_db()
    factory = _get_session_factory()

    async with factory() as session:
        try:
            from auth_device_service import login
            from auth_device_schemas import LoginRequest
            req = LoginRequest(account='admin@tt-tools.com', password='admin123', device_fingerprint='test123')
            result = await login(session, req)
            print(f'Login OK! token={result.access_token[:30]}...')
        except Exception as e:
            traceback.print_exc()

    engine = _get_engine()
    await engine.dispose()

asyncio.run(test())
