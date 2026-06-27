"""
admin-audit Pydantic 请求/响应 DTO。

对齐 shared-contract/openapi/admin-audit.yaml 契约定义。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any, List

from pydantic import BaseModel, Field


# ============================================================
# 审计日志列表项
# ============================================================

class AuditLogItem(BaseModel):
    """审计日志列表项（摘要信息）。"""
    id: str = Field(..., description="审计日志 ID（UUID）")
    admin_user_id: str = Field(..., description="操作管理员 ID")
    admin_account: str = Field(..., description="操作管理员账号")
    action: str = Field(..., description="操作类型：create / update / delete / status_change / adjust / refund / cancel")
    target_type: str = Field(..., description="目标资源类型：user / device / order / plan / credits / feature_flag / provider")
    target_id: Optional[str] = Field(default=None, description="目标资源 ID")
    summary: str = Field(..., description="操作摘要（中文）")
    ip_address: Optional[str] = Field(default=None, description="请求来源 IP")
    created_at: str = Field(..., description="操作时间")


# ============================================================
# 审计日志详情
# ============================================================

class AuditLogDetail(BaseModel):
    """审计日志详情（含完整操作数据）。"""
    id: str = Field(..., description="审计日志 ID（UUID）")
    admin_user_id: str = Field(..., description="操作管理员 ID")
    admin_account: str = Field(..., description="操作管理员账号")
    action: str = Field(..., description="操作类型")
    target_type: str = Field(..., description="目标资源类型")
    target_id: Optional[str] = Field(default=None, description="目标资源 ID")
    summary: str = Field(..., description="操作摘要（中文）")
    details_json: Optional[dict] = Field(default=None, description="操作详情（请求体、变更前后等）")
    ip_address: Optional[str] = Field(default=None, description="请求来源 IP")
    created_at: str = Field(..., description="操作时间")


# ============================================================
# 列表分页响应
# ============================================================

class AuditLogListData(BaseModel):
    """审计日志列表分页响应数据。"""
    items: List[AuditLogItem] = Field(..., description="审计日志列表")
    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="每页条数")
    offset: int = Field(..., description="当前偏移量")
