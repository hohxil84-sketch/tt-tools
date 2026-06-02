# TASK.md - desktop-ai-render-client

## 模块目标

云端效果图生成桌面入口，调用 ai-render 契约并展示任务状态和结果。

## 依赖模块

desktop-shared；contract-ai-render；cloud-ai-render。

## 允许修改目录

- `desktop/modules/ai-render-client`
- 与本模块明确相关的公共文档记录。

## 禁止内容

- 不开发用户未指定的其他模块。
- 不引入未登记依赖。
- 不提交密钥、模型大文件、缓存、构建产物。
- 不绕过 shared-contract 或公共层。

## 验收标准

- 模块目标已实现。
- 不包含禁止内容。
- 测试记录已写入 PROGRESS.md。
- 新依赖和模型已登记。
- 代码关键逻辑有中文注释。

