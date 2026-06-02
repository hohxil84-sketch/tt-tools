"""
local-worker/shared/logging — 统一日志配置

基于 Python 标准库 logging 提供本地 worker 的统一日志格式和配置。
支持：
  - 控制台输出（开发模式）
  - 文件轮转输出（生产模式）
  - request_id 和 module 标记
  - 日志级别动态调整
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

# 默认日志格式：时间 级别 request_id 模块 消息
DEFAULT_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(request_id)s | "
    "%(module)s:%(lineno)d | %(message)s"
)

# 日志目录默认值
DEFAULT_LOG_DIR = os.environ.get(
    "TT_LOG_DIR",
    "D:\\localPath\\logs",
)

# 日志文件大小上限：10MB
MAX_LOG_BYTES = 10 * 1024 * 1024
# 保留日志文件数
BACKUP_COUNT = 5

# 私有模块级状态
_log_initialized: bool = False
_log_level: int = logging.INFO


class _RequestIdFilter(logging.Filter):
    """为每条日志记录注入 request_id 字段。

    如果日志记录没有 request_id，自动从上下文中获取或使用默认值。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = getattr(record, "request_id", "-")
        return True


def setup_logging(
    level: Optional[int] = None,
    log_dir: Optional[str] = None,
    log_filename: str = "local-worker.log",
    console: bool = True,
) -> None:
    r"""配置本地 worker 的统一日志系统。

    调用此函数后，所有通过 get_logger() 获取的 logger 继承此配置。

    参数：
        level: 日志级别，默认 INFO
        log_dir: 日志文件目录，默认 D:\localPath\logs
        log_filename: 日志文件名
        console: 是否同时输出到控制台
    """
    global _log_initialized, _log_level

    if level is None:
        level = logging.INFO
    _log_level = level

    log_dir = log_dir or DEFAULT_LOG_DIR
    os.makedirs(log_dir, exist_ok=True)

    # 根 logger 配置
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除已有 handler，避免重复
    root_logger.handlers.clear()

    # 请求 ID 过滤器
    request_id_filter = _RequestIdFilter()

    # 控制台 handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
        console_handler.addFilter(request_id_filter)
        root_logger.addHandler(console_handler)

    # 文件 handler（带轮转）
    log_path = os.path.join(log_dir, log_filename)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
    file_handler.addFilter(request_id_filter)
    root_logger.addHandler(file_handler)

    _log_initialized = True

    # 记录初始化信息
    root_logger.info(
        "本地 worker 日志系统初始化完成 | log_dir=%s | level=%s",
        log_dir,
        logging.getLevelName(level),
        extra={"request_id": "init"},
    )


def get_logger(name: str, request_id: Optional[str] = None) -> logging.LoggerAdapter:
    """获取带 request_id 上下文的 logger。

    如果日志系统尚未初始化，自动以默认配置初始化。

    用法：
        logger = get_logger(__name__, request_id="req_abc123")
        logger.info("开始处理任务")

    输出：
        2026-06-03 ... | INFO     | req_abc123 | module.py:42 | 开始处理任务
    """
    global _log_initialized

    if not _log_initialized:
        setup_logging()

    logger = logging.getLogger(name)
    adapter = logging.LoggerAdapter(
        logger,
        {"request_id": request_id or "-"},
    )
    return adapter


def set_log_level(level: int) -> None:
    """动态修改日志级别。"""
    global _log_level
    _log_level = level
    logging.getLogger().setLevel(level)
    for handler in logging.getLogger().handlers:
        handler.setLevel(level)
