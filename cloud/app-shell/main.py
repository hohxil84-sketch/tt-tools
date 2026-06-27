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

# 同时将项目根目录加入 sys.path，确保 cloud.shared 等顶层包可被导入
_project_root = os.path.abspath(os.path.join(_parent_dir, "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

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

    # 启动时从数据库加载 Provider 到全局 Router
    try:
        from cloud.shared.database import _get_session_factory
        _pr_dir = os.path.join(os.path.dirname(__file__), "..", "modules", "provider-runtime")
        if _pr_dir not in sys.path:
            sys.path.insert(0, _pr_dir)
        # 清理 sys.modules 中的冲突缓存，确保 provider-runtime 导入自己的 models
        for _key in list(sys.modules.keys()):
            if _key in ("models", "service", "schemas", "router", "mock", "base", "errors", "cost", "registry", "config", "deepseek", "doubao", "http_utils") or _key.startswith(("models.", "mock.", "base.", "errors.", "cost.", "registry.", "config.", "deepseek.", "doubao.", "http_utils.")):
                del sys.modules[_key]
        from registry import get_global_router  # noqa: E402
        router = get_global_router()
        session_factory = _get_session_factory()
        async with session_factory() as session:
            loaded = await router.load_from_db(session)
            if loaded == 0:
                import logging as _log
                _log.getLogger("app-shell").warning(
                    "没有已启用的 Provider，AI 功能将不可用。"
                    "请在后台「Provider 管理」中添加并启用至少一个 Provider。"
                )
    except Exception:
        import logging as _log
        _log.getLogger("app-shell").exception("Provider 加载失败")

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

    # -- 注册审计日志中间件（记录所有后台写操作） --
    from cloud.shared.audit_middleware import AuditMiddleware
    app.add_middleware(AuditMiddleware)

    # 注意：不再通过 importlib 预加载 ORM 模型，避免与后续路由注册重复导入导致
    # "Table is already defined for this MetaData instance" 错误。
    # 各模块 ORM 模型会在对应的 router 导入链中自动加载到 Base.metadata，
    # init_db() 在 lifespan startup 阶段调用时所有模型已就绪。

    # -- 注册健康检查路由（不挂 /api/v1 前缀，便于探活） --
    app.include_router(health_router)

    # -- 后续业务模块路由注册点 --
    # 格式：app.include_router(xxx_router, prefix="/api/v1")

    # 注册 auth-device 认证/设备模块路由
    _auth_device_dir = os.path.join(os.path.dirname(__file__), "..", "modules", "auth-device")
    if _auth_device_dir not in sys.path:
        sys.path.insert(0, _auth_device_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as auth_device_router  # noqa: E402
    app.include_router(auth_device_router, prefix="/api/v1")

    # 注册 admin-feature-codes 动态功能码管理模块路由（必须在 credits-billing 之前，其 FK 引用 feature_codes 表）
    _admin_fc_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "modules", "admin-feature-codes")
    if _admin_fc_dir not in sys.path:
        sys.path.insert(0, _admin_fc_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as admin_feature_codes_router  # noqa: E402
    app.include_router(admin_feature_codes_router, prefix="/api/v1")

    # 注册 credits-billing 额度/权限模块路由
    _credits_billing_dir = os.path.join(os.path.dirname(__file__), "..", "modules", "credits-billing")
    if _credits_billing_dir not in sys.path:
        sys.path.insert(0, _credits_billing_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as credits_billing_router  # noqa: E402
    app.include_router(credits_billing_router, prefix="/api/v1")
    # 保存 ORM 模型引用供 admin-billing / admin-ops 惰性加载
    if "models" in sys.modules:
        sys.modules["credits_billing_models"] = sys.modules["models"]

    # 注册 provider-log Provider 调用日志模块路由
    _provider_log_dir = os.path.join(os.path.dirname(__file__), "..", "modules", "provider-log")
    if _provider_log_dir not in sys.path:
        sys.path.insert(0, _provider_log_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as provider_log_router  # noqa: E402
    app.include_router(provider_log_router, prefix="/api/v1")
    # 保存 ORM 模型引用供 admin-ops 惰性加载
    if "models" in sys.modules:
        sys.modules["provider_log_models"] = sys.modules["models"]

    # 注册 ai-render 效果图生成模块路由
    _ai_render_dir = os.path.join(os.path.dirname(__file__), "..", "modules", "ai-render")
    if _ai_render_dir not in sys.path:
        sys.path.insert(0, _ai_render_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as ai_render_router  # noqa: E402
    app.include_router(ai_render_router, prefix="/api/v1")

    # 注册 ai-copy 文案生成模块路由
    _ai_copy_dir = os.path.join(os.path.dirname(__file__), "..", "modules", "ai-copy")
    if _ai_copy_dir not in sys.path:
        sys.path.insert(0, _ai_copy_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as ai_copy_router  # noqa: E402
    app.include_router(ai_copy_router, prefix="/api/v1")

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
    # 保存 ORM 模型引用供 admin-billing 惰性加载（Order 模型）
    if "models" in sys.modules:
        sys.modules["orders_recharge_models"] = sys.modules["models"]

    # 注册 admin-shell 后台基础入口模块路由
    # 注：prefix 为 /api/v1/admin，admin-shell 自身的 /auth/login 等路由会挂在 /api/v1/admin/auth/* 下，
    # 避免与 auth-device 的 /api/v1/auth/* 冲突
    _admin_shell_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "modules", "admin-shell")
    if _admin_shell_dir not in sys.path:
        sys.path.insert(0, _admin_shell_dir)
    # 清理 admin 模块通用缓存名
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as admin_shell_router  # noqa: E402
    app.include_router(admin_shell_router, prefix="/api/v1/admin")

    # 注册 admin-users 后台用户和设备管理模块路由
    _admin_users_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "modules", "admin-users")
    if _admin_users_dir not in sys.path:
        sys.path.insert(0, _admin_users_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as admin_users_router  # noqa: E402
    app.include_router(admin_users_router, prefix="/api/v1")
    # 保存 ORM 模型引用供 admin-billing / admin-ops 惰性加载（User 模型）
    if "models" in sys.modules:
        sys.modules["admin_users_models"] = sys.modules["models"]

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

    # 注册 admin-audit 审计日志模块路由
    _admin_audit_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "modules", "admin-audit")
    if _admin_audit_dir not in sys.path:
        sys.path.insert(0, _admin_audit_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as admin_audit_router  # noqa: E402
    app.include_router(admin_audit_router, prefix="/api/v1")

    # 注册 admin-batch 批量操作模块路由
    _admin_batch_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "modules", "admin-batch")
    if _admin_batch_dir not in sys.path:
        sys.path.insert(0, _admin_batch_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as admin_batch_router  # noqa: E402
    app.include_router(admin_batch_router, prefix="/api/v1")

    # 注册 admin-export 数据导出模块路由
    _admin_export_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "modules", "admin-export")
    if _admin_export_dir not in sys.path:
        sys.path.insert(0, _admin_export_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as admin_export_router  # noqa: E402
    app.include_router(admin_export_router, prefix="/api/v1")

    # 注册 admin-providers Provider 配置管理模块路由
    _admin_providers_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "modules", "admin-providers")
    if _admin_providers_dir not in sys.path:
        sys.path.insert(0, _admin_providers_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as admin_providers_router  # noqa: E402
    app.include_router(admin_providers_router, prefix="/api/v1")

    # 注册 admin-roles RBAC 权限管理模块路由
    _admin_roles_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "modules", "admin-roles")
    if _admin_roles_dir not in sys.path:
        sys.path.insert(0, _admin_roles_dir)
    for _key in list(sys.modules.keys()):
        if _key in ("router", "service", "schemas", "models") or _key.startswith(("router.", "service.", "schemas.", "models.")):
            del sys.modules[_key]
    from router import router as admin_roles_router  # noqa: E402
    app.include_router(admin_roles_router, prefix="/api/v1")

    # -- 生产模式：托管 admin-web 前端静态文件（SPA） --
    # 构建产物位于 cloud/admin/modules/admin-web/dist/
    # 使用路由处理器而非 StaticFiles mount，保证 SPA fallback 可靠：
    #   - /admin/assets/* → 实际文件（JS/CSS）
    #   - /admin/*        → index.html（React Router 接管路由）
    # API 路由 /api/v1/admin/* 不受影响（路径前缀不同）
    _admin_web_dist = os.path.join(
        os.path.dirname(__file__), "..", "admin", "modules", "admin-web", "dist"
    )
    if os.path.isdir(_admin_web_dist):
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles

        # 静态资源（JS/CSS/图片等）挂载到 /admin/assets
        _assets_dir = os.path.join(_admin_web_dist, "assets")
        if os.path.isdir(_assets_dir):
            app.mount(
                "/admin/assets",
                StaticFiles(directory=_assets_dir),
                name="admin_web_assets",
            )

        # SPA 路由：所有 /admin/... 路径未命中静态文件时返回 index.html
        # 注意：FastAPI 路由优先级高于 mount，所以这个 catch-all 会生效
        _index_html = os.path.join(_admin_web_dist, "index.html")

        @app.get("/admin/{full_path:path}")
        async def _admin_spa(full_path: str = ""):
            """SPA fallback：所有 /admin/* 路由返回 index.html。

            /admin/assets/* 已被上面的 StaticFiles mount 处理，不会进入此函数。
            React Router 会根据浏览器 URL 渲染对应页面。
            """
            # 如果请求匹配到 dist 中的实际文件（非 assets 目录下的），直接返回
            candidate = os.path.join(_admin_web_dist, full_path)
            if full_path and os.path.isfile(candidate) and not full_path.startswith("assets/"):
                return FileResponse(candidate)
            return FileResponse(_index_html)

        # /admin（无尾部斜杠）也返回 index.html
        @app.get("/admin")
        async def _admin_index():
            return FileResponse(_index_html)

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
