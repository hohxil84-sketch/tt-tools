using TTShared.Logging;

namespace TTTools.ExportSettings.Models;

/// <summary>
/// 日志展示条目
/// 包装 AppLogger 的 LogEntry，提供 UI 友好的展示属性。
/// </summary>
public class LogDisplayEntry
{
    /// <summary>日志时间戳（本地时间）</summary>
    public DateTime Timestamp { get; set; }

    /// <summary>日志级别</summary>
    public LogLevel Level { get; set; }

    /// <summary>日志消息</summary>
    public string Message { get; set; } = string.Empty;

    /// <summary>日志类别</summary>
    public string Category { get; set; } = "default";

    /// <summary>异常信息（如有）</summary>
    public string? Exception { get; set; }

    /// <summary>格式化时间戳</summary>
    public string TimestampFormatted => Timestamp.ToString("yyyy-MM-dd HH:mm:ss.fff");

    /// <summary>日志级别文本</summary>
    public string LevelText => Level.ToString().ToUpperInvariant();

    /// <summary>是否有异常信息</summary>
    public bool HasException => !string.IsNullOrEmpty(Exception);

    /// <summary>
    /// 从 LogEntry 创建展示条目
    /// </summary>
    public static LogDisplayEntry FromLogEntry(LogEntry entry)
        => new()
        {
            Timestamp = entry.Timestamp.ToLocalTime(),
            Level = entry.Level,
            Message = entry.Message,
            Category = entry.Category,
            Exception = entry.Exception
        };
}
