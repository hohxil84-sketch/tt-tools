"""
cloud-app-shell 测试夹具。

提供 FastAPI TestClient 和配置覆盖等共享测试资源。
"""
from __future__ import annotations

import sys
import os

# cloud/app-shell 目录名含连字符，将父目录加入 sys.path 后直接导入
_app_shell_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if _app_shell_dir not in sys.path:
    sys.path.insert(0, _app_shell_dir)

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

import config
from config import AppSettings
from main import create_app


@pytest.fixture
def test_settings() -> AppSettings:
    """返回用于测试的配置（debug=False，确保错误处理器正常返回 JSON 响应）。

    debug=True 会使 Starlette ServerErrorMiddleware 重新抛出异常，
    导致自定义 UnifiedErrorResponse 处理器无法生成 JSON 错误响应。
    """
    return AppSettings(
        app_name="TT Tools Cloud Test",
        app_version="0.1.0-test",
        debug=False,
        database_url="",
        redis_url="",
        allowed_origins=["*"],
    )


@pytest.fixture
def app(test_settings: AppSettings) -> FastAPI:
    """创建测试用 FastAPI 应用实例（覆盖配置值）。

    使用 yield 语法确保配置在测试完成后才恢复。
    """
    # 保存原配置值（model_fields 从类访问，非实例访问）
    original = {}
    for field in AppSettings.model_fields:
        original[field] = getattr(config.settings, field)
        setattr(config.settings, field, getattr(test_settings, field))

    app = create_app()

    # 将 app 交由测试使用
    yield app

    # 测试完成后恢复原始配置
    for field, value in original.items():
        setattr(config.settings, field, value)


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncClient:
    """创建异步 HTTP 测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
