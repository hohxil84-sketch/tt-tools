"""
admin-batch Pydantic DTO。
"""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


class BatchIdsRequest(BaseModel):
    ids: List[str] = Field(..., min_length=1, max_length=100, description="目标 ID 列表")


class BatchStatusRequest(BatchIdsRequest):
    status: str = Field(..., description="目标状态：active / blocked / deleted")


class BatchAdjustRequest(BaseModel):
    user_ids: List[str] = Field(..., min_length=1, max_length=100, description="用户 ID 列表")
    amount: int = Field(..., description="调整额度（正数赠送，负数扣除）")
    description: Optional[str] = Field(default=None, description="调整说明")


class BatchResultItem(BaseModel):
    id: str
    success: bool
    message: str = ""


class BatchResult(BaseModel):
    total: int = Field(..., description="总数")
    succeeded: int = Field(..., description="成功数")
    failed: int = Field(..., description="失败数")
    results: List[BatchResultItem] = Field(default_factory=list, description="每项结果")
