"""
cloud-app-shell 健康检查模块。

提供：
- GET /health：基础健康检查端点，无需鉴权。
  响应格式对齐 shared-contract/openapi/common.yaml 中的 HealthResponse Schema：
  { status, version, checks }

后续可在 checks 字段中追加数据库、Redis 等组件检查。
"""
from __future__ import annotations

import sys
import os

# cloud/app-shell 目录名含连字符，无法用 Python 点号导入，故将本目录加入 sys.path
_parent_dir = os.path.dirname(os.path.abspath(__file__))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from fastapi import APIRouter, Request

import config
from config import settings

# 健康检查独立路由，不挂载 /api/v1 前缀，方便负载均衡器探测
router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(request: Request) -> dict:
    """基础健康检查。

    返回服务状态、版本号和各组件 checks。
    对齐 shared-contract/openapi/common.yaml #/components/schemas/HealthResponse。
    """
    checks: dict[str, dict] = {}

    # 未来可加入：数据库连接、Redis 连接、磁盘可用空间等检查
    # checks["database"] = {"status": "ok", "message": "连接正常"}
    # checks["redis"] = {"status": "ok", "message": "连接正常"}

    # 根据 checks 综合判断服务状态
    all_ok = all(c.get("status") == "ok" for c in checks.values())
    if not checks:
        status = "ok"
    elif all_ok:
        status = "ok"
    elif any(c.get("status") == "down" for c in checks.values()):
        status = "down"
    else:
        status = "degraded"

    return {
        "status": status,
        "version": settings.app_version,
        "checks": checks if checks else None,
    }
