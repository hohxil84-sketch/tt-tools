"""
cloud-provider-log 模块测试。

覆盖：
    - 日志写入（write_provider_call_log）
    - 日志查询（list_provider_call_logs）
    - API 端点（GET /provider-call-logs）
    - 鉴权保护（401）
    - 数据隔离（用户间不可见）
    - 隐私字段保护（不返回 raw_usage_json 等）
    - 分页和筛选
    - 幂等保护（重复 request_id）
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import ErrorCode, AppError

from schemas import WriteProviderCallLogRequest
from service import write_provider_call_log, list_provider_call_logs

# 本文件所有测试均为异步测试
pytestmark = pytest.mark.asyncio


# ============================================================
# 辅助函数：构造测试用的 Provider 调用日志写入请求
# ============================================================


def _make_log_request(**overrides) -> WriteProviderCallLogRequest:
    """构造一个默认的 Provider 调用日志写入请求，支持字段覆盖。

    默认值为一次成功的 deepseek-chat 调用（ai_copy_cloud 功能）。
    """
    defaults = {
        "request_id": "req_test_001",
        "feature": "ai_copy_cloud",
        "provider": "deepseek",
        "model": "deepseek-chat",
        "status": "success",
        "error_code": None,
        "input_tokens": 120,
        "output_tokens": 80,
        "total_tokens": 200,
        "reasoning_tokens": 0,
        "cached_tokens": 10,
        "image_count": 0,
        "estimated_cost": 0.002,
        "credits_charged": 1,
        "latency_ms": 1200,
        "raw_usage_json": {"prompt_tokens": 120, "completion_tokens": 80},
        "raw_meta_json": {"finish_reason": "stop"},
    }
    defaults.update(overrides)
    return WriteProviderCallLogRequest(**defaults)


# ============================================================
# 日志写入测试
# ============================================================


class TestWriteProviderCallLog:
    """测试 Provider 调用日志写入功能。"""

    async def test_write_success_log(self, db_session: AsyncSession, test_user):
        """写入一条成功的 Provider 调用日志。"""
        req = _make_log_request()
        log_entry = await write_provider_call_log(
            db_session,
            user_id=test_user.id,
            feature="ai_copy_cloud",
            req=req,
        )

        assert log_entry.id is not None
        assert log_entry.request_id == "req_test_001"
        assert log_entry.user_id == test_user.id
        assert log_entry.feature == "ai_copy_cloud"
        assert log_entry.provider == "deepseek"
        assert log_entry.model == "deepseek-chat"
        assert log_entry.status == "success"
        assert log_entry.error_code is None
        assert log_entry.input_tokens == 120
        assert log_entry.output_tokens == 80
        assert log_entry.total_tokens == 200
        assert log_entry.estimated_cost == 0.002
        assert log_entry.credits_charged == 1
        assert log_entry.latency_ms == 1200
        # 仅服务端字段应存在
        assert log_entry.raw_usage_json == {"prompt_tokens": 120, "completion_tokens": 80}
        assert log_entry.raw_meta_json == {"finish_reason": "stop"}
        assert log_entry.reasoning_tokens == 0
        assert log_entry.cached_tokens == 10
        assert log_entry.image_count == 0

    async def test_write_failed_log(self, db_session: AsyncSession, test_user):
        """写入一条失败的 Provider 调用日志。"""
        req = _make_log_request(
            request_id="req_failed_001",
            status="failed",
            error_code="PROVIDER_TIMEOUT",
            input_tokens=50,
            output_tokens=0,
            total_tokens=50,
            estimated_cost=0.0,
            credits_charged=0,
            latency_ms=30000,
        )
        log_entry = await write_provider_call_log(
            db_session,
            user_id=test_user.id,
            feature="ai_render_cloud",
            req=req,
        )

        assert log_entry.status == "failed"
        assert log_entry.error_code == "PROVIDER_TIMEOUT"
        assert log_entry.feature == "ai_render_cloud"
        assert log_entry.credits_charged == 0

    async def test_write_timeout_log(self, db_session: AsyncSession, test_user):
        """写入一条超时的 Provider 调用日志。"""
        req = _make_log_request(
            request_id="req_timeout_001",
            status="timeout",
            error_code="PROVIDER_TIMEOUT",
            latency_ms=None,
        )
        log_entry = await write_provider_call_log(
            db_session,
            user_id=test_user.id,
            feature="ai_copy_cloud",
            req=req,
        )

        assert log_entry.status == "timeout"
        assert log_entry.error_code == "PROVIDER_TIMEOUT"
        assert log_entry.latency_ms is None

    async def test_write_with_device_id(self, db_session: AsyncSession, test_user):
        """写入日志时可以携带设备 ID。"""
        req = _make_log_request(request_id="req_device_001")
        log_entry = await write_provider_call_log(
            db_session,
            user_id=test_user.id,
            feature="ai_copy_cloud",
            req=req,
            device_id="device-uuid-123",
        )

        assert log_entry.device_id == "device-uuid-123"

    async def test_write_duplicate_request_id_rejected(
        self, db_session: AsyncSession, test_user
    ):
        """重复的 request_id 写入应被拒绝（幂等保护）。"""
        req = _make_log_request(request_id="req_dup_001")
        # 第一次写入成功
        await write_provider_call_log(
            db_session, user_id=test_user.id, feature="ai_copy_cloud", req=req
        )
        await db_session.flush()

        # 第二次写入同一 request_id 应抛出 AppError
        req2 = _make_log_request(
            request_id="req_dup_001",  # 相同的 request_id
            feature="ai_render_cloud",  # 不同的功能码
        )
        with pytest.raises(AppError) as exc_info:
            await write_provider_call_log(
                db_session, user_id=test_user.id, feature="ai_render_cloud", req=req2
            )

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "req_dup_001" in exc_info.value.message


# ============================================================
# 日志查询测试
# ============================================================


class TestListProviderCallLogs:
    """测试 Provider 调用日志查询功能。"""

    async def _seed_logs(self, db_session: AsyncSession, user_id: str) -> list:
        """写入多条测试日志，返回写入的 log entry 列表。"""
        entries = []
        # 5 条成功的 deepseek ai_copy_cloud 日志
        for i in range(5):
            req = _make_log_request(
                request_id=f"req_success_{i:03d}",
                feature="ai_copy_cloud",
                provider="deepseek",
                status="success",
                input_tokens=100 + i * 10,
                output_tokens=50 + i * 5,
                total_tokens=150 + i * 15,
                credits_charged=1,
            )
            entry = await write_provider_call_log(
                db_session, user_id=user_id, feature="ai_copy_cloud", req=req
            )
            entries.append(entry)

        # 2 条失败的 openai ai_render_cloud 日志
        for i in range(2):
            req = _make_log_request(
                request_id=f"req_failed_{i:03d}",
                feature="ai_render_cloud",
                provider="openai",
                model="gpt-4o",
                status="failed",
                error_code="PROVIDER_RATE_LIMITED",
                input_tokens=200,
                output_tokens=0,
                total_tokens=200,
                credits_charged=0,
            )
            entry = await write_provider_call_log(
                db_session, user_id=user_id, feature="ai_render_cloud", req=req
            )
            entries.append(entry)

        # 1 条超时的日志
        req = _make_log_request(
            request_id="req_timeout_000",
            feature="ai_image_tools_cloud",
            provider="deepseek",
            status="timeout",
            error_code="PROVIDER_TIMEOUT",
            credits_charged=0,
        )
        entry = await write_provider_call_log(
            db_session, user_id=user_id, feature="ai_image_tools_cloud", req=req
        )
        entries.append(entry)

        await db_session.flush()
        return entries

    async def test_query_all_logs(self, db_session: AsyncSession, test_user):
        """查询用户全部日志：应返回所有日志。"""
        await self._seed_logs(db_session, test_user.id)

        result = await list_provider_call_logs(
            db_session, user_id=test_user.id
        )

        assert result.total == 8  # 5 success + 2 failed + 1 timeout
        assert len(result.items) == 8
        assert result.limit == 50
        assert result.offset == 0

    async def test_query_empty_logs(self, db_session: AsyncSession, test_user):
        """查询无日志的用户应返回空列表。"""
        result = await list_provider_call_logs(
            db_session, user_id=test_user.id
        )

        assert result.total == 0
        assert len(result.items) == 0

    async def test_query_filter_by_feature(self, db_session: AsyncSession, test_user):
        """按功能码筛选。"""
        await self._seed_logs(db_session, test_user.id)

        result = await list_provider_call_logs(
            db_session,
            user_id=test_user.id,
            feature="ai_copy_cloud",
        )

        assert result.total == 5
        assert all(item.feature == "ai_copy_cloud" for item in result.items)

    async def test_query_filter_by_status(self, db_session: AsyncSession, test_user):
        """按调用状态筛选。"""
        await self._seed_logs(db_session, test_user.id)

        result = await list_provider_call_logs(
            db_session,
            user_id=test_user.id,
            status="failed",
        )

        assert result.total == 2
        assert all(item.status == "failed" for item in result.items)

    async def test_query_filter_by_provider(self, db_session: AsyncSession, test_user):
        """按 Provider 名称筛选。"""
        await self._seed_logs(db_session, test_user.id)

        result = await list_provider_call_logs(
            db_session,
            user_id=test_user.id,
            provider="openai",
        )

        assert result.total == 2
        assert all(item.provider == "openai" for item in result.items)

    async def test_query_combined_filters(self, db_session: AsyncSession, test_user):
        """组合多个筛选条件。"""
        await self._seed_logs(db_session, test_user.id)

        result = await list_provider_call_logs(
            db_session,
            user_id=test_user.id,
            feature="ai_render_cloud",
            status="failed",
            provider="openai",
        )

        assert result.total == 2
        for item in result.items:
            assert item.feature == "ai_render_cloud"
            assert item.status == "failed"
            assert item.provider == "openai"

    async def test_query_pagination_limit(self, db_session: AsyncSession, test_user):
        """分页：limit 参数正确限制返回条数。"""
        await self._seed_logs(db_session, test_user.id)

        result = await list_provider_call_logs(
            db_session,
            user_id=test_user.id,
            limit=3,
        )

        assert len(result.items) == 3
        assert result.total == 8  # 总数不变
        assert result.limit == 3

    async def test_query_pagination_offset(self, db_session: AsyncSession, test_user):
        """分页：offset 参数正确跳过前 N 条。"""
        await self._seed_logs(db_session, test_user.id)

        # 先查第一页
        page1 = await list_provider_call_logs(
            db_session,
            user_id=test_user.id,
            limit=5,
            offset=0,
        )
        # 再查第二页
        page2 = await list_provider_call_logs(
            db_session,
            user_id=test_user.id,
            limit=5,
            offset=5,
        )

        assert len(page1.items) == 5
        assert len(page2.items) == 3  # 8 total - 5 offset = 3 remaining
        assert page2.total == 8
        assert page2.offset == 5

        # 两页的 request_id 不应重叠
        page1_ids = {item.request_id for item in page1.items}
        page2_ids = {item.request_id for item in page2.items}
        assert page1_ids.isdisjoint(page2_ids)

    async def test_query_sorted_by_created_at_desc(
        self, db_session: AsyncSession, test_user
    ):
        """查询结果应按创建时间倒序排列（最新的在前）。"""
        await self._seed_logs(db_session, test_user.id)

        result = await list_provider_call_logs(
            db_session, user_id=test_user.id
        )

        # 验证 items 按 created_at 降序排列
        for i in range(len(result.items) - 1):
            assert result.items[i].created_at >= result.items[i + 1].created_at

    async def test_query_limit_clamped(self, db_session: AsyncSession, test_user):
        """limit 超过 100 时应被限制为 100。"""
        await self._seed_logs(db_session, test_user.id)

        result = await list_provider_call_logs(
            db_session,
            user_id=test_user.id,
            limit=200,  # 传入超过上限的值
        )

        assert result.limit == 100  # 被钳制

    async def test_data_isolation_between_users(
        self, db_session: AsyncSession, test_user, test_user_2
    ):
        """用户 A 的日志不应出现在用户 B 的查询结果中。"""
        # 为用户 A 写入日志
        req_a = _make_log_request(request_id="req_user_a_001")
        await write_provider_call_log(
            db_session, user_id=test_user.id, feature="ai_copy_cloud", req=req_a
        )

        # 为用户 B 写入日志
        req_b = _make_log_request(request_id="req_user_b_001", provider="openai")
        await write_provider_call_log(
            db_session, user_id=test_user_2.id, feature="ai_copy_cloud", req=req_b
        )

        await db_session.flush()

        # 用户 A 查询：只能看到自己的日志
        result_a = await list_provider_call_logs(
            db_session, user_id=test_user.id
        )
        assert result_a.total == 1
        assert result_a.items[0].request_id == "req_user_a_001"

        # 用户 B 查询：只能看到自己的日志
        result_b = await list_provider_call_logs(
            db_session, user_id=test_user_2.id
        )
        assert result_b.total == 1
        assert result_b.items[0].request_id == "req_user_b_001"

    async def test_response_excludes_server_only_fields(
        self, db_session: AsyncSession, test_user
    ):
        """响应 DTO 不得包含 raw_usage_json、raw_meta_json 等仅服务端字段。"""
        req = _make_log_request(
            request_id="req_privacy_001",
            raw_usage_json={"api_key": "secret_key", "prompt": "top secret"},
            raw_meta_json={"internal": "data"},
        )
        await write_provider_call_log(
            db_session, user_id=test_user.id, feature="ai_copy_cloud", req=req
        )
        await db_session.flush()

        result = await list_provider_call_logs(
            db_session, user_id=test_user.id
        )

        item = result.items[0]
        # 确认公开字段存在
        assert item.id is not None
        assert item.request_id == "req_privacy_001"
        assert item.feature == "ai_copy_cloud"
        # 确认仅服务端字段不在 ProviderCallLogItem 中
        item_dict = item.model_dump()
        assert "raw_usage_json" not in item_dict
        assert "raw_meta_json" not in item_dict
        assert "reasoning_tokens" not in item_dict
        assert "cached_tokens" not in item_dict
        assert "image_count" not in item_dict


# ============================================================
# API 端点测试
# ============================================================


class TestProviderCallLogsAPI:
    """测试 GET /api/v1/provider-call-logs API 端点。"""

    async def _seed_logs_via_service(
        self, db_session: AsyncSession, user_id: str
    ):
        """通过 service 层写入测试日志。"""
        for i in range(5):
            req = _make_log_request(
                request_id=f"req_api_success_{i:03d}",
                feature="ai_copy_cloud",
                provider="deepseek",
                status="success",
            )
            await write_provider_call_log(
                db_session, user_id=user_id, feature="ai_copy_cloud", req=req
            )
        for i in range(2):
            req = _make_log_request(
                request_id=f"req_api_failed_{i:03d}",
                feature="ai_render_cloud",
                provider="openai",
                model="gpt-4o",
                status="failed",
                error_code="PROVIDER_RATE_LIMITED",
            )
            await write_provider_call_log(
                db_session, user_id=user_id, feature="ai_render_cloud", req=req
            )
        await db_session.flush()

    async def test_get_logs_returns_200(
        self, client: AsyncClient, auth_headers, db_session, test_user
    ):
        """GET /provider-call-logs 返回 200 和分页数据。"""
        await self._seed_logs_via_service(db_session, test_user.id)

        response = await client.get(
            "/api/v1/provider-call-logs", headers=auth_headers
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"] is not None
        assert body["error"] is None
        assert "request_id" in body

        data = body["data"]
        assert data["total"] == 7
        assert len(data["items"]) == 7
        assert data["limit"] == 50
        assert data["offset"] == 0

    async def test_get_logs_returns_401_without_auth(self, client: AsyncClient):
        """未认证的请求应返回 401。"""
        response = await client.get("/api/v1/provider-call-logs")

        assert response.status_code == 401

    async def test_get_logs_with_feature_filter(
        self, client: AsyncClient, auth_headers, db_session, test_user
    ):
        """按功能码筛选 API 查询。"""
        await self._seed_logs_via_service(db_session, test_user.id)

        response = await client.get(
            "/api/v1/provider-call-logs?feature=ai_render_cloud",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 2
        for item in data["items"]:
            assert item["feature"] == "ai_render_cloud"

    async def test_get_logs_with_status_filter(
        self, client: AsyncClient, auth_headers, db_session, test_user
    ):
        """按调用状态筛选 API 查询。"""
        await self._seed_logs_via_service(db_session, test_user.id)

        response = await client.get(
            "/api/v1/provider-call-logs?status=failed",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 2
        for item in data["items"]:
            assert item["status"] == "failed"

    async def test_get_logs_with_provider_filter(
        self, client: AsyncClient, auth_headers, db_session, test_user
    ):
        """按 Provider 名称筛选 API 查询。"""
        await self._seed_logs_via_service(db_session, test_user.id)

        response = await client.get(
            "/api/v1/provider-call-logs?provider=openai",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 2
        for item in data["items"]:
            assert item["provider"] == "openai"

    async def test_get_logs_pagination(
        self, client: AsyncClient, auth_headers, db_session, test_user
    ):
        """API 分页参数正确生效。"""
        await self._seed_logs_via_service(db_session, test_user.id)

        response = await client.get(
            "/api/v1/provider-call-logs?limit=3&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["items"]) == 3
        assert data["total"] == 7
        assert data["limit"] == 3
        assert data["offset"] == 0

    async def test_get_logs_data_isolation(
        self, client: AsyncClient, auth_headers, auth_headers_user_2,
        db_session, test_user, test_user_2
    ):
        """API 层数据隔离：用户不能看到其他用户的日志。"""
        # 为 test_user 写入日志
        req_a = _make_log_request(request_id="req_iso_a_001")
        await write_provider_call_log(
            db_session, user_id=test_user.id, feature="ai_copy_cloud", req=req_a
        )
        # 为 test_user_2 写入日志
        req_b = _make_log_request(request_id="req_iso_b_001", provider="openai")
        await write_provider_call_log(
            db_session, user_id=test_user_2.id, feature="ai_copy_cloud", req=req_b
        )
        await db_session.flush()

        # test_user 查询
        response_a = await client.get(
            "/api/v1/provider-call-logs", headers=auth_headers
        )
        assert response_a.status_code == 200
        data_a = response_a.json()["data"]
        assert data_a["total"] == 1
        assert data_a["items"][0]["request_id"] == "req_iso_a_001"

        # test_user_2 查询
        response_b = await client.get(
            "/api/v1/provider-call-logs", headers=auth_headers_user_2
        )
        assert response_b.status_code == 200
        data_b = response_b.json()["data"]
        assert data_b["total"] == 1
        assert data_b["items"][0]["request_id"] == "req_iso_b_001"

    async def test_get_logs_no_server_only_fields_in_response(
        self, client: AsyncClient, auth_headers, db_session, test_user
    ):
        """API 响应不得包含 raw_usage_json、raw_meta_json 等仅服务端字段。"""
        req = _make_log_request(
            request_id="req_privacy_api_001",
            raw_usage_json={"api_key": "sk-secret", "prompt": "confidential"},
            raw_meta_json={"internal": "sensitive"},
            reasoning_tokens=50,
            cached_tokens=20,
            image_count=3,
        )
        await write_provider_call_log(
            db_session, user_id=test_user.id, feature="ai_copy_cloud", req=req
        )
        await db_session.flush()

        response = await client.get(
            "/api/v1/provider-call-logs", headers=auth_headers
        )

        assert response.status_code == 200
        item = response.json()["data"]["items"][0]
        # 确认仅服务端字段不在 API 响应中
        assert "raw_usage_json" not in item
        assert "raw_meta_json" not in item
        assert "reasoning_tokens" not in item
        assert "cached_tokens" not in item
        assert "image_count" not in item
        # 确认公开字段正确
        assert item["request_id"] == "req_privacy_api_001"
        assert item["feature"] == "ai_copy_cloud"

    async def test_get_logs_response_structure(
        self, client: AsyncClient, auth_headers, db_session, test_user
    ):
        """验证 API 响应结构对齐 OpenAPI 统一响应规范。"""
        await self._seed_logs_via_service(db_session, test_user.id)

        response = await client.get(
            "/api/v1/provider-call-logs", headers=auth_headers
        )

        body = response.json()
        # 统一响应结构
        assert body["success"] is True
        assert "data" in body
        assert body["error"] is None
        assert "request_id" in body

        # data 结构
        data = body["data"]
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        # items 条目结构
        item = data["items"][0]
        required_fields = [
            "id", "request_id", "feature", "provider", "model",
            "status", "input_tokens", "output_tokens", "total_tokens",
            "estimated_cost", "credits_charged", "created_at",
        ]
        for field in required_fields:
            assert field in item, f"缺少必要字段: {field}"
