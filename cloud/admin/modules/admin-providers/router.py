"""
admin-providers FastAPI 路由。
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from cloud.shared import TokenData, require_permission, get_request_id, success_response, error_response, AppError, get_db
from schemas import CreateProviderRequest, UpdateProviderRequest
from service import list_providers, create_provider, get_provider_detail, update_provider, delete_provider

router = APIRouter(tags=["Admin Providers"])

@router.get("/admin/providers")
async def admin_list_providers(
    limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0),
    request_id: str = Depends(get_request_id), current_user: TokenData = Depends(require_permission("providers.read")),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await list_providers(db, limit, offset)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.post("/admin/providers")
async def admin_create_provider(body: CreateProviderRequest, request_id: str = Depends(get_request_id), current_user: TokenData = Depends(require_permission("providers.manage")), db: AsyncSession = Depends(get_db)):
    try:
        data = await create_provider(db, body.name, body.provider_type, api_key_encrypted=body.api_key_encrypted, base_url=body.base_url, models_json=body.models_json, is_enabled=body.is_enabled, priority=body.priority)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.get("/admin/providers/{provider_id}")
async def admin_get_provider(provider_id: str, request_id: str = Depends(get_request_id), current_user: TokenData = Depends(require_permission("providers.manage")), db: AsyncSession = Depends(get_db)):
    try:
        data = await get_provider_detail(db, provider_id)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.patch("/admin/providers/{provider_id}")
async def admin_update_provider(provider_id: str, body: UpdateProviderRequest, request_id: str = Depends(get_request_id), current_user: TokenData = Depends(require_permission("providers.read")), db: AsyncSession = Depends(get_db)):
    try:
        data = await update_provider(db, provider_id, **body.model_dump(exclude_none=True))
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.delete("/admin/providers/{provider_id}")
async def admin_delete_provider(provider_id: str, request_id: str = Depends(get_request_id), current_user: TokenData = Depends(require_permission("providers.manage")), db: AsyncSession = Depends(get_db)):
    try:
        data = await delete_provider(db, provider_id)
        return success_response(data, request_id)
    except AppError as e:
        return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)
