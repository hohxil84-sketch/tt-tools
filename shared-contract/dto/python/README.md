# Python DTO

以 `shared-contract/openapi/credits-billing.yaml` v0.1.0 为来源，手写 Pydantic 模型。

## 生成策略

- 方式：手写，严格对齐 OpenAPI。
- 工具：无自动生成工具，保持简单可控。
- 首个引入模块：`contract-credits-billing`。

## 依赖

- pydantic >= 2.0（云端已安装，见 environment/INSTALLED_DEPENDENCIES.md）

## 使用示例

```python
from shared_contract.dto.python import CreditBalanceResponse

# 反序列化云端响应
resp = CreditBalanceResponse.model_validate_json(response_text)
print(resp.data.balance)
```
