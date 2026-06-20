using TTTools.ExportSettings.Models;
using TTShared.Logging;

namespace TTTools.ExportSettings.Services;

/// <summary>
/// 日志读取服务
/// 从日志文件中读取和解析日志条目，支持过滤和搜索。
/// </summary>
public class LogReaderService
{
    private readonly string _logDirectory;

    /// <summary>
    /// 创建日志读取服务
    /// </summary>
    /// <param name="logDirectory">日志文件目录（可选，默认使用 AppData 下的 TT Tools 日志目录）</param>
    public LogReaderService(string? logDirectory = null)
    {
        _logDirectory = logDirectory ??
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "TTTools", "logs");
    }

    /// <summary>
    /// 获取所有日志文件路径（时间倒序）
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
    /// 从所有日志文件读取日志条目
    /// </summary>
    /// <param name="options">过滤选项</param>
    /// <param name="maxEntries">最大返回条目数（0 表示无限制）</param>
    /// <returns>过滤后的日志条目列表（时间倒序）</returns>
    public async Task<List<LogDisplayEntry>> ReadLogsAsync(
        LogFilterOptions? options = null,
        int maxEntries = 500)
    {
        var entries = new List<LogDisplayEntry>();
        var logFiles = GetLogFiles();

        // 按时间倒序读取（最新的文件优先）
        foreach (var file in logFiles)
        {
            if (maxEntries > 0 && entries.Count >= maxEntries)
                break;

            try
            {
                await ReadLogFileAsync(file, entries, options, maxEntries);
            }
            catch
            {
                // 跳过无法读取的文件
            }
        }

        // 时间倒序排列
        entries = entries.OrderByDescending(e => e.Timestamp).ToList();

        // 截断到最大条目数
        if (maxEntries > 0 && entries.Count > maxEntries)
            entries = entries.Take(maxEntries).ToList();

        return entries;
    }

    /// <summary>
    /// 从单个日志文件读取条目
    /// 日志格式：yyyy-MM-dd HH:mm:ss.fff [LEVEL] [CATEGORY] message
    /// 异常信息可能跨多行（以缩进开头）
    /// </summary>
    private async Task ReadLogFileAsync(
        string filePath,
        List<LogDisplayEntry> entries,
        LogFilterOptions? options,
        int maxEntries)
    {
        using var reader = new StreamReader(filePath, Encoding.UTF8);
        var exceptionLines = new StringBuilder();

        while (await reader.ReadLineAsync() is { } line)
        {
            if (maxEntries > 0 && entries.Count >= maxEntries)
                break;

            // 检查是否为异常附加行（以空格或 tab 开头）
            if (line.Length > 0 && (line[0] == ' ' || line[0] == '\t') && entries.Count > 0)
            {
                if (exceptionLines.Length > 0)
                    exceptionLines.Append('\n');
                exceptionLines.Append(line.TrimStart());
                continue;
            }

            // 如果有累积的异常信息，附加到上一条日志
            if (exceptionLines.Length > 0 && entries.Count > 0)
            {
                var lastEntry = entries[^1];
                if (lastEntry.Exception == null)
                    lastEntry.Exception = exceptionLines.ToString();
                else
                    lastEntry.Exception += "\n" + exceptionLines.ToString();
                exceptionLines.Clear();
            }

            // 解析日志行
            var entry = ParseLogLine(line);
            if (entry == null)
                continue;

            // 应用过滤
            if (options != null && !options.Matches(entry))
                continue;

            entries.Add(entry);
        }

        // 处理文件末尾的异常信息
        if (exceptionLines.Length > 0 && entries.Count > 0)
        {
            var lastEntry = entries[^1];
            if (lastEntry.Exception == null)
                lastEntry.Exception = exceptionLines.ToString();
            else
                lastEntry.Exception += "\n" + exceptionLines.ToString();
        }
    }

    /// <summary>
    /// 解析单行日志文本
    /// </summary>
    /// <param name="line">日志行文本</param>
    /// <returns>解析后的日志条目，解析失败返回 null</returns>
    public static LogDisplayEntry? ParseLogLine(string line)
    {
        if (string.IsNullOrWhiteSpace(line))
            return null;

        try
        {
            // 格式：yyyy-MM-dd HH:mm:ss.fff [LEVEL] [CATEGORY] message
            // 示例：2026-06-20 10:30:00.123 [INFO] [default] 应用启动完成

            // 提取时间戳（前 23 个字符）
            if (line.Length < 25)
                return null;

            var timestampStr = line[..23]; // yyyy-MM-dd HH:mm:ss.fff
            if (!DateTime.TryParse(timestampStr, out var timestamp))
                return null;

            // 查找日志级别
            var levelStart = line.IndexOf('[');
            if (levelStart < 0)
                return null;

            var levelEnd = line.IndexOf(']', levelStart);
            if (levelEnd < 0)
                return null;

            var levelStr = line.Substring(levelStart + 1, levelEnd - levelStart - 1);
            if (!Enum.TryParse<LogLevel>(levelStr, ignoreCase: true, out var level))
                return null;

            // 查找类别
            var categoryStart = line.IndexOf('[', levelEnd);
            if (categoryStart < 0)
                return null;

            var categoryEnd = line.IndexOf(']', categoryStart);
            if (categoryEnd < 0)
                return null;

            var category = line.Substring(categoryStart + 1, categoryEnd - categoryStart - 1);

            // 提取消息
            var message = line[(categoryEnd + 2)..];

            return new LogDisplayEntry
            {
                Timestamp = timestamp,
                Level = level,
                Category = category,
                Message = message
            };
        }
        catch
        {
            return null;
        }
    }

    /// <summary>
    /// 清除所有日志文件
    /// </summary>
    public void ClearAllLogs()
    {
        try
        {
            var logFiles = GetLogFiles();
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

    /// <summary>
    /// 获取日志目录总大小（字节）
    /// </summary>
    public long GetTotalLogSize()
    {
        try
        {
            var logFiles = GetLogFiles();
            return logFiles.Sum(f =>
            {
                try { return new FileInfo(f).Length; } catch { return 0; }
            });
        }
        catch
        {
            return 0;
        }
    }
}
