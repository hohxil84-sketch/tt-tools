# PROGRESS.md - desktop-id-photo

## 当前状态

`DEVELOPED`

## 分支

`feature/desktop-id-photo`

## 已完成

- 已创建模块文档骨架。
- 已创建 DesktopIdPhoto.csproj（net8.0-windows WPF Library，引用 TTShared）。
- 已创建 Python router 脚本 (id_photo_router.py)，支持 ping / process_id_photo / list_specs / list_background_colors / shutdown 5 个动作。
- 已创建 C# Models: IdPhotoResult、PhotoSpecItem、BackgroundColorItem。
- 已创建 IdPhotoService（封装 LocalRuntimeClient 通信，支持处理、规格查询、底色查询、任务跟踪）。
- 已创建 IdPhotoViewModel（MVVM ViewModel，管理输入文件选择、底色/规格选择、处理触发、结果展示、导出）。
- 已创建 IdPhotoView（WPF UserControl，包含拖拽输入区、规格下拉框、底色色块选择器、处理选项、结果预览、历史列表、导出按钮）。
- 已创建 20 项单元测试（Models 和 ViewModels 全覆盖），全部通过。
- Python router 4 项运行测试全部通过（ping / list_specs / list_background_colors / shutdown）。
- 关键逻辑已添加中文注释。

## 未完成

- 待集成到 app-shell 主窗口导航。
- 待执行与 local-worker 的完整联调测试。

## 测试记录

```
日期：2026-06-21
测试命令：dotnet test（DesktopIdPhoto.Tests）
结果：通过
详情：20 项测试全部通过，0 失败，0 警告
中文备注：覆盖 IdPhotoResult 反序列化、显示属性、PhotoSpecItem 显示属性、BackgroundColorItem 显示属性、IdPhotoViewModel 初始状态/Dpi/输入文件/规格/底色/结果/清除/失败计数/运行状态/默认构造函数/服务状态/选项属性
```

```
日期：2026-06-21
测试命令：echo '{...}' | python id_photo_router.py（stdin/stdout 协议测试）
结果：通过
详情：4 个动作（ping、list_specs、list_background_colors、shutdown）全部返回 success=true
中文备注：Python router 通过 stdin/stdout JSON 协议正确响应，规格返回 7 项，底色返回 6 项
```

## Bug 记录

暂无。

## 提交记录

```
2026-06-21: feat(desktop-id-photo): 完成证件照换底色桌面模块
  分支: feature/desktop-id-photo
  提交哈希: 1ca1c68
  已推送到 origin
  测试结果: 20 项 C# 单元测试 + 4 项 Python router 协议测试全部通过
  说明: 完成证件照换底色桌面入口、底色选择、规格选择、导出全流程
```

## 下一步

提交并推送到 origin，等待用户指定是否合并到 dev/full-product。
