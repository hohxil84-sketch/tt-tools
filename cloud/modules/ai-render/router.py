"""
cloud-ai-render FastAPI 路由。

提供 2 个 API 端点，全部对齐 shared-contract/openapi/ai-render.yaml：
- POST /ai/render/tasks — 创建效果图生成任务
- GET /ai/render/tasks/{task_id} — 查询任务状态和结果

标准云端 AI 调用链（对齐 MODULE_INTERFACES.md）：
    API endpoint -> auth/device check -> permission check -> credits precheck
    -> create ai_task (queued) -> provider-runtime -> provider-call-log
    -> credits charge -> update ai_task (succeeded) -> unified response

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
# （对齐 auth-device、credits-billing、ai-copy 等模块的导入方式）
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
if _MODULE_DIR not in sys.path:
    sys.path.insert(0, _MODULE_DIR)

from schemas import CreateAiRenderTaskRequest, RenderContext
from service import create_render_task, query_render_task

# 创建路由，prefix 在 app-shell 装配时指定
router = APIRouter(tags=["AI Render"])


# ============================================================
# AI Render 端点（需要 Bearer Token 鉴权）
# ============================================================


@router.post("/ai/render/tasks")
async def ai_render_create_task(
    req: CreateAiRenderTaskRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """创建效果图生成任务。

    根据场景类型、提示词、输入文件等信息，提交 AI 效果图生成任务。
    调用经过权限检查、额度预检查、Mock Provider 调用、日志记录和额度扣费。

    需要有效的 Bearer Token。
    对齐 ai-render.yaml POST /ai/render/tasks。

    请求字段说明：
    - scene_type: 场景类型（interior_design / product_showcase / poster_design 等）
    - prompt: 效果图生成提示词
    - input_file_ids: 输入文件 ID 列表
    - style: 风格参考（可选，modern / minimalist / chinese / european）
    - size: 输出尺寸规格（可选，如 1920x1080）
    - client_request_id: 客户端请求追踪 ID
    """
    try:
        # 构造渲染上下文
        ctx = RenderContext(
            user_id=current_user.user_id,
            device_id=current_user.device_id,
            role=current_user.role,
            plan_code=current_user.plan_code,
            request_id=request_id,
        )

        # 执行标准云端 AI 调用链
        data = await create_render_task(db, req, ctx)
        return success_response(data.model_dump(), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )


@router.get("/ai/render/tasks/{task_id}")
async def ai_render_query_task(
    task_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """查询效果图生成任务。

    根据任务 ID 查询效果图生成任务的状态和结果。
    用户只能查询自己的任务。

    需要有效的 Bearer Token。
    对齐 ai-render.yaml GET /ai/render/tasks/{task_id}。

    路径参数：
    - task_id: 效果图生成任务 ID（UUID）
    """
    try:
        data = await query_render_task(db, task_id, current_user.user_id)
        return success_response(data.model_dump(), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )
