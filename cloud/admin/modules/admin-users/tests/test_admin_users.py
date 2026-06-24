"""
admin-users 模块完整测试。

覆盖 7 个接口的成功路径、鉴权错误路径和业务错误路径：
- GET    /admin/users                  — 用户列表
- GET    /admin/users/{user_id}        — 用户详情
- PATCH  /admin/users/{user_id}/status — 修改用户状态
- GET    /admin/users/{user_id}/devices— 用户设备列表
- GET    /admin/devices                — 设备列表
- GET    /admin/devices/{device_id}    — 设备详情
- PATCH  /admin/devices/{device_id}/status — 修改设备状态

通过依赖覆盖（dependency_overrides）隔离测试：
- admin_client：管理员身份 → 预期 200
- user_client：普通用户 → 预期 403
- no_auth_client：无鉴权 → 预期 401
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

# 本文件所有测试均为异步测试
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
# GET /api/v1/admin/users — 用户列表
# ============================================================


class TestListUsers:
    """用户列表接口测试。"""

    async def test_as_admin_returns_all_users(self, admin_client: AsyncClient):
        """管理员查询用户列表，应返回所有用户。"""
        resp = await admin_client.get("/api/v1/admin/users")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["limit"] == 20
        assert data["offset"] == 0

    async def test_pagination(self, admin_client: AsyncClient):
        """分页参数应正确生效。"""
        resp = await admin_client.get("/api/v1/admin/users?limit=1&offset=0")
        assert resp.status_code == 200
        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 1
        assert data["total"] == 3
        assert data["limit"] == 1

        # 第二页
        resp2 = await admin_client.get("/api/v1/admin/users?limit=1&offset=1")
        assert resp2.status_code == 200
        data2 = _assert_success_response(resp2.json())
        assert len(data2["items"]) == 1

    async def test_filter_by_status_active(self, admin_client: AsyncClient):
        """按状态筛选活跃用户。"""
        resp = await admin_client.get("/api/v1/admin/users?status=active")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 2  # alice + admin
        for item in data["items"]:
            assert item["status"] == "active"

    async def test_filter_by_status_blocked(self, admin_client: AsyncClient):
        """按状态筛选被封禁用户。"""
        resp = await admin_client.get("/api/v1/admin/users?status=blocked")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 1  # bob
        assert data["items"][0]["account"] == "bob@example.com"

    async def test_search_by_account(self, admin_client: AsyncClient):
        """按账号搜索用户。"""
        resp = await admin_client.get("/api/v1/admin/users?search=alice")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["account"] == "alice@example.com"

    async def test_search_by_display_name(self, admin_client: AsyncClient):
        """按展示名称搜索用户。"""
        resp = await admin_client.get("/api/v1/admin/users?search=管理员")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 1
        assert data["items"][0]["display_name"] == "管理员"

    async def test_search_no_results(self, admin_client: AsyncClient):
        """搜索不存在的用户应返回空列表。"""
        resp = await admin_client.get("/api/v1/admin/users?search=nonexistent")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 0
        assert len(data["items"]) == 0

    async def test_invalid_status_rejected(self, admin_client: AsyncClient):
        """无效状态值应返回 400。"""
        resp = await admin_client.get("/api/v1/admin/users?status=invalid")
        assert resp.status_code == 400
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询用户列表。"""
        resp = await user_client.get("/api/v1/admin/users")
        assert resp.status_code == 403
        _assert_error_detail(resp.json(), "PERMISSION_DENIED")

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询用户列表应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/users")
        assert resp.status_code == 401
        _assert_error_detail(resp.json(), "AUTH_REQUIRED")


# ============================================================
# GET /api/v1/admin/users/{user_id} — 用户详情
# ============================================================


class TestGetUserDetail:
    """用户详情接口测试。"""

    async def test_get_existing_user(self, admin_client: AsyncClient):
        """查询已存在的用户应返回详细信息。"""
        resp = await admin_client.get("/api/v1/admin/users/user-001")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["id"] == "user-001"
        assert data["account"] == "alice@example.com"
        assert data["display_name"] == "Alice"
        assert data["role"] == "user"
        assert data["status"] == "active"
        assert data["plan_code"] == "standard"
        assert "created_at" in data
        assert "updated_at" in data
        # password_hash 不应返回
        assert "password_hash" not in data

    async def test_user_not_found(self, admin_client: AsyncClient):
        """查询不存在的用户应返回 404。"""
        resp = await admin_client.get(
            "/api/v1/admin/users/nonexistent-user-id"
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "USER_NOT_FOUND"

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询用户详情。"""
        resp = await user_client.get("/api/v1/admin/users/user-001")
        assert resp.status_code == 403
        _assert_error_detail(resp.json(), "PERMISSION_DENIED")

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询用户详情应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/users/user-001")
        assert resp.status_code == 401
        _assert_error_detail(resp.json(), "AUTH_REQUIRED")


# ============================================================
# PATCH /api/v1/admin/users/{user_id}/status — 修改用户状态
# ============================================================


class TestUpdateUserStatus:
    """修改用户状态接口测试。"""

    async def test_block_user(self, admin_client: AsyncClient):
        """封禁活跃用户应成功。"""
        resp = await admin_client.patch(
            "/api/v1/admin/users/user-001/status",
            json={"status": "blocked"},
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["id"] == "user-001"
        assert data["status"] == "blocked"

    async def test_activate_blocked_user(self, admin_client: AsyncClient):
        """激活被封禁用户应成功。"""
        resp = await admin_client.patch(
            "/api/v1/admin/users/user-002/status",
            json={"status": "active"},
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["status"] == "active"

    async def test_delete_user(self, admin_client: AsyncClient):
        """删除用户应成功。"""
        resp = await admin_client.patch(
            "/api/v1/admin/users/user-001/status",
            json={"status": "deleted"},
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["status"] == "deleted"

    async def test_invalid_status_rejected(self, admin_client: AsyncClient):
        """传入非法状态值应返回 422（Pydantic 校验）。"""
        resp = await admin_client.patch(
            "/api/v1/admin/users/user-001/status",
            json={"status": "super_admin"},
        )
        # Pydantic pattern 校验失败 → FastAPI 返回 422
        assert resp.status_code == 422

    async def test_user_not_found(self, admin_client: AsyncClient):
        """修改不存在的用户应返回 404。"""
        resp = await admin_client.patch(
            "/api/v1/admin/users/nonexistent-user/status",
            json={"status": "active"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "USER_NOT_FOUND"

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权修改用户状态。"""
        resp = await user_client.patch(
            "/api/v1/admin/users/user-001/status",
            json={"status": "blocked"},
        )
        assert resp.status_code == 403
        _assert_error_detail(resp.json(), "PERMISSION_DENIED")

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权修改用户状态应返回 401。"""
        resp = await no_auth_client.patch(
            "/api/v1/admin/users/user-001/status",
            json={"status": "blocked"},
        )
        assert resp.status_code == 401
        _assert_error_detail(resp.json(), "AUTH_REQUIRED")


# ============================================================
# GET /api/v1/admin/users/{user_id}/devices — 用户设备列表
# ============================================================


class TestListUserDevices:
    """用户设备列表接口测试。"""

    async def test_list_devices_for_user_with_devices(self, admin_client: AsyncClient):
        """查询有设备的用户应返回其设备列表。"""
        resp = await admin_client.get("/api/v1/admin/users/user-001/devices")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 2
        assert len(data["items"]) == 2
        for item in data["items"]:
            assert item["user_id"] == "user-001"

    async def test_list_devices_for_user_without_devices(self, admin_client: AsyncClient):
        """查询无设备的用户应返回空列表。"""
        resp = await admin_client.get("/api/v1/admin/users/admin-001/devices")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 0
        assert len(data["items"]) == 0

    async def test_user_not_found(self, admin_client: AsyncClient):
        """查询不存在用户的设备应返回 404。"""
        resp = await admin_client.get(
            "/api/v1/admin/users/nonexistent-user/devices"
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "USER_NOT_FOUND"

    async def test_device_item_fields(self, admin_client: AsyncClient):
        """设备列表项应包含所有必填字段。"""
        resp = await admin_client.get("/api/v1/admin/users/user-001/devices")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        for item in data["items"]:
            assert "id" in item
            assert "user_id" in item
            assert "status" in item
            assert "bound_at" in item

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询用户设备。"""
        resp = await user_client.get("/api/v1/admin/users/user-001/devices")
        assert resp.status_code == 403
        _assert_error_detail(resp.json(), "PERMISSION_DENIED")

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询用户设备应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/users/user-001/devices")
        assert resp.status_code == 401
        _assert_error_detail(resp.json(), "AUTH_REQUIRED")


# ============================================================
# GET /api/v1/admin/devices — 设备列表
# ============================================================


class TestListDevices:
    """设备列表接口测试。"""

    async def test_list_all_devices(self, admin_client: AsyncClient):
        """管理员查询所有设备应返回全部设备。"""
        resp = await admin_client.get("/api/v1/admin/devices")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_filter_by_status_active(self, admin_client: AsyncClient):
        """按状态筛选活跃设备。"""
        resp = await admin_client.get("/api/v1/admin/devices?status=active")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 2  # device-001, device-002
        for item in data["items"]:
            assert item["status"] == "active"

    async def test_filter_by_status_blocked(self, admin_client: AsyncClient):
        """按状态筛选被封禁设备。"""
        resp = await admin_client.get("/api/v1/admin/devices?status=blocked")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["total"] == 1  # device-003
        assert data["items"][0]["id"] == "device-003"

    async def test_pagination(self, admin_client: AsyncClient):
        """设备列表分页应正确。"""
        resp = await admin_client.get("/api/v1/admin/devices?limit=2&offset=0")
        assert resp.status_code == 200
        data = _assert_success_response(resp.json())
        assert len(data["items"]) == 2
        assert data["total"] == 3

    async def test_invalid_status_rejected(self, admin_client: AsyncClient):
        """无效状态值应返回 400。"""
        resp = await admin_client.get("/api/v1/admin/devices?status=invalid")
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询设备列表。"""
        resp = await user_client.get("/api/v1/admin/devices")
        assert resp.status_code == 403
        _assert_error_detail(resp.json(), "PERMISSION_DENIED")

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询设备列表应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/devices")
        assert resp.status_code == 401
        _assert_error_detail(resp.json(), "AUTH_REQUIRED")


# ============================================================
# GET /api/v1/admin/devices/{device_id} — 设备详情
# ============================================================


class TestGetDeviceDetail:
    """设备详情接口测试。"""

    async def test_get_existing_device(self, admin_client: AsyncClient):
        """查询已存在的设备应返回详细信息。"""
        resp = await admin_client.get("/api/v1/admin/devices/device-001")
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["id"] == "device-001"
        assert data["user_id"] == "user-001"
        assert data["device_name"] == "Alice-PC"
        assert data["client_version"] == "0.1.0"
        assert data["status"] == "active"
        assert "bound_at" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_device_not_found(self, admin_client: AsyncClient):
        """查询不存在的设备应返回 404。"""
        resp = await admin_client.get(
            "/api/v1/admin/devices/nonexistent-device"
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "DEVICE_NOT_FOUND"

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权查询设备详情。"""
        resp = await user_client.get("/api/v1/admin/devices/device-001")
        assert resp.status_code == 403
        _assert_error_detail(resp.json(), "PERMISSION_DENIED")

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权查询设备详情应返回 401。"""
        resp = await no_auth_client.get("/api/v1/admin/devices/device-001")
        assert resp.status_code == 401
        _assert_error_detail(resp.json(), "AUTH_REQUIRED")


# ============================================================
# PATCH /api/v1/admin/devices/{device_id}/status — 修改设备状态
# ============================================================


class TestUpdateDeviceStatus:
    """修改设备状态接口测试。"""

    async def test_block_device(self, admin_client: AsyncClient):
        """封禁活跃设备应成功。"""
        resp = await admin_client.patch(
            "/api/v1/admin/devices/device-001/status",
            json={"status": "blocked"},
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["id"] == "device-001"
        assert data["status"] == "blocked"

    async def test_activate_blocked_device(self, admin_client: AsyncClient):
        """激活被封禁设备应成功。"""
        resp = await admin_client.patch(
            "/api/v1/admin/devices/device-003/status",
            json={"status": "active"},
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["status"] == "active"

    async def test_remove_device(self, admin_client: AsyncClient):
        """移除设备应成功。"""
        resp = await admin_client.patch(
            "/api/v1/admin/devices/device-001/status",
            json={"status": "removed"},
        )
        assert resp.status_code == 200

        data = _assert_success_response(resp.json())
        assert data["status"] == "removed"

    async def test_invalid_status_rejected(self, admin_client: AsyncClient):
        """传入非法状态值应返回 422（Pydantic 校验）。"""
        resp = await admin_client.patch(
            "/api/v1/admin/devices/device-001/status",
            json={"status": "super_active"},
        )
        assert resp.status_code == 422

    async def test_device_not_found(self, admin_client: AsyncClient):
        """修改不存在的设备应返回 404。"""
        resp = await admin_client.patch(
            "/api/v1/admin/devices/nonexistent-device/status",
            json={"status": "active"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "DEVICE_NOT_FOUND"

    async def test_as_normal_user_forbidden(self, user_client: AsyncClient):
        """普通用户无权修改设备状态。"""
        resp = await user_client.patch(
            "/api/v1/admin/devices/device-001/status",
            json={"status": "blocked"},
        )
        assert resp.status_code == 403
        _assert_error_detail(resp.json(), "PERMISSION_DENIED")

    async def test_without_token_unauthorized(self, no_auth_client: AsyncClient):
        """无鉴权修改设备状态应返回 401。"""
        resp = await no_auth_client.patch(
            "/api/v1/admin/devices/device-001/status",
            json={"status": "blocked"},
        )
        assert resp.status_code == 401
        _assert_error_detail(resp.json(), "AUTH_REQUIRED")


# ============================================================
# 响应格式验证
# ============================================================


class TestResponseFormat:
    """统一响应格式验证。"""

    async def test_user_list_response_format(self, admin_client: AsyncClient):
        """用户列表响应必须符合 common.yaml ApiResponse 结构。"""
        resp = await admin_client.get("/api/v1/admin/users")
        body = resp.json()

        assert "success" in body
        assert "data" in body
        assert "error" in body
        assert "request_id" in body
        assert body["success"] is True
        assert body["error"] is None

        data = body["data"]
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    async def test_device_list_response_format(self, admin_client: AsyncClient):
        """设备列表响应必须符合统一格式。"""
        resp = await admin_client.get("/api/v1/admin/devices")
        body = resp.json()

        assert body["success"] is True
        assert body["error"] is None
        assert "request_id" in body
        assert "data" in body

    async def test_user_detail_response_format(self, admin_client: AsyncClient):
        """用户详情响应必须符合统一格式。"""
        resp = await admin_client.get("/api/v1/admin/users/user-001")
        body = resp.json()

        assert body["success"] is True
        assert body["error"] is None
        assert "request_id" in body
        assert body["data"]["id"] == "user-001"

    async def test_device_detail_response_format(self, admin_client: AsyncClient):
        """设备详情响应必须符合统一格式。"""
        resp = await admin_client.get("/api/v1/admin/devices/device-001")
        body = resp.json()

        assert body["success"] is True
        assert body["error"] is None
        assert "request_id" in body
        assert body["data"]["id"] == "device-001"

    async def test_error_response_format(self, admin_client: AsyncClient):
        """错误响应必须符合统一格式。"""
        resp = await admin_client.get("/api/v1/admin/users/nonexistent-id")
        body = resp.json()

        assert body["success"] is False
        assert body["data"] is None
        assert body["error"] is not None
        assert "code" in body["error"]
        assert "message" in body["error"]
        assert "request_id" in body
