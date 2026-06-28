"""
cloud-auth-device Pydantic 请求/响应 DTO。

所有请求和响应结构对齐 shared-contract/openapi/auth-device.yaml。
字段命名使用 snake_case，通过 Pydantic alias 映射到 OpenAPI 字段名。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 请求 DTO（对齐 OpenAPI requestBody schemas）
# ============================================================


class LoginRequest(BaseModel):
    """登录请求，对齐 auth-device.yaml #/components/schemas/LoginRequest。"""

    account: str = Field(..., description="登录账号")
    password: str = Field(..., description="密码")
    device_fingerprint: str = Field(..., description="设备指纹（客户端生成）")
    device_name: Optional[str] = Field(default=None, description="设备名称")
    client_version: Optional[str] = Field(default=None, description="客户端版本")


class RefreshRequest(BaseModel):
    """刷新令牌请求，对齐 auth-device.yaml #/components/schemas/RefreshRequest。"""

    refresh_token: str = Field(..., description="刷新令牌")


class LogoutRequest(BaseModel):
    """退出登录请求，对齐 auth-device.yaml #/components/schemas/LogoutRequest。"""

    refresh_token: str = Field(..., description="要撤销的刷新令牌")


class BindDeviceRequest(BaseModel):
    """设备绑定请求，对齐 auth-device.yaml #/components/schemas/BindDeviceRequest。"""

    device_fingerprint: str = Field(..., description="设备指纹")
    device_name: Optional[str] = Field(default=None, description="设备名称")
    client_version: Optional[str] = Field(default=None, description="客户端版本")


# ============================================================
# 响应嵌套 DTO（对齐 OpenAPI 内嵌对象 schemas）
# ============================================================


class UserInfo(BaseModel):
    """用户信息，对齐 auth-device.yaml #/components/schemas/UserInfo。"""

    id: str = Field(..., description="用户 ID（UUID）")
    account: str = Field(..., description="登录账号")
    display_name: Optional[str] = Field(default=None, description="展示名称")
    plan_id: Optional[str] = Field(default=None, description="当前套餐 ID（UUID）")


class DeviceInfo(BaseModel):
    """设备信息，对齐 auth-device.yaml #/components/schemas/DeviceInfo。"""

    id: str = Field(..., description="设备 ID（UUID）")
    status: str = Field(..., description="设备状态：active / blocked / removed")
    is_new: bool = Field(..., description="是否为新绑定设备")


class LoginData(BaseModel):
    """登录响应数据，对齐 auth-device.yaml #/components/schemas/LoginData。"""

    access_token: str = Field(..., description="访问令牌（短期有效）")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型，固定为 bearer")
    expires_in: int = Field(..., description="access_token 有效期（秒）")
    user: UserInfo = Field(..., description="用户信息")
    device: DeviceInfo = Field(..., description="设备信息")


class RefreshData(BaseModel):
    """刷新响应数据，对齐 auth-device.yaml #/components/schemas/RefreshData。"""

    access_token: str = Field(..., description="新访问令牌")
    refresh_token: str = Field(..., description="新刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="有效期（秒）")


class LogoutData(BaseModel):
    """退出响应数据，对齐 auth-device.yaml LogoutResponse data。"""

    logged_out: bool = Field(..., description="是否已退出")


class CurrentDevice(BaseModel):
    """当前设备详情，对齐 auth-device.yaml #/components/schemas/CurrentDevice。"""

    id: str = Field(..., description="设备 ID（UUID）")
    device_fingerprint: str = Field(..., description="设备指纹")
    device_name: str = Field(..., description="设备名称")
    status: str = Field(..., description="设备状态")
    bound_at: Optional[datetime] = Field(default=None, description="绑定时间")
    last_seen_at: Optional[datetime] = Field(default=None, description="最近活跃时间")


# ============================================================
# 服务层内部 DTO（不直接暴露给 API）
# ============================================================


class TokenPair(BaseModel):
    """令牌对（服务层内部使用）。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ============================================================
# 密码重置 DTO
# ============================================================


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求。"""
    account: str = Field(..., description="登录账号")


class ForgotPasswordData(BaseModel):
    """忘记密码响应（开发阶段返回重置 token，生产改发邮件）。"""
    message: str = Field(default="密码重置链接已发送", description="提示信息")
    reset_token: Optional[str] = Field(default=None, description="重置令牌（仅开发阶段返回）")


class ResetPasswordRequest(BaseModel):
    """重置密码请求。"""
    reset_token: str = Field(..., description="密码重置令牌")
    new_password: str = Field(..., description="新密码", min_length=6)


class ResetPasswordData(BaseModel):
    """重置密码响应。"""
    message: str = Field(default="密码已重置，请重新登录", description="提示信息")


class ChangePasswordRequest(BaseModel):
    """已登录用户修改密码请求。"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., description="新密码", min_length=6)


class ChangePasswordData(BaseModel):
    """修改密码响应。"""
    message: str = Field(default="密码已修改", description="提示信息")
