# PROGRESS.md - desktop-preflight-check

## 当前状态

`DEVELOPMENT_COMPLETE`

## 分支

`feature/desktop-preflight-check`

## 已完成

- 已创建模块文档骨架。
- 已创建目录结构：Models、Services、ViewModels、Views。
- 实现 preflight_check_router.py：Python stdin/stdout JSON 路由脚本，桥接 local-worker PreflightChecker。
- 实现 Models/PreflightCheckModels.cs：PreflightCheckReport / PreflightCheckResultItem / RiskLevel / CheckItemType 数据结构及 FromRouterResponse 静态解析。
- 实现 Services/PreflightCheckService.cs：封装 LocalRuntimeClient，提供单文件检查 (CheckAsync)、批量检查 (CheckBatchAsync)、带任务跟踪检查 (CheckWithJobTrackingAsync)。
- 实现 ViewModels/PreflightCheckViewModel.cs：MVVM 主 ViewModel，管理文件选择、检查触发、报告展示、拖放支持、复制报告。
- 实现 Views/PreflightCheckView.xaml：WPF 风险报告展示界面，含左侧报告列表和右侧检查详情，风险等级颜色编码。
- 实现 Views/PreflightCheckView.xaml.cs：代码后置，含拖放支持和 3 个值转换器（RiskToIconConverter、RiskToForegroundConverter、RiskToBackgroundConverter）。
- 实现 21 项单元测试全部通过（Models 5 项 + ViewModels 8 项 + Services 8 项）。
- 无新增依赖（复用 desktop-shared 已有的 NuGet 包和 local-worker-preflight-check 的 Python venv）。

## 未完成

- 需在 app-shell 集成后验证完整 UI 交互流程。
- 待用户指定合并到 dev/full-product。

## 测试记录

日期：2026-06-20
测试命令：dotnet test desktop/modules/preflight-check/DesktopPreflightCheck.Tests/DesktopPreflightCheck.Tests.csproj -v q
结果：21 passed, 0 failed
测试覆盖：
- PreflightCheckReport.FromRouterResponse 完整 JSON 解析
- CreateFailedReport 工厂方法
- 7 项检查项的 ItemDisplayName 中文名称
- RiskLevelDisplay 风险等级中文文本
- Report 展示属性计算
- ViewModel 初始状态
- ViewModel 默认构造函数和命令创建
- SelectedReport 派生属性更新
- ClearReports 状态重置
- Reports 风险统计（pass/warning/error）
- IsRunning → CanStart/CanCancel 联动
- ServiceStatusText 服务状态文本
- HasError 逻辑
- PreflightCheckService 构造函数
- SupportedFormats 格式列表
- IsFormatSupported 格式校验
- 服务未启动时 CheckAsync 异常
- Dispose 资源释放
- CheckerName 名称属性

## Bug 记录

- FromRouterResponse 测试中 PassCount 期望值错误（5→6）→ 已修复

## 提交记录

- `7460380` feat(desktop-preflight-check): 完成印前检查桌面入口和风险报告展示
  - 13 files changed, 2523 insertions(+), 18 deletions(-)
  - 21 项单元测试全部通过
  - 分支已推送到 origin

## 下一步

等待用户指示合并到 dev/full-product。
