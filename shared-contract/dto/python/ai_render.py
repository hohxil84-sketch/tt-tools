"""
ai_render DTO — 云端效果图生成 API 契约。

来源：shared-contract/openapi/ai-render.yaml v0.1.0
生成方式：手写，以 OpenAPI 为唯一来源。

客户端不得提交 provider、model、estimated_cost、credits_charged 等字段。
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ============================================================
# 通用结构
# ============================================================


class ErrorDetail(BaseModel):
    """统一错误详情结构，与 common.yaml 保持一致"""
    code: str = Field(..., description="统一错误码")
    message: str = Field(..., description="人类可读的错误描述（中文）")
    details: Optional[dict] = Field(None, description="可选补充信息")


# ============================================================
# 结果文件
# ============================================================


class ResultFile(BaseModel):
    """生成的效果图文件信息"""
    file_id: str = Field(..., description="结果文件 ID（UUID）")
    url: Optional[str] = Field(None, description="文件访问 URL（临时签名链接）")
    mime_type: str = Field(..., description="文件 MIME 类型（如 image/png、image/jpeg）")
    width: Optional[int] = Field(None, description="图片宽度（像素）")
    height: Optional[int] = Field(None, description="图片高度（像素）")


# ============================================================
# 创建任务请求
# ============================================================


class CreateAiRenderTaskRequest(BaseModel):
    """
    创建效果图生成任务请求。
    客户端不得提交 user_id、device_id、role、plan_code、
    provider、model、estimated_cost、credits_charged 等字段。
    """
    scene_type: str = Field(
        ...,
        description="场景类型（如 interior_design 室内设计、product_showcase 产品展示、poster_design 海报设计）",
    )
    prompt: str = Field(
        ...,
        description="效果图生成提示词，描述期望的视觉效果",
    )
    input_file_ids: list[str] = Field(
        ...,
        description="输入文件 ID 列表（已上传至云端的文件 UUID）",
    )
    style: Optional[str] = Field(
        None,
        description="风格参考（如 modern 现代、minimalist 极简、chinese 中式、european 欧式）",
    )
    size: Optional[str] = Field(
        None,
        description="输出尺寸规格（如 1920x1080、1024x1024）",
    )
    client_request_id: str = Field(
        ...,
        description="桌面端生成的请求追踪 ID，用于去重和幂等",
    )

    # 防御性校验：请求中不得包含客户端禁止提交字段
    model_config = {"extra": "forbid"}


# ============================================================
# 创建任务响应数据
# ============================================================


class CreatedTaskData(BaseModel):
    """效果图生成任务创建成功响应数据"""
    task_id: str = Field(..., description="任务的唯一 ID（UUID）")
    status: Literal["queued", "running", "succeeded", "failed"] = Field(
        ...,
        description="任务当前状态（queued 排队中、running 处理中、succeeded 成功、failed 失败）",
    )
    feature: Literal["ai_render_cloud"] = Field(
        ...,
        description="功能码，固定为 ai_render_cloud",
    )
    estimated_credits: int = Field(..., description="预估消耗的 AI 额度")


# ============================================================
# 任务查询响应数据
# ============================================================


class AiRenderTaskData(BaseModel):
    """
    效果图生成任务查询响应数据。
    provider、model、estimated_cost、credits_charged 由云端决定，
    客户端只读展示，不得提交。
    """
    task_id: str = Field(..., description="任务的唯一 ID（UUID）")
    status: Literal["queued", "running", "succeeded", "failed"] = Field(
        ...,
        description="任务当前状态",
    )
    feature: Literal["ai_render_cloud"] = Field(
        ...,
        description="功能码，固定为 ai_render_cloud",
    )
    result_files: list[ResultFile] = Field(
        default_factory=list,
        description="生成的效果图文件列表（succeeded 时包含结果，其他状态为空数组）",
    )
    provider: Optional[str] = Field(None, description="实际调用的 AI Provider 名称")
    model: Optional[str] = Field(None, description="实际使用的模型名称")
    estimated_cost: Optional[float] = Field(
        None, description="云端估算的调用成本（美元，仅供参考）"
    )
    credits_charged: Optional[int] = Field(
        None, description="本次调用实际扣除的 AI 额度"
    )
    provider_call_id: Optional[str] = Field(
        None, description="Provider 调用日志关联 ID（运行中/完成时有值）"
    )


# ============================================================
# 创建任务响应
# ============================================================


class CreateAiRenderTaskResponse(BaseModel):
    """
    效果图生成任务创建 API 响应。
    遵循统一响应结构（success / data / error / request_id）。
    """
    success: bool = Field(..., description="请求是否成功")
    data: Optional[CreatedTaskData] = Field(
        None, description="任务创建结果，失败时为 null"
    )
    error: Optional[ErrorDetail] = Field(None, description="错误详情，成功时为 null")
    request_id: str = Field(..., description="云端生成的请求追踪 ID")


# ============================================================
# 任务查询响应
# ============================================================


class AiRenderTaskResponse(BaseModel):
    """
    效果图生成任务查询 API 响应。
    遵循统一响应结构（success / data / error / request_id）。
    """
    success: bool = Field(..., description="请求是否成功")
    data: Optional[AiRenderTaskData] = Field(
        None, description="任务查询结果，失败时为 null"
    )
    error: Optional[ErrorDetail] = Field(None, description="错误详情，成功时为 null")
    request_id: str = Field(..., description="云端生成的请求追踪 ID")
