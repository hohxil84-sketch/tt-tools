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

- 方式：手写，严格对齐 OpenAPI。
- 首个引入模块：`contract-credits-billing`。
- Python：Pydantic >= 2.0 模型，使用 `model_validate_json` 反序列化。
- C#：System.Text.Json 序列化，`JsonPropertyName` 映射，命名空间 `TTShared.Contract.*`。

## 已登记模块

| 模块 | Python DTO | C# DTO | OpenAPI 来源 | 状态 |
|------|------------|--------|-------------|------|
| local-paid-tools | dto/python/local_paid_tools.py | dto/csharp/LocalPaidToolsDto.cs | local-paid-tools.yaml v0.1.0 | completed |
| provider-log | dto/python/provider_log.py | dto/csharp/ProviderLogDto.cs | provider-log.yaml v0.1.0 | completed |
| ai-copy | dto/python/ai_copy.py | dto/csharp/AiCopyDto.cs | ai-copy.yaml v0.1.0 | completed |

