"""
provider-runtime 核心数据模型。

定义 Provider 调用的输入输出结构，对齐 MODULE_INTERFACES.md 中
"Provider Runtime 输出结构" 的统一定义。
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================
# Provider 调用请求
# ============================================================


class ChatMessage(BaseModel):
    """聊天消息，对齐 OpenAI Chat Completions 消息格式。"""

    role: str = Field(..., description="消息角色：system / user / assistant")
    content: str = Field(..., description="消息内容")


class ProviderCallRequest(BaseModel):
    """Provider 调用请求。

    上层业务模块构造此请求，交由 ProviderRouter / BaseProvider 执行。
    请求中不包含 user_id、device_id 等客户端禁止提交字段。
    """

    model: str = Field(..., description="模型名称，如 deepseek-chat、gpt-4o")
    messages: list[ChatMessage] = Field(..., description="对话消息列表")
    feature: str = Field(..., description="功能码，如 ai_copy_cloud")
    max_tokens: int = Field(default=2048, description="最大生成 token 数")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="采样温度")
    extra_options: dict[str, Any] = Field(
        default_factory=dict, description="Provider 特有选项，透传"
    )
    request_id: str = Field(default="", description="云端请求追踪 ID")


# ============================================================
# Provider 用量结构（对齐 MODULE_INTERFACES.md 输出规范）
# ============================================================


class ProviderUsage(BaseModel):
    """Provider 返回的用量信息。

    统一解析各 Provider 的 usage 字段，字段名对齐 provider_call_log 表结构。
    """

    input_tokens: int = Field(default=0, description="输入 / prompt token 数")
    output_tokens: int = Field(default=0, description="输出 / completion token 数")
    total_tokens: int = Field(default=0, description="总 token 数")
    reasoning_tokens: int = Field(default=0, description="推理 token 数（如 o1 系列）")
    cached_tokens: int = Field(default=0, description="缓存命中 token 数")
    image_count: int = Field(default=0, description="处理的图片数量")


# ============================================================
# Provider 统一输出结果（对齐 MODULE_INTERFACES.md 输出结构）
# ============================================================


class ProviderResult(BaseModel):
    """Provider 调用统一输出。

    所有 Provider 实现（mock / 真实 API）都必须返回此结构。
    对齐 MODULE_INTERFACES.md "Provider Runtime 输出结构"。
    """

    provider: str = Field(..., description="Provider 名称，如 deepseek、openai")
    model: str = Field(..., description="实际使用的模型名称")
    status: str = Field(..., description="调用结果：success / failed / timeout")
    text: str = Field(default="", description="生成的文本内容")
    files: list[dict[str, Any]] = Field(
        default_factory=list, description="生成的文件引用列表（如图片生成结果）"
    )
    usage: ProviderUsage = Field(
        default_factory=ProviderUsage, description="用量详情"
    )
    estimated_cost: float = Field(default=0.0, description="估算成本（人民币）")
    raw_usage_json: dict[str, Any] = Field(
        default_factory=dict, description="Provider 原始 usage JSON，仅服务端使用"
    )
    provider_request_id: str = Field(
        default="", description="Provider 返回的请求 ID"
    )
    latency_ms: int = Field(default=0, description="调用延迟（毫秒）")
    error_code: Optional[str] = Field(
        default=None, description="失败时的统一错误码"
    )
    error_message: Optional[str] = Field(
        default=None, description="失败时的错误描述"
    )
