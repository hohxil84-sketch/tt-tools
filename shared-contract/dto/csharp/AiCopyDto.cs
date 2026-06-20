// ai_copy DTO — 云端文案生成 API 契约。
// 来源：shared-contract/openapi/ai-copy.yaml v0.1.0
// 生成方式：手写，以 OpenAPI 为唯一来源。
//
// 客户端不得提交 provider、model、estimated_cost、credits_charged 等字段。

using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace TTShared.Contract.AiCopy;

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
// 文案生成请求
// ============================================================

/// <summary>
/// 云端文案生成请求。
/// 客户端不得提交 user_id、device_id、role、plan_code、
/// provider、model、estimated_cost、credits_charged 等字段。
/// </summary>
public class AiCopyGenerateRequest
{
    /// <summary>使用场景（如 poster、social_media、email）</summary>
    [JsonPropertyName("scene")]
    public string Scene { get; set; } = string.Empty;

    /// <summary>产品名称（如 快印宣传单）</summary>
    [JsonPropertyName("product_name")]
    public string ProductName { get; set; } = string.Empty;

    /// <summary>产品卖点列表（如 ["当天取件", "高清印刷"]）</summary>
    [JsonPropertyName("selling_points")]
    public List<string> SellingPoints { get; set; } = new();

    /// <summary>目标受众（如 附近商户、学生群体）</summary>
    [JsonPropertyName("target_audience")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? TargetAudience { get; set; }

    /// <summary>文案语气（如 direct、professional、warm、humorous）</summary>
    [JsonPropertyName("tone")]
    public string Tone { get; set; } = string.Empty;

    /// <summary>投放平台（如 offline_poster、wechat、xiaohongshu）</summary>
    [JsonPropertyName("platform")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Platform { get; set; }

    /// <summary>额外要求（如 突出开业活动、不超过 50 字）</summary>
    [JsonPropertyName("extra_requirements")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? ExtraRequirements { get; set; }

    /// <summary>桌面端生成的请求追踪 ID，用于去重和幂等</summary>
    [JsonPropertyName("client_request_id")]
    public string ClientRequestId { get; set; } = string.Empty;
}

// ============================================================
// 文案生成响应数据
// ============================================================

/// <summary>
/// 云端文案生成结果数据。
/// provider、model、estimated_cost、credits_charged 由云端决定，
/// 客户端只读展示，不得提交。
/// </summary>
public class AiCopyGenerateData
{
    /// <summary>功能码，固定为 ai_copy_cloud</summary>
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = "ai_copy_cloud";

    /// <summary>生成的主文案（如 开业大促，高清快印，当天取件！）</summary>
    [JsonPropertyName("text")]
    public string Text { get; set; } = string.Empty;

    /// <summary>生成的备选文案列表</summary>
    [JsonPropertyName("variants")]
    public List<string> Variants { get; set; } = new();

    /// <summary>实际调用的 AI Provider 名称（如 deepseek）</summary>
    [JsonPropertyName("provider")]
    public string Provider { get; set; } = string.Empty;

    /// <summary>实际使用的模型名称（如 deepseek-chat）</summary>
    [JsonPropertyName("model")]
    public string Model { get; set; } = string.Empty;

    /// <summary>云端估算的调用成本（美元，仅供参考）</summary>
    [JsonPropertyName("estimated_cost")]
    public double EstimatedCost { get; set; }

    /// <summary>本次调用实际扣除的 AI 额度</summary>
    [JsonPropertyName("credits_charged")]
    public int CreditsCharged { get; set; }

    /// <summary>Provider 调用日志关联 ID（UUID）</summary>
    [JsonPropertyName("provider_call_id")]
    public string ProviderCallId { get; set; } = string.Empty;
}

// ============================================================
// 文案生成响应
// ============================================================

/// <summary>
/// 云端文案生成 API 响应。
/// 遵循统一响应结构（success / data / error / request_id）。
/// </summary>
public class AiCopyGenerateResponse
{
    /// <summary>请求是否成功</summary>
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    /// <summary>文案生成结果，失败时为 null</summary>
    [JsonPropertyName("data")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public AiCopyGenerateData? Data { get; set; }

    /// <summary>错误详情，成功时为 null</summary>
    [JsonPropertyName("error")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ErrorDetail? Error { get; set; }

    /// <summary>云端生成的请求追踪 ID</summary>
    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = string.Empty;
}
