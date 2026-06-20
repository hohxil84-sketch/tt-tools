"""
credits_billing DTO 契约一致性测试。

验证手写 DTO 与 shared-contract/openapi/credits-billing.yaml 对齐：
- 序列化 / 反序列化正确
- required / nullable 字段行为正确
- 统一响应结构正确
- 枚举值正确
- 客户端禁止提交字段不会出现在请求 DTO 中
"""

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from credits_billing import (
    # 通用
    ApiResponse,
    ErrorDetail,
    # 枚举
    ChangeType,
    # 余额
    CreditBalance,
    CreditBalanceResponse,
    # 流水
    CreditLedgerItem,
    CreditLedgerData,
    CreditLedgerResponse,
    # 权限检查
    EntitlementCheckRequest,
    EntitlementCheckData,
    EntitlementCheckResponse,
)


# ============================================================
# 通用结构测试
# ============================================================


class TestErrorDetail:
    """统一错误详情"""

    def test_minimal_error(self):
        err = ErrorDetail(code="CREDITS_NOT_ENOUGH", message="额度不足")
        assert err.code == "CREDITS_NOT_ENOUGH"
        assert err.message == "额度不足"
        assert err.details is None

    def test_error_with_details(self):
        err = ErrorDetail(
            code="VALIDATION_ERROR",
            message="字段校验失败",
            details={"feature": "功能码不能为空"},
        )
        assert err.details == {"feature": "功能码不能为空"}

    def test_serialize_minimal(self):
        err = ErrorDetail(code="BILLING_FAILED", message="扣费失败")
        d = err.model_dump()
        assert d == {"code": "BILLING_FAILED", "message": "扣费失败", "details": None}

    def test_serialize_exclude_none(self):
        err = ErrorDetail(code="BILLING_FAILED", message="扣费失败")
        d = err.model_dump(exclude_none=True)
        assert "details" not in d


class TestApiResponse:
    """统一响应结构"""

    def test_success_response(self):
        data = CreditBalance(
            user_id=uuid4(),
            plan_code="standard",
            monthly_grant=1000,
            balance=850,
            status="active",
            updated_at=datetime.now(timezone.utc),
        )
        resp = ApiResponse[CreditBalance](
            success=True,
            data=data,
            error=None,
            request_id="req-001",
        )
        assert resp.success is True
        assert resp.data.balance == 850
        assert resp.error is None

    def test_error_response(self):
        resp = ApiResponse[CreditBalance](
            success=False,
            data=None,
            error=ErrorDetail(code="AUTH_REQUIRED", message="请先登录"),
            request_id="req-002",
        )
        assert resp.success is False
        assert resp.data is None
        assert resp.error.code == "AUTH_REQUIRED"


# ============================================================
# 余额测试
# ============================================================


class TestCreditBalance:
    """额度余额 DTO"""

    def test_minimal(self):
        now = datetime.now(timezone.utc)
        balance = CreditBalance(
            user_id=uuid4(),
            plan_code="free",
            monthly_grant=100,
            balance=50,
            status="active",
            updated_at=now,
        )
        assert balance.balance == 50
        assert balance.period_start is None
        assert balance.period_end is None

    def test_with_period(self):
        now = datetime.now(timezone.utc)
        balance = CreditBalance(
            user_id=uuid4(),
            plan_code="standard",
            monthly_grant=1000,
            balance=1000,
            period_start=datetime(2026, 6, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 7, 1, tzinfo=timezone.utc),
            status="active",
            updated_at=now,
        )
        assert balance.period_start == datetime(2026, 6, 1, tzinfo=timezone.utc)

    def test_roundtrip_json(self):
        """反序列化 → 序列化 → 再反序列化"""
        now = datetime.now(timezone.utc)
        user_id = uuid4()
        balance = CreditBalance(
            user_id=user_id,
            plan_code="pro",
            monthly_grant=5000,
            balance=3200,
            period_start=datetime(2026, 6, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 7, 1, tzinfo=timezone.utc),
            status="active",
            updated_at=now,
        )
        resp = CreditBalanceResponse(
            success=True, data=balance, error=None, request_id="req-003"
        )
        json_str = resp.model_dump_json()
        parsed = CreditBalanceResponse.model_validate_json(json_str)
        assert parsed.success is True
        assert parsed.data.user_id == user_id
        assert parsed.data.balance == 3200
        assert parsed.data.plan_code == "pro"

    def test_from_contract_sample(self):
        """用 API_INDEX.md 中的示例结构校验"""
        sample_json = json.dumps({
            "success": True,
            "data": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "plan_code": "standard",
                "monthly_grant": 1000,
                "balance": 850,
                "period_start": "2026-06-01T00:00:00Z",
                "period_end": "2026-07-01T00:00:00Z",
                "status": "active",
                "updated_at": "2026-06-15T10:30:00Z",
            },
            "error": None,
            "request_id": "req-sample-001",
        })
        resp = CreditBalanceResponse.model_validate_json(sample_json)
        assert resp.data.user_id == UUID("550e8400-e29b-41d4-a716-446655440000")
        assert resp.data.monthly_grant == 1000


# ============================================================
# 流水测试
# ============================================================


class TestCreditLedger:
    """额度流水 DTO"""

    def test_consume_item(self):
        item = CreditLedgerItem(
            id=uuid4(),
            change_type=ChangeType.consume,
            amount=-2,
            balance_after=848,
            source_type="provider_call",
            source_id=uuid4(),
            description="AI 文案生成扣费",
            created_at=datetime.now(timezone.utc),
        )
        assert item.change_type == ChangeType.consume
        assert item.amount == -2

    def test_grant_item(self):
        item = CreditLedgerItem(
            id=uuid4(),
            change_type=ChangeType.grant,
            amount=1000,
            balance_after=1000,
            source_type="system",
            description="月度额度赠送",
            created_at=datetime.now(timezone.utc),
        )
        assert item.change_type == ChangeType.grant
        assert item.amount == 1000

    def test_enum_values(self):
        """验证所有变动类型枚举"""
        assert ChangeType.grant.value == "grant"
        assert ChangeType.consume.value == "consume"
        assert ChangeType.recharge.value == "recharge"
        assert ChangeType.refund.value == "refund"
        assert ChangeType.adjust.value == "adjust"

    def test_ledger_response_roundtrip(self):
        item = CreditLedgerItem(
            id=uuid4(),
            change_type=ChangeType.consume,
            amount=-2,
            balance_after=848,
            source_type="provider_call",
            created_at=datetime.now(timezone.utc),
        )
        data = CreditLedgerData(items=[item], total=1, limit=50, offset=0)
        resp = CreditLedgerResponse(
            success=True, data=data, error=None, request_id="req-004"
        )
        json_str = resp.model_dump_json()
        parsed = CreditLedgerResponse.model_validate_json(json_str)
        assert parsed.data.total == 1
        assert len(parsed.data.items) == 1
        assert parsed.data.items[0].change_type == ChangeType.consume

    def test_empty_ledger(self):
        data = CreditLedgerData(items=[], total=0, limit=50, offset=0)
        resp = CreditLedgerResponse(
            success=True, data=data, error=None, request_id="req-005"
        )
        assert resp.data.items == []
        assert resp.data.total == 0


# ============================================================
# 权限检查测试
# ============================================================


class TestEntitlementCheck:
    """套餐权限检查 DTO"""

    def test_request_minimal(self):
        req = EntitlementCheckRequest(
            feature="resize_image_local_paid",
            operation="single",
            client_request_id="local_req_xxx",
        )
        d = req.model_dump()
        assert d["feature"] == "resize_image_local_paid"
        # 客户端禁止提交字段不应存在
        assert "user_id" not in d
        assert "plan_code" not in d

    def test_response_allowed(self):
        data = EntitlementCheckData(
            allowed=True,
            feature="resize_image_local_paid",
            plan_code="standard",
            remaining_free_quota=None,
            reason=None,
        )
        assert data.allowed is True
        assert data.remaining_free_quota is None

    def test_response_denied(self):
        data = EntitlementCheckData(
            allowed=False,
            feature="resize_image_local_paid",
            plan_code="free",
            remaining_free_quota=0,
            reason="免费套餐已用完该功能的免费额度",
        )
        assert data.allowed is False
        assert data.remaining_free_quota == 0
        assert "免费" in data.reason

    def test_from_contract_sample(self):
        """用 API_INDEX.md 中的示例结构校验"""
        sample_json = json.dumps({
            "success": True,
            "data": {
                "allowed": True,
                "feature": "resize_image_local_paid",
                "plan_code": "standard",
                "remaining_free_quota": None,
                "reason": None,
            },
            "error": None,
            "request_id": "req-sample-002",
        })
        resp = EntitlementCheckResponse.model_validate_json(sample_json)
        assert resp.data.allowed is True
        assert resp.data.plan_code == "standard"


# ============================================================
# 禁止字段检查
# ============================================================


class TestForbiddenClientFields:
    """
    验证客户端请求 DTO 不包含禁止提交字段：
    user_id、device_id、role、plan_code、provider、model、
    estimated_cost、credits_charged、permission_granted、final_price
    """

    def test_entitlement_request_no_forbidden_fields(self):
        """EntitlementCheckRequest 不得包含禁止字段"""
        req = EntitlementCheckRequest(
            feature="resize_image_local_paid",
            operation="single",
            client_request_id="req-001",
        )
        field_names = set(req.model_dump().keys())
        forbidden = {
            "user_id", "device_id", "role", "plan_code",
            "provider", "model", "estimated_cost", "credits_charged",
            "permission_granted", "final_price",
        }
        assert field_names.isdisjoint(forbidden), (
            f"请求 DTO 包含禁止字段: {field_names & forbidden}"
        )

    def test_balance_response_does_not_contain_forbidden_client_fields(self):
        """CreditBalance 响应中可以包含 user_id 和 plan_code（服务端返回）"""
        now = datetime.now(timezone.utc)
        balance = CreditBalance(
            user_id=uuid4(),
            plan_code="standard",
            monthly_grant=1000,
            balance=500,
            status="active",
            updated_at=now,
        )
        # user_id 和 plan_code 由服务端返回是允许的
        assert balance.user_id is not None
        assert balance.plan_code == "standard"
        # 但不包含 provider / model / estimated_cost 等 Provider 相关字段
        assert not hasattr(balance, "provider")
        assert not hasattr(balance, "estimated_cost")
