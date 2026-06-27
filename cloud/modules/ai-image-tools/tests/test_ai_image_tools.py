"""
cloud-ai-image-tools 测试套件。

测试覆盖：
- 成功创建任务（5 种子功能码各一种）
- 权限检查（免费用户被拒绝）
- 额度检查（余额不足被拒绝）
- 鉴权检查（未登录被拒绝、无效 Token）
- 请求校验（缺少必填字段、无效 feature 值）
- 响应结构校验（对齐 OpenAPI ai-image-tools.yaml）
- 最小请求（仅必填字段）
- 不同 feature 组合
- 任务查询（创建后查询状态和结果）
- result_files 按功能码不同
- result_json 按功能码不同（特别是 OCR 的文字识别结果）
- 跨用户任务隔离（其他用户不能查询）
- 任务不存在（404）
- 扣费验证（创建任务后余额减少，不同功能码扣费不同）
- 日志验证（provider_call_log 和 credit_ledger 写入）
- 幂等性（不同 client_request_id 独立）

测试数据库：SQLite 内存数据库 + Mock Provider。
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


# ============================================================
# 所有功能码列表
# ============================================================

_ALL_FEATURES = [
    "upscale_image_cloud",
    "vectorize_image_cloud",
    "ai_edit_image_cloud",
    "remove_bg_cloud",
    "ocr_cloud",
]

# 各功能码的预期扣费额度
_FEATURE_CREDITS = {
    "upscale_image_cloud": 3,
    "vectorize_image_cloud": 3,
    "ai_edit_image_cloud": 5,
    "remove_bg_cloud": 2,
    "ocr_cloud": 2,
}


# ============================================================
# 成功场景 - 创建任务（5 种子功能码）
# ============================================================


@pytest.mark.asyncio
async def test_create_upscale_task_success(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_upscale_request: dict,
):
    """标准用户成功创建高清修复任务。

    验证：
    - HTTP 200 返回
    - 响应包含 success=true
    - data 包含所有必需字段
    - feature 回显为 upscale_image_cloud
    - task_id 非空
    - status 为 succeeded（Mock 同步完成）
    - estimated_credits 为 3
    """
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_upscale_request,
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
    assert data["feature"] == "upscale_image_cloud"
    assert len(data["task_id"]) > 0, "task_id 不应为空"
    assert data["status"] == "succeeded", "Mock 同步执行后应为 succeeded"
    assert data["estimated_credits"] == 3


@pytest.mark.asyncio
async def test_create_vectorize_task_success(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_vectorize_request: dict,
):
    """标准用户成功创建转矢量任务。"""
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_vectorize_request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["feature"] == "vectorize_image_cloud"
    assert body["data"]["status"] == "succeeded"
    assert body["data"]["estimated_credits"] == 3


@pytest.mark.asyncio
async def test_create_ai_edit_task_success(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_ai_edit_request: dict,
):
    """标准用户成功创建 AI 改图任务。"""
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_ai_edit_request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["feature"] == "ai_edit_image_cloud"
    assert body["data"]["status"] == "succeeded"
    assert body["data"]["estimated_credits"] == 5


@pytest.mark.asyncio
async def test_create_remove_bg_task_success(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_remove_bg_request: dict,
):
    """标准用户成功创建高级抠图任务。"""
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["feature"] == "remove_bg_cloud"
    assert body["data"]["status"] == "succeeded"
    assert body["data"]["estimated_credits"] == 2


@pytest.mark.asyncio
async def test_create_ocr_task_success(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_ocr_request: dict,
):
    """标准用户成功创建高级 OCR 任务。"""
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_ocr_request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["feature"] == "ocr_cloud"
    assert body["data"]["status"] == "succeeded"
    assert body["data"]["estimated_credits"] == 2


@pytest.mark.asyncio
async def test_create_task_success_pro(
    client: AsyncClient,
    pro_auth_headers: dict,
    valid_remove_bg_request: dict,
):
    """专业用户成功创建任务。"""
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
        headers=pro_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_create_task_minimal_request(
    client: AsyncClient,
    standard_auth_headers: dict,
    minimal_request: dict,
):
    """最小必填字段请求成功创建任务。"""
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=minimal_request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]["task_id"]) > 0


@pytest.mark.asyncio
async def test_create_task_all_features(
    client: AsyncClient,
    standard_auth_headers: dict,
):
    """全部 5 种子功能码均能成功创建任务。"""
    for feature in _ALL_FEATURES:
        request = {
            "feature": feature,
            "input_file_ids": ["11111111-1111-1111-1111-111111111111"],
            "client_request_id": f"test_all_features_{feature}",
        }
        response = await client.post(
            "/api/v1/ai/image-tools/tasks",
            json=request,
            headers=standard_auth_headers,
        )
        assert response.status_code == 200, f"功能码 '{feature}' 应返回 200"
        body = response.json()
        assert body["success"] is True, f"功能码 '{feature}' 应成功"
        assert body["data"]["feature"] == feature, f"功能码 '{feature}' 应回显正确"


@pytest.mark.asyncio
async def test_create_task_with_options(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_ocr_request: dict,
):
    """带 options 可选字段创建任务成功。"""
    # valid_ocr_request 已包含 options 字段
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_ocr_request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


# ============================================================
# 成功场景 - 查询任务（含 result_files 和 result_json 验证）
# ============================================================


@pytest.mark.asyncio
async def test_query_task_after_creation(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_remove_bg_request: dict,
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
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
        headers=standard_auth_headers,
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["data"]["task_id"]

    # 查询任务
    query_resp = await client.get(
        f"/api/v1/ai/image-tools/tasks/{task_id}",
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
    assert data["feature"] == "remove_bg_cloud"

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
async def test_query_task_ocr_result_json(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_ocr_request: dict,
):
    """OCR 任务查询结果中包含 text_lines 等自定义 result_json。"""
    create_resp = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_ocr_request,
        headers=standard_auth_headers,
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["data"]["task_id"]

    query_resp = await client.get(
        f"/api/v1/ai/image-tools/tasks/{task_id}",
        headers=standard_auth_headers,
    )

    body = query_resp.json()
    data = body["data"]
    assert data["feature"] == "ocr_cloud"

    # OCR 应有 result_json 自定义数据
    assert data["result_json"] is not None
    assert "text_lines" in data["result_json"]
    assert isinstance(data["result_json"]["text_lines"], list)
    assert len(data["result_json"]["text_lines"]) > 0
    # 每行有 text、confidence、bbox
    line = data["result_json"]["text_lines"][0]
    assert "text" in line
    assert "confidence" in line
    assert "bbox" in line
    assert data["result_json"]["language"] == "zh"


@pytest.mark.asyncio
async def test_query_task_upscale_result_files(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_upscale_request: dict,
):
    """高清修复任务的结果文件包含高分辨率元数据。"""
    create_resp = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_upscale_request,
        headers=standard_auth_headers,
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["data"]["task_id"]

    query_resp = await client.get(
        f"/api/v1/ai/image-tools/tasks/{task_id}",
        headers=standard_auth_headers,
    )

    body = query_resp.json()
    data = body["data"]
    assert data["feature"] == "upscale_image_cloud"

    # 高清修复的结果文件应有高分辨率参数
    rf = data["result_files"][0]
    assert rf["width"] >= 1920, "高清修复结果宽度应 >= 1920"
    assert rf["mime_type"] == "image/png"

    # result_json 应包含缩放信息
    assert data["result_json"] is not None
    assert "scale_factor" in data["result_json"]


@pytest.mark.asyncio
async def test_query_task_vectorize_result_files(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_vectorize_request: dict,
):
    """转矢量任务的结果文件为 SVG 格式。"""
    create_resp = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_vectorize_request,
        headers=standard_auth_headers,
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["data"]["task_id"]

    query_resp = await client.get(
        f"/api/v1/ai/image-tools/tasks/{task_id}",
        headers=standard_auth_headers,
    )

    body = query_resp.json()
    data = body["data"]
    assert data["feature"] == "vectorize_image_cloud"

    # 转矢量结果文件应为 SVG
    rf = data["result_files"][0]
    assert rf["mime_type"] == "image/svg+xml"

    # result_json 应包含矢量图层信息
    assert data["result_json"] is not None
    assert "layer_count" in data["result_json"]


@pytest.mark.asyncio
async def test_query_task_response_structure_matches_openapi(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_remove_bg_request: dict,
):
    """查询任务响应结构完全对齐 ai-image-tools.yaml。"""
    create_resp = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
        headers=standard_auth_headers,
    )
    task_id = create_resp.json()["data"]["task_id"]

    query_resp = await client.get(
        f"/api/v1/ai/image-tools/tasks/{task_id}",
        headers=standard_auth_headers,
    )

    assert query_resp.status_code == 200
    body = query_resp.json()

    # 外层结构（对齐 ApiResponse）
    assert isinstance(body["success"], bool)
    assert "data" in body
    assert "error" in body
    assert "request_id" in body
    assert isinstance(body["request_id"], str)

    # data 内层结构（对齐 AiImageToolTaskData schema）
    data = body["data"]
    assert isinstance(data["task_id"], str)
    assert data["status"] in ("queued", "running", "succeeded", "failed")
    assert isinstance(data["feature"], str)
    assert isinstance(data["result_files"], list)

    # 成功状态下 result_files 中每个元素的结构
    for f in data["result_files"]:
        assert isinstance(f["file_id"], str)
        assert isinstance(f["mime_type"], str)
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

    # result_json 可选，但成功时 checking
    if data["result_json"] is not None:
        assert isinstance(data["result_json"], dict)


# ============================================================
# 权限和额度检查
# ============================================================


@pytest.mark.asyncio
async def test_free_user_permission_denied(
    client: AsyncClient,
    free_auth_headers: dict,
    valid_remove_bg_request: dict,
):
    """免费用户权限被拒绝——免费套餐不支持 AI 图片子功能。"""
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
        headers=free_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"] is not None
    assert body["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_free_user_all_features_denied(
    client: AsyncClient,
    free_auth_headers: dict,
):
    """免费用户对所有 5 种子功能码均被拒绝。"""
    for feature in _ALL_FEATURES:
        request = {
            "feature": feature,
            "input_file_ids": ["11111111-1111-1111-1111-111111111111"],
            "client_request_id": f"test_free_denied_{feature}",
        }
        response = await client.post(
            "/api/v1/ai/image-tools/tasks",
            json=request,
            headers=free_auth_headers,
        )

        body = response.json()
        assert body["success"] is False, f"免费用户应无法使用 '{feature}'"
        assert body["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_low_balance_rejected(
    client: AsyncClient,
    low_balance_auth_headers: dict,
    valid_remove_bg_request: dict,
):
    """额度不足用户被拒绝——余额为 0，需要 2 额度。"""
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
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
    valid_remove_bg_request: dict,
):
    """未登录请求创建任务被拒绝（401）。"""
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_query_rejected(
    client: AsyncClient,
):
    """未登录请求查询任务被拒绝（401）。"""
    response = await client.get(
        "/api/v1/ai/image-tools/tasks/00000000-0000-0000-0000-000000000001",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected(
    client: AsyncClient,
    valid_remove_bg_request: dict,
):
    """无效 Token 请求被拒绝（401）。"""
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
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
        "feature": "remove_bg_cloud",
        "input_file_ids": ["11111111-1111-1111-1111-111111111111"],
        "client_request_id": "test_req_validation",
    }

    required_fields = ["feature", "input_file_ids", "client_request_id"]

    for field in required_fields:
        incomplete = {k: v for k, v in complete_request.items() if k != field}
        response = await client.post(
            "/api/v1/ai/image-tools/tasks",
            json=incomplete,
            headers=standard_auth_headers,
        )
        assert response.status_code == 422, (
            f"缺少 '{field}' 应返回 422，实际返回 {response.status_code}"
        )


@pytest.mark.asyncio
async def test_invalid_feature_value(
    client: AsyncClient,
    standard_auth_headers: dict,
):
    """无效的 feature 值应返回 422 校验错误。"""
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json={
            "feature": "invalid_feature_code",
            "input_file_ids": ["11111111-1111-1111-1111-111111111111"],
            "client_request_id": "test_invalid_feature",
        },
        headers=standard_auth_headers,
    )

    assert response.status_code == 422, "无效 feature 应返回 422"


@pytest.mark.asyncio
async def test_empty_input_file_ids(
    client: AsyncClient,
    standard_auth_headers: dict,
):
    """空 input_file_ids 列表仍能创建任务。"""
    request = {
        "feature": "ocr_cloud",
        "input_file_ids": [],
        "client_request_id": "test_empty_files",
    }
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
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
    """查询不存在的任务返回业务错误。"""
    response = await client.get(
        "/api/v1/ai/image-tools/tasks/00000000-0000-0000-0000-000000000099",
        headers=standard_auth_headers,
    )

    body = response.json()
    assert body["success"] is False
    assert body["error"] is not None
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_query_task_cross_user_isolation(
    client: AsyncClient,
    standard_auth_headers: dict,
    other_auth_headers: dict,
    valid_remove_bg_request: dict,
):
    """用户 A 不能查询用户 B 的任务（跨用户隔离）。"""
    # 用户 A（standard_user）创建任务
    create_resp = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
        headers=standard_auth_headers,
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["data"]["task_id"]

    # 用户 B（other_user）尝试查询
    query_resp = await client.get(
        f"/api/v1/ai/image-tools/tasks/{task_id}",
        headers=other_auth_headers,
    )

    body = query_resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "PERMISSION_DENIED"


# ============================================================
# 业务验证：扣费、日志
# ============================================================


@pytest.mark.asyncio
async def test_credits_are_consumed_for_remove_bg(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_remove_bg_request: dict,
    db_session,
    standard_user,
):
    """验证创建高级抠图任务后额度确实被扣除 2。"""
    from sqlalchemy import text as sql_text

    # 生成前余额
    result = await db_session.execute(
        sql_text("SELECT balance FROM credit_accounts WHERE user_id = :uid"),
        {"uid": standard_user.id},
    )
    row = result.fetchone()
    balance_before = row[0] if row else 0

    # 创建任务
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
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
async def test_credits_are_consumed_for_ai_edit(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_ai_edit_request: dict,
    db_session,
    standard_user,
):
    """验证 AI 改图任务扣除 5 额度（不同功能码扣费不同）。"""
    from sqlalchemy import text as sql_text

    result = await db_session.execute(
        sql_text("SELECT balance FROM credit_accounts WHERE user_id = :uid"),
        {"uid": standard_user.id},
    )
    row = result.fetchone()
    balance_before = row[0] if row else 0

    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_ai_edit_request,
        headers=standard_auth_headers,
    )
    assert response.status_code == 200

    result = await db_session.execute(
        sql_text("SELECT balance FROM credit_accounts WHERE user_id = :uid"),
        {"uid": standard_user.id},
    )
    row = result.fetchone()
    balance_after = row[0] if row else 0

    assert balance_after == balance_before - 5, (
        f"AI 改图应扣 5 额度，余额从 {balance_before} 应减为 {balance_before - 5}，实际为 {balance_after}"
    )


@pytest.mark.asyncio
async def test_provider_call_log_written(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_upscale_request: dict,
    db_session,
):
    """验证 Provider 调用日志已写入 provider_call_log 表。"""
    from sqlalchemy import text as sql_text

    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_upscale_request,
        headers=standard_auth_headers,
    )
    assert response.status_code == 200

    # 检查各功能码的日志记录
    result = await db_session.execute(
        sql_text("SELECT COUNT(*) FROM provider_call_log WHERE feature = 'upscale_image_cloud'")
    )
    count = result.scalar()
    assert count >= 1, "provider_call_log 表中应有 upscale_image_cloud 记录"


@pytest.mark.asyncio
async def test_credit_ledger_entry_created(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_ocr_request: dict,
    db_session,
):
    """验证额度流水已写入 credit_ledger 表（consume 类型）。"""
    from sqlalchemy import text as sql_text

    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_ocr_request,
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
    valid_remove_bg_request: dict,
    db_session,
):
    """验证任务记录已写入 ai_tasks 表。"""
    from sqlalchemy import text as sql_text

    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
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
    assert row[2] == "remove_bg_cloud", "功能码应为 remove_bg_cloud"
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
        "feature": "ocr_cloud",
        "input_file_ids": ["11111111-1111-1111-1111-111111111111"],
        "client_request_id": "idempotent_image_tools_test_a",
    }
    request_b = {
        **request_a,
        "client_request_id": "idempotent_image_tools_test_b",
    }

    resp_a = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=request_a,
        headers=standard_auth_headers,
    )
    resp_b = await client.post(
        "/api/v1/ai/image-tools/tasks",
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
    valid_remove_bg_request: dict,
):
    """创建任务响应结构对齐 ai-image-tools.yaml CreatedTaskData schema。"""
    response = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
        headers=standard_auth_headers,
    )

    assert response.status_code == 200
    body = response.json()

    # 外层结构
    assert isinstance(body["success"], bool)
    assert "data" in body
    assert "error" in body
    assert "request_id" in body

    # data 内层结构（对齐 CreatedTaskData）
    data = body["data"]
    assert isinstance(data["task_id"], str)
    assert data["status"] in ("queued", "running", "succeeded", "failed")
    assert isinstance(data["feature"], str)
    assert isinstance(data["estimated_credits"], int)
    assert data["estimated_credits"] > 0


# ============================================================
# 各功能码的 result_json 验证
# ============================================================


@pytest.mark.asyncio
async def test_upscale_result_json_structure(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_upscale_request: dict,
):
    """高清修复的 result_json 包含缩放参数。"""
    create_resp = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_upscale_request,
        headers=standard_auth_headers,
    )
    task_id = create_resp.json()["data"]["task_id"]

    query_resp = await client.get(
        f"/api/v1/ai/image-tools/tasks/{task_id}",
        headers=standard_auth_headers,
    )
    data = query_resp.json()["data"]
    rj = data["result_json"]
    assert rj is not None
    assert rj["scale_factor"] == 2.0
    assert rj["algorithm"] == "ai_super_resolution_v2"


@pytest.mark.asyncio
async def test_vectorize_result_json_structure(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_vectorize_request: dict,
):
    """转矢量的 result_json 包含图层和路径信息。"""
    create_resp = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_vectorize_request,
        headers=standard_auth_headers,
    )
    task_id = create_resp.json()["data"]["task_id"]

    query_resp = await client.get(
        f"/api/v1/ai/image-tools/tasks/{task_id}",
        headers=standard_auth_headers,
    )
    data = query_resp.json()["data"]
    rj = data["result_json"]
    assert rj is not None
    assert rj["output_format"] == "svg"
    assert rj["path_count"] == 128


@pytest.mark.asyncio
async def test_ai_edit_result_json_structure(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_ai_edit_request: dict,
):
    """AI 改图的 result_json 包含编辑参数。"""
    create_resp = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_ai_edit_request,
        headers=standard_auth_headers,
    )
    task_id = create_resp.json()["data"]["task_id"]

    query_resp = await client.get(
        f"/api/v1/ai/image-tools/tasks/{task_id}",
        headers=standard_auth_headers,
    )
    data = query_resp.json()["data"]
    rj = data["result_json"]
    assert rj is not None
    assert rj["edit_type"] == "intelligent_enhancement"
    assert "applied_filters" in rj


@pytest.mark.asyncio
async def test_remove_bg_result_json_structure(
    client: AsyncClient,
    standard_auth_headers: dict,
    valid_remove_bg_request: dict,
):
    """高级抠图的 result_json 包含抠图参数。"""
    create_resp = await client.post(
        "/api/v1/ai/image-tools/tasks",
        json=valid_remove_bg_request,
        headers=standard_auth_headers,
    )
    task_id = create_resp.json()["data"]["task_id"]

    query_resp = await client.get(
        f"/api/v1/ai/image-tools/tasks/{task_id}",
        headers=standard_auth_headers,
    )
    data = query_resp.json()["data"]
    rj = data["result_json"]
    assert rj is not None
    assert rj["has_transparency"] is True
    assert "detected_subjects" in rj
