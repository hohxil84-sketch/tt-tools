"""完整模拟 FastAPI 生命周期测试登录"""
import sys, os, asyncio, traceback
os.environ['APP_DATABASE_URL'] = 'sqlite+aiosqlite:///d:/TT Tools/data/tt_tools.db'

# 模拟 main.py 的 create_app 逻辑
_project_root = 'd:/TT Tools'
sys.path.insert(0, _project_root)

# 加载 cloud.shared
from cloud.shared.database import init_db, _get_session_factory

# 预加载 admin-users 模型（模拟 create_app 中的 router 注册效果）
import importlib.util

_admin_users_dir = os.path.join(_project_root, 'cloud', 'admin', 'modules', 'admin-users')
sys.path.insert(0, _admin_users_dir)

# 清理缓存
for _key in list(sys.modules.keys()):
    if _key in ('router', 'service', 'schemas', 'models') or _key.startswith(('router.', 'service.', 'schemas.', 'models.')):
        del sys.modules[_key]

# 加载 admin-users models（模拟 import chain: router -> service -> models）
_models_path = os.path.join(_admin_users_dir, 'models.py')
spec = importlib.util.spec_from_file_location('models', _models_path)
mod = importlib.util.module_from_spec(spec)
sys.modules['models'] = mod
spec.loader.exec_module(mod)

# 加载 admin-users service（router 导入它）
_service_path = os.path.join(_admin_users_dir, 'service.py')
spec2 = importlib.util.spec_from_file_location('service', _service_path)
mod2 = importlib.util.module_from_spec(spec2)
sys.modules['service'] = mod2
spec2.loader.exec_module(mod2)

User = sys.modules['models'].User


async def test_login():
    await init_db()
    factory = _get_session_factory()
    async with factory() as db:
        # 测试 1: 直接查询用户
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.account == 'admin@tt-tools.com'))
        user = result.scalar_one_or_none()
        print(f'User found: {user is not None}')
        if user:
            print(f'  id: {user.id}')
            print(f'  role: {user.role}')
            print(f'  password_hash[:20]: {user.password_hash[:20]}')

            # 测试 2: 调用 admin-shell service 的 login_admin（用 importlib 绕过连字符问题）
            _admin_shell_dir = os.path.join(_project_root, 'cloud', 'admin', 'modules', 'admin-shell')
            sys.path.insert(0, _admin_shell_dir)
            # 清理 sys.modules 中的 schemas（避免加载到 admin-users 的 schemas）
            for _k in ('schemas', 'router', 'service'):
                sys.modules.pop(_k, None)
            _svc_path = os.path.join(_admin_shell_dir, 'service.py')
            if 'admin_shell_service' in sys.modules:
                del sys.modules['admin_shell_service']
            spec3 = importlib.util.spec_from_file_location('admin_shell_service', _svc_path)
            mod3 = importlib.util.module_from_spec(spec3)
            sys.modules['admin_shell_service'] = mod3
            spec3.loader.exec_module(mod3)
            login_admin = mod3.login_admin
            try:
                result = await login_admin(
                    db,
                    account='admin@tt-tools.com',
                    password='admin123',
                    device_fingerprint='test',
                )
                print(f'Login OK! token={result.access_token[:30]}...')
            except Exception as e:
                print(f'Login FAILED:')
                traceback.print_exc()

asyncio.run(test_login())
