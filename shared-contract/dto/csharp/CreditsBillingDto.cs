// credits_billing DTO — 套餐权限、额度余额、额度流水。
// 来源：shared-contract/openapi/credits-billing.yaml v0.1.0
// 生成方式：手写，以 OpenAPI 为唯一来源。

using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace TTShared.Contract.CreditsBilling;

// ============================================================
// 枚举
// ============================================================

/// <summary>额度变动类型</summary>
[JsonConverter(typeof(JsonStringEnumConverter))]
public enum ChangeType
{
    /// <summary>周期赠送</summary>
    grant,
    /// <summary>消费扣费</summary>
    consume,
    /// <summary>充值</summary>
    recharge,
    /// <summary>退款</summary>
    refund,
    /// <summary>管理员调整</summary>
    adjust
}

// ============================================================
// 通用结构
// ============================================================

/// <summary>统一错误详情</summary>
public class ErrorDetail
{
    /// <summary>统一错误码</summary>
    [JsonPropertyName("code")]
    public string Code { get; set; } = string.Empty;

    /// <summary>人类可读的错误描述（中文）</summary>
    [JsonPropertyName("message")]
    public string Message { get; set; } = string.Empty;

    /// <summary>可选补充信息</summary>
    [JsonPropertyName("details")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public Dictionary<string, object>? Details { get; set; }
}

/// <summary>统一 API 响应外层</summary>
public class ApiResponse<T>
{
    /// <summary>请求是否成功</summary>
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    /// <summary>业务数据载荷</summary>
    [JsonPropertyName("data")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public T? Data { get; set; }

    /// <summary>错误详情</summary>
    [JsonPropertyName("error")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ErrorDetail? Error { get; set; }

    /// <summary>云端生成的请求追踪 ID</summary>
    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = string.Empty;
}

// ============================================================
// 余额
// ============================================================

/// <summary>AI 额度账户余额信息</summary>
public class CreditBalance
{
    /// <summary>用户 ID</summary>
    [JsonPropertyName("user_id")]
    public Guid UserId { get; set; }

    /// <summary>当前套餐编码</summary>
    [JsonPropertyName("plan_code")]
    public string PlanCode { get; set; } = string.Empty;

    /// <summary>每计费周期赠送的 AI 额度</summary>
    [JsonPropertyName("monthly_grant")]
    public int MonthlyGrant { get; set; }

    /// <summary>当前可用 AI 额度余额</summary>
    [JsonPropertyName("balance")]
    public int Balance { get; set; }

    /// <summary>当前计费周期开始时间（UTC）</summary>
    [JsonPropertyName("period_start")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public DateTime? PeriodStart { get; set; }

    /// <summary>当前计费周期结束时间（UTC）</summary>
    [JsonPropertyName("period_end")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public DateTime? PeriodEnd { get; set; }

    /// <summary>账户状态（active / frozen）</summary>
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    /// <summary>余额最后更新时间（UTC）</summary>
    [JsonPropertyName("updated_at")]
    public DateTime UpdatedAt { get; set; }
}

/// <summary>额度余额查询响应（ApiResponse&lt;CreditBalance&gt; 别名）</summary>
public class CreditBalanceResponse : ApiResponse<CreditBalance> { }

// ============================================================
// 流水
// ============================================================

/// <summary>单条额度变动流水记录</summary>
public class CreditLedgerItem
{
    /// <summary>流水记录 ID</summary>
    [JsonPropertyName("id")]
    public Guid Id { get; set; }

    /// <summary>变动类型</summary>
    [JsonPropertyName("change_type")]
    [JsonConverter(typeof(JsonStringEnumConverter))]
    public ChangeType ChangeType { get; set; }

    /// <summary>变动额度值（正数为增加，负数为扣减）</summary>
    [JsonPropertyName("amount")]
    public int Amount { get; set; }

    /// <summary>变动后的账户余额</summary>
    [JsonPropertyName("balance_after")]
    public int BalanceAfter { get; set; }

    /// <summary>来源类型（provider_call / order / system / admin）</summary>
    [JsonPropertyName("source_type")]
    public string SourceType { get; set; } = string.Empty;

    /// <summary>来源记录 ID</summary>
    [JsonPropertyName("source_id")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public Guid? SourceId { get; set; }

    /// <summary>变动说明（中文）</summary>
    [JsonPropertyName("description")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Description { get; set; }

    /// <summary>流水记录创建时间（UTC）</summary>
    [JsonPropertyName("created_at")]
    public DateTime CreatedAt { get; set; }
}

/// <summary>额度流水分页数据</summary>
public class CreditLedgerData
{
    /// <summary>流水记录列表</summary>
    [JsonPropertyName("items")]
    public List<CreditLedgerItem> Items { get; set; } = new();

    /// <summary>符合条件的总记录数</summary>
    [JsonPropertyName("total")]
    public int Total { get; set; }

    /// <summary>当前页大小</summary>
    [JsonPropertyName("limit")]
    public int Limit { get; set; }

    /// <summary>当前偏移量</summary>
    [JsonPropertyName("offset")]
    public int Offset { get; set; }
}

/// <summary>额度流水查询响应（ApiResponse&lt;CreditLedgerData&gt; 别名）</summary>
public class CreditLedgerResponse : ApiResponse<CreditLedgerData> { }

// ============================================================
// 权限检查
// ============================================================

/// <summary>
/// 套餐权限检查请求 — 客户端不得提交 user_id、plan_code 等字段
/// </summary>
public class EntitlementCheckRequest
{
    /// <summary>功能码，例如 resize_image_local_paid</summary>
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    /// <summary>操作类型（single / batch 等）</summary>
    [JsonPropertyName("operation")]
    public string Operation { get; set; } = string.Empty;

    /// <summary>桌面端生成的请求追踪 ID，用于去重和幂等</summary>
    [JsonPropertyName("client_request_id")]
    public string ClientRequestId { get; set; } = string.Empty;
}

/// <summary>套餐权限检查结果</summary>
public class EntitlementCheckData
{
    /// <summary>是否允许使用指定功能</summary>
    [JsonPropertyName("allowed")]
    public bool Allowed { get; set; }

    /// <summary>检查的功能码</summary>
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    /// <summary>用户当前套餐编码</summary>
    [JsonPropertyName("plan_code")]
    public string PlanCode { get; set; } = string.Empty;

    /// <summary>免费套餐剩余免费额度</summary>
    [JsonPropertyName("remaining_free_quota")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? RemainingFreeQuota { get; set; }

    /// <summary>不允许时的拒绝原因（中文）</summary>
    [JsonPropertyName("reason")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Reason { get; set; }
}

/// <summary>套餐权限检查响应（ApiResponse&lt;EntitlementCheckData&gt; 别名）</summary>
public class EntitlementCheckResponse : ApiResponse<EntitlementCheckData> { }
