"""
cloud-provider-log —— Provider 调用日志模块。

提供 Provider 调用日志的写入和查询能力：
    - 写入：write_provider_call_log() 供 provider-runtime / AI 模块在调用完成后写入日志。
    - 查询：GET /api/v1/provider-call-logs 供桌面端查询当前用户的调用记录。

本模块是 library + API 组合模块：
    - service.py 提供可被其他模块调用的写入函数。
    - router.py 提供对外的查询 API 端点。
    - models.py 定义 provider_call_log 表的 ORM 模型。

注意：目录名含连字符（provider-log），Python 无法直接 import。
使用时需将模块目录加入 sys.path 后直接导入：
    import sys
    sys.path.insert(0, "<project_root>/cloud/modules/provider-log")
    from router import router
    from service import write_provider_call_log

使用示例（写入日志）：
    from service import write_provider_call_log
    from schemas import WriteProviderCallLogRequest

    req = WriteProviderCallLogRequest(
        request_id="req_xxx",
        feature="ai_copy_cloud",
        provider="deepseek",
        model="deepseek-chat",
        status="success",
        input_tokens=120,
        output_tokens=80,
        total_tokens=200,
        estimated_cost=0.002,
        credits_charged=1,
        latency_ms=1200,
    )
    log_entry = await write_provider_call_log(db, user_id="uuid", feature="ai_copy_cloud", req=req)
"""
from __future__ import annotations

# -- ORM 数据模型 --
from models import ProviderCallLog

# -- DTO --
from schemas import (
    WriteProviderCallLogRequest,
    ProviderCallLogItem,
    ProviderCallLogListData,
)

# -- 业务逻辑 --
from service import (
    write_provider_call_log,
    list_provider_call_logs,
)

# -- 路由 --
from router import router

__all__ = [
    # ORM
    "ProviderCallLog",
    # DTO
    "WriteProviderCallLogRequest",
    "ProviderCallLogItem",
    "ProviderCallLogListData",
    # 业务逻辑
    "write_provider_call_log",
    "list_provider_call_logs",
    # 路由
    "router",
]
