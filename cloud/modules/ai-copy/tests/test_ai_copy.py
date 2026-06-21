"""
cloud-ai-copy 测试套件。

测试覆盖：
- 成功生成（标准用户、专业用户）
- 权限检查（免费用户被拒绝）
- 额度检查（余额不足被拒绝）
- 鉴权检查（未登录被拒绝）
- 请求校验（缺少必填字段）
- 响应结构校验（对齐 OpenAPI ai-copy.yaml）
- 最小请求（仅必填字段）
- 不同 scene/tone 组合
- 扣费验证（生成后余额减少）
- 日志验证（provider_call_log 和 credit_ledger 写入）

测试数据库：SQLite 内存数据库 + Mock Provider。
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


# ============================================================
# 成功场景
# ============================================================


@pytest.mark.asyncio
async def test_generate_copy_success_standard(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_request: dict,
):
    """标准用户成功生成文案。

    验证：
    - HTTP 200 返回
    - 响应包含 success=true
    - data 包含所有必需字段
    - feature 固定为 ai_copy_cloud
    - text 非空
    - variants 是列表
    - provider 和 model 非空
    - estimated_cost 和 credits_charged 为正数
    - provider_call_id 非空
    """
    response = await client.post(
        "/api/v1/ai/copy/generate",
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
    assert data["feature"] == "ai_copy_cloud"
    assert len(data["text"]) > 0, "主文案不应为空"
    assert isinstance(data["variants"], list), "variants 应为列表"
    assert len(data["provider"]) > 0, "provider 不应为空"
    assert len(data["model"]) > 0, "model 不应为空"
    assert data["estimated_cost"] >= 0
    assert data["credits_charged"] == 1
    assert len(data["provider_call_id"]) > 0, "provider_call_id 不应为空"


@pytest.mark.asyncio
async def test_generate_copy_success_pro(
    client: AsyncClient,
    pro_auth_headers: dict,
    valid_request: dict,
):
    """专业用户成功生成文案。"""
    response = await client.post(
        "/api/v1/ai/copy/generate",
        json=valid_request,
        headers=pro_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["feature"] == "ai_copy_cloud"


@pytest.mark.asyncio
async def test_generate_copy_minimal_request(
    client: AsyncClient,
    standard_auth_headers: dict,
    minimal_request: dict,
):
    """最小必填字段请求成功生成文案。"""
    response = await client.post(
        "/api/v1/ai/copy/generate",
        json=minimal_request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]["text"]) > 0


@pytest.mark.asyncio
async def test_generate_copy_with_different_tones(
    client: AsyncClient,
    standard_auth_headers: dict,
):
    """不同语气风格均能成功生成。"""
    tones = ["direct", "professional", "friendly", "urgent", "elegant"]
    for tone in tones:
        request = {
            "scene": "poster",
            "product_name": f"测试产品-{tone}",
            "selling_points": ["高品质", "快速交付"],
            "tone": tone,
            "client_request_id": f"test_tone_{tone}",
        }
        response = await client.post(
            "/api/v1/ai/copy/generate",
            json=request,
            headers=standard_auth_headers,
        )
        assert response.status_code == 200, f"语气 '{tone}' 应返回 200"
        body = response.json()
        assert body["success"] is True, f"语气 '{tone}' 应成功"


@pytest.mark.asyncio
async def test_generate_copy_all_scenes(
    client: AsyncClient,
    standard_auth_headers: dict,
):
    """所有场景类型均能成功生成。"""
    scenes = ["poster", "social_post", "ad_banner", "flyer", "slogan"]
    for scene in scenes:
        request = {
            "scene": scene,
            "product_name": "测试产品",
            "selling_points": ["卖点A"],
            "tone": "direct",
            "client_request_id": f"test_scene_{scene}",
        }
        response = await client.post(
            "/api/v1/ai/copy/generate",
            json=request,
            headers=standard_auth_headers,
        )
        assert response.status_code == 200, f"场景 '{scene}' 应返回 200"


# ============================================================
# 权限和额度检查
# ============================================================


@pytest.mark.asyncio
async def test_free_user_permission_denied(
    client: AsyncClient,
    free_auth_headers: dict,
    valid_request: dict,
):
    """免费用户权限被拒绝——免费套餐不支持 ai_copy_cloud。"""
    response = await client.post(
        "/api/v1/ai/copy/generate",
        json=valid_request,
        headers=free_auth_headers,
    )

    # 业务错误不改变 HTTP 状态码（对齐项目既有模式）
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
    """额度不足用户被拒绝——余额为 0，需要 1 额度。"""
    response = await client.post(
        "/api/v1/ai/copy/generate",
        json=valid_request,
        headers=low_balance_auth_headers,
    )

    # 业务错误不改变 HTTP 状态码（对齐项目既有模式）
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "CREDITS_NOT_ENOUGH"


# ============================================================
# 鉴权检查
# ============================================================


@pytest.mark.asyncio
async def test_unauthenticated_rejected(
    client: AsyncClient,
    valid_request: dict,
):
    """未登录请求被拒绝（401）。"""
    response = await client.post(
        "/api/v1/ai/copy/generate",
        json=valid_request,
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected(
    client: AsyncClient,
    valid_request: dict,
):
    """无效 Token 请求被拒绝（401）。"""
    response = await client.post(
        "/api/v1/ai/copy/generate",
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
        "scene": "poster",
        "product_name": "快印宣传单",
        "selling_points": ["当天取件"],
        "tone": "direct",
        "client_request_id": "test_req_validation",
    }

    required_fields = ["scene", "product_name", "selling_points", "tone", "client_request_id"]

    for field in required_fields:
        incomplete = {k: v for k, v in complete_request.items() if k != field}
        response = await client.post(
            "/api/v1/ai/copy/generate",
            json=incomplete,
            headers=standard_auth_headers,
        )
        assert response.status_code == 422, (
            f"缺少 '{field}' 应返回 422，实际返回 {response.status_code}"
        )


@pytest.mark.asyncio
async def test_empty_selling_points(
    client: AsyncClient,
    standard_auth_headers: dict,
):
    """空卖点列表仍能正常生成。"""
    request = {
        "scene": "poster",
        "product_name": "快印宣传单",
        "selling_points": [],
        "tone": "direct",
        "client_request_id": "test_empty_selling_points",
    }
    response = await client.post(
        "/api/v1/ai/copy/generate",
        json=request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


# ============================================================
# 响应字段校验（对齐 OpenAPI）
# ============================================================


@pytest.mark.asyncio
async def test_response_structure_matches_openapi(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_request: dict,
):
    """响应结构完全对齐 ai-copy.yaml。"""
    response = await client.post(
        "/api/v1/ai/copy/generate",
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
    assert isinstance(body["request_id"], str)

    # data 内层结构（对齐 AiCopyGenerateData schema）
    data = body["data"]
    assert isinstance(data["feature"], str)
    assert data["feature"] == "ai_copy_cloud"
    assert isinstance(data["text"], str)
    assert isinstance(data["variants"], list)
    for variant in data["variants"]:
        assert isinstance(variant, str)
    assert isinstance(data["provider"], str)
    assert isinstance(data["model"], str)
    assert isinstance(data["estimated_cost"], (int, float))
    assert isinstance(data["credits_charged"], int)
    assert isinstance(data["provider_call_id"], str)


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
    """验证生成文案后额度确实被扣除 1。"""
    from sqlalchemy import text as sql_text

    # 生成前余额（使用 raw SQL 避免 ORM 表重复注册）
    result = await db_session.execute(
        sql_text("SELECT balance FROM credit_accounts WHERE user_id = :uid"),
        {"uid": standard_user.id},
    )
    row = result.fetchone()
    balance_before = row[0] if row else 0

    # 生成文案
    response = await client.post(
        "/api/v1/ai/copy/generate",
        json=valid_request,
        headers=standard_auth_headers,
    )
    assert response.status_code == 200

    # 生成后余额（raw SQL）
    result = await db_session.execute(
        sql_text("SELECT balance FROM credit_accounts WHERE user_id = :uid"),
        {"uid": standard_user.id},
    )
    row = result.fetchone()
    balance_after = row[0] if row else 0

    assert balance_after == balance_before - 1, (
        f"余额应从 {balance_before} 减为 {balance_before - 1}，实际为 {balance_after}"
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
        "/api/v1/ai/copy/generate",
        json=valid_request,
        headers=standard_auth_headers,
    )
    assert response.status_code == 200

    # 使用 raw SQL 查询（避免 ORM 表重复注册）
    result = await db_session.execute(
        sql_text("SELECT COUNT(*) FROM provider_call_log")
    )
    count = result.scalar()
    assert count >= 1, "provider_call_log 表中应有记录"


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
        "/api/v1/ai/copy/generate",
        json=valid_request,
        headers=standard_auth_headers,
    )
    assert response.status_code == 200

    # 使用 raw SQL 查询（避免 ORM 表重复注册）
    result = await db_session.execute(
        sql_text("SELECT COUNT(*) FROM credit_ledger WHERE change_type = 'consume'")
    )
    consume_count = result.scalar()
    assert consume_count >= 1, "credit_ledger 表中应有 consume 流水记录"


# ============================================================
# 幂等和重复请求
# ============================================================


@pytest.mark.asyncio
async def test_different_client_request_ids_independent(
    client: AsyncClient,
    standard_auth_headers: dict,
):
    """不同 client_request_id 的请求各自独立，返回不同的 provider_call_id。"""
    request_a = {
        "scene": "poster",
        "product_name": "测试产品",
        "selling_points": ["卖点一"],
        "tone": "direct",
        "client_request_id": "idempotent_test_a",
    }
    request_b = {
        **request_a,
        "client_request_id": "idempotent_test_b",
    }

    resp_a = await client.post(
        "/api/v1/ai/copy/generate",
        json=request_a,
        headers=standard_auth_headers,
    )
    resp_b = await client.post(
        "/api/v1/ai/copy/generate",
        json=request_b,
        headers=standard_auth_headers,
    )

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert (
        resp_a.json()["data"]["provider_call_id"]
        != resp_b.json()["data"]["provider_call_id"]
    )
