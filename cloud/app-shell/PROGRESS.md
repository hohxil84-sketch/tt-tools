# PROGRESS.md - cloud-app-shell

## 当前状态

`DEVELOPMENT_COMPLETE`

## 分支

`feature/cloud-app-shell`

## 已完成

- 已安装 Python 3.11.9 到 C:\Program Files\Python311。
- 已创建虚拟环境 D:\localPath\venvs\cloud-app-shell。
- 已安装 FastAPI 0.138.0 / uvicorn 0.49.0 / pydantic-settings 2.14.2 / httpx 0.28.1 / pytest 9.1.1 / pytest-asyncio 1.4.0。
- 已实现配置管理模块（config.py）：AppSettings 类，支持环境变量映射（前缀 APP_）。
- 已实现健康检查端点（health.py）：GET /health，对齐 common.yaml HealthResponse Schema（status、version、checks）。
- 已实现基础中间件（middleware.py）：统一错误处理（外层 BaseHTTPMiddleware 兜底）、CORS 跨域、X-Request-ID 追踪。
- 已实现应用入口（main.py）：create_app() 工厂函数、lifespan 生命周期管理、uvicorn 启动。
- 已实现测试套件：test_config.py（10 项）、test_health.py（4 项）、test_middleware.py（9 项）。
- 代码关键逻辑已加中文注释。
- 新依赖已登记到 environment/INSTALLED_DEPENDENCIES.md。
- 安装历史已登记到 environment/SETUP_HISTORY.md。

## 测试记录

日期：2026-06-20
测试命令：pytest cloud/app-shell/tests/ -v
结果：23 passed, 0 failed
失败原因：无
修复提交：无
中文备注：首次开发完成，全部 23 项测试通过。配置 10 项 + 健康检查 4 项 + 中间件 9 项。

## Bug 记录

### 2026-06-25: credits-billing 路由未注册导致 entitlements/check 返回 404

- **现象**：桌面端调用 `POST /api/v1/entitlements/check` 返回 404，`GET /credits/balance` 和 `GET /credits/ledger` 同样 404。
- **根因**：`cloud-credits-billing` 模块已实现并合并到 dev/full-product，但 `main.py` 的 `create_app()` 中从未调用 `app.include_router()` 注册其路由。
- **修复点**：
  1. 新增 `_preload_credits_billing_models()` 函数，预加载 Plan/CreditAccount/CreditLedger/UsageEvent 等 ORM 模型
  2. `create_app()` 开头调用 `_preload_auth_device_models()` 和 `_preload_credits_billing_models()`
  3. 注册 credits-billing router，清理 sys.modules 缓存避免交叉污染
- **测试命令**：`pytest cloud/modules/credits-billing/tests/ -v`
- **测试结果**：30 passed, 0 failed
- **分支**：`fix/cloud-app-shell-credits-billing-router-not-registered`
- **提交**：`549715a`
- **中文备注**：修复后需在 192.168.2.101:8000 上重新部署验证。

## 提交记录

| 日期 | 提交哈希 | 说明 |
|---|---|---|
| 2026-06-20 | 4493c45 | feat(cloud-app-shell): 完成 FastAPI 云端启动骨架、配置、路由装配、健康检查和基础中间件。23 项测试全部通过。 |
