# CC_DEVELOPMENT_ORDER_AND_TERMS.md

本文件用于指导两台电脑上的 Claude Code 并行开发。一个 CC 主要负责桌面端和本地 worker，另一个 CC 主要负责云端和后台。

开始任何模块前，两个 CC 都必须先阅读根目录 `CLAUDE.md`。

## 总原则

- 先 shared-contract，后桌面端和云端并行。
- 涉及接口的模块，必须先完成对应 OpenAPI 契约。
- 桌面端不得猜云端字段。
- 云端不得返回 OpenAPI 未定义字段。
- 本地 worker 不得调用云端 Provider。
- 云端 AI 模块不得直接调用 OpenAI、DeepSeek 或其他 Provider，必须通过 `provider-runtime`。
- 下载依赖、安装包、模型、工具缓存必须优先放到 `D:\localPath`。
- 每个模块完成后必须测试、更新进度、提交推送，然后停止等待用户指定下一个模块。

## 推荐开发主线

```text
shared-contract
  -> cloud 基础
  -> desktop 基础
  -> local-worker 基础
  -> auth/device 联调
  -> 文件和任务系统
  -> 本地免费功能
  -> 本地付费权限
  -> Provider Runtime
  -> 云端 AI
  -> 后台管理
```

## 共享契约开发顺序

这部分建议先由云端电脑或专门的 CC 负责，完成后两端都按它开发。

1. `shared-contract/modules/base-rules`
   - 目标：确认统一响应结构、错误结构、request_id、鉴权规则。
   - 重点文件：`shared-contract/openapi/common.yaml`
   - 完成后：运行 OpenAPI 校验工具，并登记依赖。

2. `shared-contract/modules/auth-device`
   - 目标：登录、刷新、退出、设备绑定契约。
   - 重点文件：`shared-contract/openapi/auth-device.yaml`

3. `shared-contract/modules/credits-billing`
   - 目标：余额、流水、套餐权限检查契约。
   - 重点文件：`shared-contract/openapi/credits-billing.yaml`

4. `shared-contract/modules/local-paid-tools`
   - 目标：本地付费工具权限检查规则。
   - 依赖：`credits-billing`

5. `shared-contract/modules/ai-copy`
   - 目标：云端文案生成契约。
   - 重点文件：`shared-contract/openapi/ai-copy.yaml`

6. `shared-contract/modules/provider-log`
   - 目标：Provider 调用日志查询契约。
   - 重点文件：`shared-contract/openapi/provider-log.yaml`

7. `shared-contract/modules/ai-render`
   - 目标：效果图任务创建和查询契约。
   - 重点文件：`shared-contract/openapi/ai-render.yaml`

8. `shared-contract/modules/ai-image-tools`
   - 目标：高级图片 AI 任务契约。
   - 重点文件：`shared-contract/openapi/ai-image-tools.yaml`

## 云端 CC 开发顺序

云端 CC 的工作目录主要在 `cloud/` 和 `shared-contract/`。

### 第一阶段：云端基础

1. `cloud/app-shell`
   - 建 FastAPI 启动骨架、健康检查、路由装配。
   - 不做具体业务。

2. `cloud/shared`
   - 建数据库连接、配置、统一响应、错误处理、request_id、日志、鉴权依赖骨架。
   - 必须对齐 `shared-contract/API_INDEX.md` 和 `cloud/DATABASE_SCHEMA.md`。

3. `cloud/modules/auth-device`
   - 实现登录、刷新、退出、设备绑定。
   - 必须对齐 `shared-contract/openapi/auth-device.yaml`。

4. `cloud/modules/credits-billing`
   - 实现套餐权限、额度账户、额度流水、本地付费功能权限检查。
   - 必须先保证 `credit_accounts` 和 `credit_ledger` 写入边界清楚。

### 第二阶段：Provider 和 AI 基础

5. `cloud/modules/provider-runtime`
   - 实现 Provider 公共调用层。
   - 先做 `mock provider`，不要一开始接真实 OpenAI/DeepSeek。
   - 统一 usage、成本、错误码、超时、重试结构。

6. `cloud/modules/provider-log`
   - 实现 Provider 调用日志写入和查询。
   - 不返回完整 prompt、API Key、Token、原图隐私内容。

7. `cloud/modules/ai-copy`
   - 先通过 mock provider 实现文案生成闭环。
   - 通过权限检查、额度预检查、Provider Runtime、日志、扣费。

8. `cloud/modules/ai-render`
   - 先实现 mock 任务流。
   - 支持创建任务、查询任务状态。

9. `cloud/modules/ai-image-tools`
   - 先实现 mock 任务流。
   - 包含高清修复、转矢量、AI 改图、高级抠图、高级 OCR 的统一入口。

### 第三阶段：商业和后台

10. `cloud/modules/orders-recharge`
    - 订单和充值预留。
    - 未经用户确认，不接真实支付 SDK。

11. `cloud/admin/modules/admin-shell`
    - 后台入口、导航、权限框架。

12. `cloud/admin/modules/admin-users`
    - 用户和设备管理。

13. `cloud/admin/modules/admin-billing`
    - 套餐、订单、额度管理。

14. `cloud/admin/modules/admin-ops`
    - 调用记录、成本统计、风控日志、功能开关。

## 桌面端 CC 开发顺序

桌面端 CC 的工作目录主要在 `desktop/` 和 `local-worker/`。

### 第一阶段：桌面基础

1. `desktop/app-shell`
   - 建 WPF 原生主程序外壳。
   - 包含主窗口、导航、首页占位、模块入口占位。
   - 不做具体业务功能。

2. `desktop/shared`
   - 建桌面公共层。
   - 包含 auth 状态、cloud-api client、local-runtime client、file-system、job-system、logging、settings、ui-components。

3. `desktop/modules/auth-device`
   - 实现登录、退出、设备绑定状态展示。
   - 先接云端 mock API，再接真实 API。

4. `desktop/modules/file-workbench`
   - 实现文件拖拽导入、文件预览、最近文件、工作台基础流程。

5. `desktop/modules/job-system`
   - 实现任务状态、任务历史、失败重试、任务详情。

6. `desktop/modules/export-settings`
   - 实现导出、设置、日志查看、版本更新入口。
   - 自动更新依赖必须单独确认，不得擅自引入。

### 第二阶段：本地 worker 基础

7. `local-worker/shared`
   - 建本地 worker 公共层。
   - 包含进程协议、模型加载、文件 IO、错误结构、日志、CPU/GPU 检测。
   - Python 虚拟环境优先放到 `D:\localPath\venvs`。

8. `local-worker/modules/ocr`
   - 开发前先做 OCR 选型记录。
   - 候选：RapidOCR、PaddleOCR、Tesseract。
   - 模型和缓存放到 `D:\localPath\models` 或 `D:\localPath\caches`。

9. `desktop/modules/ocr`
   - 调用 `local-worker/modules/ocr`。
   - 只做 UI、任务流、结果展示和错误展示。

10. `local-worker/modules/preflight-check`
    - 实现印前检查基础项：尺寸、DPI、文件类型、透明通道、低清风险。

11. `desktop/modules/preflight-check`
    - 展示印前风险报告。

12. `local-worker/modules/id-photo`
    - 实现证件照换底色。

13. `desktop/modules/id-photo`
    - 实现底色选择、规格选择、导出。

14. `local-worker/modules/remove-bg`
    - 开发前先做抠图选型记录。
    - 候选：rembg、SAM、其他开源方案。

15. `desktop/modules/remove-bg`
    - 实现智能抠图入口、预览、结果保存。

### 第三阶段：本地付费工具

16. `local-worker/modules/resize-image`
    - 实现图片改尺寸本地处理。

17. `desktop/modules/resize-image`
    - 调用云端 `entitlements/check` 检查套餐权限。
    - 权限通过后再调用本地 worker。

18. `local-worker/modules/pdf-image-convert`
    - 实现 PDF/图片互转。

19. `desktop/modules/pdf-image-convert`
    - 调用云端权限检查。
    - 权限通过后再调用本地 worker。

20. `local-worker/modules/format-convert`
    - 实现格式转换、压缩、裁剪、旋转。

21. `desktop/modules/format-convert`
    - 实现对应 UI 和任务流。

### 第四阶段：云端 AI 桌面入口

22. `desktop/modules/ai-copy-client`
    - 调用 `/api/v1/ai/copy/generate`。
    - 展示文案结果、扣费、错误。

23. `desktop/modules/ai-render-client`
    - 调用 `/api/v1/ai/render/tasks` 创建任务。
    - 调用 `/api/v1/ai/render/tasks/{task_id}` 查询结果。

## 两台电脑并行规则

## 可以并行的组合

- 云端：`cloud/app-shell`  
  桌面端：`desktop/app-shell`

- 云端：`cloud/shared`  
  桌面端：`desktop/shared`

- 云端：`cloud/modules/auth-device`  
  桌面端：`desktop/modules/auth-device`
  前提：`shared-contract/modules/auth-device` 已完成。

- 云端：`cloud/modules/credits-billing`  
  桌面端：`desktop/modules/resize-image` 或 `desktop/modules/pdf-image-convert`
  前提：`shared-contract/modules/credits-billing` 和 `local-paid-tools` 已完成。

- 云端：`cloud/modules/ai-copy`  
  桌面端：`desktop/modules/ai-copy-client`
  前提：`shared-contract/modules/ai-copy` 已完成，云端至少有 mock API。

## 不建议并行的组合

- 未完成 shared-contract，就同时开发对应桌面端和云端业务。
- 未完成 `local-worker/shared`，就开发具体本地 worker 模块。
- 未完成 `desktop/shared`，就开发大量桌面业务模块。
- 未完成 `provider-runtime`，就开发真实云端 AI 模块。

## 常用术语

### shared-contract

桌面端和云端共同遵守的接口契约层。包括 OpenAPI、DTO、错误码、功能码、计费规则。

### OpenAPI

机器可校验的接口契约。路径在 `shared-contract/openapi/*.yaml`。接口字段变更必须先改 OpenAPI。

### DTO

Data Transfer Object，接口请求和响应的数据结构。DTO 必须以 OpenAPI 为来源，不能桌面端和云端各自发明字段。

### mock API

外形真实、内部模拟的 API。用于桌面端提前联调，不调用真实 Provider，不扣真实额度。

### app-shell

应用外壳。桌面端指 WPF 主窗口、导航、模块入口；云端指 FastAPI 启动、路由装配、中间件。

### shared

公共层。放所有模块都会用的能力，例如认证、日志、错误、配置、任务、文件、数据库。

### local-worker

本地处理引擎。负责 OCR、抠图、证件照、印前检查、图片改尺寸、PDF/图片互转等本地任务。

### Provider Runtime

云端 AI 公共调用层。所有 OpenAI、DeepSeek 或其他 AI Provider 调用必须经过它。

### Provider

第三方 AI 或自建 AI 服务，例如 OpenAI、DeepSeek、通义、火山、Replicate、自建 ComfyUI。

### provider_call_log

Provider 调用日志表。记录 provider、model、token、成本、扣费、延迟、错误码。

### credit_ledger

额度流水表。所有 AI 额度变化都必须写入这里。

### entitlement

套餐权限。用于判断用户是否能使用某个本地付费功能或云端 AI 功能。

### feature code

功能码。用于权限、计费、日志和统计，例如 `ocr_local`、`resize_image_local_paid`、`ai_copy_cloud`。

### client_request_id

桌面端生成的请求 ID，用于防止重复点击、重复提交和辅助排查。

### request_id

云端生成的请求追踪 ID。所有 API 响应都必须返回。

### idempotency

幂等。相同请求重复提交时，不能重复扣费或重复创建不可控任务。

### credits

AI 额度。用户看到的是额度，不直接看到 Provider 原始成本。

### estimated_cost

云端根据 Provider usage 计算的估算成本。客户端不得提交。

### credits_charged

云端最终扣除的 AI 额度。客户端不得提交。

### raw_usage_json

Provider 返回的原始 usage。只能服务端保存，不能返回给普通客户端。

## 用户给 CC 的推荐指令模板

### 云端模块

```text
进入 D:\Project\TT Tools，严格阅读 CLAUDE.md。
按照 cloud/modules/auth-device/TASK.md 开发当前模块。
不要开发其他模块。
如需下载或安装任何依赖，必须优先放到 D:\localPath，并更新 environment/INSTALLED_DEPENDENCIES.md 和 SETUP_HISTORY.md。
开发完成后运行测试，失败先定位根因再修复，最后提交推送并写中文备注。
完成后停止，等待我指定下一个模块。
```

### 桌面端模块

```text
进入 D:\Project\TT Tools，严格阅读 CLAUDE.md。
按照 desktop/modules/ocr/TASK.md 开发当前模块。
不要开发其他模块。
如需下载或安装任何依赖、模型或缓存，必须优先放到 D:\localPath，并更新 environment/INSTALLED_DEPENDENCIES.md、SETUP_HISTORY.md 和 MODEL_REGISTRY.md。
开发完成后运行测试，失败先定位根因再修复，最后提交推送并写中文备注。
完成后停止，等待我指定下一个模块。
```

