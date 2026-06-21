"""
cloud-ai-image-tools FastAPI 路由。

提供 2 个 API 端点，全部对齐 shared-contract/openapi/ai-image-tools.yaml：
- POST /ai/image-tools/tasks — 创建高级图片 AI 任务
- GET /ai/image-tools/tasks/{task_id} — 查询任务状态和结果

标准云端 AI 调用链（对齐 MODULE_INTERFACES.md）：
    API endpoint -> auth/device check -> permission check -> credits precheck
    -> create ai_task (queued) -> provider-runtime -> provider-call-log
    -> credits charge -> update ai_task (succeeded) -> unified response

统一响应格式和错误处理通过 cloud-shared 公共层实现。

支持 5 种子功能码：
- upscale_image_cloud：高清修复
- vectorize_image_cloud：转矢量
- ai_edit_image_cloud：AI 改图
- remove_bg_cloud：高级抠图
- ocr_cloud：高级 OCR
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
# （对齐 auth-device、credits-billing、ai-copy、ai-render 等模块的导入方式）
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
if _MODULE_DIR not in sys.path:
    sys.path.insert(0, _MODULE_DIR)

from schemas import CreateAiImageToolTaskRequest, ImageToolContext
from service import create_image_tool_task, query_image_tool_task

# 创建路由，prefix 在 app-shell 装配时指定
router = APIRouter(tags=["AI Image Tools"])


# ============================================================
# AI Image Tools 端点（需要 Bearer Token 鉴权）
# ============================================================


@router.post("/ai/image-tools/tasks")
async def ai_image_tools_create_task(
    req: CreateAiImageToolTaskRequest,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """创建高级图片 AI 任务。

    根据功能码（feature）、输入文件（input_file_ids）和可选参数（options），
    提交高级图片 AI 处理任务。
    调用经过权限检查、额度预检查、Mock Provider 调用、日志记录和额度扣费。

    需要有效的 Bearer Token。
    对齐 ai-image-tools.yaml POST /ai/image-tools/tasks。

    请求字段说明：
    - feature: AI 图片工具功能码（upscale_image_cloud / vectorize_image_cloud / ai_edit_image_cloud / remove_bg_cloud / ocr_cloud）
    - input_file_ids: 输入文件 ID 列表（已上传至云端的文件 UUID）
    - options: 各功能的自定义选项（如目标分辨率、输出格式、OCR 语言等，可选）
    - client_request_id: 客户端请求追踪 ID
    """
    try:
        # 构造图片 AI 上下文
        ctx = ImageToolContext(
            user_id=current_user.user_id,
            device_id=current_user.device_id,
            role=current_user.role,
            plan_code=current_user.plan_code,
            request_id=request_id,
        )

        # 执行标准云端 AI 调用链
        data = await create_image_tool_task(db, req, ctx)
        return success_response(data.model_dump(), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )


@router.get("/ai/image-tools/tasks/{task_id}")
async def ai_image_tools_query_task(
    task_id: str,
    request_id: str = Depends(get_request_id),
    current_user: TokenData = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """查询高级图片 AI 任务。

    根据任务 ID 查询高级图片 AI 任务的状态和结果。
    用户只能查询自己的任务。

    需要有效的 Bearer Token。
    对齐 ai-image-tools.yaml GET /ai/image-tools/tasks/{task_id}。

    路径参数：
    - task_id: 高级图片 AI 任务 ID（UUID）
    """
    try:
        data = await query_image_tool_task(db, task_id, current_user.user_id)
        return success_response(data.model_dump(), request_id)
    except AppError as e:
        return error_response(
            code=e.code,
            message=e.message,
            request_id=request_id,
            status_code=e.status_code,
            details=e.details,
        )
