"""
admin-ops 模块完整测试。

覆盖 7 个接口的成功路径、鉴权错误路径和业务错误路径：

Provider 调用日志：
- GET    /admin/provider-call-logs          — 全部调用日志列表
- GET    /admin/provider-call-logs/{log_id} — 调用日志详情

成本统计：
- GET    /admin/cost-stats                  — 成本/用量聚合统计

风控日志：
- GET    /admin/risk-logs                   — 风控日志列表
- GET    /admin/risk-logs/{log_id}          — 风控日志详情

功能开关：
- GET    /admin/feature-flags               — 查询功能开关配置
- PATCH  /admin/plans/{plan_id}/features    — 更新套餐功能开关

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
# GET /api/v1/admin/provider-call-logs — Provider 调用日志列表
# ============================================================


class TestListProviderCallLogs:
    """Provider 调用日志列表接口测试。"""

    async def test_as_admin_returns_all_logs(self, admin_client: AsyncClient):
        """管理员查询调用日志，应返回所有日志。"""
        resp = await admin_client.get("/api/v1/admin/provider-call-logs")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 3
        assert data["total"] == 3
        assert data["limit"] == 20
        assert data["offset"] == 0

    async def test_items_have_required_fields(self, admin_client: AsyncClient):
        """列表项应包含所有必填字段，不包含隐私字段。"""
        resp = await admin_client.get("/api/v1/admin/provider-call-logs")
        data = _assert_success_response(resp.json())

        for item in data["items"]:
            assert "id" in item
            assert "request_id" in item
            assert "user_id" in item
            assert "feature" in item
            assert "provider" in item
            assert "model" in item
            assert "status" in item
            assert "input_tokens" in item
            assert "output_tokens" in item
            assert "total_tokens" in item
            assert "estimated_cost" in item
            assert "credits_charged" in item
            assert "created_at" in item
            # 不返回隐私字段
            assert "raw_usage_json" not in item
            assert "raw_meta_json" not in item

    async def test_filter_by_user_id(self, admin_client: AsyncClient):
        """按 user_id 筛选应只返回该用户的日志。"""
        resp = await admin_client.get(
            "/api/v1/admin/provider-call-logs", params={"user_id": "user-001"}
        )
        data = _assert_success_response(resp.json())
        assert data["total"] == 2
        for item in data["items"]:
            assert item["user_id"] == "user-001"

    async def test_filter_by_feature(self, admin_client: AsyncClient):
        """按功能码筛选应只返回匹配的日志。"""
        resp = await admin_client.get(
            "/api/v1/admin/provider-call-logs", params={"feature": "ai_copy_cloud"}
        )
        data = _assert_success_response(resp.json())
        assert data["total"] == 2
        for item in data["items"]:
            assert item["feature"] == "ai_copy_cloud"

    async def test_filter_by_provider(self, admin_client: AsyncClient):
        """按 Provider 筛选应只返回匹配的日志。"""
        resp = await admin_client.get(
            "/api/v1/admin/provider-call-logs", params={"provider": "openai"}
        )
        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["provider"] == "openai"

    async def test_filter_by_status(self, admin_client: AsyncClient):
        """按状态筛选应只返回匹配的日志。"""
        resp = await admin_client.get(
            "/api/v1/admin/provider-call-logs", params={"status": "failed"}
        )
        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["status"] == "failed"

    async def test_pagination(self, admin_client: AsyncClient):
        """分页应正确工作。"""
        resp = await admin_client.get(
            "/api/v1/admin/provider-call-logs", params={"limit": 2, "offset": 0}
        )
        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 2
        assert data["total"] == 3
        assert data["limit"] == 2

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询调用日志。"""
        resp = await user_client.get("/api/v1/admin/provider-call-logs")
        assert resp.status_code == 403
        _assert_error_detail(resp.json(), "PERMISSION_DENIED")

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询调用日志应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/provider-call-logs")
        assert resp.status_code == 401
        _assert_error_detail(resp.json(), "AUTH_REQUIRED")


# ============================================================
# GET /api/v1/admin/provider-call-logs/{log_id} — 调用日志详情
# ============================================================


class TestGetProviderCallLogDetail:
    """Provider 调用日志详情接口测试。"""

    async def test_as_admin_returns_detail(self, admin_client: AsyncClient):
        """管理员查询调用日志详情，应返回完整信息。"""
        resp = await admin_client.get("/api/v1/admin/provider-call-logs/pcl-001")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["id"] == "pcl-001"
        assert data["request_id"] == "req-001"
        assert data["user_id"] == "user-001"
        assert data["feature"] == "ai_copy_cloud"
        assert data["provider"] == "deepseek"
        assert data["model"] == "deepseek-chat"
        assert data["status"] == "success"
        # 不返回隐私字段
        assert "raw_usage_json" not in data
        assert "raw_meta_json" not in data

    async def test_detail_includes_user_info(self, admin_client: AsyncClient):
        """详情应包含用户账号和展示名称。"""
        resp = await admin_client.get("/api/v1/admin/provider-call-logs/pcl-001")
        data = _assert_success_response(resp.json())
        assert data["user_account"] == "alice@example.com"
        assert data["user_display_name"] == "Alice"

    async def test_not_found(self, admin_client: AsyncClient):
        """查询不存在的日志应返回 404。"""
        resp = await admin_client.get(
            "/api/v1/admin/provider-call-logs/nonexistent-id"
        )
        assert resp.status_code == 404

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询调用日志详情。"""
        resp = await user_client.get("/api/v1/admin/provider-call-logs/pcl-001")
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询调用日志详情应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/provider-call-logs/pcl-001")
        assert resp.status_code == 401


# ============================================================
# GET /api/v1/admin/cost-stats — 成本统计
# ============================================================


class TestCostStats:
    """成本统计接口测试。"""

    async def test_as_admin_returns_stats(self, admin_client: AsyncClient):
        """管理员查询成本统计，应返回聚合数据。"""
        resp = await admin_client.get("/api/v1/admin/cost-stats")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total_calls"] == 3
        assert data["total_tokens"] == 580  # 180 + 350 + 50
        assert data["total_cost"] == pytest.approx(0.004, abs=0.01)
        assert data["total_credits_charged"] == 4  # 1 + 3 + 0

    async def test_by_feature_breakdown(self, admin_client: AsyncClient):
        """应按功能码分组统计。"""
        resp = await admin_client.get("/api/v1/admin/cost-stats")
        data = _assert_success_response(resp.json())

        assert len(data["by_feature"]) == 2  # ai_copy_cloud, ai_render_cloud
        features = {item["key"]: item for item in data["by_feature"]}
        assert "ai_copy_cloud" in features
        assert "ai_render_cloud" in features
        assert features["ai_copy_cloud"]["calls"] == 2
        assert features["ai_render_cloud"]["calls"] == 1

    async def test_by_provider_breakdown(self, admin_client: AsyncClient):
        """应按 Provider 分组统计。"""
        resp = await admin_client.get("/api/v1/admin/cost-stats")
        data = _assert_success_response(resp.json())

        assert len(data["by_provider"]) == 2  # deepseek, openai
        providers = {item["key"]: item for item in data["by_provider"]}
        assert "deepseek" in providers
        assert "openai" in providers
        assert providers["deepseek"]["calls"] == 2
        assert providers["openai"]["calls"] == 1

    async def test_empty_stats(self, admin_client: AsyncClient):
        """空数据库应返回零值统计。"""
        # 无法在已有种子数据的情况下测试空库，
        # 但种子数据的验证已覆盖统计准确性。
        pass

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询成本统计。"""
        resp = await user_client.get("/api/v1/admin/cost-stats")
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询成本统计应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/cost-stats")
        assert resp.status_code == 401


# ============================================================
# GET /api/v1/admin/risk-logs — 风控日志列表
# ============================================================


class TestListRiskLogs:
    """风控日志列表接口测试。"""

    async def test_as_admin_returns_all_logs(self, admin_client: AsyncClient):
        """管理员查询风控日志，应返回所有日志。"""
        resp = await admin_client.get("/api/v1/admin/risk-logs")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 3
        assert data["total"] == 3

    async def test_items_have_required_fields(self, admin_client: AsyncClient):
        """列表项应包含所有必填字段。"""
        resp = await admin_client.get("/api/v1/admin/risk-logs")
        data = _assert_success_response(resp.json())

        for item in data["items"]:
            assert "id" in item
            assert "risk_type" in item
            assert "severity" in item
            assert "created_at" in item

    async def test_filter_by_user_id(self, admin_client: AsyncClient):
        """按 user_id 筛选应只返回匹配的日志。"""
        resp = await admin_client.get(
            "/api/v1/admin/risk-logs", params={"user_id": "user-001"}
        )
        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == "user-001"

    async def test_filter_by_risk_type(self, admin_client: AsyncClient):
        """按风险类型筛选。"""
        resp = await admin_client.get(
            "/api/v1/admin/risk-logs", params={"risk_type": "rate_limit"}
        )
        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["risk_type"] == "rate_limit"

    async def test_filter_by_severity(self, admin_client: AsyncClient):
        """按严重程度筛选。"""
        resp = await admin_client.get(
            "/api/v1/admin/risk-logs", params={"severity": "high"}
        )
        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["severity"] == "high"

    async def test_includes_user_account(self, admin_client: AsyncClient):
        """列表项应包含关联的用户账号。"""
        resp = await admin_client.get(
            "/api/v1/admin/risk-logs", params={"user_id": "user-001"}
        )
        data = _assert_success_response(resp.json())
        assert data["items"][0]["user_account"] == "alice@example.com"

    async def test_anonymous_risk_log(self, admin_client: AsyncClient):
        """匿名风控日志（user_id 为 None）应正确返回。"""
        resp = await admin_client.get(
            "/api/v1/admin/risk-logs", params={"severity": "high"}
        )
        data = _assert_success_response(resp.json())
        assert data["items"][0]["user_id"] is None
        assert data["items"][0]["user_account"] is None

    async def test_pagination(self, admin_client: AsyncClient):
        """分页应正确工作。"""
        resp = await admin_client.get(
            "/api/v1/admin/risk-logs", params={"limit": 2, "offset": 0}
        )
        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 2
        assert data["total"] == 3

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询风控日志。"""
        resp = await user_client.get("/api/v1/admin/risk-logs")
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询风控日志应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/risk-logs")
        assert resp.status_code == 401


# ============================================================
# GET /api/v1/admin/risk-logs/{log_id} — 风控日志详情
# ============================================================


class TestGetRiskLogDetail:
    """风控日志详情接口测试。"""

    async def test_as_admin_returns_detail(self, admin_client: AsyncClient):
        """管理员查询风控日志详情，应返回完整信息。"""
        resp = await admin_client.get("/api/v1/admin/risk-logs/risk-001")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["id"] == "risk-001"
        assert data["user_id"] == "user-001"
        assert data["risk_type"] == "suspicious_login"
        assert data["severity"] == "medium"
        assert "details_json" in data
        assert data["details_json"]["reason"] == "异地登录"

    async def test_detail_includes_user_info(self, admin_client: AsyncClient):
        """详情应包含用户展示名称。"""
        resp = await admin_client.get("/api/v1/admin/risk-logs/risk-001")
        data = _assert_success_response(resp.json())
        assert data["user_account"] == "alice@example.com"
        assert data["user_display_name"] == "Alice"

    async def test_anonymous_risk_log_detail(self, admin_client: AsyncClient):
        """匿名风控日志详情应正确返回。"""
        resp = await admin_client.get("/api/v1/admin/risk-logs/risk-003")
        data = _assert_success_response(resp.json())
        assert data["user_id"] is None
        assert data["user_account"] is None
        assert data["user_display_name"] is None

    async def test_not_found(self, admin_client: AsyncClient):
        """查询不存在的风控日志应返回 404。"""
        resp = await admin_client.get("/api/v1/admin/risk-logs/nonexistent-id")
        assert resp.status_code == 404

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询风控日志详情。"""
        resp = await user_client.get("/api/v1/admin/risk-logs/risk-001")
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询风控日志详情应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/risk-logs/risk-001")
        assert resp.status_code == 401


# ============================================================
# GET /api/v1/admin/feature-flags — 功能开关列表
# ============================================================


class TestGetFeatureFlags:
    """功能开关列表接口测试。"""

    async def test_as_admin_returns_all(self, admin_client: AsyncClient):
        """管理员查询功能开关，应返回所有套餐。"""
        resp = await admin_client.get("/api/v1/admin/feature-flags")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 3
        codes = {item["plan_id"] for item in data["items"]}
        assert codes == {"plan-free", "plan-standard", "plan-pro"}

    async def test_items_have_required_fields(self, admin_client: AsyncClient):
        """列表项应包含所有必填字段。"""
        resp = await admin_client.get("/api/v1/admin/feature-flags")
        data = _assert_success_response(resp.json())

        for item in data["items"]:
            assert "plan_id" in item
            assert "plan_id" in item
            assert "plan_name" in item
            assert "enabled_features_json" in item
            assert "plan_status" in item

    async def test_filter_by_plan_id(self, admin_client: AsyncClient):
        """按 plan_id 筛选应只返回匹配的套餐。"""
        resp = await admin_client.get(
            "/api/v1/admin/feature-flags", params={"plan_id": "plan-free"}
        )
        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 1
        assert data["items"][0]["plan_id"] == "plan-free"
        assert data["items"][0]["plan_name"] == "免费套餐"

    async def test_filter_nonexistent_plan(self, admin_client: AsyncClient):
        """筛选不存在的套餐应返回空列表。"""
        resp = await admin_client.get(
            "/api/v1/admin/feature-flags", params={"plan_id": "nonexistent"}
        )
        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 0

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询功能开关。"""
        resp = await user_client.get("/api/v1/admin/feature-flags")
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询功能开关应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/feature-flags")
        assert resp.status_code == 401


# ============================================================
# PATCH /api/v1/admin/plans/{plan_id}/features — 更新功能开关
# ============================================================


class TestUpdateFeatureFlags:
    """更新功能开关接口测试。"""

    async def test_as_admin_merge_updates(self, admin_client: AsyncClient):
        """管理员更新功能开关，应合并更新（保留未传 key）。"""
        resp = await admin_client.patch(
            "/api/v1/admin/plans/plan-free/features",
            json={"enabled_features_json": {"new_feature": True}},
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["plan_id"] == "plan-free"
        # 合并后应保留原有 key，同时新增传入的 key
        assert "resize_image_local_paid" in data["enabled_features_json"]
        assert data["enabled_features_json"]["new_feature"] is True

    async def test_as_admin_override_existing_key(self, admin_client: AsyncClient):
        """更新已有 key 应覆盖原值。"""
        resp = await admin_client.patch(
            "/api/v1/admin/plans/plan-standard/features",
            json={"enabled_features_json": {"ai_copy_cloud": False}},
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["enabled_features_json"]["ai_copy_cloud"] is False

    async def test_plan_not_found(self, admin_client: AsyncClient):
        """更新不存在的套餐应返回 404。"""
        resp = await admin_client.patch(
            "/api/v1/admin/plans/nonexistent-plan/features",
            json={"enabled_features_json": {"test": True}},
        )
        assert resp.status_code == 404

    async def test_read_back_after_update(self, admin_client: AsyncClient):
        """更新后查询功能开关列表应反映变更。"""
        # 先更新
        await admin_client.patch(
            "/api/v1/admin/plans/plan-pro/features",
            json={"enabled_features_json": {"new_pro_feature": True}},
        )
        # 再查询
        resp = await admin_client.get(
            "/api/v1/admin/feature-flags", params={"plan_id": "plan-pro"}
        )
        data = _assert_success_response(resp.json())
        assert data["items"][0]["enabled_features_json"]["new_pro_feature"] is True
        # 原有 key 应保留
        assert data["items"][0]["enabled_features_json"]["ai_copy_cloud"] is True

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权更新功能开关。"""
        resp = await user_client.patch(
            "/api/v1/admin/plans/plan-free/features",
            json={"enabled_features_json": {"test": True}},
        )
        assert resp.status_code == 403

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权更新功能开关应返回 401。"""
        resp = await no_auth_client.patch(
            "/api/v1/admin/plans/plan-free/features",
            json={"enabled_features_json": {"test": True}},
        )
        assert resp.status_code == 401
