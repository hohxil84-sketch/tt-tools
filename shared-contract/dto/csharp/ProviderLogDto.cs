// provider_log DTO — Provider 调用日志查询。
// 来源：shared-contract/openapi/provider-log.yaml v0.1.0
// 生成方式：手写，以 OpenAPI 为唯一来源。
//
// 不得返回完整 prompt、原图、API Key、Token、完整隐私内容。

using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace TTShared.Contract.ProviderLog;

// ============================================================
// 通用结构
// ============================================================

/// <summary>统一错误详情结构，与 common.yaml 保持一致</summary>
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

// ============================================================
// Provider 调用日志条目
// ============================================================

/// <summary>
/// Provider 调用日志条目，记录单次 AI Provider 调用的核心信息。
/// 不得包含完整 prompt、原图、API Key、Token、完整隐私内容。
/// </summary>
public class ProviderCallLogItem
{
    /// <summary>调用日志唯一 ID（UUID）</summary>
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    /// <summary>请求追踪 ID，用于全链路追踪</summary>
    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = string.Empty;

    /// <summary>功能码（如 ai_copy_cloud、ai_render_cloud、ai_image_tools_cloud）</summary>
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    /// <summary>AI Provider 名称（如 openai、deepseek、qwen）</summary>
    [JsonPropertyName("provider")]
    public string Provider { get; set; } = string.Empty;

    /// <summary>使用的模型名称（如 gpt-4o、deepseek-chat）</summary>
    [JsonPropertyName("model")]
    public string Model { get; set; } = string.Empty;

    /// <summary>调用状态（success / failed / timeout）</summary>
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    /// <summary>失败时的统一错误码（如 PROVIDER_TIMEOUT），成功时为 null</summary>
    [JsonPropertyName("error_code")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? ErrorCode { get; set; }

    /// <summary>输入 token 数量</summary>
    [JsonPropertyName("input_tokens")]
    public int InputTokens { get; set; }

    /// <summary>输出 token 数量</summary>
    [JsonPropertyName("output_tokens")]
    public int OutputTokens { get; set; }

    /// <summary>总 token 数量（input + output）</summary>
    [JsonPropertyName("total_tokens")]
    public int TotalTokens { get; set; }

    /// <summary>云端估算的调用成本（美元，仅供参考）</summary>
    [JsonPropertyName("estimated_cost")]
    public double EstimatedCost { get; set; }

    /// <summary>本次调用实际扣除的 AI 额度</summary>
    [JsonPropertyName("credits_charged")]
    public int CreditsCharged { get; set; }

    /// <summary>调用延迟（毫秒），超时时可能为 null</summary>
    [JsonPropertyName("latency_ms")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? LatencyMs { get; set; }

    /// <summary>调用发生时间（UTC，ISO 8601 格式）</summary>
    [JsonPropertyName("created_at")]
    public string CreatedAt { get; set; } = string.Empty;
}

// ============================================================
// 分页列表响应
// ============================================================

/// <summary>Provider 调用日志分页列表数据</summary>
public class ProviderCallLogListData
{
    /// <summary>当前页的调用日志条目列表</summary>
    [JsonPropertyName("items")]
    public List<ProviderCallLogItem> Items { get; set; } = new();

    /// <summary>符合条件的总记录数</summary>
    [JsonPropertyName("total")]
    public int Total { get; set; }

    /// <summary>当前每页条数</summary>
    [JsonPropertyName("limit")]
    public int Limit { get; set; }

    /// <summary>当前偏移量</summary>
    [JsonPropertyName("offset")]
    public int Offset { get; set; }
}

/// <summary>
/// Provider 调用日志查询响应。
/// 遵循统一响应结构（success / data / error / request_id）。
/// </summary>
public class ProviderCallLogListResponse
{
    /// <summary>请求是否成功</summary>
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    /// <summary>成功时返回分页列表数据，失败时为 null</summary>
    [JsonPropertyName("data")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ProviderCallLogListData? Data { get; set; }

    /// <summary>错误详情，成功时为 null</summary>
    [JsonPropertyName("error")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ErrorDetail? Error { get; set; }

    /// <summary>云端生成的请求追踪 ID</summary>
    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = string.Empty;
}
