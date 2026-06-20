"""
cloud-shared 日志配置模块。

提供结构化的日志配置，支持：
- text / json 两种输出格式
- request_id 上下文注入（从 request.state 获取）
- 日志级别从配置读取
"""
from __future__ import annotations

import logging
import sys
from typing import Optional


def setup_logging(
    level: str = "info",
    fmt: str = "text",
) -> None:
    """配置应用级日志。

    Args:
        level: 日志级别（debug / info / warning / error）
        fmt: 输出格式（text / json）
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    # 清除已有 handler，避免重复
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level.upper())

    if fmt == "json":
        formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # 第三方库日志静默
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取带模块名的 Logger 实例。

    Args:
        name: 模块名（通常传 __name__）

    Returns:
        logging.Logger 实例
    """
    return logging.getLogger(name)


class _JsonFormatter(logging.Formatter):
    """极简 JSON 日志格式化器（零外部依赖）。"""

    def format(self, record: logging.LogRecord) -> str:
        import json
        log_entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # 注入 request_id（如有）
        req_id = getattr(record, "request_id", None)
        if req_id:
            log_entry["request_id"] = req_id
        return json.dumps(log_entry, ensure_ascii=False)
