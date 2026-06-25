# PROGRESS.md - desktop-app-shell

## 当前状态

`DEVELOPMENT_COMPLETE`

## 分支

`feature/desktop-app-shell`

## 已完成

- 已创建模块文档骨架。
- .NET 8.0.421 SDK 已安装并验证（系统级安装，安装包存于 D:\localPath\downloads）。
- D:\localPath 目录结构已创建（downloads、tools、caches\nuget、venvs、models、logs）。
- NuGet 全局包缓存已配置到 D:\localPath\caches\nuget。
- WPF 项目 TTShell 已创建并编译通过。
- 主窗口布局：标题栏、导航侧栏（200px）、主内容区、状态栏。
- 导航系统：首页、文件工作台、AI 工具、导出、设置（各模块为占位页面）。
- 主题系统：浅色主题（LightTheme.xaml）和深色主题（DarkTheme.xaml），支持一键切换。
- 公共样式：导航按钮、主按钮、标题文字、占位文字、状态栏。
- 全局异常捕获：UI 线程异常和非 UI 线程异常统一处理。
- 窗口管理：最小化、最大化/还原、关闭、标题栏拖拽、双击最大化。
- 代码关键逻辑已写中文注释。

## 未完成

- 无（当前模块目标已全部实现）。

## 测试记录

```text
日期：2026-06-03
测试命令：dotnet build
结果：通过（0 个警告，0 个错误）
失败原因：无
修复提交：无
中文备注：WPF 主程序外壳编译通过，所有功能点均已实现

日期：2026-06-26
测试命令：dotnet build
结果：通过（0 个警告，0 个错误）
失败原因：无
修复提交：f0271f7
分支：fix/desktop-app-shell-titlebar
中文备注：修复标题栏系统按钮不可见、登录/主题按钮点击无效；替换应用图标；左上角新增图标显示
```

## Bug 记录

### WindowChrome 导致系统按钮不可见 + 自定义按钮无响应

- **现象**：右上角登录和主题切换按钮点击无效；最小化、还原、关闭三个系统按钮不可见
- **根因**：`WindowChrome` 的 `CaptionHeight="32"` 让 Windows 在 OS 层面拦截标题栏区域鼠标事件；`GlassFrameThickness="1"` 玻璃边框过窄，系统按钮无渲染空间
- **修复点**：
  1. `UseAeroCaptionButtons="False"` `CaptionHeight="0"` `GlassFrameThickness="0"` —— 完全由 WPF 控制标题栏
  2. 新增自定义最小化/最大化/关闭按钮，带悬停变色
  3. 左上角新增 18×18 应用图标
- **分支**：`fix/desktop-app-shell-titlebar`
- **提交**：f0271f7
- **测试命令**：`dotnet build`
- **测试结果**：0 警告 0 错误，编译通过

## 提交记录

- 2026-06-26 | f0271f7 | fix/desktop-app-shell-titlebar | 修复标题栏按钮 + 替换图标

## 下一步

等待用户验收并指定下一个模块。
