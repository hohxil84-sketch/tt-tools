"""
ai_image_tools DTO — 高级图片 AI API 契约。

来源：shared-contract/openapi/ai-image-tools.yaml v0.1.0
生成方式：手写，以 OpenAPI 为唯一来源。

本模块提供以下高级图片 AI 功能的统一入口：
- upscale_image_cloud：高清修复
- vectorize_image_cloud：转矢量
- ai_edit_image_cloud：AI 改图
- remove_bg_cloud：高级抠图
- ocr_cloud：高级 OCR

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
    """AI 图片处理结果文件信息"""
    file_id: str = Field(..., description="结果文件 ID（UUID）")
    url: Optional[str] = Field(None, description="文件访问 URL（临时签名链接）")
    mime_type: str = Field(..., description="文件 MIME 类型（如 image/png、image/svg+xml、application/pdf）")
    width: Optional[int] = Field(None, description="图片宽度（像素）")
    height: Optional[int] = Field(None, description="图片高度（像素）")


# ============================================================
# AI 图片工具功能码
# ============================================================

# 高级图片 AI 支持的子功能码清单
# 对应 OpenAPI feature 字段的 enum 值
_AI_IMAGE_TOOL_FEATURES = Literal[
    "upscale_image_cloud",    # 高清修复
    "vectorize_image_cloud",  # 转矢量
    "ai_edit_image_cloud",    # AI 改图
    "remove_bg_cloud",        # 高级抠图
    "ocr_cloud",              # 高级 OCR
]


# ============================================================
# 创建任务请求
# ============================================================


class CreateAiImageToolTaskRequest(BaseModel):
    """
    创建高级图片 AI 任务请求。
    通过 feature 字段指定具体的 AI 图片处理功能。

    客户端不得提交 user_id、device_id、role、plan_code、
    provider、model、estimated_cost、credits_charged 等字段。
    """
    feature: _AI_IMAGE_TOOL_FEATURES = Field(
        ...,
        description=(
            "AI 图片工具功能码："
            "upscale_image_cloud 高清修复、"
            "vectorize_image_cloud 转矢量、"
            "ai_edit_image_cloud AI 改图、"
            "remove_bg_cloud 高级抠图、"
            "ocr_cloud 高级 OCR"
        ),
    )
    input_file_ids: list[str] = Field(
        ...,
        description="输入文件 ID 列表（已上传至云端的文件 UUID）",
    )
    options: Optional[dict] = Field(
        None,
        description="各功能的自定义选项（如分辨率、输出格式、OCR 语言等）",
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
    """高级图片 AI 任务创建成功响应数据"""
    task_id: str = Field(..., description="任务的唯一 ID（UUID）")
    status: Literal["queued", "running", "succeeded", "failed"] = Field(
        ...,
        description="任务当前状态（queued 排队中、running 处理中、succeeded 成功、failed 失败）",
    )
    feature: str = Field(
        ...,
        description="功能码，回显请求中指定的 AI 图片工具功能",
    )
    estimated_credits: int = Field(..., description="预估消耗的 AI 额度")


# ============================================================
# 任务查询响应数据
# ============================================================


class AiImageToolTaskData(BaseModel):
    """
    高级图片 AI 任务查询响应数据。

    provider、model、estimated_cost、credits_charged 由云端决定，
    客户端只读展示，不得提交。

    result_json 为各功能自定义结果数据（如 OCR 文本行、矢量路径数等），
    仅任务成功时可能包含。
    """
    task_id: str = Field(..., description="任务的唯一 ID（UUID）")
    status: Literal["queued", "running", "succeeded", "failed"] = Field(
        ...,
        description="任务当前状态",
    )
    feature: str = Field(
        ...,
        description="功能码，回显请求中指定的 AI 图片工具功能",
    )
    result_files: list[ResultFile] = Field(
        default_factory=list,
        description="AI 处理结果文件列表（succeeded 时包含结果，其他状态为空数组）",
    )
    result_json: Optional[dict] = Field(
        None,
        description="各功能自定义结果数据（如 OCR 识别文本、矢量图层信息），成功时可能为 null",
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


class CreateAiImageToolTaskResponse(BaseModel):
    """
    高级图片 AI 任务创建 API 响应。
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


class AiImageToolTaskResponse(BaseModel):
    """
    高级图片 AI 任务查询 API 响应。
    遵循统一响应结构（success / data / error / request_id）。
    """
    success: bool = Field(..., description="请求是否成功")
    data: Optional[AiImageToolTaskData] = Field(
        None, description="任务查询结果，失败时为 null"
    )
    error: Optional[ErrorDetail] = Field(None, description="错误详情，成功时为 null")
    request_id: str = Field(..., description="云端生成的请求追踪 ID")
