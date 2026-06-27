"""
admin-feature-codes FastAPI 路由。
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from cloud.shared import TokenData, require_permission, get_request_id, success_response, error_response, AppError, get_db
from schemas import CreateFeatureCodeRequest, UpdateFeatureCodeRequest
from service import list_feature_codes, create_feature_code, get_feature_code_detail, update_feature_code, delete_feature_code

router = APIRouter(tags=["Admin Feature Codes"])

@router.get("/admin/feature-codes/list")
async def admin_list_feature_codes(
    limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None),
    request_id: str = Depends(get_request_id), current_user: TokenData = Depends(require_permission("features.read")),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await list_feature_codes(db, limit, offset, category)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.post("/admin/feature-codes")
async def admin_create_feature_code(body: CreateFeatureCodeRequest, request_id: str = Depends(get_request_id), current_user: TokenData = Depends(require_permission("features.manage")), db: AsyncSession = Depends(get_db)):
    try:
        data = await create_feature_code(db, body.code, body.name, body.category, body.description)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.get("/admin/feature-codes/{fc_id}")
async def admin_get_feature_code(fc_id: str, request_id: str = Depends(get_request_id), current_user: TokenData = Depends(require_permission("features.manage")), db: AsyncSession = Depends(get_db)):
    try:
        data = await get_feature_code_detail(db, fc_id)
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.patch("/admin/feature-codes/{fc_id}")
async def admin_update_feature_code(fc_id: str, body: UpdateFeatureCodeRequest, request_id: str = Depends(get_request_id), current_user: TokenData = Depends(require_permission("features.read")), db: AsyncSession = Depends(get_db)):
    try:
        data = await update_feature_code(db, fc_id, **body.model_dump(exclude_none=True))
        return success_response(data.model_dump(mode="json"), request_id)
    except AppError as e:
        return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.delete("/admin/feature-codes/{fc_id}")
async def admin_delete_feature_code(fc_id: str, request_id: str = Depends(get_request_id), current_user: TokenData = Depends(require_permission("features.manage")), db: AsyncSession = Depends(get_db)):
    try:
        data = await delete_feature_code(db, fc_id)
        return success_response(data, request_id)
    except AppError as e:
        return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)
