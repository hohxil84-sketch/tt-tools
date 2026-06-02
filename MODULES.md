# MODULES.md

| 模块 | 目录 | 类型 | 说明 |
|---|---|---|---|
| api-index | shared-contract/API_INDEX.md | 权威规格 | 云端 API 名称、请求字段、响应字段、错误码归属 |
| openapi-contracts | shared-contract/openapi/*.yaml | 机器契约 | 桌面端和云端共同遵守的 OpenAPI 文件 |
| contract-testing | shared-contract/CONTRACT_TESTING.md | 测试规则 | mock API、云端 API、桌面端 API client 的契约测试规则 |
| dto-rules | shared-contract/dto/README.md | DTO 规则 | DTO 生成或手写规则，必须以 OpenAPI 为来源 |
| database-schema | cloud/DATABASE_SCHEMA.md | 权威规格 | 云端数据库表、字段、索引、写入边界 |
| module-interfaces | docs/architecture/MODULE_INTERFACES.md | 权威规格 | 桌面端、本地 worker、云端模块之间的调用边界 |
| cc-development-order-and-terms | docs/development/CC_DEVELOPMENT_ORDER_AND_TERMS.md | 调度文档 | 两台 CC 的桌面端/云端开发顺序和常用术语 |
| desktop-app-shell | desktop/app-shell | 公共基础 | WPF 原生主程序外壳，负责启动、主窗口、导航、主题、基础布局和模块入口装配。 |
| desktop-shared | desktop/shared | 公共基础 | 桌面端公共层，包含认证状态、云端 API 客户端、本地 runtime 客户端、文件系统、任务系统、日志、设置和通用 UI 组件。 |
| desktop-auth-device | desktop/modules/auth-device | 业务模块 | 登录、退出、设备绑定状态展示，调用云端 auth/device 契约。 |
| desktop-file-workbench | desktop/modules/file-workbench | 业务模块 | 文件拖拽导入、文件预览、最近文件和工作台基础流程。 |
| desktop-job-system | desktop/modules/job-system | 业务模块 | 统一任务状态、任务历史、失败重试和任务详情。 |
| desktop-ocr | desktop/modules/ocr | 免费功能 | OCR 桌面入口、文件选择、结果展示、调用 local-worker OCR。 |
| desktop-remove-bg | desktop/modules/remove-bg | 免费功能 | 智能抠图桌面入口、预览、结果保存、调用 local-worker remove-bg。 |
| desktop-id-photo | desktop/modules/id-photo | 免费功能 | 证件照换底色桌面入口、底色选择、规格选择、导出。 |
| desktop-preflight-check | desktop/modules/preflight-check | 免费功能 | 印刷前检查桌面入口和风险报告展示。 |
| desktop-resize-image | desktop/modules/resize-image | 本地付费 | 图片改尺寸桌面入口，本地执行但需要套餐权限。 |
| desktop-pdf-image-convert | desktop/modules/pdf-image-convert | 本地付费 | PDF/图片互转桌面入口，本地执行但需要套餐权限。 |
| desktop-format-convert | desktop/modules/format-convert | 免费/付费混合 | 图片格式转换、压缩、裁剪、旋转入口。 |
| desktop-ai-copy-client | desktop/modules/ai-copy-client | 云端 AI 付费 | 云端文案生成桌面入口，调用 ai-copy 契约并展示扣费和结果。 |
| desktop-ai-render-client | desktop/modules/ai-render-client | 云端 AI 付费 | 云端效果图生成桌面入口，调用 ai-render 契约并展示任务状态和结果。 |
| desktop-export-settings | desktop/modules/export-settings | 基础功能 | 导出、设置、日志查看、版本更新入口。 |
| local-worker-shared | local-worker/shared | 公共基础 | 本地 worker 公共层，负责进程协议、模型加载、文件 IO、错误结构、日志和 CPU/GPU 能力检测。 |
| local-worker-ocr | local-worker/modules/ocr | 免费功能 | OCR 本地识别实现，候选 RapidOCR/PaddleOCR/Tesseract 需开发前选型并记录。 |
| local-worker-remove-bg | local-worker/modules/remove-bg | 免费功能 | 智能抠图本地实现，需选型 rembg/SAM/其他开源方案。 |
| local-worker-id-photo | local-worker/modules/id-photo | 免费功能 | 证件照换底色本地实现，依赖抠图或分割能力，支持常用底色和规格。 |
| local-worker-preflight-check | local-worker/modules/preflight-check | 免费功能 | 印前检查本地实现，检查尺寸、DPI、文件类型、透明通道、低清风险等基础项。 |
| local-worker-resize-image | local-worker/modules/resize-image | 本地付费 | 图片改尺寸本地实现，支持常见尺寸、比例、导出策略。 |
| local-worker-pdf-image-convert | local-worker/modules/pdf-image-convert | 本地付费 | PDF/图片互转本地实现，支持单文件和后续批量扩展。 |
| local-worker-format-convert | local-worker/modules/format-convert | 免费/付费混合 | 格式转换、压缩、裁剪、旋转本地实现。 |
| cloud-app-shell | cloud/app-shell | 公共基础 | FastAPI 云端启动、配置、路由装配、健康检查和基础中间件。 |
| cloud-shared | cloud/shared | 公共基础 | 云端公共层：数据库、鉴权依赖、权限、额度公共能力、错误响应、request_id、日志、配置。 |
| cloud-auth-device | cloud/modules/auth-device | 基础功能 | 登录、刷新、退出、设备绑定和设备状态服务。 |
| cloud-credits-billing | cloud/modules/credits-billing | 商业系统 | 套餐权限、额度账户、扣费、额度流水和本地付费功能权限检查。 |
| cloud-orders-recharge | cloud/modules/orders-recharge | 商业系统 | 订单、充值和支付预留，不直接接真实支付前必须有任务确认。 |
| cloud-provider-runtime | cloud/modules/provider-runtime | AI 公共层 | Provider 公共调用层，负责模型路由、调用、usage 解析、成本估算、错误标准化、mock provider。 |
| cloud-provider-log | cloud/modules/provider-log | 审计成本 | Provider 调用日志、成本记录、查询 API 和审计数据。 |
| cloud-ai-copy | cloud/modules/ai-copy | 云端 AI 付费 | 云端文案生成业务模块，必须通过 provider-runtime 调用模型并经过权限、额度、日志。 |
| cloud-ai-render | cloud/modules/ai-render | 云端 AI 付费 | 云端效果图生成业务模块，支持 mock 和后续真实图片 Provider。 |
| cloud-ai-image-tools | cloud/modules/ai-image-tools | 云端 AI 付费 | 高清修复、转矢量、AI 改图、云端高级抠图和高级 OCR 的云端模块。 |
| admin-shell | cloud/admin/modules/admin-shell | 后台基础 | 后台基础入口、导航、权限框架和基础布局。 |
| admin-users | cloud/admin/modules/admin-users | 后台管理 | 后台用户和设备管理。 |
| admin-billing | cloud/admin/modules/admin-billing | 后台管理 | 后台套餐、订单、额度管理。 |
| admin-ops | cloud/admin/modules/admin-ops | 后台管理 | 后台调用记录、成本统计、风控日志、功能开关。 |
| contract-base-rules | shared-contract/modules/base-rules | 契约基础 | 统一响应、错误结构、request_id、鉴权头、API 版本和通用规则。 |
| contract-auth-device | shared-contract/modules/auth-device | 接口契约 | 登录、刷新、退出、设备绑定 API 契约。 |
| contract-credits-billing | shared-contract/modules/credits-billing | 接口契约 | 套餐、额度、扣费、订单和流水 API 契约。 |
| contract-ai-copy | shared-contract/modules/ai-copy | 接口契约 | 云端文案生成 API 契约。 |
| contract-ai-render | shared-contract/modules/ai-render | 接口契约 | 云端效果图生成 API 契约。 |
| contract-ai-image-tools | shared-contract/modules/ai-image-tools | 接口契约 | 高级图片 AI API 契约。 |
| contract-provider-log | shared-contract/modules/provider-log | 接口契约 | Provider 调用日志查询 API 契约。 |
| contract-local-paid-tools | shared-contract/modules/local-paid-tools | 接口契约 | 本地付费工具权限校验 API 契约。 |

