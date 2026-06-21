"""
cloud-ai-render 测试套件。

测试覆盖：
- 成功创建任务（标准用户、专业用户）
- 权限检查（免费用户被拒绝）
- 额度检查（余额不足被拒绝）
- 鉴权检查（未登录被拒绝）
- 请求校验（缺少必填字段）
- 响应结构校验（对齐 OpenAPI ai-render.yaml）
- 最小请求（仅必填字段）
- 不同 scene_type 组合
- 任务查询（创建后查询状态和结果）
- 跨用户任务隔离（其他用户不能查询）
- 任务不存在（404）
- 扣费验证（创建任务后余额减少）
- 日志验证（provider_call_log 和 credit_ledger 写入）

测试数据库：SQLite 内存数据库 + Mock Provider。
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


# ============================================================
# 成功场景 - 创建任务
# ============================================================


@pytest.mark.asyncio
async def test_create_render_task_success_standard(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_request: dict,
):
    """标准用户成功创建效果图生成任务。

    验证：
    - HTTP 200 返回
    - 响应包含 success=true
    - data 包含所有必需字段
    - feature 固定为 ai_render_cloud
    - task_id 非空
    - status 为 succeeded（Mock 同步完成）
    - estimated_credits 为正数
    """
    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()

    # 统一响应结构
    assert body["success"] is True
    assert body["error"] is None
    assert body["request_id"] is not None

    # 业务数据
    data = body["data"]
    assert data["feature"] == "ai_render_cloud"
    assert len(data["task_id"]) > 0, "task_id 不应为空"
    assert data["status"] == "succeeded", "Mock 同步执行后应为 succeeded"
    assert data["estimated_credits"] >= 1


@pytest.mark.asyncio
async def test_create_render_task_success_pro(
    client: AsyncClient,
    pro_auth_headers: dict,
    valid_request: dict,
):
    """专业用户成功创建效果图生成任务。"""
    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=pro_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["feature"] == "ai_render_cloud"
    assert body["data"]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_create_render_task_minimal_request(
    client: AsyncClient,
    standard_auth_headers: dict,
    minimal_request: dict,
):
    """最小必填字段请求成功创建任务。"""
    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=minimal_request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]["task_id"]) > 0


@pytest.mark.asyncio
async def test_create_render_task_different_scenes(
    client: AsyncClient,
    standard_auth_headers: dict,
):
    """不同场景类型均能成功创建任务。"""
    scenes = ["interior_design", "product_showcase", "poster_design"]
    for scene in scenes:
        request = {
            "scene_type": scene,
            "prompt": f"测试{scene}场景效果图",
            "input_file_ids": ["11111111-1111-1111-1111-111111111111"],
            "client_request_id": f"test_scene_{scene}",
        }
        response = await client.post(
            "/api/v1/ai/render/tasks",
            json=request,
            headers=standard_auth_headers,
        )
        assert response.status_code == 200, f"场景 '{scene}' 应返回 200"
        body = response.json()
        assert body["success"] is True, f"场景 '{scene}' 应成功"


@pytest.mark.asyncio
async def test_create_render_task_with_optional_fields(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_request: dict,
):
    """带全部可选字段创建任务成功。"""
    # valid_request 已包含 style 和 size 可选字段
    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


# ============================================================
# 成功场景 - 查询任务
# ============================================================


@pytest.mark.asyncio
async def test_query_task_after_creation(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_request: dict,
):
    """创建任务后可以成功查询任务状态和结果。

    验证：
    - HTTP 200 返回
    - 响应包含完整任务数据
    - status 为 succeeded
    - result_files 非空（Mock 返回了结果文件）
    - result_files 中每个文件包含必需字段
    - provider、model、estimated_cost 有值
    """
    # 先创建任务
    create_resp = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=standard_auth_headers,
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["data"]["task_id"]

    # 查询任务
    query_resp = await client.get(
        f"/api/v1/ai/render/tasks/{task_id}",
        headers=standard_auth_headers,
    )

    assert query_resp.status_code == 200
    body = query_resp.json()

    # 统一响应结构
    assert body["success"] is True
    assert body["error"] is None
    assert body["request_id"] is not None

    # 业务数据
    data = body["data"]
    assert data["task_id"] == task_id
    assert data["status"] == "succeeded"
    assert data["feature"] == "ai_render_cloud"

    # 结果文件
    assert isinstance(data["result_files"], list)
    assert len(data["result_files"]) > 0, "Mock 应返回结果文件"
    for f in data["result_files"]:
        assert len(f["file_id"]) > 0, "每个结果文件应有 file_id"
        assert len(f["mime_type"]) > 0, "每个结果文件应有 mime_type"

    # 服务端决策字段
    assert len(data["provider"]) > 0
    assert len(data["model"]) > 0
    assert data["estimated_cost"] >= 0
    assert data["credits_charged"] >= 1
    assert data["provider_call_id"] is not None


@pytest.mark.asyncio
async def test_query_task_response_structure_matches_openapi(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_request: dict,
):
    """查询任务响应结构完全对齐 ai-render.yaml。"""
    create_resp = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=standard_auth_headers,
    )
    task_id = create_resp.json()["data"]["task_id"]

    query_resp = await client.get(
        f"/api/v1/ai/render/tasks/{task_id}",
        headers=standard_auth_headers,
    )

    assert query_resp.status_code == 200
    body = query_resp.json()

    # 外层结构
    assert isinstance(body["success"], bool)
    assert "data" in body
    assert "error" in body
    assert "request_id" in body
    assert isinstance(body["request_id"], str)

    # data 内层结构（对齐 AiRenderTaskData schema）
    data = body["data"]
    assert isinstance(data["task_id"], str)
    assert data["status"] in ("queued", "running", "succeeded", "failed")
    assert isinstance(data["feature"], str)
    assert data["feature"] == "ai_render_cloud"
    assert isinstance(data["result_files"], list)

    # 成功状态下 result_files 中每个元素的结构
    for f in data["result_files"]:
        assert isinstance(f["file_id"], str)
        assert isinstance(f["mime_type"], str)
        # url、width、height 是可选字段
        if "url" in f and f["url"] is not None:
            assert isinstance(f["url"], str)
        if "width" in f and f["width"] is not None:
            assert isinstance(f["width"], int)
        if "height" in f and f["height"] is not None:
            assert isinstance(f["height"], int)

    # 服务端决策字段
    if data["provider"] is not None:
        assert isinstance(data["provider"], str)
    if data["model"] is not None:
        assert isinstance(data["model"], str)
    if data["estimated_cost"] is not None:
        assert isinstance(data["estimated_cost"], (int, float))
    if data["credits_charged"] is not None:
        assert isinstance(data["credits_charged"], int)
    if data["provider_call_id"] is not None:
        assert isinstance(data["provider_call_id"], str)


# ============================================================
# 权限和额度检查
# ============================================================


@pytest.mark.asyncio
async def test_free_user_permission_denied(
    client: AsyncClient,
    free_auth_headers: dict,
    valid_request: dict,
):
    """免费用户权限被拒绝——免费套餐不支持 ai_render_cloud。"""
    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=free_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"] is not None
    assert body["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_low_balance_rejected(
    client: AsyncClient,
    low_balance_auth_headers: dict,
    valid_request: dict,
):
    """额度不足用户被拒绝——余额为 0，需要 2 额度。"""
    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=low_balance_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "CREDITS_NOT_ENOUGH"


# ============================================================
# 鉴权检查
# ============================================================


@pytest.mark.asyncio
async def test_unauthenticated_create_rejected(
    client: AsyncClient,
    valid_request: dict,
):
    """未登录请求创建任务被拒绝（401）。"""
    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_query_rejected(
    client: AsyncClient,
):
    """未登录请求查询任务被拒绝（401）。"""
    response = await client.get(
        "/api/v1/ai/render/tasks/00000000-0000-0000-0000-000000000001",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected(
    client: AsyncClient,
    valid_request: dict,
):
    """无效 Token 请求被拒绝（401）。"""
    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers={"Authorization": "Bearer invalid_token_here"},
    )

    assert response.status_code == 401


# ============================================================
# 请求校验
# ============================================================


@pytest.mark.asyncio
async def test_missing_required_fields(
    client: AsyncClient,
    standard_auth_headers: dict,
):
    """缺少必填字段时返回 422 校验错误。"""
    complete_request = {
        "scene_type": "interior_design",
        "prompt": "测试效果图",
        "input_file_ids": ["11111111-1111-1111-1111-111111111111"],
        "client_request_id": "test_req_validation",
    }

    required_fields = ["scene_type", "prompt", "input_file_ids", "client_request_id"]

    for field in required_fields:
        incomplete = {k: v for k, v in complete_request.items() if k != field}
        response = await client.post(
            "/api/v1/ai/render/tasks",
            json=incomplete,
            headers=standard_auth_headers,
        )
        assert response.status_code == 422, (
            f"缺少 '{field}' 应返回 422，实际返回 {response.status_code}"
        )


@pytest.mark.asyncio
async def test_empty_input_file_ids(
    client: AsyncClient,
    standard_auth_headers: dict,
):
    """空 input_file_ids 列表仍能创建任务。"""
    request = {
        "scene_type": "poster_design",
        "prompt": "海报设计效果图",
        "input_file_ids": [],
        "client_request_id": "test_empty_files",
    }
    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


# ============================================================
# 任务查询 - 错误场景
# ============================================================


@pytest.mark.asyncio
async def test_query_task_not_found(
    client: AsyncClient,
    standard_auth_headers: dict,
):
    """查询不存在的任务返回 404。"""
    response = await client.get(
        "/api/v1/ai/render/tasks/00000000-0000-0000-0000-000000000099",
        headers=standard_auth_headers,
    )

    # 业务错误响应为 200，通过 body 区分
    body = response.json()
    assert body["success"] is False
    assert body["error"] is not None
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_query_task_cross_user_isolation(
    client: AsyncClient,
    standard_auth_headers: dict,
    other_auth_headers: dict,
    valid_request: dict,
):
    """用户 A 不能查询用户 B 的任务（跨用户隔离）。"""
    # 用户 A（standard_user）创建任务
    create_resp = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=standard_auth_headers,
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["data"]["task_id"]

    # 用户 B（other_user）尝试查询
    query_resp = await client.get(
        f"/api/v1/ai/render/tasks/{task_id}",
        headers=other_auth_headers,
    )

    body = query_resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "PERMISSION_DENIED"


# ============================================================
# 业务验证：扣费、日志
# ============================================================


@pytest.mark.asyncio
async def test_credits_are_consumed(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_request: dict,
    db_session,
    standard_user,
):
    """验证创建效果图任务后额度确实被扣除 2。"""
    from sqlalchemy import text as sql_text

    # 生成前余额
    result = await db_session.execute(
        sql_text("SELECT balance FROM credit_accounts WHERE user_id = :uid"),
        {"uid": standard_user.id},
    )
    row = result.fetchone()
    balance_before = row[0] if row else 0

    # 创建效果图任务
    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=standard_auth_headers,
    )
    assert response.status_code == 200

    # 生成后余额
    result = await db_session.execute(
        sql_text("SELECT balance FROM credit_accounts WHERE user_id = :uid"),
        {"uid": standard_user.id},
    )
    row = result.fetchone()
    balance_after = row[0] if row else 0

    assert balance_after == balance_before - 2, (
        f"余额应从 {balance_before} 减为 {balance_before - 2}，实际为 {balance_after}"
    )


@pytest.mark.asyncio
async def test_provider_call_log_written(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_request: dict,
    db_session,
):
    """验证 Provider 调用日志已写入 provider_call_log 表。"""
    from sqlalchemy import text as sql_text

    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=standard_auth_headers,
    )
    assert response.status_code == 200

    # 使用 raw SQL 查询
    result = await db_session.execute(
        sql_text("SELECT COUNT(*) FROM provider_call_log WHERE feature = 'ai_render_cloud'")
    )
    count = result.scalar()
    assert count >= 1, "provider_call_log 表中应有 ai_render_cloud 记录"


@pytest.mark.asyncio
async def test_credit_ledger_entry_created(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_request: dict,
    db_session,
):
    """验证额度流水已写入 credit_ledger 表（consume 类型）。"""
    from sqlalchemy import text as sql_text

    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=standard_auth_headers,
    )
    assert response.status_code == 200

    # 查询 consume 流水
    result = await db_session.execute(
        sql_text("SELECT COUNT(*) FROM credit_ledger WHERE change_type = 'consume'")
    )
    consume_count = result.scalar()
    assert consume_count >= 1, "credit_ledger 表中应有 consume 流水记录"


@pytest.mark.asyncio
async def test_ai_tasks_record_created(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_request: dict,
    db_session,
):
    """验证任务记录已写入 ai_tasks 表。"""
    from sqlalchemy import text as sql_text

    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=standard_auth_headers,
    )
    assert response.status_code == 200
    task_id = response.json()["data"]["task_id"]

    # 查询 ai_tasks 表
    result = await db_session.execute(
        sql_text("SELECT id, status, feature, credits_charged FROM ai_tasks WHERE id = :tid"),
        {"tid": task_id},
    )
    row = result.fetchone()
    assert row is not None, "ai_tasks 表中应有对应记录"
    assert row[1] == "succeeded", "任务状态应为 succeeded"
    assert row[2] == "ai_render_cloud", "功能码应为 ai_render_cloud"
    assert row[3] >= 1, "应已扣除额度"


# ============================================================
# 幂等和重复请求
# ============================================================


@pytest.mark.asyncio
async def test_different_client_request_ids_independent(
    client: AsyncClient,
    standard_auth_headers: dict,
):
    """不同 client_request_id 的请求各自独立，返回不同的 task_id。"""
    request_a = {
        "scene_type": "poster_design",
        "prompt": "测试产品效果图",
        "input_file_ids": ["11111111-1111-1111-1111-111111111111"],
        "client_request_id": "idempotent_render_test_a",
    }
    request_b = {
        **request_a,
        "client_request_id": "idempotent_render_test_b",
    }

    resp_a = await client.post(
        "/api/v1/ai/render/tasks",
        json=request_a,
        headers=standard_auth_headers,
    )
    resp_b = await client.post(
        "/api/v1/ai/render/tasks",
        json=request_b,
        headers=standard_auth_headers,
    )

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert (
        resp_a.json()["data"]["task_id"]
        != resp_b.json()["data"]["task_id"]
    ), "不同请求应有不同 task_id"


@pytest.mark.asyncio
async def test_create_response_structure_matches_openapi(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_request: dict,
):
    """创建任务响应结构对齐 ai-render.yaml CreatedTaskData schema。"""
    response = await client.post(
        "/api/v1/ai/render/tasks",
        json=valid_request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()

    # 外层结构
    assert isinstance(body["success"], bool)
    assert "data" in body
    assert "error" in body
    assert "request_id" in body

    # data 内层结构
    data = body["data"]
    assert isinstance(data["task_id"], str)
    assert data["status"] in ("queued", "running", "succeeded", "failed")
    assert isinstance(data["feature"], str)
    assert data["feature"] == "ai_render_cloud"
    assert isinstance(data["estimated_credits"], int)
    assert data["estimated_credits"] > 0
