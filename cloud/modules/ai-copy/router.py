"""
cloud-ai-copy FastAPI 路由。

提供 1 个 API 端点，全部对齐 shared-contract/openapi/ai-copy.yaml：
- POST /ai/copy/generate — 生成广告文案

标准云端 AI 调用链（对齐 MODULE_INTERFACES.md）：
    API endpoint -> auth/device check -> permission check -> credits precheck
    -> provider-runtime -> provider-call-log -> credits charge
    -> unified response

统一响应格式和错误处理通过 cloud-shared 公共层实现。
"""
from __future__ import annotations

import sys
import os

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import (
    get_db,
    get_request_id,
    require_auth,
    success_response,
    error_response,
    AppError,
    TokenData,
)

# 将本模块目录加入 sys.path，使得同目录下的 schemas / service 可直接导入
# （对齐 auth-device、credits-billing 等模块的导入方式）
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
if _MODULE_DIR not in sys.path:
    sys.path.insert(0, _MODULE_DIR)

from schemas import AiCopyGenerateRequest, GenerateContext
from service import generate_ai_copy

# 创建路由，prefix 在 app-shell 装配时指定
router = APIRouter(tags=["AI Copy"])


# ============================================================
# AI Copy 端点（需要 Bearer Token 鉴权）
# ============================================================


@router.post("/ai/copy/generate")
async def ai_copy_generate(
    req: AiCopyGenerateRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """生成 AI 广告文案。

    根据场景、产品信息、卖点、语气等参数，通过 AI 模型生成广告文案。
    调用经过权限检查、额度预检查、Provider 调用、日志记录和额度扣费。

    需要有效的 Bearer Token。
    对齐 ai-copy.yaml POST /ai/copy/generate。

    请求字段说明：
    - scene: 使用场景（poster / social_post / ad_banner / flyer / slogan）
    - product_name: 产品/服务名称
    - selling_points: 卖点列表
    - target_audience: 目标受众（可选）
    - tone: 语气风格（direct / professional / friendly / urgent / elegant）
    - platform: 投放平台（可选）
    - extra_requirements: 额外要求（可选）
    - client_request_id: 客户端请求追踪 ID
    """
    try:
        # 构造生成上下文
        ctx = GenerateContext(
            user_id=current_user.user_id,
            device_id=current_user.device_id,
            role=current_user.role,
            plan_code=current_user.plan_code,
            request_id=request_id,
        )

        # 执行标准云端 AI 调用链
        data = await generate_ai_copy(db, req, ctx)
        return success_response(data.model_dump(), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )
