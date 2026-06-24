# PROGRESS.md - desktop-ai-copy-client

## 当前状态

`IN_PROGRESS` — 核心功能已实现，测试通过，待合并。

## 分支

`feature/desktop-ai-copy-client`

## 已完成

- 已创建模块文档骨架。
- 已创建 DesktopAiCopyClient.csproj 并引用 DesktopShared。
- 已实现 AiCopyViewModel：
  - 场景类型预设（8种：海报、传单、社交媒体、微信、小红书、抖音、邮件、网站）。
  - 语气预设（6种：直接、专业、亲切、幽默、紧迫、温暖）。
  - 平台预设（8种：线下海报、微信朋友圈、小红书、抖音、微博、邮件、网站、印刷）。
  - 核心卖点管理（添加 / 删除 / 去重 / Enter 键支持）。
  - 调用 CloudApiClient.GenerateAiCopyAsync() 生成文案。
  - 检查登录状态，未登录时提示用户。
  - 线程安全的 UI 更新（Dispatcher.Invoke）。
  - 结果展示：主文案、变体列表、Provider/Model/扣费/成本信息。
  - 文案历史记录（保存最近生成结果，可点击回看）。
  - 复制文案到剪贴板。
  - 清空输入和结果。
  - 取消生成。
  - 所有关键逻辑已添加中文注释。
- 已实现 AiCopyView.xaml + AiCopyView.xaml.cs：
  - 左右分栏布局：左侧输入表单 / 右侧结果+历史。
  - 错误提示条（可关闭）。
  - 状态栏（加载指示器 / 状态消息 / Provider Call ID）。
  - 动态主题资源绑定（DynamicResource）。
- 已创建 DesktopAiCopyClient.Tests 测试项目（xUnit）：
  - 28 个测试全部通过。
  - 覆盖：初始状态、命令绑定、属性变更通知、卖点增删、生成流程（Mock API）、清除行为、历史记录显示属性。
- 模块无需新增 NuGet 依赖（复用 DesktopShared 已有能力）。
- 模块无需新增 Python 虚拟环境或本地 worker（纯云端调用）。

## 未完成

- 模块尚未集成到 app-shell 导航（app-shell 不在本模块允许修改范围内）。

## 测试记录

日期：2026-06-24
测试命令：dotnet test --configuration Release
结果：28 passed, 0 failed, 0 skipped
中文备注：全部单元测试通过，覆盖 ViewModel 初始状态、命令绑定、参数管理、卖点增删、生成流程 Mock、清除和重置、历史记录显示。

## Bug 记录

暂无。

## 提交记录

- `30a54d9` — feat(desktop-ai-copy-client): 完成云端文案生成桌面入口
  - 分支：feature/desktop-ai-copy-client
  - 测试结果：28 passed, 0 failed, 0 skipped
  - 中文备注：模块核心功能完成，所有单元测试通过，已推送到 origin。

## 下一步

提交、推送 feature/desktop-ai-copy-client，等待合并到 dev/full-product。
