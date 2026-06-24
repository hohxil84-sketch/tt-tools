"""
cloud-app-shell FastAPI 应用入口。

提供：
- create_app() 工厂函数：创建并配置 FastAPI 应用实例。
- 主入口：直接运行 python main.py 启动 uvicorn 开发服务器。

后续模块通过路由装配机制接入：
    在 create_app() 中调用 app.include_router(module_router, prefix="/api/v1")
"""
from __future__ import annotations

import sys
import os
from contextlib import asynccontextmanager

# cloud/app-shell 目录名含连字符，无法用 Python 点号导入，故将本目录加入 sys.path
_parent_dir = os.path.dirname(os.path.abspath(__file__))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

import uvicorn
from fastapi import FastAPI

from config import settings
from health import router as health_router
from middleware import setup_middleware


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化资源，关闭时清理资源。"""
    from cloud.shared.database import init_db, close_db
    await init_db()
    yield
    # 关闭：释放数据库连接池
    await close_db()


def _preload_auth_device_models():
    """预加载 auth-device ORM 模型，确保 init_db() 能创建 users/devices/auth_sessions 表。

    使用 importlib 直接加载，避免与 admin-users 的 User/Device 类冲突。
    """
    import importlib.util
    _auth_device_dir = os.path.join(os.path.dirname(__file__), "..", "modules", "auth-device")
    if _auth_device_dir not in sys.path:
        sys.path.insert(0, _auth_device_dir)
    _models_path = os.path.join(_auth_device_dir, "models.py")
    if os.path.exists(_models_path) and "auth_device_models" not in sys.modules:
        spec = importlib.util.spec_from_file_location("auth_device_models", _models_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules["auth_device_models"] = mod
            # 让 auth-device models 在 sys.modules 中作为 "models" 也可用
            sys.modules.setdefault("models", mod)
            spec.loader.exec_module(mod)


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。

    Returns:
        已装配中间件和路由的 FastAPI 实例。
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        description="TT Tools 云端 API 服务。为桌面端提供认证、额度、AI 调用等能力。",
        lifespan=_lifespan,
        # API 版本前缀在路由注册时指定：/api/v1
    )

    # -- 注册基础中间件 --
    setup_middleware(app)

    # -- 注册健康检查路由（不挂 /api/v1 前缀，便于探活） --
    app.include_router(health_router)

    # -- 后续业务模块路由注册点 --
    # 格式：app.include_router(xxx_router, prefix="/api/v1")

    # 注册 ai-render 效果图生成模块路由
    _ai_render_dir = os.path.join(os.path.dirname(__file__), "..", "modules", "ai-render")
    if _ai_render_dir not in sys.path:
        sys.path.insert(0, _ai_render_dir)
    from router import router as ai_render_router  # noqa: E402
    app.include_router(ai_render_router, prefix="/api/v1")

    # 注册 ai-image-tools 高级图片 AI 模块路由
    _ai_image_tools_dir = os.path.join(os.path.dirname(__file__), "..", "modules", "ai-image-tools")
    if _ai_image_tools_dir not in sys.path:
        sys.path.insert(0, _ai_image_tools_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as ai_image_tools_router  # noqa: E402
    app.include_router(ai_image_tools_router, prefix="/api/v1")

    # 注册 orders-recharge 订单/充值模块路由
    _orders_recharge_dir = os.path.join(os.path.dirname(__file__), "..", "modules", "orders_recharge")
    if _orders_recharge_dir not in sys.path:
        sys.path.insert(0, _orders_recharge_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as orders_recharge_router  # noqa: E402
    app.include_router(orders_recharge_router, prefix="/api/v1")

    # 注册 admin-shell 后台基础入口模块路由
    _admin_shell_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "modules", "admin-shell")
    if _admin_shell_dir not in sys.path:
        sys.path.insert(0, _admin_shell_dir)
    # 清理 admin 模块通用缓存名
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as admin_shell_router  # noqa: E402
    app.include_router(admin_shell_router, prefix="/api/v1")

    # 注册 admin-users 后台用户和设备管理模块路由
    _admin_users_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "modules", "admin-users")
    if _admin_users_dir not in sys.path:
        sys.path.insert(0, _admin_users_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as admin_users_router  # noqa: E402
    app.include_router(admin_users_router, prefix="/api/v1")

    # 注册 admin-billing 后台套餐、订单、额度管理模块路由
    _admin_billing_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "modules", "admin-billing")
    if _admin_billing_dir not in sys.path:
        sys.path.insert(0, _admin_billing_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as admin_billing_router  # noqa: E402
    app.include_router(admin_billing_router, prefix="/api/v1")

    # 注册 admin-ops 后台运维管理模块路由
    _admin_ops_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "modules", "admin-ops")
    if _admin_ops_dir not in sys.path:
        sys.path.insert(0, _admin_ops_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as admin_ops_router  # noqa: E402
    app.include_router(admin_ops_router, prefix="/api/v1")

    return app


# ---------- 开发服务器直接启动入口 ----------
if __name__ == "__main__":
    uvicorn.run(
        "main:create_app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level,
        factory=True,
    )
