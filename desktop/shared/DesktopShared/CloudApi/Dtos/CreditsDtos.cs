using System.Text.Json.Serialization;

namespace TTShared.CloudApi.Dtos;

// ============ Credits / Billing DTOs（对应 OpenAPI credits-billing.yaml）============

/// <summary>额度余额</summary>
public class CreditBalanceDto
{
    [JsonPropertyName("user_id")]
    public string UserId { get; set; } = string.Empty;

    [JsonPropertyName("plan_code")]
    public string PlanCode { get; set; } = string.Empty;

    [JsonPropertyName("monthly_grant")]
    public int MonthlyGrant { get; set; }

    [JsonPropertyName("balance")]
    public int Balance { get; set; }

    [JsonPropertyName("period_start")]
    public string? PeriodStart { get; set; }

    [JsonPropertyName("period_end")]
    public string? PeriodEnd { get; set; }

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("updated_at")]
    public string UpdatedAt { get; set; } = string.Empty;
}

/// <summary>额度流水条目</summary>
public class CreditLedgerItemDto
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("change_type")]
    public string ChangeType { get; set; } = string.Empty;

    [JsonPropertyName("amount")]
    public int Amount { get; set; }

    [JsonPropertyName("balance_after")]
    public int BalanceAfter { get; set; }

    [JsonPropertyName("source_type")]
    public string SourceType { get; set; } = string.Empty;

    [JsonPropertyName("source_id")]
    public string? SourceId { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("created_at")]
    public string CreatedAt { get; set; } = string.Empty;
}

/// <summary>套餐权限检查请求</summary>
public class EntitlementCheckRequest
{
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    [JsonPropertyName("operation")]
    public string Operation { get; set; } = "single";

    [JsonPropertyName("client_request_id")]
    public string ClientRequestId { get; set; } = string.Empty;
}

/// <summary>套餐权限检查响应数据</summary>
public class EntitlementCheckData
{
    [JsonPropertyName("allowed")]
    public bool Allowed { get; set; }

    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    [JsonPropertyName("plan_code")]
    public string PlanCode { get; set; } = string.Empty;

    [JsonPropertyName("remaining_free_quota")]
    public int? RemainingFreeQuota { get; set; }

    [JsonPropertyName("reason")]
    public string? Reason { get; set; }
}
