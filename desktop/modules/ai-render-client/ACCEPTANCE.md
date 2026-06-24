# ACCEPTANCE.md - desktop-ai-render-client

## 验收状态

`READY_FOR_REVIEW`

## 验收清单

- [x] 模块目标已实现：云端效果图生成桌面入口，调用 ai-render 契约并展示任务状态和结果。
- [x] 不包含禁止内容：无密钥、无模型大文件、无缓存、无构建产物、无跨模块修改、无绕过 shared-contract。
- [x] 测试记录已写入 PROGRESS.md：31 项单元测试全部通过。
- [x] 新依赖和模型已登记：无新增依赖（复用已登记的 .NET 8 + WPF + desktop-shared）。
- [x] 代码关键逻辑有中文注释：ViewModel、View、XAML 关键区域均有中文注释。

## 是否允许合并

是。待用户审查确认后合并。
