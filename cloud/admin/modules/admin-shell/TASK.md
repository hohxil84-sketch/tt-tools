# TASK.md - admin-shell

## 模块目标

后台基础入口、导航、权限框架和基础布局。

## 依赖模块

cloud-shared；cloud-auth-device。

## 允许修改目录

- `cloud/admin/modules/admin-shell`
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

