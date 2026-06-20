# ACCEPTANCE.md - contract-local-paid-tools

## 验收状态

`REVIEWED`

## 验收清单

- [x] 模块目标已实现：本地付费工具权限校验 API 契约已定义。
  - `shared-contract/openapi/local-paid-tools.yaml`：机器可校验 OpenAPI 契约。
  - `shared-contract/API_INDEX.md`：人读接口索引（Local Paid Tools 章节）。
  - `shared-contract/dto/python/local_paid_tools.py`：Python Pydantic DTO。
  - `shared-contract/dto/csharp/LocalPaidToolsDto.cs`：C# DTO。
- [x] 不包含禁止内容：无密钥、模型大文件、缓存、构建产物。
- [x] 测试记录已写入 PROGRESS.md：
  - Spectral OpenAPI lint：0 errors, 0 warnings。
  - Python DTO 契约一致性测试：36 passed, 0 failed。
- [x] 新依赖和模型已登记：本模块无新增依赖（ENVIRONMENT.md 已声明）。
- [x] 代码关键逻辑有中文注释：OpenAPI 所有 schema 和字段包含中文 description，DTO 包含中文注释。
- [x] 依赖模块 contract-base-rules 和 contract-credits-billing 均已 COMPLETED。

## 是否允许合并

是。本模块已完成开发、测试，具备合并条件。
