# PROGRESS.md - desktop-pdf-image-convert

## 当前状态

`DEVELOPMENT_COMPLETE`

## 分支

`feature/desktop-pdf-image-convert`

## 已完成

- 已创建模块文档骨架。
- 已创建 Python router 脚本 `pdf_image_convert_router.py`（stdin/stdout JSON 协议）。
- 已创建 C# 项目 `DesktopPdfImageConvert`（net8.0-windows WPF Library）。
- 已创建 Models：PdfImageConvertParams、PdfImageConvertResult、PageResult。
- 已创建 Service：PdfImageConvertService（含套餐权限校验 + LocalRuntimeClient 通信）。
- 已创建 ViewModel：PdfImageConvertViewModel（含完整 UI 状态管理和命令绑定）。
- 已创建 View：PdfImageConvertView（XAML + code-behind，支持拖拽）。
- 已创建测试项目 `DesktopPdfImageConvert.Tests`。
- 已创建 PdfImageConvertServiceTests（覆盖构造/null校验/格式校验/权限拒绝/未登录/401/文件不存在/不支持的格式/Dispose/初始状态/FromRouterResponse 解析等 25 项测试）。
- 已确认不新增 NuGet 依赖（复用 DesktopShared 现有依赖）。

## 未完成

- 无。

## 测试记录

日期：2026-06-24
测试命令：dotnet test DesktopPdfImageConvert.Tests.csproj
结果：25 通过，0 失败，0 跳过
失败原因：无
修复提交：无
中文备注：全部 25 项单元测试通过，覆盖权限 fail closed 所有场景、格式校验、模型解析、构造函数校验等

## Bug 记录

暂无。

## 提交记录

| 哈希 | 说明 | 测试结果 |
|---|---|---|
| ad0440c | feat(desktop-pdf-image-convert): 完成桌面端 PDF/图片互转入口 | 25 通过 / 0 失败 |

## 下一步

提交、推送，更新全局 PROGRESS.md，合并到 dev/full-product。
