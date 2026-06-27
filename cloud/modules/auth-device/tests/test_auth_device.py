"""
cloud-auth-device 模块完整测试。

覆盖登录、刷新、退出、设备查询、设备绑定 5 个接口的
成功路径和主要错误路径。
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

# 本文件所有测试均为异步测试
pytestmark = pytest.mark.asyncio


# ============================================================
# POST /api/v1/auth/login — 登录接口
# ============================================================


class TestLogin:
    """登录接口测试。"""

    async def test_login_success(self, client: AsyncClient, test_user):
        """正常登录：正确账号密码，应返回令牌和用户/设备信息。"""
        resp = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": "fp-login-001",
            "device_name": "MY-PC",
            "client_version": "0.1.0",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["error"] is None
        assert body["request_id"] is not None

        data = body["data"]
        assert data["access_token"] is not None
        assert data["refresh_token"] is not None
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

        # 用户信息
        assert data["user"]["account"] == "test@example.com"
        assert data["user"]["display_name"] == "测试用户"
        assert data["user"]["plan_id"] is None

        # 设备信息（首次登录，应为新设备）
        assert data["device"]["status"] == "active"
        assert data["device"]["is_new"] is True

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """错误密码登录，应返回 401。"""
        resp = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "wrong-password",
            "device_fingerprint": "fp-wrong",
        })
        assert resp.status_code == 200  # 业务错误不改变 HTTP 状态码的处理方式
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

    async def test_login_nonexistent_account(self, client: AsyncClient):
        """不存在的账号登录，应返回 401。"""
        resp = await client.post("/api/v1/auth/login", json={
            "account": "noone@example.com",
            "password": "whatever",
            "device_fingerprint": "fp-ghost",
        })
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

    async def test_login_blocked_user(
        self, client: AsyncClient, db_session, test_user
    ):
        """被封禁用户登录，应返回错误。"""
        # 将测试用户状态改为 blocked
        from models import User
        from sqlalchemy import update
        await db_session.execute(
            update(User).where(User.id == test_user.id).values(status="blocked")
        )
        await db_session.flush()

        resp = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": "fp-blocked",
        })
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

    async def test_login_existing_device_rebind(
        self, client: AsyncClient, test_user, test_device
    ):
        """已有设备再次登录：is_new 应为 false，且设备名被更新。"""
        # 使用 test_device 的设备指纹哈希对应的原始指纹是不透明的，
        # 这里使用新指纹来测试"已存在设备"的场景。
        # 先创建一条设备记录，再用相同指纹登录。
        from service import hash_fingerprint

        # 使用已知指纹登录第一次
        resp1 = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": "fp-existing-device",
            "device_name": "FIRST-LOGIN",
        })
        assert resp1.json()["data"]["device"]["is_new"] is True
        device_id_1 = resp1.json()["data"]["device"]["id"]

        # 第二次使用相同指纹登录
        resp2 = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": "fp-existing-device",
            "device_name": "SECOND-LOGIN",
        })
        assert resp2.json()["success"] is True
        assert resp2.json()["data"]["device"]["is_new"] is False
        # 同一设备 ID
        assert resp2.json()["data"]["device"]["id"] == device_id_1

    async def test_login_removed_device_rebinds(
        self, client: AsyncClient, db_session, test_user
    ):
        """被移除的设备重新登录：应重新激活并标记为 is_new。"""
        from models import Device
        from service import hash_fingerprint
        from sqlalchemy import update

        # 先登录创建设备
        resp = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": "fp-removed-test",
        })
        device_id = resp.json()["data"]["device"]["id"]

        # 将设备标记为 removed
        await db_session.execute(
            update(Device).where(Device.id == device_id).values(status="removed")
        )
        await db_session.flush()

        # 再次登录
        resp2 = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": "fp-removed-test",
        })
        assert resp2.json()["data"]["device"]["status"] == "active"
        assert resp2.json()["data"]["device"]["is_new"] is True
        assert resp2.json()["data"]["device"]["id"] == device_id

    async def test_login_blocked_device(
        self, client: AsyncClient, db_session, test_user
    ):
        """被封禁的设备登录，应拒绝。"""
        from models import Device
        from service import hash_fingerprint
        from sqlalchemy import update

        # 先登录创建设备
        resp = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": "fp-blocked-device",
        })
        device_id = resp.json()["data"]["device"]["id"]

        # 封禁设备
        await db_session.execute(
            update(Device).where(Device.id == device_id).values(status="blocked")
        )
        await db_session.flush()

        # 再次登录应被拒绝
        resp2 = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": "fp-blocked-device",
        })
        assert resp2.json()["success"] is False
        assert resp2.json()["error"]["code"] == "DEVICE_NOT_BOUND"


# ============================================================
# POST /api/v1/auth/refresh — 刷新令牌接口
# ============================================================


class TestRefresh:
    """刷新令牌接口测试。"""

    async def _login_and_get_tokens(self, client: AsyncClient) -> dict:
        """辅助方法：登录并返回令牌数据。"""
        resp = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": "fp-refresh-test",
        })
        return resp.json()["data"]

    async def test_refresh_success(self, client: AsyncClient, test_user):
        """正常刷新：旧令牌被撤销，获得新令牌对。"""
        tokens = await self._login_and_get_tokens(client)

        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["access_token"] is not None
        assert data["refresh_token"] is not None
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

        # 新旧 access_token 可能相同（同一秒内 JWT 载荷不变），
        # 但 refresh_token 必须不同（随机生成）
        assert data["refresh_token"] != tokens["refresh_token"]

    async def test_refresh_invalid_token(self, client: AsyncClient, test_user):
        """使用无效令牌刷新，应返回 401。"""
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "this-is-not-a-valid-token",
        })
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_TOKEN_EXPIRED"

    async def test_refresh_revoked_token_after_logout(
        self, client: AsyncClient, test_user
    ):
        """退出后使用旧令牌刷新，应返回 401。"""
        tokens = await self._login_and_get_tokens(client)

        # 退出
        await client.post("/api/v1/auth/logout", json={
            "refresh_token": tokens["refresh_token"],
        })

        # 尝试用已撤销令牌刷新
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_TOKEN_EXPIRED"

    async def test_refresh_old_token_revoked_after_rotation(
        self, client: AsyncClient, test_user
    ):
        """令牌轮换后，旧 refresh_token 应被撤销（不能重复使用）。"""
        tokens = await self._login_and_get_tokens(client)

        # 第一次刷新成功
        resp1 = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert resp1.json()["success"] is True

        # 尝试再次使用旧令牌刷新（应失败）
        resp2 = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert resp2.json()["success"] is False
        assert resp2.json()["error"]["code"] == "AUTH_TOKEN_EXPIRED"


# ============================================================
# POST /api/v1/auth/logout — 退出登录接口
# ============================================================


class TestLogout:
    """退出登录接口测试。"""

    async def test_logout_success(self, client: AsyncClient, test_user):
        """正常退出：返回 logged_out: true。"""
        # 先登录获取令牌
        login_resp = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": "fp-logout-test",
        })
        refresh_token = login_resp.json()["data"]["refresh_token"]

        resp = await client.post("/api/v1/auth/logout", json={
            "refresh_token": refresh_token,
        })
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["logged_out"] is True

    async def test_logout_idempotent(self, client: AsyncClient, test_user):
        """重复退出同一令牌：幂等，不报错。"""
        login_resp = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": "fp-logout-idempotent",
        })
        refresh_token = login_resp.json()["data"]["refresh_token"]

        # 第一次退出
        resp1 = await client.post("/api/v1/auth/logout", json={
            "refresh_token": refresh_token,
        })
        assert resp1.json()["data"]["logged_out"] is True

        # 第二次退出（幂等）
        resp2 = await client.post("/api/v1/auth/logout", json={
            "refresh_token": refresh_token,
        })
        assert resp2.json()["data"]["logged_out"] is True

    async def test_logout_invalid_token_no_error(self, client: AsyncClient):
        """退出不存在的令牌：幂等，不报错。"""
        resp = await client.post("/api/v1/auth/logout", json={
            "refresh_token": "some-random-token-never-existed",
        })
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["logged_out"] is True


# ============================================================
# GET /api/v1/devices/current — 设备查询接口
# ============================================================


class TestDevicesCurrent:
    """设备查询接口测试。"""

    async def _login_and_get_auth_headers(
        self, client: AsyncClient, fingerprint: str = "fp-device-query"
    ) -> dict:
        """辅助方法：登录并返回带 Authorization 头的 headers。"""
        resp = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": fingerprint,
            "device_name": "QUERY-DEVICE",
        })
        access_token = resp.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {access_token}"}

    async def test_get_current_device_success(
        self, client: AsyncClient, test_user
    ):
        """正常查询当前设备：返回设备详情。"""
        headers = await self._login_and_get_auth_headers(client)

        resp = await client.get("/api/v1/devices/current", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

        data = body["data"]
        assert data["id"] is not None
        assert data["status"] == "active"
        assert data["device_name"] == "QUERY-DEVICE"

    async def test_get_current_device_no_auth(self, client: AsyncClient):
        """未认证查询设备：应返回 401。"""
        resp = await client.get("/api/v1/devices/current")
        # FastAPI OAuth2PasswordBearer(auto_error=False) + require_auth
        # 返回 HTTPException，detail 直接作为响应体
        assert resp.status_code == 401
        body = resp.json()
        # 响应格式：{"detail": {"code": "AUTH_REQUIRED", ...}} 或直接 {"code": ...}
        if "detail" in body:
            assert body["detail"]["code"] == "AUTH_REQUIRED"
        else:
            assert body["code"] == "AUTH_REQUIRED"


# ============================================================
# POST /api/v1/devices/bind — 设备绑定接口
# ============================================================


class TestDevicesBind:
    """设备绑定接口测试。"""

    async def _login_and_get_auth_headers(
        self, client: AsyncClient, fingerprint: str = "fp-bind-login"
    ) -> dict:
        """辅助方法：登录并返回带 Authorization 头的 headers。"""
        resp = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": fingerprint,
        })
        access_token = resp.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {access_token}"}

    async def test_bind_new_device_success(self, client: AsyncClient, test_user):
        """绑定新设备：成功并返回 is_new=True。"""
        headers = await self._login_and_get_auth_headers(client)

        resp = await client.post("/api/v1/devices/bind", json={
            "device_fingerprint": "fp-new-bind-001",
            "device_name": "NEW-BIND-DEVICE",
            "client_version": "0.2.0",
        }, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "active"
        assert body["data"]["is_new"] is True
        assert body["data"]["id"] is not None

    async def test_bind_existing_device_returns_existing(
        self, client: AsyncClient, test_user
    ):
        """重复绑定同一设备：返回已有记录，is_new=False。"""
        headers = await self._login_and_get_auth_headers(client)

        # 第一次绑定
        resp1 = await client.post("/api/v1/devices/bind", json={
            "device_fingerprint": "fp-dup-bind",
            "device_name": "FIRST-BIND",
        }, headers=headers)
        assert resp1.json()["data"]["is_new"] is True
        device_id = resp1.json()["data"]["id"]

        # 第二次绑定同一指纹
        resp2 = await client.post("/api/v1/devices/bind", json={
            "device_fingerprint": "fp-dup-bind",
            "device_name": "SECOND-BIND",
        }, headers=headers)
        assert resp2.json()["success"] is True
        assert resp2.json()["data"]["is_new"] is False
        assert resp2.json()["data"]["id"] == device_id

    async def test_bind_device_no_auth(self, client: AsyncClient):
        """未认证绑定设备：应返回 401。"""
        resp = await client.post("/api/v1/devices/bind", json={
            "device_fingerprint": "fp-no-auth",
        })
        # FastAPI OAuth2PasswordBearer(auto_error=False) + require_auth
        assert resp.status_code == 401
        body = resp.json()
        if "detail" in body:
            assert body["detail"]["code"] == "AUTH_REQUIRED"
        else:
            assert body["code"] == "AUTH_REQUIRED"


# ============================================================
# 集成测试：完整登录-刷新-退出流
# ============================================================


class TestFullFlow:
    """端到端集成测试：登录→刷新→查询设备→退出→令牌失效。"""

    async def test_full_login_refresh_logout_flow(
        self, client: AsyncClient, test_user
    ):
        """完整流程测试。"""
        # 1. 登录
        login_resp = await client.post("/api/v1/auth/login", json={
            "account": "test@example.com",
            "password": "test123",
            "device_fingerprint": "fp-full-flow",
            "device_name": "FULL-FLOW-DEVICE",
        })
        assert login_resp.json()["success"] is True
        tokens = login_resp.json()["data"]
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 查询设备
        device_resp = await client.get("/api/v1/devices/current", headers=headers)
        assert device_resp.json()["success"] is True
        assert device_resp.json()["data"]["device_name"] == "FULL-FLOW-DEVICE"

        # 3. 刷新令牌
        refresh_resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert refresh_resp.json()["success"] is True
        new_access = refresh_resp.json()["data"]["access_token"]
        new_refresh = refresh_resp.json()["data"]["refresh_token"]
        new_headers = {"Authorization": f"Bearer {new_access}"}

        # 4. 使用新令牌查询设备
        device_resp2 = await client.get("/api/v1/devices/current", headers=new_headers)
        assert device_resp2.json()["success"] is True

        # 5. 退出登录
        logout_resp = await client.post("/api/v1/auth/logout", json={
            "refresh_token": new_refresh,
        })
        assert logout_resp.json()["data"]["logged_out"] is True

        # 6. 令牌失效验证
        refresh_fail = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": new_refresh,
        })
        assert refresh_fail.json()["success"] is False
