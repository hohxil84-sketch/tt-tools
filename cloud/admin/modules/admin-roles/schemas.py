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
    permission_ids: List[str] = Field(..., min_length=1)

class AssignRolesRequest(BaseModel):
    role_ids: List[str] = Field(..., min_length=1)

class UserRoleItem(BaseModel):
    user_id: str; role_id: str; role_name: str
