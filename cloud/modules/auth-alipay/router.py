"""
支付宝 OAuth 第三方登录路由。

GET  /api/v1/auth/alipay/url       → 桌面端获取授权跳转 URL
POST /api/v1/auth/alipay/callback  → 桌面端提交 auth_code 换取 JWT
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from cloud.shared import get_db, get_request_id, success_response, error_response, AppError
from service import alipay_get_login_url, alipay_handle_callback

router = APIRouter(tags=["Auth Alipay"])

class AlipayCallbackRequest(BaseModel):
    auth_code: str = Field(..., description="支付宝回调携带的 auth_code")


@router.get("/auth/alipay/url")
async def alipay_get_url():
    """返回支付宝授权登录 URL，桌面端用 WebView 打开。"""
    try:
        return JSONResponse({"login_url": alipay_get_login_url()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/auth/alipay/callback")
async def alipay_callback_get(
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    """支付宝授权回调（GET）—— 浏览器重定向。

    支付宝在用户授权后会重定向到此 URL，携带 auth_code。
    直接从 request.query_params 读取，避免 FastAPI Query 验证的编码问题。
    """
    auth_code = request.query_params.get("auth_code", "")
    if not auth_code:
        return JSONResponse(
            content=error_response(code="VALIDATION_ERROR", message="缺少 auth_code 参数", request_id=request_id),
            status_code=400,
        )
    try:
        data = await alipay_handle_callback(db, auth_code)
        return success_response(data, request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details),
            status_code=e.status_code,
        )


class AlipayCallbackRequest(BaseModel):
    auth_code: str = Field(..., description="支付宝回调携带的 auth_code")


@router.post("/auth/alipay/callback")
async def alipay_callback_post(
    body: AlipayCallbackRequest,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    """桌面端提交 auth_code 换取 JWT（POST）。

    桌面端在 WebView 中拦截支付宝回调 URL，提取 auth_code，
    POST 到此接口完成登录。
    """
    try:
        data = await alipay_handle_callback(db, body.auth_code)
        return success_response(data, request_id)
    except AppError as e:
        return JSONResponse(
            content=error_response(code=e.code, message=e.message, request_id=request_id, details=e.details),
            status_code=e.status_code,
        )
