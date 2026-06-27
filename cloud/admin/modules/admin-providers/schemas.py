"""
admin-providers Pydantic DTO。
"""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


class ProviderItem(BaseModel):
    id: str; name: str; provider_type: str; is_enabled: bool; priority: int = 0; created_at: str


class ProviderDetail(BaseModel):
    id: str; name: str; provider_type: str; api_key_encrypted: Optional[str] = None
    base_url: Optional[str] = None; models_json: Optional[dict] = None
    is_enabled: bool; priority: int = 0; created_at: str; updated_at: str


class ProviderListData(BaseModel):
    items: List[ProviderItem]; total: int; limit: int; offset: int


class CreateProviderRequest(BaseModel):
    name: str = Field(..., description="Provider 名称")
    provider_type: str = Field(..., description="Provider 类型")
    api_key_encrypted: Optional[str] = None
    base_url: Optional[str] = None
    models_json: Optional[dict] = None
    is_enabled: bool = True
    priority: int = Field(default=0, description="优先级，数字越大越优先")


class UpdateProviderRequest(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    api_key_encrypted: Optional[str] = None
    base_url: Optional[str] = None
    models_json: Optional[dict] = None
    is_enabled: Optional[bool] = None
    priority: Optional[int] = None
