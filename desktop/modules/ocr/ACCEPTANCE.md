# ACCEPTANCE.md - desktop-ocr

## 验收状态

`REVIEWED`

## 验收清单

- [x] 模块目标已实现：OCR 桌面入口、文件选择、结果展示、调用 local-worker OCR。
- [x] 不包含禁止内容：无密钥、无模型文件、无跨模块修改、无第三方 AI 直接调用。
- [x] 测试记录已写入 PROGRESS.md：33 项全部通过。
- [x] 新依赖和模型已登记：本模块未新增依赖，全部使用已有依赖（desktop-shared、desktop-job-system、local-worker-ocr）。
- [x] 代码关键逻辑有中文注释：所有 ViewModel、Service、Model、View 文件均有中文注释。

## 是否允许合并

是。模块开发完成，测试通过，无禁止内容，可合并到 dev/full-product。
