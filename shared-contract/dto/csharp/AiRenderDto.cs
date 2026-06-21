// ai_render DTO — 云端效果图生成 API 契约。
// 来源：shared-contract/openapi/ai-render.yaml v0.1.0
// 生成方式：手写，以 OpenAPI 为唯一来源。
//
// 客户端不得提交 provider、model、estimated_cost、credits_charged 等字段。

using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace TTShared.Contract.AiRender;

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

/// <summary>生成的效果图文件信息</summary>
public class ResultFile
{
    /// <summary>结果文件 ID（UUID）</summary>
    [JsonPropertyName("file_id")]
    public string FileId { get; set; } = string.Empty;

    /// <summary>文件访问 URL（临时签名链接）</summary>
    [JsonPropertyName("url")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Url { get; set; }

    /// <summary>文件 MIME 类型（如 image/png、image/jpeg）</summary>
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
/// 创建效果图生成任务请求。
/// 客户端不得提交 user_id、device_id、role、plan_code、
/// provider、model、estimated_cost、credits_charged 等字段。
/// </summary>
public class CreateAiRenderTaskRequest
{
    /// <summary>场景类型（如 interior_design 室内设计、product_showcase 产品展示、poster_design 海报设计）</summary>
    [JsonPropertyName("scene_type")]
    public string SceneType { get; set; } = string.Empty;

    /// <summary>效果图生成提示词，描述期望的视觉效果</summary>
    [JsonPropertyName("prompt")]
    public string Prompt { get; set; } = string.Empty;

    /// <summary>输入文件 ID 列表（已上传至云端的文件 UUID）</summary>
    [JsonPropertyName("input_file_ids")]
    public List<string> InputFileIds { get; set; } = new();

    /// <summary>风格参考（如 modern 现代、minimalist 极简、chinese 中式、european 欧式）</summary>
    [JsonPropertyName("style")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Style { get; set; }

    /// <summary>输出尺寸规格（如 1920x1080、1024x1024）</summary>
    [JsonPropertyName("size")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Size { get; set; }

    /// <summary>桌面端生成的请求追踪 ID，用于去重和幂等</summary>
    [JsonPropertyName("client_request_id")]
    public string ClientRequestId { get; set; } = string.Empty;
}

// ============================================================
// 创建任务响应数据
// ============================================================

/// <summary>效果图生成任务创建成功响应数据</summary>
public class CreatedTaskData
{
    /// <summary>任务的唯一 ID（UUID）</summary>
    [JsonPropertyName("task_id")]
    public string TaskId { get; set; } = string.Empty;

    /// <summary>任务当前状态（queued 排队中、running 处理中、succeeded 成功、failed 失败）</summary>
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    /// <summary>功能码，固定为 ai_render_cloud</summary>
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = "ai_render_cloud";

    /// <summary>预估消耗的 AI 额度</summary>
    [JsonPropertyName("estimated_credits")]
    public int EstimatedCredits { get; set; }
}

// ============================================================
// 任务查询响应数据
// ============================================================

/// <summary>
/// 效果图生成任务查询响应数据。
/// provider、model、estimated_cost、credits_charged 由云端决定，
/// 客户端只读展示，不得提交。
/// </summary>
public class AiRenderTaskData
{
    /// <summary>任务的唯一 ID（UUID）</summary>
    [JsonPropertyName("task_id")]
    public string TaskId { get; set; } = string.Empty;

    /// <summary>任务当前状态</summary>
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    /// <summary>功能码，固定为 ai_render_cloud</summary>
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = "ai_render_cloud";

    /// <summary>生成的效果图文件列表（succeeded 时包含结果，其他状态为空数组）</summary>
    [JsonPropertyName("result_files")]
    public List<ResultFile> ResultFiles { get; set; } = new();

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
/// 效果图生成任务创建 API 响应。
/// 遵循统一响应结构（success / data / error / request_id）。
/// </summary>
public class CreateAiRenderTaskResponse
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
/// 效果图生成任务查询 API 响应。
/// 遵循统一响应结构（success / data / error / request_id）。
/// </summary>
public class AiRenderTaskResponse
{
    /// <summary>请求是否成功</summary>
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    /// <summary>任务查询结果，失败时为 null</summary>
    [JsonPropertyName("data")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public AiRenderTaskData? Data { get; set; }

    /// <summary>错误详情，成功时为 null</summary>
    [JsonPropertyName("error")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ErrorDetail? Error { get; set; }

    /// <summary>云端生成的请求追踪 ID</summary>
    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = string.Empty;
}
