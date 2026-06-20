"""
cloud-app-shell 配置管理模块。
使用 pydantic-settings 管理应用运行配置，支持环境变量自动映射。
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """应用全局配置，所有字段可从环境变量自动读取（前缀 APP_）。"""

    model_config = SettingsConfigDict(
        env_prefix="APP_",          # 环境变量前缀：APP_DEBUG、APP_HOST 等
        env_nested_delimiter="__",  # 嵌套配置分隔符
        extra="ignore",             # 忽略未定义的环境变量
    )

    # -- 基本信息 --
    app_name: str = "TT Tools Cloud"
    app_version: str = "0.1.0"
    debug: bool = False

    # -- 服务绑定 --
    host: str = "127.0.0.1"
    port: int = 8000

    # -- 数据库连接（占位，后续 cloud/shared 承载真实连接） --
    database_url: str = ""
    redis_url: str = ""

    # -- CORS 允许来源 --
    allowed_origins: list[str] = ["*"]

    # -- 日志级别 --
    log_level: str = "info"


# 全局单例，模块导入时即创建
settings = AppSettings()
