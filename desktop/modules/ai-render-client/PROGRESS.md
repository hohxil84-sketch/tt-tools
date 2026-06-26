# PROGRESS.md - desktop-ai-render-client

## 当前状态

`DEVELOPMENT_COMPLETE`

## 分支

`feature/desktop-ai-render-client`

## 已完成

- 已创建模块文档骨架。
- 已创建 WPF 类库项目 DesktopAiRenderClient（net8.0-windows）。
- 已实现 AiRenderViewModel：场景类型选择、提示词输入、文件 ID 输入、风格/尺寸选择、任务创建、状态轮询、结果展示、历史记录。
- 已实现 AiRenderView.xaml：左右布局（输入/结果），包含工具栏、错误提示、任务状态区、结果文件列表、历史列表、状态栏。
- 已创建 xunit 测试项目 DesktopAiRenderClient.Tests，31 项测试全部通过。
- 已引入 MockHttpMessageHandler 支持 API 模拟测试。
- 代码关键逻辑均有中文注释。

## 未完成

- 无。

## 测试记录

```
日期：2026-06-24
测试命令：dotnet test desktop/modules/ai-render-client/DesktopAiRenderClient.Tests/DesktopAiRenderClient.Tests.csproj --configuration Release
结果：通过 - 31 项测试全部通过，0 失败，0 跳过
中文备注：覆盖初始状态、命令绑定、参数校验、属性变更通知、任务创建（含 Mock API 联调）、状态展示、清除行为、历史记录项显示属性、集合变更通知、历史项选择恢复
```

## Bug 记录

### 2026-06-26：下拉框空白 + 图片无预览 + 结果被清空 + 无下载按钮

- **分支**：`fix/ai-render-client-multi-fix`
- **提交**：31b5bc6
- **现象**：
  1. 场景类型/风格/尺寸三个下拉框全部空白
  2. 生成的图片没有缩略图预览，点击提示"暂无预览链接"
  3. 生成第二张图片时，第一张图片从结果区消失
  4. 没有手动保存/下载图片的按钮
- **根因**：
  1. `List<(string Value, string Display)>` 是 C# 命名元组，运行时属性为 Item1/Item2，WPF DisplayMemberPath 反射找不到
  2. 结果区为文字列表，无图片控件；Mock 阶段 URL 为 null
  3. `CreateTaskAsync` 和 `SelectHistoryItem` 无脑 `ResultFiles.Clear()`，且历史项不恢复已完成任务的结果
  4. 仅有自动下载到固定目录，无用户可见的保存操作
- **修复**：
  1. 新增 `record ComboOption(string Value, string Display)`，下拉框列表改为 `List<ComboOption>`
  2. 结果区改为 144px 缩略图网格（WrapPanel + Image 异步加载）+ 全屏大图预览弹窗
  3. 移除不必要的 Clear()，SelectHistoryItem 始终调用 QueryAndUpdateTaskStatus 恢复结果
  4. 新增 💾 另存为按钮（SaveFileDialog）/ 📁 打开目录按钮
  5. 新增 `DownloadToLocalAsync` 自动下载图片到 `%LOCALAPPDATA%\TTTools\ai-render-output\`
  6. 新增 `UrlToBitmapConverter` 支持 URL/本地路径 → BitmapImage
- **编译**：0 错误

## 提交记录

- 提交哈希：d7b0690
- 分支：feature/desktop-ai-render-client
- 提交信息：feat(desktop-ai-render-client): 完成云端效果图生成桌面入口
- 测试结果：31 项测试全部通过，0 失败，0 跳过
- 推送状态：已推送到 origin/feature/desktop-ai-render-client

## 下一步

等待用户指定下一模块。
