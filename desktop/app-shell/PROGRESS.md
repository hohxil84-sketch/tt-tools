# PROGRESS.md - desktop-app-shell

## 当前状态

`DEVELOPMENT_COMPLETE`

## 分支

`feat/desktop-ui-v2-stage3`

## Bug 修复记录

日期：2026-06-29
分支：feat/desktop-ui-v2-stage3
提交：c47aebd
测试结果：DesktopAuthDevice.Tests 20/20 通过
说明：
- CommonStyles.xaml: 新增全局 WPF 渲染优化样式
- HomePage.xaml/cs: 按钮样式适配新图标
- 合并到 dev/full-product：3e80607..c47aebd

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

日期：2026-06-29
测试命令：dotnet build
结果：通过（0 个警告，0 个错误）
失败原因：无
修复提交：待用户验收后提交
分支：fix/wpf-rendering-sharpness
中文备注：WPF 渲染清晰度修复 — DPI感知+ClearType+像素对齐+矢量图标+强制方角

日期：2026-06-26
测试命令：dotnet build
结果：通过（0 个警告，0 个错误）
失败原因：无
修复提交：f0271f7
分支：fix/desktop-app-shell-titlebar
中文备注：修复标题栏系统按钮不可见、登录/主题按钮点击无效；替换应用图标；左上角新增图标显示
```

## WPF 渲染清晰度修复

### 窗口边缘毛刺 / 字体发糊 / 图标发虚修复

- **分支**：`fix/wpf-rendering-sharpness`
- **范围**：仅 MainWindow.xaml / MainWindow.xaml.cs / App.xaml / app.manifest / TTShell.csproj，不改 UI 布局，不改业务逻辑
- **现象**：窗口边缘毛刺、圆角倒刺、字体轻微发糊、图标发虚，在 125%/150% DPI 下尤为明显
- **根因分析**：
  1. 缺少 DPI 感知清单（无 app.manifest）—— WPF 以 96 DPI 渲染，Windows 对位图做缩放，导致整体发糊
  2. 缺少全局 ClearType 隐式样式（App.xaml）—— TextBlock/TextBox/Label 使用默认 Ideal 模式渲染文字
  3. MainWindow 缺少 UseLayoutRounding / SnapsToDevicePixels / TextOptions —— 像素未对齐
  4. ResizeBorderThickness=6 —— 125% DPI 下 = 7.5 物理像素，产生半像素边缘
  5. 系统按钮 Width=46 —— 125% DPI 下 = 57.5 物理像素
  6. 主题切换按钮使用 emoji（🌙/☀️）而非 Segoe MDL2 Assets 矢量图标 —— emoji 为彩色位图，在 WPF 中渲染模糊
  7. WindowChrome 未显式设置 CornerRadius=0 —— 系统可能尝试施加圆角处理
- **修复点**：
  1. 新建 `app.manifest` —— DPI 感知 `PerMonitorV2`
  2. `TTShell.csproj` —— 添加 `<ApplicationManifest>app.manifest</ApplicationManifest>`
  3. `App.xaml` —— 新增 TextBlock / TextBox / Label 全局隐式样式（Display + ClearType + Fixed）
  4. `MainWindow.xaml` Window 根 —— 添加 `UseLayoutRounding` / `SnapsToDevicePixels` / `TextOptions.TextFormattingMode=Display` / `TextOptions.TextRenderingMode=ClearType` / `TextOptions.TextHintingMode=Fixed`
  5. `MainWindow.xaml` WindowChrome —— `ResizeBorderThickness` 6→4（偶数值，所有常见 DPI 下精确对齐）+ `CornerRadius=0`（强制方角）
  6. `MainWindow.xaml` 系统按钮 —— 3 个按钮 Width 46→48（48 在 100%/125%/150% 下均为整数物理像素）
  7. `MainWindow.xaml` 主题切换按钮 —— emoji `🌙` → Segoe MDL2 Assets `&#xE708;`（矢量图标，任意 DPI 清晰），添加 `FontFamily="Segoe MDL2 Assets"`
  8. `MainWindow.xaml` 应用图标 —— 添加 `RenderOptions.BitmapScalingMode="HighQuality"`
  9. `MainWindow.xaml` 侧栏 Border —— 添加 `SnapsToDevicePixels` / `UseLayoutRounding`
  10. `MainWindow.xaml.cs` OnThemeToggle —— emoji `☀️/🌙` → Segoe MDL2 Assets `` / `` 矢量字符

### 按钮黑色虚线焦点框修复

- **现象**：点击按钮后出现黑色虚线焦点框（WPF 默认 FocusVisualStyle）
- **根因**：所有 Button 默认使用系统 FocusVisualStyle（黑色虚线圈），与 UI V2 现代设计冲突
- **修复方案**：全局禁用黑色虚线框 + ControlTemplate 内 Focused 触发器使用 PrimaryBrush 描边替代
- **修复点**：
  1. `App.xaml` —— 新增全局隐式 `<Style TargetType="Button">`，`FocusVisualStyle="{x:Null}"`（覆盖所有未使用命名样式的按钮，包括系统按钮、登录按钮、主题按钮及各模块内的普通按钮）
  2. `CommonStyles.xaml` `NavButtonStyle` —— 新增 `FocusVisualStyle="{x:Null}"` + ControlTemplate 内 Border 增加 `BorderBrush="Transparent" BorderThickness="2"` + `IsFocused` 触发器（键盘 Tab 时显示 PrimaryBrush 蓝色描边）
  3. `CommonStyles.xaml` `PrimaryButtonStyle` —— 同上模式
  4. `NavButtonSelectedStyle` —— 自动继承（BasedOn NavButtonStyle），无需重复设置
- **TODO（UI V2 Stage 1 合并后必须补充）**：以下 6 个样式当前在 `dev/full-product` 上尚不存在，合并后必须同样添加 `FocusVisualStyle="{x:Null}"` + ControlTemplate 内 `Focused` 触发器（PrimaryBrush 描边）：
  1. `SecondaryButtonStyle`
  2. `GhostButtonStyle`
  3. `DangerButtonStyle`
  4. `NavItemStyle`（如与 NavButtonStyle 不同）
  5. `ToolbarButtonStyle`
  6. `IconButtonStyle`

### 阶段 3：首页 Dashboard + 设备绑定页重构

- **分支**：`feat/desktop-ui-v2-stage3`
- **范围**：HomePage.xaml/.cs + DeviceStatusView.xaml/.cs + CommonStyles.xaml + LastCharsConverter.cs，不改业务逻辑
- **删除**：大扳手图标、"欢迎使用 Alphoria"、"版本 0.1.0 - 开发中"、"模块开发状态"、"即将开发"列表
- **HomePage Dashboard 改造**：
  1. 欢迎区："欢迎回来 👋" + "今天准备处理什么工作？"
  2. 快捷入口（UniformGrid 4 列）：OCR 文字识别 / 图片改尺寸 / 证件照 / 智能抠图，卡片可点击跳转
  3. 最近任务 Card + EmptyState（图标 + 标题 + 说明）
  4. 算力概览 Card：剩余算力 / 今日使用 / 本月使用（占位 "—"）
  5. 本地引擎状态 Card：OCR / 抠图 / 图片处理（绿色圆点 + 名称）
- **DeviceStatusView 重构**：
  1. 设备 ID 仅显示后 8 位（LastCharsConverter），悬停 ToolTip 显示完整 ID
  2. 新增"复制"按钮，点击复制完整设备 ID 到剪贴板，1.5s 反馈"已复制 ✓"
  3. 状态指示器颜色改用 DynamicResource（SuccessBrush / ErrorBrush / TextSecondaryBrush）
  4. 设备详情放入 SurfaceBrush 底色子卡片
  5. 所有按钮添加 FocusVisualStyle="{x:Null}"
- **CommonStyles 新增**：CardStyle / QuickActionCardStyle / SectionHeaderStyle / SubtitleTextStyle / EmptyState 系列（Border + Icon + Title + Desc）
- **新增文件**：`LastCharsConverter.cs`（字符串截尾 N 位转换器）

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
