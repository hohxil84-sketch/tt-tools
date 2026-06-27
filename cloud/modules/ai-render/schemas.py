"""
cloud-ai-render Pydantic 请求/响应 DTO。

所有请求和响应结构对齐 shared-contract/openapi/ai-render.yaml。
字段命名使用 snake_case，通过 Pydantic 序列化输出。
"""
from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel, Field


# ============================================================
# 请求 DTO（对齐 OpenAPI ai-render.yaml CreateAiRenderTaskRequest）
# ============================================================


class CreateAiRenderTaskRequest(BaseModel):
    """效果图生成任务创建请求，对齐 ai-render.yaml #/components/schemas/CreateAiRenderTaskRequest。

    客户端不得提交 user_id、device_id、role、plan_code、
    provider、model、estimated_cost、credits_charged 等服务端决策字段。
    """

    scene_type: str = Field(
        ..., description="场景类型（如 interior_design 室内设计、product_showcase 产品展示、poster_design 海报设计）"
    )
    prompt: str = Field(..., description="效果图生成提示词，描述期望的视觉效果")
    input_file_ids: List[str] = Field(
        ..., description="输入文件 ID 列表（已上传至云端的文件 UUID）"
    )
    style: Optional[str] = Field(
        default=None, description="风格参考（如 modern 现代、minimalist 极简、chinese 中式、european 欧式）"
    )
    size: Optional[str] = Field(
        default=None, description="输出尺寸规格（如 1920x1080、1024x1024）"
    )
    client_request_id: str = Field(
        ..., description="桌面端生成的请求追踪 ID，用于去重和幂等"
    )


# ============================================================
# 响应 DTO（对齐 OpenAPI ai-render.yaml）
# ============================================================


class ResultFile(BaseModel):
    """生成的效果图文件信息，对齐 ai-render.yaml #/components/schemas/ResultFile。"""

    file_id: str = Field(..., description="结果文件 ID（UUID）")
    url: Optional[str] = Field(default=None, description="文件访问 URL（临时签名链接）")
    mime_type: str = Field(..., description="文件 MIME 类型（如 image/png、image/jpeg）")
    width: Optional[int] = Field(default=None, description="图片宽度（像素）")
    height: Optional[int] = Field(default=None, description="图片高度（像素）")


class CreatedTaskData(BaseModel):
    """效果图生成任务创建成功响应数据，对齐 ai-render.yaml #/components/schemas/CreatedTaskData。"""

    task_id: str = Field(..., description="任务的唯一 ID（UUID）")
    status: str = Field(..., description="任务当前状态（queued / running / succeeded / failed）")
    feature: str = Field(default="ai_render_cloud", description="功能码，固定为 ai_render_cloud")
    estimated_credits: int = Field(..., description="预估消耗的 AI 额度")


class AiRenderTaskData(BaseModel):
    """效果图生成任务查询响应数据，对齐 ai-render.yaml #/components/schemas/AiRenderTaskData。

    provider、model、estimated_cost、credits_charged、provider_call_id 由云端决定，
    客户端只读展示，不得提交。
    """

    task_id: str = Field(..., description="任务的唯一 ID（UUID）")
    status: str = Field(..., description="任务当前状态（queued / running / succeeded / failed）")
    feature: str = Field(default="ai_render_cloud", description="功能码，固定为 ai_render_cloud")
    result_files: List[ResultFile] = Field(
        default_factory=list, description="生成的效果图文件列表（succeeded 时包含结果，其他状态为空数组）"
    )
    provider: Optional[str] = Field(default=None, description="实际调用的 AI Provider 名称")
    model: Optional[str] = Field(default=None, description="实际使用的模型名称")
    estimated_cost: Optional[float] = Field(default=None, description="云端估算的调用成本（美元，仅供参考）")
    credits_charged: Optional[int] = Field(default=None, description="本次调用实际扣除的 AI 额度")
    provider_call_id: Optional[str] = Field(default=None, description="Provider 调用日志关联 ID")


# ============================================================
# 服务层内部 DTO（不直接暴露给 API）
# ============================================================


class RenderContext(BaseModel):
    """服务层内部使用的渲染上下文，聚合鉴权和请求信息。

    用于在 service 层各步骤间传递信息，避免重复传入多个参数。
    """

    user_id: str = Field(..., description="用户 ID")
    device_id: Optional[str] = Field(default=None, description="设备 ID")
    role: str = Field(default="user", description="用户角色")
    plan_id: Optional[str] = Field(default=None, description="当前套餐 ID（UUID）")
    request_id: str = Field(..., description="云端请求追踪 ID")
