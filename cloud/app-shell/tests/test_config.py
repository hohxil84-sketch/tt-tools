"""
配置模块测试。

验证 AppSettings 的默认值和环境变量映射。
"""
from __future__ import annotations

import sys
import os

# cloud/app-shell 目录名含连字符，将父目录加入 sys.path 后直接导入
_app_shell_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if _app_shell_dir not in sys.path:
    sys.path.insert(0, _app_shell_dir)

import pytest

from config import AppSettings


class TestAppSettingsDefaults:
    """测试 AppSettings 默认值。"""

    def test_default_app_name(self) -> None:
        settings = AppSettings()
        assert settings.app_name == "TT Tools Cloud"

    def test_default_app_version(self) -> None:
        settings = AppSettings()
        assert settings.app_version == "0.1.0"

    def test_default_debug_false(self) -> None:
        settings = AppSettings()
        assert settings.debug is False

    def test_default_host(self) -> None:
        settings = AppSettings()
        assert settings.host == "127.0.0.1"

    def test_default_port(self) -> None:
        settings = AppSettings()
        assert settings.port == 8000

    def test_default_allowed_origins(self) -> None:
        settings = AppSettings()
        assert settings.allowed_origins == ["*"]

    def test_default_log_level(self) -> None:
        settings = AppSettings()
        assert settings.log_level == "info"


class TestAppSettingsEnvOverride:
    """测试 AppSettings 环境变量覆盖。"""

    def test_env_override_debug(self) -> None:
        import builtins
        os.environ["APP_DEBUG"] = "true"
        try:
            settings = AppSettings()
            assert settings.debug is True
        finally:
            del os.environ["APP_DEBUG"]

    def test_env_override_port(self) -> None:
        os.environ["APP_PORT"] = "9000"
        try:
            settings = AppSettings()
            assert settings.port == 9000
        finally:
            del os.environ["APP_PORT"]

    def test_env_override_host(self) -> None:
        os.environ["APP_HOST"] = "0.0.0.0"
        try:
            settings = AppSettings()
            assert settings.host == "0.0.0.0"
        finally:
            del os.environ["APP_HOST"]
