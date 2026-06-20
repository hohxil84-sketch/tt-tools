namespace TTTools.ExportSettings.Models;

/// <summary>
/// 导出结果模型
/// 包含导出操作的结果统计和详情。
/// </summary>
public class ExportResult
{
    /// <summary>是否全部成功</summary>
    public bool Success { get; set; }

    /// <summary>成功导出的文件数</summary>
    public int SuccessCount { get; set; }

    /// <summary>失败的文件数</summary>
    public int FailureCount { get; set; }

    /// <summary>成功导出的输出文件路径列表</summary>
    public List<string> OutputPaths { get; set; } = new();

    /// <summary>失败详情（文件路径 -> 错误信息）</summary>
    public List<ExportError> Errors { get; set; } = new();

    /// <summary>导出耗时（毫秒）</summary>
    public long ElapsedMs { get; set; }

    /// <summary>
    /// 创建全成功结果
    /// </summary>
    public static ExportResult AllSuccess(List<string> outputPaths, long elapsedMs)
        => new()
        {
            Success = true,
            SuccessCount = outputPaths.Count,
            OutputPaths = outputPaths,
            ElapsedMs = elapsedMs
        };

    /// <summary>
    /// 创建含失败的结果
    /// </summary>
    public static ExportResult WithFailures(int successCount, List<string> outputPaths,
        List<ExportError> errors, long elapsedMs)
        => new()
        {
            Success = errors.Count == 0,
            SuccessCount = successCount,
            FailureCount = errors.Count,
            OutputPaths = outputPaths,
            Errors = errors,
            ElapsedMs = elapsedMs
        };
}

/// <summary>
/// 导出错误详情
/// </summary>
public class ExportError
{
    /// <summary>源文件路径</summary>
    public string SourcePath { get; set; } = string.Empty;

    /// <summary>错误信息</summary>
    public string Message { get; set; } = string.Empty;

    /// <summary>错误异常类型</summary>
    public string? ExceptionType { get; set; }
}
