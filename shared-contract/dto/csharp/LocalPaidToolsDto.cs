// local_paid_tools DTO — 本地付费工具权限校验。
// 来源：shared-contract/openapi/local-paid-tools.yaml v0.1.0
// 生成方式：手写，以 OpenAPI 为唯一来源。

using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace TTShared.Contract.LocalPaidTools;

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
// 权限检查
// ============================================================

/// <summary>
/// 本地付费工具套餐权限检查请求。
/// 客户端不得提交 user_id、plan_code、provider、model 等字段。
/// </summary>
public class LocalPaidToolEntitlementRequest
{
    /// <summary>本地付费功能码（如 resize_image_local_paid、pdf_image_convert_local_paid）</summary>
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    /// <summary>操作类型（single / batch）</summary>
    [JsonPropertyName("operation")]
    public string Operation { get; set; } = string.Empty;

    /// <summary>桌面端生成的请求追踪 ID，用于去重和幂等</summary>
    [JsonPropertyName("client_request_id")]
    public string ClientRequestId { get; set; } = string.Empty;
}

/// <summary>本地付费工具套餐权限检查结果</summary>
public class LocalPaidToolEntitlementData
{
    /// <summary>是否允许使用指定功能</summary>
    [JsonPropertyName("allowed")]
    public bool Allowed { get; set; }

    /// <summary>检查的功能码，与请求中的 feature 一致</summary>
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    /// <summary>用户当前套餐编码（free / standard / pro）</summary>
    [JsonPropertyName("plan_code")]
    public string PlanCode { get; set; } = string.Empty;

    /// <summary>免费套餐剩余免费使用次数（仅 free 套餐有意义）</summary>
    [JsonPropertyName("remaining_free_quota")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? RemainingFreeQuota { get; set; }

    /// <summary>不允许时的拒绝原因（中文）</summary>
    [JsonPropertyName("reason")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Reason { get; set; }
}

/// <summary>本地付费工具套餐权限检查响应</summary>
public class LocalPaidToolEntitlementResponse
{
    /// <summary>请求是否成功</summary>
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    /// <summary>权限检查结果，失败时为 null</summary>
    [JsonPropertyName("data")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public LocalPaidToolEntitlementData? Data { get; set; }

    /// <summary>错误详情，成功时为 null</summary>
    [JsonPropertyName("error")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ErrorDetail? Error { get; set; }

    /// <summary>云端生成的请求追踪 ID</summary>
    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = string.Empty;
}
