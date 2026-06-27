"""
admin-audit 测试夹具。
"""
from __future__ import annotations

import sys
import os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# 确保 cloud 目录在 sys.path 中
_cloud_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
if _cloud_dir not in sys.path:
    sys.path.insert(0, _cloud_dir)

# 确保本模块目录在 sys.path 中
_module_dir = os.path.join(os.path.dirname(__file__), "..")
if _module_dir not in sys.path:
    sys.path.insert(0, _module_dir)


@pytest.fixture
def anyio_backend():
    return "asyncio"
