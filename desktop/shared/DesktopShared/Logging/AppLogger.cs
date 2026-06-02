using System.Collections.Concurrent;
using System.Text;

namespace TTShared.Logging;

/// <summary>
/// 日志级别
/// </summary>
public enum LogLevel
{
    Debug,
    Info,
    Warning,
    Error,
    Fatal
}

/// <summary>
/// 应用日志记录器
/// 支持文件日志和控制台输出，自动按日轮转。
/// 日志文件存储在用户本地应用数据目录。
/// </summary>
public class AppLogger : IDisposable
{
    private readonly string _logDirectory;
    private readonly ConcurrentQueue<string> _logQueue = new();
    private readonly SemaphoreSlim _flushSignal = new(0);
    private readonly CancellationTokenSource _cts = new();
    private Task? _flushTask;
    private LogLevel _minLevel = LogLevel.Info;

    /// <summary>最大日志文件大小（10MB）</summary>
    private const long MaxLogFileSize = 10 * 1024 * 1024;

    /// <summary>最大保留日志文件数</summary>
    private const int MaxLogFiles = 7;

    /// <summary>是否启用文件日志</summary>
    public bool FileLoggingEnabled { get; set; } = true;

    /// <summary>是否启用控制台输出</summary>
    public bool ConsoleLoggingEnabled { get; set; } = false;

    /// <summary>最低日志级别</summary>
    public LogLevel MinimumLevel
    {
        get => _minLevel;
        set => _minLevel = value;
    }

    /// <summary>日志事件（用于 UI 展示）</summary>
    public event EventHandler<LogEntry>? LogWritten;

    public AppLogger() : this(
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "TTTools", "logs"))
    { }

    public AppLogger(string logDirectory)
    {
        _logDirectory = logDirectory;
        if (!Directory.Exists(_logDirectory))
            Directory.CreateDirectory(_logDirectory);

        StartFlushLoop();
    }

    /// <summary>记录 Debug 级别日志</summary>
    public void Debug(string message, string? category = null) => Log(LogLevel.Debug, message, null, category);

    /// <summary>记录 Info 级别日志</summary>
    public void Info(string message, string? category = null) => Log(LogLevel.Info, message, null, category);

    /// <summary>记录 Warning 级别日志</summary>
    public void Warning(string message, string? category = null) => Log(LogLevel.Warning, message, null, category);

    /// <summary>记录 Error 级别日志（含异常）</summary>
    public void Error(string message, Exception? ex = null, string? category = null) => Log(LogLevel.Error, message, ex, category);

    /// <summary>记录 Fatal 级别日志（含异常）</summary>
    public void Fatal(string message, Exception? ex = null, string? category = null) => Log(LogLevel.Fatal, message, ex, category);

    /// <summary>
    /// 记录日志
    /// </summary>
    public void Log(LogLevel level, string message, Exception? ex = null, string? category = null)
    {
        if (level < _minLevel) return;

        var entry = new LogEntry
        {
            Timestamp = DateTime.UtcNow,
            Level = level,
            Message = message,
            Category = category ?? "default",
            Exception = ex?.ToString()
        };

        // 控制台输出
        if (ConsoleLoggingEnabled)
        {
            var color = level switch
            {
                LogLevel.Error => ConsoleColor.Red,
                LogLevel.Fatal => ConsoleColor.DarkRed,
                LogLevel.Warning => ConsoleColor.Yellow,
                LogLevel.Debug => ConsoleColor.Gray,
                _ => ConsoleColor.White
            };

            var originalColor = Console.ForegroundColor;
            Console.ForegroundColor = color;
            Console.WriteLine(FormatLogLine(entry));
            Console.ForegroundColor = originalColor;
        }

        // 文件日志异步写入
        if (FileLoggingEnabled)
        {
            _logQueue.Enqueue(FormatLogLine(entry));
            try { _flushSignal.Release(); } catch { /* flush 循环已停止 */ }
        }

        // 触发事件（UI 层可订阅）
        LogWritten?.Invoke(this, entry);
    }

    /// <summary>
    /// 强制刷新日志队列到文件
    /// </summary>
    public async Task FlushAsync()
    {
        var lines = new List<string>();
        while (_logQueue.TryDequeue(out var line))
            lines.Add(line);

        if (lines.Count > 0)
            await WriteToFileAsync(lines);
    }

    /// <summary>
    /// 获取今天的日志文件路径
    /// </summary>
    public string GetTodayLogPath()
        => Path.Combine(_logDirectory, $"tttools-{DateTime.UtcNow:yyyyMMdd}.log");

    /// <summary>
    /// 获取所有日志文件路径（按时间倒序）
    /// </summary>
    public List<string> GetLogFiles()
    {
        try
        {
            return Directory.GetFiles(_logDirectory, "tttools-*.log")
                .OrderByDescending(f => f)
                .ToList();
        }
        catch
        {
            return new List<string>();
        }
    }

    /// <summary>
    /// 启动异步日志刷新循环
    /// </summary>
    private void StartFlushLoop()
    {
        _flushTask = Task.Run(async () =>
        {
            var batch = new List<string>();
            while (!_cts.Token.IsCancellationRequested)
            {
                try
                {
                    // 等待信号或 5 秒超时
                    await _flushSignal.WaitAsync(5000, _cts.Token);
                }
                catch (OperationCanceledException)
                {
                    break;
                }

                // 收集当前队列中的所有日志
                batch.Clear();
                while (_logQueue.TryDequeue(out var line))
                    batch.Add(line);

                if (batch.Count > 0)
                    await WriteToFileAsync(batch);
            }

            // 退出前最后一次刷新
            batch.Clear();
            while (_logQueue.TryDequeue(out var line))
                batch.Add(line);

            if (batch.Count > 0)
                await WriteToFileAsync(batch);
        });
    }

    /// <summary>
    /// 写入日志行到文件
    /// </summary>
    private async Task WriteToFileAsync(List<string> lines)
    {
        try
        {
            var logPath = GetTodayLogPath();

            // 检查并轮转大文件
            RotateIfNeeded(logPath);

            using var writer = new StreamWriter(logPath, append: true, Encoding.UTF8);
            foreach (var line in lines)
                await writer.WriteLineAsync(line);
        }
        catch
        {
            // 日志写入失败不应影响应用运行
        }
    }

    /// <summary>
    /// 检查日志文件大小，超过限制则轮转
    /// </summary>
    private void RotateIfNeeded(string logPath)
    {
        try
        {
            if (File.Exists(logPath) && new FileInfo(logPath).Length > MaxLogFileSize)
            {
                var rotated = logPath.Replace(".log", $"-{DateTime.UtcNow:HHmmss}.log");
                File.Move(logPath, rotated);

                // 清理旧日志文件
                CleanOldLogs();
            }
        }
        catch
        {
            // 轮转失败不影响日志记录
        }
    }

    /// <summary>
    /// 清理旧日志文件，保留最近 N 个
    /// </summary>
    private void CleanOldLogs()
    {
        try
        {
            var logFiles = Directory.GetFiles(_logDirectory, "tttools-*.log")
                .OrderByDescending(f => f)
                .Skip(MaxLogFiles);

            foreach (var file in logFiles)
            {
                try { File.Delete(file); } catch { /* 跳过锁定文件 */ }
            }
        }
        catch
        {
            // 静默失败
        }
    }

    private static string FormatLogLine(LogEntry entry)
        => $"{entry.Timestamp:yyyy-MM-dd HH:mm:ss.fff} [{entry.Level.ToString().ToUpperInvariant()}] [{entry.Category}] {entry.Message}{(entry.Exception != null ? $"\n{entry.Exception}" : "")}";

    public void Dispose()
    {
        _cts.Cancel();
        try { _flushSignal.Release(); } catch { }
        try { _flushTask?.Wait(TimeSpan.FromSeconds(5)); } catch { }
        _cts.Dispose();
        _flushSignal.Dispose();
        GC.SuppressFinalize(this);
    }
}

/// <summary>
/// 日志条目
/// </summary>
public class LogEntry
{
    public DateTime Timestamp { get; set; }
    public LogLevel Level { get; set; }
    public string Message { get; set; } = string.Empty;
    public string Category { get; set; } = "default";
    public string? Exception { get; set; }
}
