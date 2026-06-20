"""
cloud-shared 扩展配置模块。

在 cloud-app-shell AppSettings 已有字段（database_url、redis_url、log_level）
基础上，追加本层专属配置（JWT 密钥、连接池、Redis 等）。
两个 Settings 类读取同一组 APP_ 前缀环境变量，字段同名时值自然一致。
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class SharedSettings(BaseSettings):
    """cloud/shared 专属配置，只定义本层新增的字段。

    cloud-app-shell AppSettings 已有的 database_url / redis_url / log_level
    不再重复定义——本层直接按需读取同名环境变量即可。

    用 pydantic-settings 管理，所有字段可从环境变量自动读取（前缀 APP_）。
    """

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # -- 数据库（与 AppSettings 读同一 APP_DATABASE_URL 环境变量） --
    database_url: str = ""
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # -- Redis（与 AppSettings 读同一 APP_REDIS_URL 环境变量） --
    redis_url: str = ""
    redis_max_connections: int = 10

    # -- 鉴权（JWT） --
    auth_secret_key: str = "dev-secret-change-in-production"
    auth_algorithm: str = "HS256"
    auth_access_token_expire_minutes: int = 30

    # -- 日志 --
    log_level: str = "info"
    log_format: str = "text"  # text 或 json


# 全局单例
shared_settings = SharedSettings()
