"""
admin-roles FastAPI 路由。

所有端点需要对应的 RBAC 权限（通过 cloud-shared require_permission 鉴权）。
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from cloud.shared import TokenData, require_permission, get_request_id, success_response, error_response, AppError, get_db
from schemas import CreateRoleRequest, UpdateRoleRequest, AssignPermissionsRequest, AssignRolesRequest
from service import *

router = APIRouter(tags=["Admin Roles"])

# -- 角色 CRUD --
@router.get("/admin/roles")
async def list_r(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), request_id=Depends(get_request_id), current_user: TokenData=Depends(require_permission("roles.read")), db=Depends(get_db)):
    try: return success_response((await list_roles(db, limit, offset)).model_dump(mode="json"), request_id)
    except AppError as e: return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.post("/admin/roles")
async def create_r(body: CreateRoleRequest, request_id=Depends(get_request_id), current_user: TokenData=Depends(require_permission("roles.manage")), db=Depends(get_db)):
    try: return success_response((await create_role(db, body.name, body.code, body.description)).model_dump(mode="json"), request_id)
    except AppError as e: return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.get("/admin/roles/{role_id}")
async def get_r(role_id: str, request_id=Depends(get_request_id), current_user: TokenData=Depends(require_permission("roles.read")), db=Depends(get_db)):
    try: return success_response((await get_role_detail(db, role_id)).model_dump(mode="json"), request_id)
    except AppError as e: return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.patch("/admin/roles/{role_id}")
async def update_r(role_id: str, body: UpdateRoleRequest, request_id=Depends(get_request_id), current_user: TokenData=Depends(require_permission("roles.manage")), db=Depends(get_db)):
    try: return success_response((await update_role(db, role_id, **body.model_dump(exclude_none=True))).model_dump(mode="json"), request_id)
    except AppError as e: return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.delete("/admin/roles/{role_id}")
async def delete_r(role_id: str, request_id=Depends(get_request_id), current_user: TokenData=Depends(require_permission("roles.manage")), db=Depends(get_db)):
    try: return success_response(await delete_role(db, role_id), request_id)
    except AppError as e: return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

# -- 权限查询 --
@router.get("/admin/permissions")
async def list_p(request_id=Depends(get_request_id), current_user: TokenData=Depends(require_permission("roles.read")), db=Depends(get_db)):
    try: return success_response((await list_permissions(db)).model_dump(mode="json"), request_id)
    except AppError as e: return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

# -- 角色-权限关联 --
@router.post("/admin/roles/{role_id}/permissions")
async def assign_p(role_id: str, body: AssignPermissionsRequest, request_id=Depends(get_request_id), current_user: TokenData=Depends(require_permission("roles.manage")), db=Depends(get_db)):
    try: return success_response((await assign_permissions_to_role(db, role_id, body.permission_ids)).model_dump(mode="json"), request_id)
    except AppError as e: return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

# -- 用户-角色关联 --
@router.get("/admin/users/{user_id}/roles")
async def get_ur(user_id: str, request_id=Depends(get_request_id), current_user: TokenData=Depends(require_permission("roles.read")), db=Depends(get_db)):
    try: return success_response([r.model_dump(mode="json") for r in await get_user_roles(db, user_id)], request_id)
    except AppError as e: return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)

@router.post("/admin/users/{user_id}/roles")
async def assign_ur(user_id: str, body: AssignRolesRequest, request_id=Depends(get_request_id), current_user: TokenData=Depends(require_permission("roles.manage")), db=Depends(get_db)):
    try: return success_response([r.model_dump(mode="json") for r in await assign_roles_to_user(db, user_id, body.role_ids)], request_id)
    except AppError as e: return JSONResponse(content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details), status_code=e.status_code)
