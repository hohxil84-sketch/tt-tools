"""
admin-shell 模块完整测试。

覆盖仪表盘、导航菜单、服务状态 3 个接口的成功路径和鉴权错误路径。
通过依赖覆盖（dependency_overrides）隔离测试 admin-shell 端点：
- admin_client：模拟管理员身份 → 预期 200
- user_client：模拟普通用户身份 → 预期 403
- no_auth_client：无鉴权 → 预期 401
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

# 本文件所有测试均为异步测试
pytestmark = pytest.mark.asyncio


# ============================================================
# GET /api/v1/admin/dashboard — 仪表盘接口
# ============================================================


class TestDashboard:
    """仪表盘接口测试。"""

    async def test_as_admin_success(self, admin_client: AsyncClient):
        """管理员获取仪表盘，应返回 200 + 统计指标。"""
        resp = await admin_client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["error"] is None
        assert body["request_id"] is not None

        data = body["data"]
        assert data["users_total"] == 0
        assert data["orders_today"] == 0
        assert data["revenue_today_cents"] == 0
        assert data["active_devices"] == 0
        assert data["server_status"] == "healthy"

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户获取仪表盘，应返回 403。"""
        resp = await user_client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 403
        body = resp.json()
        assert body["detail"]["code"] == "PERMISSION_DENIED"

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权获取仪表盘，应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 401
        body = resp.json()
        assert body["detail"]["code"] == "AUTH_REQUIRED"


# ============================================================
# GET /api/v1/admin/menu — 导航菜单接口
# ============================================================


class TestMenu:
    """导航菜单接口测试。"""

    async def test_as_admin_success(self, admin_client: AsyncClient):
        """管理员获取导航菜单，应返回 200 + 完整菜单。"""
        resp = await admin_client.get("/api/v1/admin/menu")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["error"] is None
        assert body["request_id"] is not None

        data = body["data"]
        assert "menu" in data
        menu = data["menu"]
        assert isinstance(menu, list)
        assert len(menu) >= 4

        # 验证必填字段
        required_fields = {"id", "title", "icon", "path"}
        for item in menu:
            for field in required_fields:
                assert field in item, f"Menu item missing field {field}"

        # 验证菜单项 ID（含拆分后的系统用户/客户端用户/设备管理）
        menu_ids = [item["id"] for item in menu]
        assert "dashboard" in menu_ids
        assert "system-users" in menu_ids
        assert "client-users" in menu_ids
        assert "devices" in menu_ids
        assert "billing" in menu_ids
        assert "ops" in menu_ids

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户获取导航菜单，应返回 403。"""
        resp = await user_client.get("/api/v1/admin/menu")
        assert resp.status_code == 403
        body = resp.json()
        assert body["detail"]["code"] == "PERMISSION_DENIED"

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权获取导航菜单，应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/menu")
        assert resp.status_code == 401
        body = resp.json()
        assert body["detail"]["code"] == "AUTH_REQUIRED"


# ============================================================
# GET /api/v1/admin/status — 服务状态接口
# ============================================================


class TestStatus:
    """服务状态接口测试。"""

    async def test_as_admin_success(self, admin_client: AsyncClient):
        """管理员获取服务状态，应返回 200 + 状态数据。"""
        resp = await admin_client.get("/api/v1/admin/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["error"] is None
        assert body["request_id"] is not None

        data = body["data"]
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户获取服务状态，应返回 403。"""
        resp = await user_client.get("/api/v1/admin/status")
        assert resp.status_code == 403
        body = resp.json()
        assert body["detail"]["code"] == "PERMISSION_DENIED"

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权获取服务状态，应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/status")
        assert resp.status_code == 401
        body = resp.json()
        assert body["detail"]["code"] == "AUTH_REQUIRED"


# ============================================================
# 菜单数据结构验证
# ============================================================


class TestMenuStructure:
    """导航菜单详细结构验证。"""

    async def test_items_have_required_fields(self, admin_client: AsyncClient):
        """每个菜单项字段类型正确。"""
        resp = await admin_client.get("/api/v1/admin/menu")
        body = resp.json()
        menu = body["data"]["menu"]

        for item in menu:
            assert isinstance(item["id"], str) and len(item["id"]) > 0
            assert isinstance(item["title"], str) and len(item["title"]) > 0
            assert isinstance(item["icon"], str) and len(item["icon"]) > 0
            assert isinstance(item["path"], str) and len(item["path"]) > 0

    async def test_dashboard_is_first(self, admin_client: AsyncClient):
        """仪表盘为第一个菜单项。"""
        resp = await admin_client.get("/api/v1/admin/menu")
        body = resp.json()
        menu = body["data"]["menu"]
        assert menu[0]["id"] == "dashboard"
        assert menu[0]["title"] == "仪表盘"


# ============================================================
# 响应格式验证
# ============================================================


class TestResponseFormat:
    """统一响应格式验证。"""

    async def test_dashboard_response_format(self, admin_client: AsyncClient):
        """仪表盘响应必须符合 common.yaml ApiResponse 结构。"""
        resp = await admin_client.get("/api/v1/admin/dashboard")
        body = resp.json()

        # 统一响应格式：success, data, error, request_id
        assert "success" in body
        assert "data" in body
        assert "error" in body
        assert "request_id" in body
        assert body["success"] is True
        assert body["error"] is None

    async def test_menu_response_format(self, admin_client: AsyncClient):
        """菜单响应必须符合统一格式。"""
        resp = await admin_client.get("/api/v1/admin/menu")
        body = resp.json()

        assert body["success"] is True
        assert body["error"] is None
        assert "request_id" in body
        assert "data" in body

    async def test_status_response_format(self, admin_client: AsyncClient):
        """状态响应必须符合统一格式。"""
        resp = await admin_client.get("/api/v1/admin/status")
        body = resp.json()

        assert body["success"] is True
        assert body["error"] is None
        assert "request_id" in body
        assert "data" in body
