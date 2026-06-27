# AI 图片工具桌面端 — 进度记录

## 模块信息

- **模块名**: ai-image-tools-client
- **桌面端目录**: `desktop/modules/ai-image-tools-client/`
- **云端接口**: `POST/GET /api/v1/ai/image-tools/tasks`
- **契约文件**: `shared-contract/openapi/ai-image-tools.yaml`
- **功能码**: `upscale_image_cloud` / `vectorize_image_cloud` / `ai_edit_image_cloud` / `remove_bg_cloud` / `ocr_cloud`（各子功能独立控制）
- **分支**: `feature/desktop-ai-image-tools-client`

## 功能概述

桌面端云端 AI 图片工具入口模块，支持五种云端 AI 图片处理功能：

| 功能码 | 中文名 | 说明 |
|--------|--------|------|
| `upscale_image_cloud` | 高清修复 | 提升图片分辨率，增强清晰度 |
| `vectorize_image_cloud` | 转矢量 | 将位图转换为 SVG/PDF/EPS 矢量格式 |
| `ai_edit_image_cloud` | AI 改图 | 通过 AI 提示词编辑和修改图片内容 |
| `remove_bg_cloud` | 云端高级抠图 | 云端 AI 精准去除背景 |
| `ocr_cloud` | 云端高级 OCR | 云端 AI 文字识别，保留排版结构 |

## 实现要点

- 复用 `CloudApiClient.CreateAiImageToolTaskAsync` / `GetAiImageToolTaskAsync`
- 不直接调用第三方 AI，全部通过云端 provider-runtime
- 选择图片后只加入待处理列表，不自动提交
- 用户点击「开始处理」后才调用云端接口
- 创建任务前检查登录状态、套餐权限、积分余额
- 服务不可用、未登录、权限不足、积分不足时给出明确状态提示
- 任务提交后自动轮询状态（每 3 秒），实时更新
- 处理完成后展示结果文件、下载入口
- 高级 OCR 结果保留排版，多行展示（等宽字体）
- AI 改图提供 prompt 输入框
- 转矢量支持 SVG/PDF/EPS 格式选择
- 高清修复和高级抠图显示前后对比区域

## 测试覆盖

39 个测试全部通过，覆盖：

1. ✅ 未登录不能开始
2. ✅ 无权限不能开始（套餐不支持）
3. ✅ 积分不足不能开始
4. ✅ 选择文件不会自动处理
5. ✅ 点击开始才创建云端任务
6. ✅ 任务轮询成功后展示结果

额外覆盖：初始状态、命令绑定、功能选择、文件管理、属性变更、历史记录、清除重置、AI改图参数校验、服务不可用提示。

## 修改文件

| 文件 | 说明 |
|------|------|
| `desktop/modules/ai-image-tools-client/DesktopAiImageToolsClient/` | 新增模块 |
| `desktop/modules/ai-image-tools-client/DesktopAiImageToolsClient.Tests/` | 新增测试 |
| `desktop/app-shell/TTShell/MainWindow.xaml` | 添加「AI 图片工具」导航按钮 |
| `desktop/app-shell/TTShell/MainWindow.xaml.cs` | 添加导航路由和页面名 |
| `desktop/app-shell/TTShell/TTShell.csproj` | 添加项目引用 |

## 提交记录

| 提交 | 哈希 | 说明 |
|------|------|------|
| 首次实现 | `482d7f8` | feat(ai-image-tools-client): 新增桌面端云端 AI 图片工具入口模块，含 39 个测试全部通过 |
