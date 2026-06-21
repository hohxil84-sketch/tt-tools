// ai_image_tools DTO — 高级图片 AI API 契约。
// 来源：shared-contract/openapi/ai-image-tools.yaml v0.1.0
// 生成方式：手写，以 OpenAPI 为唯一来源。
//
// 本模块提供以下高级图片 AI 功能的统一入口：
// - upscale_image_cloud：高清修复
// - vectorize_image_cloud：转矢量
// - ai_edit_image_cloud：AI 改图
// - remove_bg_cloud：高级抠图
// - ocr_cloud：高级 OCR
//
// 客户端不得提交 provider、model、estimated_cost、credits_charged 等字段。

using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace TTShared.Contract.AiImageTools;

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
// 结果文件
// ============================================================

/// <summary>AI 图片处理结果文件信息</summary>
public class ResultFile
{
    /// <summary>结果文件 ID（UUID）</summary>
    [JsonPropertyName("file_id")]
    public string FileId { get; set; } = string.Empty;

    /// <summary>文件访问 URL（临时签名链接）</summary>
    [JsonPropertyName("url")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Url { get; set; }

    /// <summary>文件 MIME 类型（如 image/png、image/svg+xml、application/pdf）</summary>
    [JsonPropertyName("mime_type")]
    public string MimeType { get; set; } = string.Empty;

    /// <summary>图片宽度（像素）</summary>
    [JsonPropertyName("width")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? Width { get; set; }

    /// <summary>图片高度（像素）</summary>
    [JsonPropertyName("height")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? Height { get; set; }
}

// ============================================================
// 创建任务请求
// ============================================================

/// <summary>
/// 创建高级图片 AI 任务请求。
/// 通过 Feature 字段指定具体的 AI 图片处理功能。
///
/// 客户端不得提交 user_id、device_id、role、plan_code、
/// provider、model、estimated_cost、credits_charged 等字段。
/// </summary>
public class CreateAiImageToolTaskRequest
{
    /// <summary>
    /// AI 图片工具功能码。
    /// 可选值：upscale_image_cloud（高清修复）、vectorize_image_cloud（转矢量）、
    /// ai_edit_image_cloud（AI 改图）、remove_bg_cloud（高级抠图）、ocr_cloud（高级 OCR）
    /// </summary>
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    /// <summary>输入文件 ID 列表（已上传至云端的文件 UUID）</summary>
    [JsonPropertyName("input_file_ids")]
    public List<string> InputFileIds { get; set; } = new();

    /// <summary>各功能的自定义选项（如分辨率、输出格式、OCR 语言等）</summary>
    [JsonPropertyName("options")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public Dictionary<string, object>? Options { get; set; }

    /// <summary>桌面端生成的请求追踪 ID，用于去重和幂等</summary>
    [JsonPropertyName("client_request_id")]
    public string ClientRequestId { get; set; } = string.Empty;
}

// ============================================================
// 创建任务响应数据
// ============================================================

/// <summary>高级图片 AI 任务创建成功响应数据</summary>
public class CreatedTaskData
{
    /// <summary>任务的唯一 ID（UUID）</summary>
    [JsonPropertyName("task_id")]
    public string TaskId { get; set; } = string.Empty;

    /// <summary>任务当前状态（queued 排队中、running 处理中、succeeded 成功、failed 失败）</summary>
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    /// <summary>功能码，回显请求中指定的 AI 图片工具功能</summary>
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    /// <summary>预估消耗的 AI 额度</summary>
    [JsonPropertyName("estimated_credits")]
    public int EstimatedCredits { get; set; }
}

// ============================================================
// 任务查询响应数据
// ============================================================

/// <summary>
/// 高级图片 AI 任务查询响应数据。
///
/// provider、model、estimated_cost、credits_charged 由云端决定，
/// 客户端只读展示，不得提交。
///
/// ResultJson 为各功能自定义结果数据（如 OCR 文本行、矢量路径数等），
/// 仅任务成功时可能包含。
/// </summary>
public class AiImageToolTaskData
{
    /// <summary>任务的唯一 ID（UUID）</summary>
    [JsonPropertyName("task_id")]
    public string TaskId { get; set; } = string.Empty;

    /// <summary>任务当前状态</summary>
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    /// <summary>功能码，回显请求中指定的 AI 图片工具功能</summary>
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    /// <summary>AI 处理结果文件列表（succeeded 时包含结果，其他状态为空数组）</summary>
    [JsonPropertyName("result_files")]
    public List<ResultFile> ResultFiles { get; set; } = new();

    /// <summary>各功能自定义结果数据（如 OCR 识别文本、矢量图层信息），成功时可能为 null</summary>
    [JsonPropertyName("result_json")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public Dictionary<string, object>? ResultJson { get; set; }

    /// <summary>实际调用的 AI Provider 名称</summary>
    [JsonPropertyName("provider")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Provider { get; set; }

    /// <summary>实际使用的模型名称</summary>
    [JsonPropertyName("model")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Model { get; set; }

    /// <summary>云端估算的调用成本（美元，仅供参考）</summary>
    [JsonPropertyName("estimated_cost")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public double? EstimatedCost { get; set; }

    /// <summary>本次调用实际扣除的 AI 额度</summary>
    [JsonPropertyName("credits_charged")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? CreditsCharged { get; set; }

    /// <summary>Provider 调用日志关联 ID（运行中/完成时有值）</summary>
    [JsonPropertyName("provider_call_id")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? ProviderCallId { get; set; }
}

// ============================================================
// 创建任务响应
// ============================================================

/// <summary>
/// 高级图片 AI 任务创建 API 响应。
/// 遵循统一响应结构（success / data / error / request_id）。
/// </summary>
public class CreateAiImageToolTaskResponse
{
    /// <summary>请求是否成功</summary>
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    /// <summary>任务创建结果，失败时为 null</summary>
    [JsonPropertyName("data")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public CreatedTaskData? Data { get; set; }

    /// <summary>错误详情，成功时为 null</summary>
    [JsonPropertyName("error")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ErrorDetail? Error { get; set; }

    /// <summary>云端生成的请求追踪 ID</summary>
    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = string.Empty;
}

// ============================================================
// 任务查询响应
// ============================================================

/// <summary>
/// 高级图片 AI 任务查询 API 响应。
/// 遵循统一响应结构（success / data / error / request_id）。
/// </summary>
public class AiImageToolTaskResponse
{
    /// <summary>请求是否成功</summary>
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    /// <summary>任务查询结果，失败时为 null</summary>
    [JsonPropertyName("data")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public AiImageToolTaskData? Data { get; set; }

    /// <summary>错误详情，成功时为 null</summary>
    [JsonPropertyName("error")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ErrorDetail? Error { get; set; }

    /// <summary>云端生成的请求追踪 ID</summary>
    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = string.Empty;
}
