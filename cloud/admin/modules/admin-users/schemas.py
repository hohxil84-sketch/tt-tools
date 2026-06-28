"""
admin-users Pydantic 请求/响应 DTO。

所有响应结构对齐 shared-contract/openapi/admin-users.yaml。
字段命名使用 snake_case，通过 Pydantic 序列化为 JSON。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 用户相关 DTO
# ============================================================


class UserItem(BaseModel):
    """用户列表项（摘要信息），对齐 admin-users.yaml UserItem。"""

    id: str = Field(..., description="用户 ID（UUID）")
    account: str = Field(..., description="登录账号")
    display_name: Optional[str] = Field(default=None, description="展示名称")
    role: str = Field(..., description="用户角色：user / admin")
    status: str = Field(..., description="用户状态：active / blocked / deleted")
    plan_id: Optional[str] = Field(default=None, description="当前套餐 ID（UUID）")
    plan_name: Optional[str] = Field(default=None, description="当前套餐中文名（从 plans 表关联查询）")
    created_at: datetime = Field(..., description="注册时间")
    # === 新增聚合展示字段 ===
    updated_at: Optional[datetime] = Field(default=None, description="最近更新时间")
    last_login_at: Optional[datetime] = Field(default=None, description="最后登录时间（来自 auth_sessions 表）")
    device_count: int = Field(default=0, description="绑定设备数（来自 devices 表）")
    credit_balance: Optional[int] = Field(default=None, description="额度余额（来自 credit_accounts 表，仅普通用户有值）")
    role_names: Optional[str] = Field(default=None, description="RBAC 角色名称，逗号分隔（来自 user_roles/roles 表，仅系统用户有值）")
    monthly_usage: int = Field(default=0, description="本月消费额度（来自 credit_ledger 表，仅普通用户有值）")
    audit_count: int = Field(default=0, description="操作审计次数（来自 admin_audit_logs 表，仅系统用户有值）")
    period_end: Optional[datetime] = Field(default=None, description="套餐到期时间（来自 credit_accounts 表，仅普通用户有值）")


class UserDetail(BaseModel):
    """用户详细信息，对齐 admin-users.yaml UserDetail。"""

    id: str = Field(..., description="用户 ID（UUID）")
    account: str = Field(..., description="登录账号")
    display_name: Optional[str] = Field(default=None, description="展示名称")
    role: str = Field(..., description="用户角色")
    status: str = Field(..., description="用户状态")
    plan_id: Optional[str] = Field(default=None, description="当前套餐 ID（UUID）")
    plan_name: Optional[str] = Field(default=None, description="当前套餐中文名（从 plans 表关联查询）")
    created_at: datetime = Field(..., description="注册时间")
    updated_at: Optional[datetime] = Field(default=None, description="最近更新时间")
    # === 新增聚合展示字段 ===
    last_login_at: Optional[datetime] = Field(default=None, description="最后登录时间（来自 auth_sessions 表）")
    device_count: int = Field(default=0, description="绑定设备数（来自 devices 表）")
    credit_balance: Optional[int] = Field(default=None, description="额度余额（来自 credit_accounts 表）")
    role_names: Optional[str] = Field(default=None, description="RBAC 角色名称，逗号分隔（来自 user_roles/roles 表）")
    monthly_usage: int = Field(default=0, description="本月消费额度（来自 credit_ledger 表）")
    audit_count: int = Field(default=0, description="操作审计次数（来自 admin_audit_logs 表）")
    period_end: Optional[datetime] = Field(default=None, description="套餐到期时间（来自 credit_accounts 表）")


class CreateUserRequest(BaseModel):
    """创建用户请求，对齐 admin-users.yaml CreateUserRequest。"""

    account: str = Field(..., description="登录账号")
    password: str = Field(..., description="登录密码（明文，服务端 bcrypt 哈希存储）")
    display_name: str = Field(..., min_length=1, description="展示名称（必填）")
    role: str = Field(default="user", description="用户角色：user / admin", pattern="^(user|admin)$")
    plan_id: Optional[str] = Field(default=None, description="套餐 ID（UUID），必选")
    role_ids: Optional[list[str]] = Field(default=None, description="RBAC 角色 ID 列表，管理员必选")


class UpdateUserRequest(BaseModel):
    """编辑用户信息请求，对齐 admin-users.yaml UpdateUserRequest。"""

    display_name: Optional[str] = Field(default=None, description="展示名称")
    plan_id: Optional[str] = Field(default=None, description="套餐 ID（UUID）")
    role: Optional[str] = Field(default=None, description="用户角色：user / admin", pattern="^(user|admin)$")


class ResetPasswordRequest(BaseModel):
    """管理员重置用户密码请求，对齐 admin-users.yaml ResetPasswordRequest。"""

    new_password: str = Field(
        ..., min_length=1, max_length=128,
        description="新密码（明文，服务端 bcrypt 哈希存储）"
    )


class UpdateUserStatusRequest(BaseModel):
    """修改用户状态请求，对齐 admin-users.yaml UpdateUserStatusRequest。"""

    status: str = Field(
        ...,
        description="目标状态：active / blocked / deleted",
        pattern="^(active|blocked|deleted)$",
    )


class UserListData(BaseModel):
    """用户列表分页响应数据，对齐 admin-users.yaml UserListData。"""

    items: list[UserItem] = Field(..., description="用户列表")
    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="每页条数")
    offset: int = Field(..., description="当前偏移量")


# ============================================================
# 设备相关 DTO
# ============================================================


class DeviceItem(BaseModel):
    """设备列表项（摘要信息），对齐 admin-users.yaml DeviceItem。"""

    id: str = Field(..., description="设备 ID（UUID）")
    user_id: str = Field(..., description="所属用户 ID")
    user_account: Optional[str] = Field(default=None, description="所属用户账号（从 users 表关联查询）")
    user_display_name: Optional[str] = Field(default=None, description="所属用户展示名称")
    device_name: Optional[str] = Field(default=None, description="设备名称")
    client_version: Optional[str] = Field(default=None, description="客户端版本")
    status: str = Field(..., description="设备状态：active / blocked / removed")
    bound_at: datetime = Field(..., description="绑定时间")
    last_seen_at: Optional[datetime] = Field(default=None, description="最近活跃时间")


class DeviceDetail(BaseModel):
    """设备详细信息，对齐 admin-users.yaml DeviceDetail。"""

    id: str = Field(..., description="设备 ID（UUID）")
    user_id: str = Field(..., description="所属用户 ID")
    user_account: Optional[str] = Field(default=None, description="所属用户账号（从 users 表关联查询）")
    user_display_name: Optional[str] = Field(default=None, description="所属用户展示名称")
    device_name: Optional[str] = Field(default=None, description="设备名称")
    client_version: Optional[str] = Field(default=None, description="客户端版本")
    status: str = Field(..., description="设备状态")
    bound_at: datetime = Field(..., description="绑定时间")
    last_seen_at: Optional[datetime] = Field(default=None, description="最近活跃时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最近更新时间")


class UpdateDeviceStatusRequest(BaseModel):
    """修改设备状态请求，对齐 admin-users.yaml UpdateDeviceStatusRequest。"""

    status: str = Field(
        ...,
        description="目标状态：active / blocked / removed",
        pattern="^(active|blocked|removed)$",
    )


class DeviceListData(BaseModel):
    """设备列表分页响应数据，对齐 admin-users.yaml DeviceListData。"""

    items: list[DeviceItem] = Field(..., description="设备列表")
    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="每页条数")
    offset: int = Field(..., description="当前偏移量")
