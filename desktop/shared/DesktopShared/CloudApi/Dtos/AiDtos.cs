using System.Text.Json.Serialization;

namespace TTShared.CloudApi.Dtos;

// ============ AI Copy DTOs（对应 OpenAPI ai-copy.yaml）============

/// <summary>AI 文案生成请求</summary>
public class AiCopyGenerateRequest
{
    [JsonPropertyName("scene")]
    public string Scene { get; set; } = string.Empty;

    [JsonPropertyName("product_name")]
    public string ProductName { get; set; } = string.Empty;

    [JsonPropertyName("selling_points")]
    public List<string> SellingPoints { get; set; } = new();

    [JsonPropertyName("target_audience")]
    public string? TargetAudience { get; set; }

    [JsonPropertyName("tone")]
    public string Tone { get; set; } = "direct";

    [JsonPropertyName("platform")]
    public string? Platform { get; set; }

    [JsonPropertyName("extra_requirements")]
    public string? ExtraRequirements { get; set; }

    [JsonPropertyName("client_request_id")]
    public string ClientRequestId { get; set; } = string.Empty;
}

/// <summary>AI 文案生成响应数据</summary>
public class AiCopyGenerateData
{
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = "ai_copy_cloud";

    [JsonPropertyName("text")]
    public string Text { get; set; } = string.Empty;

    [JsonPropertyName("variants")]
    public List<string> Variants { get; set; } = new();

    [JsonPropertyName("provider")]
    public string Provider { get; set; } = string.Empty;

    [JsonPropertyName("model")]
    public string Model { get; set; } = string.Empty;

    [JsonPropertyName("estimated_cost")]
    public decimal EstimatedCost { get; set; }

    [JsonPropertyName("credits_charged")]
    public int CreditsCharged { get; set; }

    [JsonPropertyName("provider_call_id")]
    public string ProviderCallId { get; set; } = string.Empty;
}

// ============ AI Render DTOs（对应 OpenAPI ai-render.yaml）============

/// <summary>AI 效果图生成任务创建请求</summary>
public class CreateAiRenderTaskRequest
{
    [JsonPropertyName("scene_type")]
    public string SceneType { get; set; } = string.Empty;

    [JsonPropertyName("prompt")]
    public string Prompt { get; set; } = string.Empty;

    [JsonPropertyName("input_file_ids")]
    public List<string> InputFileIds { get; set; } = new();

    [JsonPropertyName("style")]
    public string? Style { get; set; }

    [JsonPropertyName("size")]
    public string? Size { get; set; }

    [JsonPropertyName("client_request_id")]
    public string ClientRequestId { get; set; } = string.Empty;
}

/// <summary>已创建任务的基础数据</summary>
public class CreatedTaskData
{
    [JsonPropertyName("task_id")]
    public string TaskId { get; set; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; set; } = "queued";

    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    [JsonPropertyName("estimated_credits")]
    public int EstimatedCredits { get; set; }
}

/// <summary>AI 效果图任务详情数据</summary>
public class AiRenderTaskData
{
    [JsonPropertyName("task_id")]
    public string TaskId { get; set; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("result_files")]
    public List<ResultFileDto> ResultFiles { get; set; } = new();

    [JsonPropertyName("provider")]
    public string? Provider { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("estimated_cost")]
    public decimal? EstimatedCost { get; set; }

    [JsonPropertyName("credits_charged")]
    public int? CreditsCharged { get; set; }

    [JsonPropertyName("provider_call_id")]
    public string? ProviderCallId { get; set; }
}

// ============ AI Image Tools DTOs（对应 OpenAPI ai-image-tools.yaml）============

/// <summary>高级图片 AI 任务创建请求</summary>
public class CreateAiImageToolTaskRequest
{
    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    [JsonPropertyName("input_file_ids")]
    public List<string> InputFileIds { get; set; } = new();

    [JsonPropertyName("options")]
    public Dictionary<string, object>? Options { get; set; }

    [JsonPropertyName("client_request_id")]
    public string ClientRequestId { get; set; } = string.Empty;
}

/// <summary>高级图片 AI 任务详情数据</summary>
public class AiImageToolTaskData
{
    [JsonPropertyName("task_id")]
    public string TaskId { get; set; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    [JsonPropertyName("result_files")]
    public List<ResultFileDto> ResultFiles { get; set; } = new();

    [JsonPropertyName("result_json")]
    public Dictionary<string, object>? ResultJson { get; set; }

    [JsonPropertyName("provider")]
    public string? Provider { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("estimated_cost")]
    public decimal? EstimatedCost { get; set; }

    [JsonPropertyName("credits_charged")]
    public int? CreditsCharged { get; set; }

    [JsonPropertyName("provider_call_id")]
    public string? ProviderCallId { get; set; }
}

/// <summary>结果文件</summary>
public class ResultFileDto
{
    [JsonPropertyName("file_id")]
    public string FileId { get; set; } = string.Empty;

    [JsonPropertyName("url")]
    public string? Url { get; set; }

    [JsonPropertyName("mime_type")]
    public string MimeType { get; set; } = string.Empty;

    [JsonPropertyName("width")]
    public int? Width { get; set; }

    [JsonPropertyName("height")]
    public int? Height { get; set; }
}

// ============ Provider Log DTOs（对应 OpenAPI provider-log.yaml）============

/// <summary>Provider 调用日志条目</summary>
public class ProviderCallLogItemDto
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = string.Empty;

    [JsonPropertyName("feature")]
    public string Feature { get; set; } = string.Empty;

    [JsonPropertyName("provider")]
    public string Provider { get; set; } = string.Empty;

    [JsonPropertyName("model")]
    public string Model { get; set; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("error_code")]
    public string? ErrorCode { get; set; }

    [JsonPropertyName("input_tokens")]
    public int InputTokens { get; set; }

    [JsonPropertyName("output_tokens")]
    public int OutputTokens { get; set; }

    [JsonPropertyName("total_tokens")]
    public int TotalTokens { get; set; }

    [JsonPropertyName("estimated_cost")]
    public decimal EstimatedCost { get; set; }

    [JsonPropertyName("credits_charged")]
    public int CreditsCharged { get; set; }

    [JsonPropertyName("latency_ms")]
    public int? LatencyMs { get; set; }

    [JsonPropertyName("created_at")]
    public string CreatedAt { get; set; } = string.Empty;
}
