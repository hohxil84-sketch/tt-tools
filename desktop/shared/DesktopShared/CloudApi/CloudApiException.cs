namespace TTShared.CloudApi;

/// <summary>
/// 云端 API 异常，包含错误码和请求 ID 用于排查
/// </summary>
public class CloudApiException : Exception
{
    /// <summary>统一错误码</summary>
    public string ErrorCode { get; }

    /// <summary>云端请求 ID</summary>
    public string RequestId { get; }

    public CloudApiException(string errorCode, string message, string requestId)
        : base(message)
    {
        ErrorCode = errorCode;
        RequestId = requestId;
    }

    public CloudApiException(string errorCode, string message, string requestId,
        Exception innerException)
        : base(message, innerException)
    {
        ErrorCode = errorCode;
        RequestId = requestId;
    }
}
