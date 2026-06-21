# ACCEPTANCE.md - desktop-remove-bg

## 验收状态

`READY_FOR_REVIEW`

## 验收清单

- [x] 模块目标已实现：智能抠图桌面入口、预览、结果保存、调用 local-worker remove-bg。
- [x] 不包含禁止内容。
- [x] 测试记录已写入 PROGRESS.md。
- [x] 新依赖和模型已登记（无新增依赖，模型由 local-worker 管理）。
- [x] 代码关键逻辑有中文注释。

## 实现概览

- DesktopRemoveBg：net8.0-windows WPF 类库
- remove_bg_router.py：stdin/stdout JSON 协议路由脚本
- RemoveBgService：封装 LocalRuntimeClient 与 Python worker 通信
- RemoveBgViewModel：MVVM 模式，支持模型选择、Alpha Matting、背景合成、拖拽导入
- RemoveBgView：WPF UserControl，左右分栏布局（结果列表 + 详情预览）
- DesktopRemoveBg.Tests：36 项单元测试全部通过

## 是否允许合并

是。模块开发已完成，测试全部通过，可以合并到 dev/full-product。
