"""
cloud-ai-image-tools Pydantic 请求/响应 DTO。

所有请求和响应结构对齐 shared-contract/openapi/ai-image-tools.yaml。
字段命名使用 snake_case，通过 Pydantic 序列化输出。

支持 5 种高级图片 AI 子功能：
- upscale_image_cloud：高清修复
- vectorize_image_cloud：转矢量
- ai_edit_image_cloud：AI 改图
- remove_bg_cloud：高级抠图
- ocr_cloud：高级 OCR
"""
from __future__ import annotations

from typing import Optional, List, Literal

from pydantic import BaseModel, Field


# ============================================================
# 请求 DTO（对齐 OpenAPI ai-image-tools.yaml CreateAiImageToolTaskRequest）
# ============================================================


class CreateAiImageToolTaskRequest(BaseModel):
    """高级图片 AI 任务创建请求，对齐 ai-image-tools.yaml #/components/schemas/CreateAiImageToolTaskRequest。

    客户端不得提交 user_id、device_id、role、plan_code、
    provider、model、estimated_cost、credits_charged 等服务端决策字段。
    """

    feature: Literal[
        "upscale_image_cloud",
        "vectorize_image_cloud",
        "ai_edit_image_cloud",
        "remove_bg_cloud",
        "ocr_cloud",
    ] = Field(
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
    input_file_ids: List[str] = Field(
        ..., description="输入文件 ID 列表（已上传至云端的文件 UUID）"
    )
    options: Optional[dict] = Field(
        default=None,
        description="各功能的自定义选项（如目标分辨率、输出格式、OCR 语言等）",
    )
    client_request_id: str = Field(
        ..., description="桌面端生成的请求追踪 ID，用于去重和幂等"
    )


# ============================================================
# 响应 DTO（对齐 OpenAPI ai-image-tools.yaml）
# ============================================================


class ResultFile(BaseModel):
    """AI 图片处理结果文件信息，对齐 ai-image-tools.yaml #/components/schemas/ResultFile。"""

    file_id: str = Field(..., description="结果文件 ID（UUID）")
    url: Optional[str] = Field(default=None, description="文件访问 URL（临时签名链接）")
    mime_type: str = Field(..., description="文件 MIME 类型（如 image/png、image/svg+xml、application/pdf）")
    width: Optional[int] = Field(default=None, description="图片宽度（像素）")
    height: Optional[int] = Field(default=None, description="图片高度（像素）")


class CreatedTaskData(BaseModel):
    """高级图片 AI 任务创建成功响应数据，对齐 ai-image-tools.yaml #/components/schemas/CreatedTaskData。"""

    task_id: str = Field(..., description="任务的唯一 ID（UUID）")
    status: str = Field(..., description="任务当前状态（queued / running / succeeded / failed）")
    feature: str = Field(..., description="功能码，回显请求中指定的 AI 图片工具功能")
    estimated_credits: int = Field(..., description="预估消耗的 AI 额度")


class AiImageToolTaskData(BaseModel):
    """高级图片 AI 任务查询响应数据，对齐 ai-image-tools.yaml #/components/schemas/AiImageToolTaskData。

    provider、model、estimated_cost、credits_charged、provider_call_id 由云端决定，
    客户端只读展示，不得提交。

    result_json 为各功能自定义结果数据（如 OCR 文本、矢量图层信息等），
    仅任务成功时可能包含。
    """

    task_id: str = Field(..., description="任务的唯一 ID（UUID）")
    status: str = Field(..., description="任务当前状态（queued / running / succeeded / failed）")
    feature: str = Field(..., description="功能码，回显请求中指定的 AI 图片工具功能")
    result_files: List[ResultFile] = Field(
        default_factory=list,
        description="AI 处理结果文件列表（succeeded 时包含结果，其他状态为空数组）",
    )
    result_json: Optional[dict] = Field(
        default=None,
        description="各功能自定义结果数据（如 OCR 识别文本、矢量图层信息），成功时可能为 null",
    )
    provider: Optional[str] = Field(default=None, description="实际调用的 AI Provider 名称")
    model: Optional[str] = Field(default=None, description="实际使用的模型名称")
    estimated_cost: Optional[float] = Field(
        default=None, description="云端估算的调用成本（美元，仅供参考）"
    )
    credits_charged: Optional[int] = Field(
        default=None, description="本次调用实际扣除的 AI 额度"
    )
    provider_call_id: Optional[str] = Field(
        default=None, description="Provider 调用日志关联 ID"
    )


# ============================================================
# 服务层内部 DTO（不直接暴露给 API）
# ============================================================


class ImageToolContext(BaseModel):
    """服务层内部使用的图片 AI 上下文，聚合鉴权和请求信息。

    用于在 service 层各步骤间传递信息，避免重复传入多个参数。
    """

    user_id: str = Field(..., description="用户 ID")
    device_id: Optional[str] = Field(default=None, description="设备 ID")
    role: str = Field(default="user", description="用户角色")
    plan_id: Optional[str] = Field(default=None, description="当前套餐 ID（UUID）")
    request_id: str = Field(..., description="云端请求追踪 ID")
