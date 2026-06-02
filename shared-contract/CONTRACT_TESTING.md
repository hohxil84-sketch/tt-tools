# CONTRACT_TESTING.md

本文件定义桌面端和云端并行开发的契约测试规则。

## 核心原则

- 接口变更必须先改 `shared-contract/openapi/*.yaml`。
- `shared-contract/API_INDEX.md` 是人读索引，`openapi/*.yaml` 是机器校验契约。
- 云端 mock API、真实 API、桌面端 API client 都必须对齐 OpenAPI。
- 未通过契约测试的模块不得提交合并。

## 标准流程

```text
1. 修改 shared-contract/openapi/*.yaml
2. 更新 shared-contract/API_INDEX.md
3. 更新 shared-contract/dto/README.md 或生成 DTO
4. 云端按 OpenAPI 实现 mock API
5. 桌面端按 OpenAPI 实现 API client
6. 运行契约测试
7. 契约测试通过后再接真实业务逻辑
```

## 云端必须验证

- 响应必须包含 `success`、`data`、`error`、`request_id`。
- 错误响应必须使用统一错误结构。
- 不得返回 OpenAPI 未定义字段，除非先更新契约。
- 不得返回完整 prompt、API Key、Token、原图隐私内容。
- 客户端禁止提交的字段必须被忽略或拒绝。

## 桌面端必须验证

- API client 请求字段必须来自 OpenAPI。
- 响应 DTO 必须覆盖 OpenAPI 定义字段。
- 错误处理必须使用统一错误码。
- 不得假设云端返回 OpenAPI 未定义字段。

## Mock API 规则

- mock API 的路径、字段、错误结构必须与 OpenAPI 一致。
- mock API 可返回固定结果，但不得改变字段名。
- mock API 不扣真实额度、不调用真实 Provider。

## 建议测试命令

具体工具由首个 contract 模块确定，确定后必须登记到 `environment/INSTALLED_DEPENDENCIES.md`。

下载安装包、CLI 工具、缓存和临时文件必须优先放到 `D:\localPath`，不得默认下载到系统盘、用户目录或模块目录。

候选工具：

- OpenAPI lint：Spectral 或 Redocly CLI
- Python schema 校验：openapi-spec-validator
- 云端响应校验：pytest + jsonschema
- 桌面端 DTO 校验：.NET 单元测试

## 合并门槛

涉及接口的模块合并前必须记录：

- 修改了哪些 OpenAPI 文件。
- 是否更新 API_INDEX.md。
- 云端 mock API 是否通过契约测试。
- 桌面端 API client 是否通过契约测试。
- 是否存在兼容性破坏。
