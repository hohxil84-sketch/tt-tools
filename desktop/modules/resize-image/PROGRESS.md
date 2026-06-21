# PROGRESS.md - desktop-resize-image

## 当前状态

`DEVELOPMENT_COMPLETE`

## 分支

`feature/desktop-resize-image`

## 已完成

- 已创建项目结构和 csproj 文件（DesktopResizeImage + DesktopResizeImage.Tests）
- 已实现 Python bridge（resize_image_router.py）：ping / resize / list_presets / shutdown，stdin/stdout JSON 协议
- 已实现 Models：ResizeImageParams（C# 侧参数映射）、ResizeImageResult（处理结果 + 权限信息）、PresetInfo（预设尺寸 DTO）
- 已实现 ResizeImageService：组合 CloudApiClient 权限校验 + LocalRuntimeClient worker 通信
  - 权限 fail closed：未登录/网络错误/401/null/Allowed=false 全部拒绝
  - 每次 resize 前调用 CheckEntitlementAsync("resize_image_local_paid", "single")
  - 权限拒绝时不启动 worker、不创建输出文件
  - ProcessWithJobTrackingAsync：权限拒绝标记 Failed，worker 失败标记 Failed，成功标记 Succeeded
- 已实现 ResizeImageViewModel：7 种缩放模式、20 个预设尺寸、条件可见性、权限状态、文件选择和拖拽
- 已实现 ResizeImageView.xaml + .xaml.cs：WPF 界面含参数配置、结果列表、详情预览、拖拽支持
- 已实现单元测试：
  - ResizeImageResultTests（12 项）
  - ResizeImageServiceTests（18 项，含权限拒绝/401/null/未登录等 fail closed 场景）
  - ResizeImageViewModelTests（24 项，含模式切换可见性、预设选择、边界检查）
- Python bridge smoke tests 全部通过（ping / list_presets / resize with preset / resize invalid path）
- 关键逻辑已添加中文注释
- 无新依赖（Python venv 和 .NET SDK 已存在）

## 未完成

- C5: 已注册到桌面壳（TTShell 引用 DesktopResizeImage，导航栏增加"图片改尺寸"入口）。
  - 壳层暂无统一 AuthState/CloudApiClient 注入机制，当前使用 ViewModel 默认构造函数（IsServiceAvailable=false）。
  - 剩余集成项：待壳层统一 DI 就位后，将默认构造函数替换为带参构造函数（注入 ResizeImageService + AuthState + CloudApiClient）。

## 测试记录

日期：2026-06-21
测试命令：dotnet test desktop/modules/resize-image/DesktopResizeImage.Tests/DesktopResizeImage.Tests.csproj -v normal
结果：54 passed，0 failed
失败原因：无
中文备注：覆盖模型默认值/显示属性/JSON反序列化、Service构造函数null校验/格式校验/权限拒绝5场景（Allowed=false/401/null response/未登录/文件不存在/格式不支持）、ViewModel初始状态/7种模式可见性/预设选择/命令创建/边界Clamp/CanStart-CanCancel/PropertyChanged通知/BuildParamsFromUI。

日期：2026-06-21
测试命令：Python bridge smoke tests（ping / list_presets / resize with preset / resize invalid path）
结果：4 passed
中文备注：ping 返回 7 modes + 6 filters + 20 presets，list_presets 返回正确预设，resize with id_1inch 正确缩放到 295x221，resize invalid path 返回错误。

## Bug 记录

暂无。

## 提交记录

- 2026-06-21：`7ffc118` — feat(desktop-resize-image): 完成图片改尺寸桌面入口模块，54 项 C# 单测 + 4 项 Python bridge smoke tests 全部通过。
- 2026-06-21：C5 壳层注册 — TTShell.csproj 引用 DesktopResizeImage，MainWindow.xaml 增加导航按钮，MainWindow.xaml.cs switch 增加 ResizeImageView 入口。

## 下一步

提交推送，等待用户指定后续操作。
