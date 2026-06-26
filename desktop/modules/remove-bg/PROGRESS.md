# PROGRESS.md - desktop-remove-bg

## 当前状态

`DEVELOPED`

## 分支

`feature/desktop-remove-bg`

## 已完成

- 已创建模块文档骨架。
- 已创建 remove_bg_router.py Python 路由脚本（与 local-worker remove-bg 通信）。
- 已创建 DesktopRemoveBg C# 类库项目（net8.0-windows, WPF）。
- 已创建 Models/RemoveBgResult.cs 数据模型（含 RemoveBgModelInfo）。
- 已创建 Services/RemoveBgService.cs 服务层（封装 LocalRuntimeClient 通信）。
- 已创建 ViewModels/RemoveBgViewModel.cs（完整 MVVM 模式）。
- 已创建 Views/RemoveBgView.xaml 和 .xaml.cs（支持拖拽导入）。
- 已创建 DesktopRemoveBg.Tests 测试项目。
- 已创建 Services/RemoveBgServiceTests.cs（15 项测试）。
- 已创建 ViewModels/RemoveBgViewModelTests.cs（21 项测试）。
- 所有测试通过。

## 未完成

- 无。模块已开发完成。

## 测试记录

### 2026-06-21 第一次测试

```text
日期：2026-06-21
测试命令：cd DesktopRemoveBg.Tests && dotnet restore && dotnet build && dotnet test --no-build
结果：通过 (36/36)
失败原因：无
修复提交：无
中文备注：DesktopRemoveBg 主项目编译 0 错误 0 警告，测试项目 36 项全部通过。
测试覆盖：服务层构造、格式校验、默认参数、属性变更通知、命令可执行性、背景色设置、
        结果集合操作、进度值、状态消息等。
```

### 模块文件清单

```
desktop/modules/remove-bg/
├── README.md
├── TASK.md
├── ENVIRONMENT.md
├── DEVELOPMENT.md
├── TESTING.md
├── ACCEPTANCE.md
├── PROGRESS.md
├── NOTES.md
├── BUGFIX_RULES.md
├── COMMIT_RULES.md
├── DesktopRemoveBg/
│   ├── DesktopRemoveBg.csproj
│   ├── remove_bg_router.py
│   ├── remove_bg_models/         (本地 ONNX 模型，不提交 git)
│   ├── Models/
│   │   └── RemoveBgResult.cs
│   ├── Services/
│   │   ├── RemoveBgService.cs
│   │   └── Win32FolderBrowser.cs
│   ├── ViewModels/
│   │   └── RemoveBgViewModel.cs
│   └── Views/
│       ├── RemoveBgView.xaml
│       └── RemoveBgView.xaml.cs
└── DesktopRemoveBg.Tests/
    ├── DesktopRemoveBg.Tests.csproj
    ├── Services/
    │   └── RemoveBgServiceTests.cs
    └── ViewModels/
        └── RemoveBgViewModelTests.cs
```

## Bug 记录

### 2026-06-27 Bug 修复：引擎启动失败 + 超时 + 乱码 + 输出目录 + 失败结果显示 + 缩略图 + 按钮灰色 + 模型下拉空白

**分支**: `fix/remove-bg-init-and-layout`

**Bug 清单和修复**:

1. **引擎启动失败**: `RemoveBgService` 默认构造函数未创建 `_runtimeClient`，`StartAsync()` 直接返回 false。修复：默认构造函数中创建 `LocalRuntimeClient`。

2. **Worker 操作超时**: `rembg` 首次运行需下载 ONNX 模型（u2net 约 168MB），120 秒超时不够。修复：超时提升至 300 秒；添加 PYTHONIOENCODING=utf-8 环境变量；收集 stderr 用于诊断。

3. **处理详情乱码**: Python 子进程 stdout 使用系统默认编码（非 UTF-8）。修复：`sys.stdout.reconfigure(encoding='utf-8')` + `PYTHONIOENCODING=utf-8` + `PYTHONUNBUFFERED=1`。

4. **输出目录选择**: 缺少用户指定输出位置的功能。修复：新增 `Win32FolderBrowser`（P/Invoke）、`SelectOutputDirectoryCommand`、`GenerateOutputPath()`。

5. **抠图失败结果显示不正确**: XAML 模板中成功/失败信息重叠在同一 Grid.Row。修复：重构 DataTemplate，通过 DataTrigger 分离成功/失败显示。

6. **已选图片无缩略图**: `PendingFiles` 只存路径字符串，无可视化展示。修复：新增 `PendingFileInfo` 模型（含缩略图异步加载），XAML 增加待处理文件列表。

7. **"开始抠图"按钮灰色**: `IsServiceAvailable` 变化时未刷新 Command CanExecute。修复：setter 中调用 `RefreshCommandStates()`。

8. **模型下拉框空白**: Worker 启动失败时模型列表为空。修复：新增 `PopulateDefaultModels()` 硬编码兜底。

9. **本地模型打包**: 用户部署时需要内嵌 .onnx 模型文件避免联网下载。修复：新增 `remove_bg_models/` 目录，`processor.py` 支持 `models_dir` 参数优先本地加载，`.csproj` 随编译复制。

**涉及文件**: 12 个文件，+835/-220 行
- .gitignore
- desktop/app-shell/TTShell/MainWindow.xaml.cs
- desktop/modules/remove-bg/DesktopRemoveBg/DesktopRemoveBg.csproj
- desktop/modules/remove-bg/DesktopRemoveBg/Models/RemoveBgResult.cs
- desktop/modules/remove-bg/DesktopRemoveBg/Services/RemoveBgService.cs
- desktop/modules/remove-bg/DesktopRemoveBg/Services/Win32FolderBrowser.cs (新建)
- desktop/modules/remove-bg/DesktopRemoveBg/ViewModels/RemoveBgViewModel.cs
- desktop/modules/remove-bg/DesktopRemoveBg/Views/RemoveBgView.xaml
- desktop/modules/remove-bg/DesktopRemoveBg/remove_bg_router.py
- desktop/modules/remove-bg/DesktopRemoveBg.Tests/ViewModels/RemoveBgViewModelTests.cs
- desktop/shared/DesktopShared/LocalRuntime/LocalRuntimeClient.cs
- local-worker/modules/remove-bg/processor.py

## 提交记录

- 2026-06-21: `70c282d` — feat(desktop-remove-bg): 完成智能抠图桌面入口模块，36 项测试全部通过，已推送到 origin/feature/desktop-remove-bg
- 2026-06-27: `5232f45` — fix(remove-bg): 修复引擎启动、超时、乱码、输出目录选择、失败结果显示、缩略图缺失、按钮灰色、模型下拉空白、本地模型打包，46 项测试全部通过，已推送到 origin/fix/remove-bg-init-and-layout

## 下一步

提交并推送到 origin，等待用户确认合并到 dev/full-product。
