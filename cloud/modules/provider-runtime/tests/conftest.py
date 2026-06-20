"""
provider-runtime 测试夹具。

提供 MockProvider 实例、ProviderRouter 实例、标准请求等共享测试资源。

注意：cloud/modules/provider-runtime 目录名含连字符，Python 无法直接
import cloud.modules.provider_runtime。本文件将模块目录加入 sys.path 后
直接导入（对齐 auth-device 模块的处理方式）。
"""
from __future__ import annotations

import sys
import os

# 将项目根目录加入 sys.path，使 cloud.shared.* 可导入
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 将 provider-runtime 模块目录加入 sys.path（目录名含连字符，需直接导入）
_MODULE_DIR = os.path.join(_PROJECT_ROOT, "cloud", "modules", "provider-runtime")
if _MODULE_DIR not in sys.path:
    sys.path.insert(0, _MODULE_DIR)

import pytest
import pytest_asyncio

# 从 provider-runtime 模块目录直接导入（已在 sys.path 中）
from models import ProviderCallRequest, ProviderResult, ProviderUsage, ChatMessage
from mock import MockProvider
from router import ProviderRouter
from errors import ProviderError


@pytest.fixture
def mock_provider() -> MockProvider:
    """创建默认 MockProvider 实例。"""
    return MockProvider()


@pytest.fixture
def router() -> ProviderRouter:
    """创建 ProviderRouter 实例。"""
    return ProviderRouter()


@pytest.fixture
def standard_request() -> ProviderCallRequest:
    """创建标准测试请求（deepseek-chat + ai_copy_cloud）。"""
    return ProviderCallRequest(
        model="deepseek-chat",
        messages=[
            ChatMessage(role="user", content="帮我写一段广告文案"),
        ],
        feature="ai_copy_cloud",
        request_id="test-req-001",
    )


@pytest.fixture
def gpt_request() -> ProviderCallRequest:
    """创建 GPT 模型测试请求。"""
    return ProviderCallRequest(
        model="gpt-4o-mini",
        messages=[
            ChatMessage(role="user", content="Hello"),
        ],
        feature="ai_copy_cloud",
        request_id="test-req-002",
    )
