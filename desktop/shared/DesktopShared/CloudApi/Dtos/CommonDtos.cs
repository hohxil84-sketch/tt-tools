using System.Text.Json.Serialization;

namespace TTShared.CloudApi.Dtos;

/// <summary>
/// 统一 API 响应包装（对应 OpenAPI common.yaml ApiResponse）
/// </summary>
public class ApiResponse<T>
{
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    [JsonPropertyName("data")]
    public T? Data { get; set; }

    [JsonPropertyName("error")]
    public ApiError? Error { get; set; }

    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = string.Empty;

    /// <summary>是否成功且数据不为 null</summary>
    [JsonIgnore]
    public bool IsSuccess => Success && Error == null;
}

/// <summary>
/// 统一错误结构（对应 OpenAPI ErrorDetail）
/// </summary>
public class ApiError
{
    [JsonPropertyName("code")]
    public string Code { get; set; } = string.Empty;

    [JsonPropertyName("message")]
    public string Message { get; set; } = string.Empty;

    [JsonPropertyName("details")]
    public Dictionary<string, object>? Details { get; set; }
}

/// <summary>
/// 分页数据结构（对应 OpenAPI Pagination）
/// </summary>
public class PaginatedData<T>
{
    [JsonPropertyName("items")]
    public List<T> Items { get; set; } = new();

    [JsonPropertyName("total")]
    public int Total { get; set; }

    [JsonPropertyName("limit")]
    public int Limit { get; set; }

    [JsonPropertyName("offset")]
    public int Offset { get; set; }
}
