"""
admin-roles Pydantic DTO。
"""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field

class PermissionItem(BaseModel):
    id: str; code: str; name: str; resource: str; action: str

class RoleItem(BaseModel):
    id: str; name: str; code: str; is_system: bool; created_at: str

class RoleDetail(BaseModel):
    id: str; name: str; code: str; description: Optional[str] = None
    is_system: bool; created_at: str
    permissions: List[PermissionItem] = Field(default_factory=list)

class RoleListData(BaseModel):
    items: List[RoleItem]; total: int; limit: int; offset: int

class PermissionListData(BaseModel):
    items: List[PermissionItem]

class CreateRoleRequest(BaseModel):
    name: str; code: str; description: Optional[str] = None

class UpdateRoleRequest(BaseModel):
    name: Optional[str] = None; description: Optional[str] = None

class AssignPermissionsRequest(BaseModel):
    permission_ids: List[str] = Field(default_factory=list, description="权限 ID 列表（允许空数组，表示清空角色权限）")

class AssignRolesRequest(BaseModel):
    role_ids: List[str] = Field(default_factory=list, description="角色 ID 列表（允许空数组，表示清空用户角色）")

class UserRoleItem(BaseModel):
    """用户拥有的角色信息（供前端角色分配弹窗使用）。"""
    id: str = Field(..., description="角色 ID")
    name: str = Field(..., description="角色名称")
    code: str = Field(..., description="角色编码")
    is_system: bool = Field(default=False, description="是否系统内置角色")
