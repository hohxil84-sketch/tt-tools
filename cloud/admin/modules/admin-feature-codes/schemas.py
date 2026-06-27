"""
admin-feature-codes Pydantic DTO。
"""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field

class FeatureCodeItem(BaseModel):
    id: str; code: str; name: str; category: str; is_active: bool; plan_count: int = 0; created_at: str

class FeatureCodeDetail(BaseModel):
    id: str; code: str; name: str; category: str; description: Optional[str] = None; is_active: bool; created_at: str

class FeatureCodeListData(BaseModel):
    items: List[FeatureCodeItem]; total: int; limit: int; offset: int

class CreateFeatureCodeRequest(BaseModel):
    code: str; name: str; category: str = "cloud_ai"; description: Optional[str] = None

class UpdateFeatureCodeRequest(BaseModel):
    name: Optional[str] = None; category: Optional[str] = None; description: Optional[str] = None; is_active: Optional[bool] = None
