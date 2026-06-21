"""
cloud-orders-recharge 模块完整测试。

覆盖创建订单、查询订单列表、确认支付 3 个接口的成功路径和负例路径。

测试覆盖清单：
正例：创建 credits/plan 订单、订单列表分页筛选、确认支付（充值+套餐切换）
负例：未认证拒绝、跨用户隔离、closed 拒绝、无效参数拒绝、决策字段忽略、
       重复确认幂等（不重复写 ledger）、OpenAPI-DTO 字段一致
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select, func, text

# 本文件所有测试均为异步测试
pytestmark = pytest.mark.asyncio


# ============================================================
# 辅助函数
# ============================================================


async def _get_balance(db_session, user_id: str) -> int:
    """通过数据库查询用户额度余额。"""
    result = await db_session.execute(
        text("SELECT balance FROM credit_accounts WHERE user_id = :uid"),
        {"uid": user_id},
    )
    row = result.fetchone()
    return row[0] if row else 0


async def _count_ledger_by_source(db_session, source_id: str) -> int:
    """统计指定 source_id 的 credit_ledger 记录数。"""
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM credit_ledger WHERE source_id = :sid"),
        {"sid": source_id},
    )
    return result.scalar()


async def _get_user_plan_code(db_session, user_id: str) -> str:
    """查询用户的 plan_code。"""
    result = await db_session.execute(
        text("SELECT plan_code FROM users WHERE id = :uid"),
        {"uid": user_id},
    )
    row = result.fetchone()
    return row[0] if row else ""


# ============================================================
# POST /api/v1/orders — 创建订单
# ============================================================


class TestCreateOrder:
    """创建订单接口测试。"""

    async def test_create_credits_order_success(
        self, client: AsyncClient, test_user, auth_headers
    ):
        """创建 credits 充值订单：应返回订单详情，金额由服务端定价表决定。"""
        resp = await client.post("/api/v1/orders", json={
            "order_type": "credits",
            "product_code": "credits_100",
            "client_request_id": "req_001",
        }, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["error"] is None

        data = body["data"]
        assert data["order_type"] == "credits"
        assert data["product_code"] == "credits_100"
        assert data["amount_cents"] == 1000  # 服务端定价 ¥10 = 1000分
        assert data["credit_amount"] == 100
        assert data["currency"] == "CNY"
        assert data["status"] == "pending"
        assert data["order_no"].startswith("ORD-")
        assert data["paid_at"] is None
        _assert_order_fields(data)

    async def test_create_plan_order_success(
        self, client: AsyncClient, test_user, auth_headers
    ):
        """创建 plan 套餐购买订单。"""
        resp = await client.post("/api/v1/orders", json={
            "order_type": "plan",
            "product_code": "standard",
            "client_request_id": "req_002",
        }, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

        data = body["data"]
        assert data["order_type"] == "plan"
        assert data["product_code"] == "standard"
        assert data["amount_cents"] == 2900  # 服务端定价 ¥29 = 2900分
        assert data["credit_amount"] is None  # plan 订单无 credit_amount
        assert data["status"] == "pending"
        _assert_order_fields(data)

    async def test_create_order_no_auth(self, client: AsyncClient):
        """未认证创建订单：应返回 401。"""
        resp = await client.post("/api/v1/orders", json={
            "order_type": "credits",
            "product_code": "credits_100",
            "client_request_id": "req_noauth",
        })
        assert resp.status_code == 401

    async def test_create_order_invalid_product_code(
        self, client: AsyncClient, test_user, auth_headers
    ):
        """无效 product_code：应返回错误。"""
        resp = await client.post("/api/v1/orders", json={
            "order_type": "credits",
            "product_code": "credits_99999",
            "client_request_id": "req_bad_code",
        }, headers=auth_headers)
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            body = resp.json()
            assert body["success"] is False
            assert "无效" in body["error"]["message"]

    async def test_create_order_ignores_extra_fields(
        self, client: AsyncClient, test_user, auth_headers
    ):
        """客户端传入 user_id/final_price 等决策字段：应被忽略，金额仍由服务端决定。"""
        resp = await client.post("/api/v1/orders", json={
            "order_type": "credits",
            "product_code": "credits_100",
            "client_request_id": "req_extra",
            "user_id": "attacker_user_id",       # 客户端不应提交，应被忽略
            "final_price": 1,                      # 客户端不应提交，应被忽略
            "plan_code": "pro",                    # 客户端不应提交，应被忽略
        }, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        # 金额仍由服务端定价，不受客户端传入字段影响
        assert data["amount_cents"] == 1000
        assert data["product_code"] == "credits_100"

    async def test_create_order_invalid_plan_code(
        self, client: AsyncClient, test_user, auth_headers
    ):
        """创建订单时无效 plan code 被拒绝。"""
        resp = await client.post("/api/v1/orders", json={
            "order_type": "plan",
            "product_code": "enterprise",
            "client_request_id": "req_bad_plan",
        }, headers=auth_headers)
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            body = resp.json()
            assert body["success"] is False


# ============================================================
# GET /api/v1/orders — 查询订单列表
# ============================================================


class TestListOrders:
    """订单列表查询接口测试。"""

    async def test_list_orders_empty(
        self, client: AsyncClient, test_user, auth_headers
    ):
        """无订单用户查询：返回空列表。"""
        resp = await client.get("/api/v1/orders", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["total"] == 0
        assert body["data"]["items"] == []
        assert body["data"]["limit"] == 50
        assert body["data"]["offset"] == 0

    async def test_list_orders_with_data(
        self, client: AsyncClient, test_user, auth_headers,
        pending_credits_order, pending_plan_order
    ):
        """有订单的用户查询：应返回所有订单。"""
        resp = await client.get("/api/v1/orders", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["total"] == 2
        assert len(body["data"]["items"]) == 2

    async def test_list_orders_filter_by_type(
        self, client: AsyncClient, test_user, auth_headers,
        pending_credits_order, pending_plan_order
    ):
        """按 order_type 筛选。"""
        resp = await client.get(
            "/api/v1/orders?order_type=credits", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        for item in body["data"]["items"]:
            assert item["order_type"] == "credits"

    async def test_list_orders_filter_by_status(
        self, client: AsyncClient, test_user, auth_headers,
        pending_credits_order, pending_plan_order
    ):
        """按 status 筛选。"""
        resp = await client.get(
            "/api/v1/orders?status=pending", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        for item in body["data"]["items"]:
            assert item["status"] == "pending"

    async def test_list_orders_pagination(
        self, client: AsyncClient, test_user, auth_headers,
        pending_credits_order, pending_plan_order
    ):
        """分页功能正常。"""
        resp = await client.get(
            "/api/v1/orders?limit=1&offset=0", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["limit"] == 1
        assert body["data"]["offset"] == 0
        assert body["data"]["total"] == 2
        assert len(body["data"]["items"]) == 1

    async def test_list_orders_no_auth(self, client: AsyncClient):
        """未认证查询订单列表：应返回 401。"""
        resp = await client.get("/api/v1/orders")
        assert resp.status_code == 401

    async def test_list_orders_user_isolation(
        self, client: AsyncClient, test_user, user_b,
        auth_headers, user_b_auth_headers,
        pending_credits_order
    ):
        """用户 A 的订单列表不包含用户 B 的订单，反之亦然。"""
        # 用户 A 查询
        resp_a = await client.get("/api/v1/orders", headers=auth_headers)
        assert resp_a.status_code == 200
        a_ids = {item["id"] for item in resp_a.json()["data"]["items"]}

        # 用户 B 查询
        resp_b = await client.get("/api/v1/orders", headers=user_b_auth_headers)
        assert resp_b.status_code == 200
        b_ids = {item["id"] for item in resp_b.json()["data"]["items"]}

        # 两个用户不应看到彼此的订单
        assert pending_credits_order.id in a_ids
        assert pending_credits_order.id not in b_ids


# ============================================================
# POST /api/v1/orders/{order_id}/confirm — 确认支付
# ============================================================


class TestConfirmOrder:
    """确认支付接口测试。"""

    # --- 正例 ---

    async def test_confirm_credits_order(
        self, client: AsyncClient, test_user, auth_headers,
        pending_credits_order, db_session
    ):
        """确认 credits 充值订单：发放额度，写入 ledger，状态变 paid。"""
        order_id = pending_credits_order.id

        # 确认前余额
        balance_before = await _get_balance(db_session, test_user.id)

        # 确认支付
        resp = await client.post(
            f"/api/v1/orders/{order_id}/confirm", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "paid"
        assert body["data"]["paid_at"] is not None

        # 验证额度已发放（通过 DB 查询）
        balance_after = await _get_balance(db_session, test_user.id)
        assert balance_after == balance_before + pending_credits_order.credit_amount

        # 验证 ledger 可追溯（source_id = order.id）
        recharge_count = await _count_ledger_by_source(db_session, order_id)
        assert recharge_count == 1, "ledger 应有一条 recharge 记录"

    async def test_confirm_plan_order(
        self, client: AsyncClient, test_user, auth_headers,
        pending_plan_order, db_session
    ):
        """确认 plan 套餐购买订单：更新用户 plan_code。"""
        order_id = pending_plan_order.id

        # 验证确认前 plan_code 为 standard
        plan_before = await _get_user_plan_code(db_session, test_user.id)
        assert plan_before == "standard"

        # 确认支付
        resp = await client.post(
            f"/api/v1/orders/{order_id}/confirm", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "paid"

        # 验证 plan_code 已更新为 pro
        plan_after = await _get_user_plan_code(db_session, test_user.id)
        assert plan_after == "pro"

    # --- 负例：幂等 ---

    async def test_confirm_idempotent(
        self, client: AsyncClient, test_user, auth_headers,
        pending_credits_order, db_session
    ):
        """重复确认同一订单：不重复发放额度，ledger 只写一次。"""
        order_id = pending_credits_order.id

        # 第一次确认：成功
        resp1 = await client.post(
            f"/api/v1/orders/{order_id}/confirm", headers=auth_headers
        )
        assert resp1.status_code == 200
        assert resp1.json()["data"]["status"] == "paid"

        # 第二次确认：幂等返回相同结果
        resp2 = await client.post(
            f"/api/v1/orders/{order_id}/confirm", headers=auth_headers
        )
        assert resp2.status_code == 200
        assert resp2.json()["data"]["status"] == "paid"
        assert resp2.json()["data"]["paid_at"] is not None

        # 验证 ledger 中该订单只有 1 条 recharge 记录（硬约束 #4）
        recharge_count = await _count_ledger_by_source(db_session, order_id)
        assert recharge_count == 1, (
            f"重复确认导致 ledger 重复写入：{recharge_count} 条记录（应只有 1 条）"
        )

        # 验证余额只增加了一次
        balance = await _get_balance(db_session, test_user.id)
        expected = 500 + pending_credits_order.credit_amount
        assert balance == expected, (
            f"余额应为 {expected}（初始赠送 + 1 次充值），实际为 {balance}"
        )

    # --- 负例：跨用户隔离 ---

    async def test_confirm_order_user_isolation(
        self, client: AsyncClient, test_user, user_b,
        auth_headers, user_b_auth_headers,
        pending_credits_order
    ):
        """用户 B 不能确认用户 A 的订单（硬约束 #2）。"""
        order_id = pending_credits_order.id

        resp = await client.post(
            f"/api/v1/orders/{order_id}/confirm", headers=user_b_auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "ORDER_NOT_FOUND"

    # --- 负例：closed 订单拒绝 ---

    async def test_confirm_closed_order_rejected(
        self, client: AsyncClient, test_user, auth_headers,
        pending_credits_order, db_session
    ):
        """closed 订单不能确认支付。"""
        from sqlalchemy import update
        from models import Order  # noqa: F811

        # 手动将订单置为 closed
        await db_session.execute(
            update(Order)
            .where(Order.id == pending_credits_order.id)
            .values(status="closed")
        )
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/orders/{pending_credits_order.id}/confirm",
            headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False

        # 验证不发放额度
        balance = await _get_balance(db_session, test_user.id)
        assert balance == 500  # 未变

    # --- 负例：未认证 ---

    async def test_confirm_order_no_auth(
        self, client: AsyncClient, pending_credits_order
    ):
        """未认证确认支付：应返回 401。"""
        resp = await client.post(
            f"/api/v1/orders/{pending_credits_order.id}/confirm"
        )
        assert resp.status_code == 401


# ============================================================
# 响应结构测试
# ============================================================


def _assert_order_fields(data: dict):
    """验证 OrderData 响应的字段与 OpenAPI 契约一致。"""
    required_fields = [
        "id", "order_no", "order_type", "product_code",
        "amount_cents", "currency", "status", "created_at", "updated_at",
    ]
    for field in required_fields:
        assert field in data, f"响应缺少 OpenAPI 定义字段: {field}"
    # amount_cents 必须是整数（非浮点）—— 硬约束 #7
    assert isinstance(data["amount_cents"], int), (
        f"amount_cents 必须是整数分，实际类型: {type(data['amount_cents'])}"
    )


class TestResponseStructure:
    """响应结构与 OpenAPI 契约一致性测试。"""

    async def test_create_order_response_structure(
        self, client: AsyncClient, test_user, auth_headers
    ):
        """创建订单响应字段与 OpenAPI 一致。"""
        resp = await client.post("/api/v1/orders", json={
            "order_type": "credits",
            "product_code": "credits_500",
            "client_request_id": "req_struct",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        _assert_order_fields(data)
        # credits_500: ¥40 = 4000 分, 500 额度
        assert data["amount_cents"] == 4000
        assert data["credit_amount"] == 500

    async def test_confirm_response_structure(
        self, client: AsyncClient, test_user, auth_headers,
        pending_credits_order
    ):
        """确认支付响应字段与 OpenAPI 一致。"""
        resp = await client.post(
            f"/api/v1/orders/{pending_credits_order.id}/confirm",
            headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        _assert_order_fields(data)
        assert data["status"] == "paid"
        assert data["paid_at"] is not None

    async def test_list_orders_response_structure(
        self, client: AsyncClient, test_user, auth_headers,
        pending_credits_order
    ):
        """订单列表响应字段与 OpenAPI 一致。"""
        resp = await client.get("/api/v1/orders", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        list_data = body["data"]
        assert "items" in list_data
        assert "total" in list_data
        assert "limit" in list_data
        assert "offset" in list_data
        for item in list_data["items"]:
            _assert_order_fields(item)

    async def test_error_response_structure(
        self, client: AsyncClient, test_user, auth_headers
    ):
        """错误响应也包含 success/data/error/request_id。"""
        resp = await client.post("/api/v1/orders", json={
            "order_type": "credits",
            "product_code": "credits_99999",
            "client_request_id": "req_err",
        }, headers=auth_headers)
        if resp.status_code == 200:
            body = resp.json()
            if not body["success"]:
                assert "success" in body
                assert "data" in body
                assert "error" in body
                assert "request_id" in body


# ============================================================
# 完整流程集成测试
# ============================================================


class TestFullFlow:
    """完整订单生命周期：创建 → 查询 → 确认 → 验证。"""

    async def test_credits_order_full_flow(
        self, client: AsyncClient, test_user, auth_headers, db_session
    ):
        """credits 订单完整流程。"""
        # 1. 创建订单
        create_resp = await client.post("/api/v1/orders", json={
            "order_type": "credits",
            "product_code": "credits_2000",
            "client_request_id": "flow_001",
        }, headers=auth_headers)
        assert create_resp.status_code == 200
        order = create_resp.json()["data"]
        assert order["status"] == "pending"
        assert order["amount_cents"] == 15000  # ¥150 = 15000分
        assert order["credit_amount"] == 2000

        # 2. 查询订单列表确认可见
        list_resp = await client.get("/api/v1/orders", headers=auth_headers)
        order_ids = {item["id"] for item in list_resp.json()["data"]["items"]}
        assert order["id"] in order_ids

        # 3. 确认支付
        confirm_resp = await client.post(
            f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["data"]["status"] == "paid"

        # 4. 验证余额（DB 查询）
        balance = await _get_balance(db_session, test_user.id)
        assert balance == 2500  # 初始 500 + 充值 2000

        # 5. 验证 ledger（DB 查询）
        recharge_count = await _count_ledger_by_source(db_session, order["id"])
        assert recharge_count == 1

    async def test_plan_order_full_flow(
        self, client: AsyncClient, test_user, auth_headers, db_session
    ):
        """plan 订单完整流程。"""
        # 1. 创建订单（从 standard 升级到 pro）
        create_resp = await client.post("/api/v1/orders", json={
            "order_type": "plan",
            "product_code": "pro",
            "client_request_id": "flow_plan",
        }, headers=auth_headers)
        assert create_resp.status_code == 200
        order = create_resp.json()["data"]
        assert order["status"] == "pending"

        # 2. 确认支付
        confirm_resp = await client.post(
            f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["data"]["status"] == "paid"

        # 3. 验证 plan_code 已更新
        plan_after = await _get_user_plan_code(db_session, test_user.id)
        assert plan_after == "pro"

        # 4. 验证额度不受影响（plan 订单不改变额度）
        balance = await _get_balance(db_session, test_user.id)
        assert balance == 500  # 初始赠送不变
