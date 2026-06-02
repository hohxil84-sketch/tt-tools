# DTO README

本目录用于保存由 OpenAPI 生成或人工维护的 DTO。

## 规则

- DTO 必须以 `shared-contract/openapi/*.yaml` 为来源。
- 手写 DTO 时必须注明对应 OpenAPI 文件和版本。
- 接口字段变更必须先改 OpenAPI，再更新 DTO。
- 桌面端和云端不得各自发明字段。

## 建议目录

```text
dto/
  csharp/
    README.md
  python/
    README.md
```

## 生成策略

首个契约模块开发时再决定具体生成工具。工具一旦确定，必须登记到：

- `environment/INSTALLED_DEPENDENCIES.md`
- `environment/SETUP_HISTORY.md`
- 对应 contract 模块的 `ENVIRONMENT.md`

