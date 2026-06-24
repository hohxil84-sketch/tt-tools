"""
admin-billing 模块完整测试。

覆盖 11 个接口的成功路径、鉴权错误路径和业务错误路径：
套餐管理：
- GET    /admin/plans              — 套餐列表
- GET    /admin/plans/{plan_id}    — 套餐详情
- POST   /admin/plans              — 创建套餐
- PATCH  /admin/plans/{plan_id}    — 更新套餐
- PATCH  /admin/plans/{plan_id}/status — 启用/停用套餐
订单管理：
- GET    /admin/orders             — 全部订单列表
- GET    /admin/orders/{order_id}  — 订单详情
额度管理：
- GET    /admin/credits/accounts   — 额度账户列表
- GET    /admin/credits/accounts/{account_id} — 额度账户详情
- GET    /admin/credits/ledger     — 全部额度流水
- POST   /admin/credits/adjust     — 手动调整额度

通过依赖覆盖（dependency_overrides）隔离测试：
- admin_client：管理员身份 → 预期 200
- user_client：普通用户 → 预期 403
- no_auth_client：无鉴权 → 预期 401
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ============================================================
# 工具函数
# ============================================================


def _assert_success_response(body: dict) -> dict:
    """验证统一成功响应格式，返回 data。"""
    assert body["success"] is True
    assert body["error"] is None
    assert "request_id" in body
    assert body["request_id"] is not None
    assert "data" in body
    return body["data"]


def _assert_error_detail(body: dict, code: str) -> None:
    """验证 HTTPException 错误详情。"""
    assert "detail" in body
    assert body["detail"]["code"] == code


# ============================================================
# GET /api/v1/admin/plans — 套餐列表
# ============================================================


class TestListPlans:
    """套餐列表接口测试。"""

    async def test_as_admin_returns_all_plans(self, admin_client: AsyncClient):
        """管理员查询套餐列表，应返回所有套餐。"""
        resp = await admin_client.get("/api/v1/admin/plans")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 3
        codes = {item["code"] for item in data["items"]}
        assert codes == {"free", "standard", "pro"}

    async def test_plan_items_have_required_fields(self, admin_client: AsyncClient):
        """套餐列表项应包含所有必填字段。"""
        resp = await admin_client.get("/api/v1/admin/plans")
        data = _assert_success_response(resp.json())

        for item in data["items"]:
            assert "id" in item
            assert "code" in item
            assert "name" in item
            assert "monthly_grant" in item
            assert "status" in item
            assert "created_at" in item
            # 列表不返回 enabled_features_json
            assert "enabled_features_json" not in item

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询套餐列表。"""
        resp = await user_client.get("/api/v1/admin/plans")
        assert resp.status_code == 403
        _assert_error_detail(resp.json(), "PERMISSION_DENIED")

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询套餐列表应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/plans")
        assert resp.status_code == 401
        _assert_error_detail(resp.json(), "AUTH_REQUIRED")


# ============================================================
# GET /api/v1/admin/plans/{plan_id} — 套餐详情
# ============================================================


class TestGetPlanDetail:
    """套餐详情接口测试。"""

    async def test_get_existing_plan(self, admin_client: AsyncClient):
        """查询已存在的套餐应返回完整信息。"""
        resp = await admin_client.get("/api/v1/admin/plans/plan-standard")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["id"] == "plan-standard"
        assert data["code"] == "standard"
        assert data["name"] == "标准套餐"
        assert data["monthly_grant"] == 500
        assert data["status"] == "active"
        assert "enabled_features_json" in data
        assert data["enabled_features_json"]["ai_copy_cloud"] is True
        assert "created_at" in data
        assert "updated_at" in data

    async def test_plan_not_found(self, admin_client: AsyncClient):
        """查询不存在的套餐应返回 404。"""
        resp = await admin_client.get("/api/v1/admin/plans/nonexistent-plan")
        assert resp.status_code == 404
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "PLAN_NOT_FOUND"

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询套餐详情。"""
        resp = await user_client.get("/api/v1/admin/plans/plan-free")
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询套餐详情应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/plans/plan-free")
        assert resp.status_code == 401


# ============================================================
# POST /api/v1/admin/plans — 创建套餐
# ============================================================


class TestCreatePlan:
    """创建套餐接口测试。"""

    async def test_create_plan_success(self, admin_client: AsyncClient):
        """创建新套餐应成功。"""
        resp = await admin_client.post(
            "/api/v1/admin/plans",
            json={
                "code": "enterprise",
                "name": "企业套餐",
                "monthly_grant": 5000,
                "enabled_features_json": {"ai_copy_cloud": True, "ai_render_cloud": True},
            },
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["code"] == "enterprise"
        assert data["name"] == "企业套餐"
        assert data["monthly_grant"] == 5000
        assert data["status"] == "active"
        assert data["enabled_features_json"]["ai_copy_cloud"] is True

    async def test_create_plan_duplicate_code(self, admin_client: AsyncClient):
        """创建重复编码的套餐应返回 409。"""
        resp = await admin_client.post(
            "/api/v1/admin/plans",
            json={"code": "free", "name": "重复免费"},
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["error"]["code"] == "PLAN_CODE_EXISTS"

    async def test_create_plan_defaults(self, admin_client: AsyncClient):
        """创建套餐时使用默认值。"""
        resp = await admin_client.post(
            "/api/v1/admin/plans",
            json={"code": "basic", "name": "基础套餐"},
        )
        assert resp.status_code == 200
        data = _assert_success_response(resp.json())
        assert data["monthly_grant"] == 0
        assert data["enabled_features_json"] == {}

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权创建套餐。"""
        resp = await user_client.post(
            "/api/v1/admin/plans",
            json={"code": "hack", "name": "Hack"},
        )
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权创建套餐应返回 401。"""
        resp = await no_auth_client.post(
            "/api/v1/admin/plans",
            json={"code": "hack", "name": "Hack"},
        )
        assert resp.status_code == 401


# ============================================================
# PATCH /api/v1/admin/plans/{plan_id} — 更新套餐
# ============================================================


class TestUpdatePlan:
    """更新套餐接口测试。"""

    async def test_update_name(self, admin_client: AsyncClient):
        """更新套餐名称应成功。"""
        resp = await admin_client.patch(
            "/api/v1/admin/plans/plan-free",
            json={"name": "免费套餐（新版）"},
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["name"] == "免费套餐（新版）"
        # code 不应改变
        assert data["code"] == "free"

    async def test_update_monthly_grant(self, admin_client: AsyncClient):
        """更新月赠额度应成功。"""
        resp = await admin_client.patch(
            "/api/v1/admin/plans/plan-standard",
            json={"monthly_grant": 800},
        )
        assert resp.status_code == 200
        data = _assert_success_response(resp.json())
        assert data["monthly_grant"] == 800

    async def test_update_features(self, admin_client: AsyncClient):
        """更新功能开关应成功。"""
        resp = await admin_client.patch(
            "/api/v1/admin/plans/plan-standard",
            json={"enabled_features_json": {"ai_image_tools_cloud": True}},
        )
        assert resp.status_code == 200
        data = _assert_success_response(resp.json())
        assert data["enabled_features_json"]["ai_image_tools_cloud"] is True

    async def test_plan_not_found(self, admin_client: AsyncClient):
        """更新不存在的套餐应返回 404。"""
        resp = await admin_client.patch(
            "/api/v1/admin/plans/nonexistent",
            json={"name": "不存在"},
        )
        assert resp.status_code == 404

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权更新套餐。"""
        resp = await user_client.patch(
            "/api/v1/admin/plans/plan-free",
            json={"name": "Hack"},
        )
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权更新套餐应返回 401。"""
        resp = await no_auth_client.patch(
            "/api/v1/admin/plans/plan-free",
            json={"name": "Hack"},
        )
        assert resp.status_code == 401


# ============================================================
# PATCH /api/v1/admin/plans/{plan_id}/status — 套餐状态
# ============================================================


class TestUpdatePlanStatus:
    """套餐状态管理接口测试。"""

    async def test_disable_plan(self, admin_client: AsyncClient):
        """停用套餐应成功。"""
        resp = await admin_client.patch(
            "/api/v1/admin/plans/plan-free/status",
            json={"status": "disabled"},
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["status"] == "disabled"

    async def test_activate_disabled_plan(self, admin_client: AsyncClient):
        """重新启用已停用套餐。"""
        # 先停用
        await admin_client.patch(
            "/api/v1/admin/plans/plan-free/status",
            json={"status": "disabled"},
        )
        # 再启用
        resp = await admin_client.patch(
            "/api/v1/admin/plans/plan-free/status",
            json={"status": "active"},
        )
        assert resp.status_code == 200
        data = _assert_success_response(resp.json())
        assert data["status"] == "active"

    async def test_invalid_status_rejected(self, admin_client: AsyncClient):
        """传入非法状态值应返回 422（Pydantic 校验）。"""
        resp = await admin_client.patch(
            "/api/v1/admin/plans/plan-free/status",
            json={"status": "deleted"},
        )
        assert resp.status_code == 422

    async def test_plan_not_found(self, admin_client: AsyncClient):
        """修改不存在的套餐状态应返回 404。"""
        resp = await admin_client.patch(
            "/api/v1/admin/plans/nonexistent/status",
            json={"status": "disabled"},
        )
        assert resp.status_code == 404

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权修改套餐状态。"""
        resp = await user_client.patch(
            "/api/v1/admin/plans/plan-free/status",
            json={"status": "disabled"},
        )
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权修改套餐状态应返回 401。"""
        resp = await no_auth_client.patch(
            "/api/v1/admin/plans/plan-free/status",
            json={"status": "disabled"},
        )
        assert resp.status_code == 401


# ============================================================
# GET /api/v1/admin/orders — 全部订单列表
# ============================================================


class TestListOrders:
    """订单列表接口测试。"""

    async def test_as_admin_returns_all_orders(self, admin_client: AsyncClient):
        """管理员查询全部订单应返回所有订单。"""
        resp = await admin_client.get("/api/v1/admin/orders")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_filter_by_user_id(self, admin_client: AsyncClient):
        """按用户 ID 筛选订单。"""
        resp = await admin_client.get("/api/v1/admin/orders?user_id=user-001")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == "user-001"

    async def test_filter_by_status(self, admin_client: AsyncClient):
        """按状态筛选订单。"""
        resp = await admin_client.get("/api/v1/admin/orders?status=paid")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["status"] == "paid"

    async def test_filter_by_order_type(self, admin_client: AsyncClient):
        """按订单类型筛选。"""
        resp = await admin_client.get("/api/v1/admin/orders?order_type=plan")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["order_type"] == "plan"

    async def test_order_items_contain_user_account(self, admin_client: AsyncClient):
        """订单列表项应包含用户账号信息。"""
        resp = await admin_client.get("/api/v1/admin/orders?user_id=user-001")
        data = _assert_success_response(resp.json())
        assert data["items"][0]["user_account"] == "alice@example.com"

    async def test_pagination(self, admin_client: AsyncClient):
        """分页应正确生效。"""
        resp = await admin_client.get("/api/v1/admin/orders?limit=1&offset=0")
        assert resp.status_code == 200
        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 1
        assert data["total"] == 2

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询全部订单。"""
        resp = await user_client.get("/api/v1/admin/orders")
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询订单列表应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/orders")
        assert resp.status_code == 401


# ============================================================
# GET /api/v1/admin/orders/{order_id} — 订单详情
# ============================================================


class TestGetOrderDetail:
    """订单详情接口测试。"""

    async def test_get_existing_order(self, admin_client: AsyncClient):
        """查询已存在的订单应返回详细信息。"""
        resp = await admin_client.get("/api/v1/admin/orders/order-001")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["id"] == "order-001"
        assert data["order_no"] == "ORD-20260624-a1b2c3d4"
        assert data["order_type"] == "credits"
        assert data["product_code"] == "credits_100"
        assert data["amount_cents"] == 1000
        assert data["status"] == "pending"
        assert data["user_id"] == "user-001"
        assert data["user_account"] == "alice@example.com"
        assert data["user_display_name"] == "Alice"

    async def test_order_not_found(self, admin_client: AsyncClient):
        """查询不存在的订单应返回 404。"""
        resp = await admin_client.get("/api/v1/admin/orders/nonexistent-order")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "ORDER_NOT_FOUND"

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询订单详情。"""
        resp = await user_client.get("/api/v1/admin/orders/order-001")
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询订单详情应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/orders/order-001")
        assert resp.status_code == 401


# ============================================================
# GET /api/v1/admin/credits/accounts — 额度账户列表
# ============================================================


class TestListCreditAccounts:
    """额度账户列表接口测试。"""

    async def test_as_admin_returns_all_accounts(self, admin_client: AsyncClient):
        """管理员查询全部额度账户应返回所有账户。"""
        resp = await admin_client.get("/api/v1/admin/credits/accounts")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_filter_by_status(self, admin_client: AsyncClient):
        """按状态筛选额度账户。"""
        resp = await admin_client.get("/api/v1/admin/credits/accounts?status=active")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 3
        for item in data["items"]:
            assert item["status"] == "active"

    async def test_filter_by_plan_code(self, admin_client: AsyncClient):
        """按套餐编码筛选。"""
        resp = await admin_client.get("/api/v1/admin/credits/accounts?plan_code=free")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["plan_code"] == "free"

    async def test_accounts_contain_user_account(self, admin_client: AsyncClient):
        """额度账户列表应包含用户账号。"""
        resp = await admin_client.get("/api/v1/admin/credits/accounts")
        data = _assert_success_response(resp.json())

        accounts = {item["user_id"]: item.get("user_account") for item in data["items"]}
        assert accounts.get("user-001") == "alice@example.com"
        assert accounts.get("user-002") == "bob@example.com"

    async def test_pagination(self, admin_client: AsyncClient):
        """分页应正确生效。"""
        resp = await admin_client.get("/api/v1/admin/credits/accounts?limit=1&offset=0")
        assert resp.status_code == 200
        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 1
        assert data["total"] == 3

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询额度账户列表。"""
        resp = await user_client.get("/api/v1/admin/credits/accounts")
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询额度账户应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/credits/accounts")
        assert resp.status_code == 401


# ============================================================
# GET /api/v1/admin/credits/accounts/{account_id} — 额度账户详情
# ============================================================


class TestGetCreditAccountDetail:
    """额度账户详情接口测试。"""

    async def test_get_existing_account(self, admin_client: AsyncClient):
        """查询已存在的额度账户应返回完整信息。"""
        resp = await admin_client.get("/api/v1/admin/credits/accounts/acct-001")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["id"] == "acct-001"
        assert data["user_id"] == "user-001"
        assert data["user_account"] == "alice@example.com"
        assert data["user_display_name"] == "Alice"
        assert data["plan_code"] == "standard"
        assert data["balance"] == 450
        assert data["monthly_grant"] == 500
        assert data["status"] == "active"

    async def test_account_not_found(self, admin_client: AsyncClient):
        """查询不存在的额度账户应返回 404。"""
        resp = await admin_client.get(
            "/api/v1/admin/credits/accounts/nonexistent-acct"
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "CREDIT_ACCOUNT_NOT_FOUND"

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询额度账户详情。"""
        resp = await user_client.get("/api/v1/admin/credits/accounts/acct-001")
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询额度账户应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/credits/accounts/acct-001")
        assert resp.status_code == 401


# ============================================================
# GET /api/v1/admin/credits/ledger — 全部额度流水
# ============================================================


class TestListCreditLedger:
    """额度流水列表接口测试。"""

    async def test_as_admin_returns_all_ledger(self, admin_client: AsyncClient):
        """管理员查询全部流水应返回所有记录。"""
        resp = await admin_client.get("/api/v1/admin/credits/ledger")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_filter_by_user_id(self, admin_client: AsyncClient):
        """按用户 ID 筛选流水。"""
        resp = await admin_client.get("/api/v1/admin/credits/ledger?user_id=user-001")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 2
        for item in data["items"]:
            assert item["user_id"] == "user-001"

    async def test_filter_by_change_type(self, admin_client: AsyncClient):
        """按变化类型筛选。"""
        resp = await admin_client.get(
            "/api/v1/admin/credits/ledger?change_type=consume"
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["change_type"] == "consume"
        assert data["items"][0]["amount"] == -50

    async def test_filter_by_source_type(self, admin_client: AsyncClient):
        """按来源类型筛选。"""
        resp = await admin_client.get(
            "/api/v1/admin/credits/ledger?source_type=system"
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["source_type"] == "system"

    async def test_ledger_contains_user_account(self, admin_client: AsyncClient):
        """流水列表项应包含用户账号。"""
        resp = await admin_client.get(
            "/api/v1/admin/credits/ledger?user_id=user-001"
        )
        data = _assert_success_response(resp.json())
        assert data["items"][0]["user_account"] == "alice@example.com"

    async def test_pagination(self, admin_client: AsyncClient):
        """分页应正确生效。"""
        resp = await admin_client.get("/api/v1/admin/credits/ledger?limit=1&offset=0")
        assert resp.status_code == 200
        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 1
        assert data["total"] == 2

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询全部流水。"""
        resp = await user_client.get("/api/v1/admin/credits/ledger")
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询流水应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/credits/ledger")
        assert resp.status_code == 401


# ============================================================
# POST /api/v1/admin/credits/adjust — 手动调整额度
# ============================================================


class TestAdjustCredits:
    """手动调整额度接口测试。"""

    async def test_grant_credits(self, admin_client: AsyncClient):
        """赠送额度应成功，账户余额增加。"""
        resp = await admin_client.post(
            "/api/v1/admin/credits/adjust",
            json={
                "user_id": "user-002",
                "amount": 100,
                "description": "活动赠送 100 额度",
            },
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["balance"] == 105  # 原来 5 + 100
        assert data["user_account"] == "bob@example.com"

    async def test_deduct_credits(self, admin_client: AsyncClient):
        """扣除额度应成功（余额充足时），账户余额减少。"""
        resp = await admin_client.post(
            "/api/v1/admin/credits/adjust",
            json={
                "user_id": "user-001",
                "amount": -100,
                "description": "违规扣除 100 额度",
            },
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["balance"] == 350  # 原来 450 - 100

    async def test_adjust_zero_amount_rejected(self, admin_client: AsyncClient):
        """调整额度为 0 应返回 422。"""
        resp = await admin_client.post(
            "/api/v1/admin/credits/adjust",
            json={"user_id": "user-001", "amount": 0},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    async def test_user_not_found(self, admin_client: AsyncClient):
        """调整不存在的用户额度应返回 404。"""
        resp = await admin_client.post(
            "/api/v1/admin/credits/adjust",
            json={"user_id": "nonexistent-user", "amount": 100},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "USER_NOT_FOUND"

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权手动调整额度。"""
        resp = await user_client.post(
            "/api/v1/admin/credits/adjust",
            json={"user_id": "user-001", "amount": 100},
        )
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权调整额度应返回 401。"""
        resp = await no_auth_client.post(
            "/api/v1/admin/credits/adjust",
            json={"user_id": "user-001", "amount": 100},
        )
        assert resp.status_code == 401


# ============================================================
# 响应格式验证
# ============================================================


class TestResponseFormat:
    """统一响应格式验证。"""

    async def test_plan_list_response_format(self, admin_client: AsyncClient):
        """套餐列表响应格式应正确。"""
        resp = await admin_client.get("/api/v1/admin/plans")
        body = resp.json()

        assert body["success"] is True
        assert body["error"] is None
        assert "request_id" in body
        assert "data" in body
        assert "items" in body["data"]

    async def test_order_list_response_format(self, admin_client: AsyncClient):
        """订单列表响应格式应正确。"""
        resp = await admin_client.get("/api/v1/admin/orders")
        body = resp.json()

        assert body["success"] is True
        assert body["error"] is None
        assert "request_id" in body
        data = body["data"]
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    async def test_credit_account_list_response_format(self, admin_client: AsyncClient):
        """额度账户列表响应格式应正确。"""
        resp = await admin_client.get("/api/v1/admin/credits/accounts")
        body = resp.json()

        assert body["success"] is True
        assert body["error"] is None
        assert "data" in body
        assert "items" in body["data"]
        assert "total" in body["data"]

    async def test_credit_ledger_response_format(self, admin_client: AsyncClient):
        """额度流水列表响应格式应正确。"""
        resp = await admin_client.get("/api/v1/admin/credits/ledger")
        body = resp.json()

        assert body["success"] is True
        assert body["error"] is None
        assert "data" in body
        data = body["data"]
        assert "items" in data
        assert "total" in data

    async def test_error_response_format(self, admin_client: AsyncClient):
        """错误响应格式应正确。"""
        resp = await admin_client.get("/api/v1/admin/plans/nonexistent-id")
        body = resp.json()

        assert body["success"] is False
        assert body["data"] is None
        assert body["error"] is not None
        assert "code" in body["error"]
        assert "message" in body["error"]
        assert "request_id" in body
