"""
健康检查端点测试。

验证 GET /health 返回的响应结构对齐
shared-contract/openapi/common.yaml #/components/schemas/HealthResponse
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200_and_required_fields(client: AsyncClient) -> None:
    """健康检查端点：200 OK，响应包含 status、version、checks 字段。"""
    response = await client.get("/health")
    assert response.status_code == 200, f"期望 200，实际 {response.status_code}"

    body = response.json()

    # 对齐 HealthResponse Schema：必须包含 status 和 version
    assert "status" in body, "响应缺少 status 字段"
    assert "version" in body, "响应缺少 version 字段"


@pytest.mark.asyncio
async def test_health_status_is_valid(client: AsyncClient) -> None:
    """健康检查端点：status 字段值必须在 [ok, degraded, down] 范围内。"""
    response = await client.get("/health")
    body = response.json()

    valid_statuses = {"ok", "degraded", "down"}
    assert body["status"] in valid_statuses, (
        f"status 值应为 {valid_statuses}，实际为 {body['status']}"
    )


@pytest.mark.asyncio
async def test_health_version_matches_config(client: AsyncClient) -> None:
    """健康检查端点：version 字段值应与配置一致。"""
    response = await client.get("/health")
    body = response.json()

    assert body["version"] is not None
    assert isinstance(body["version"], str)
    assert len(body["version"]) > 0
    assert body["version"] == "0.1.0-test"


@pytest.mark.asyncio
async def test_health_no_components_returns_ok(client: AsyncClient) -> None:
    """健康检查端点：无组件检查时 status 应为 ok，checks 可为 null。"""
    response = await client.get("/health")
    body = response.json()

    # 当前没有任何组件检查注册，status 应为 ok
    assert body["status"] == "ok", (
        f"无组件注册时 status 应为 ok，实际为 {body['status']}"
    )
