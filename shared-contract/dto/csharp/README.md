# C# DTO

以 `shared-contract/openapi/credits-billing.yaml` v0.1.0 为来源，手写 C# 类型。

## 生成策略

- 方式：手写，严格对齐 OpenAPI。
- 序列化：System.Text.Json，JsonPropertyName 映射。
- 命名空间：`TTShared.Contract.CreditsBilling`
- 首个引入模块：`contract-credits-billing`。

## 依赖

- .NET 8（桌面端已安装，见 environment/INSTALLED_DEPENDENCIES.md）
- System.Text.Json（.NET 内置）

## 使用示例

```csharp
using System.Text.Json;
using TTShared.Contract.CreditsBilling;

var response = JsonSerializer.Deserialize<CreditBalanceResponse>(json);
Console.WriteLine(response.Data.Balance);
```
