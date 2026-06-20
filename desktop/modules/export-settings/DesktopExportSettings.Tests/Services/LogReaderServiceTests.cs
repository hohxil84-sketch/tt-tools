using TTTools.ExportSettings.Models;
using TTTools.ExportSettings.Services;
using TTShared.Logging;

namespace TTTools.ExportSettings.Tests.Services;

/// <summary>
/// LogReaderService 服务单元测试
/// </summary>
public class LogReaderServiceTests : IDisposable
{
    private readonly string _testLogDir;
    private readonly LogReaderService _service;

    public LogReaderServiceTests()
    {
        _testLogDir = Path.Combine(Path.GetTempPath(), $"TTTools_LogTest_{Guid.NewGuid():N}");
        Directory.CreateDirectory(_testLogDir);
        _service = new LogReaderService(_testLogDir);
    }

    [Fact]
    public void GetLogFiles_NoLogFiles_ReturnsEmpty()
    {
        var files = _service.GetLogFiles();
        Assert.Empty(files);
    }

    [Fact]
    public async Task ReadLogsAsync_NoLogFiles_ReturnsEmpty()
    {
        var entries = await _service.ReadLogsAsync();
        Assert.Empty(entries);
    }

    [Fact]
    public async Task ReadLogsAsync_WithLogFile_ReadsEntries()
    {
        // 创建测试日志文件
        var logPath = Path.Combine(_testLogDir, "tttools-20260620.log");
        await File.WriteAllTextAsync(logPath,
            "2026-06-20 10:00:00.123 [INFO] [default] 应用启动\n" +
            "2026-06-20 10:01:00.456 [WARNING] [auth] 令牌即将过期\n" +
            "2026-06-20 10:02:00.789 [ERROR] [export] 导出失败：文件不存在\n");

        var entries = await _service.ReadLogsAsync();

        Assert.Equal(3, entries.Count);
        // 时间倒序
        Assert.Equal("导出失败：文件不存在", entries[0].Message);
        Assert.Equal("令牌即将过期", entries[1].Message);
        Assert.Equal("应用启动", entries[2].Message);
    }

    [Fact]
    public async Task ReadLogsAsync_WithFilterLevel_FiltersCorrectly()
    {
        var logPath = Path.Combine(_testLogDir, "tttools-20260620.log");
        await File.WriteAllTextAsync(logPath,
            "2026-06-20 10:00:00.000 [INFO] [default] info message\n" +
            "2026-06-20 10:01:00.000 [ERROR] [default] error message\n" +
            "2026-06-20 10:02:00.000 [FATAL] [default] fatal message\n");

        var options = new LogFilterOptions { MinLevel = LogLevel.Error };
        var entries = await _service.ReadLogsAsync(options);

        Assert.Equal(2, entries.Count);
        Assert.All(entries, e => Assert.True(e.Level >= LogLevel.Error));
    }

    [Fact]
    public async Task ReadLogsAsync_WithMaxEntries_LimitsResult()
    {
        var logPath = Path.Combine(_testLogDir, "tttools-20260620.log");
        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < 50; i++)
            sb.AppendLine($"2026-06-20 10:{i:D2}:00.000 [INFO] [default] message {i}");
        await File.WriteAllTextAsync(logPath, sb.ToString());

        var entries = await _service.ReadLogsAsync(maxEntries: 10);

        Assert.Equal(10, entries.Count);
    }

    [Fact]
    public async Task ReadLogsAsync_WithSearchText_FiltersByMessage()
    {
        var logPath = Path.Combine(_testLogDir, "tttools-20260620.log");
        await File.WriteAllTextAsync(logPath,
            "2026-06-20 10:00:00.000 [INFO] [default] normal message\n" +
            "2026-06-20 10:01:00.000 [INFO] [default] important message\n" +
            "2026-06-20 10:02:00.000 [INFO] [default] another normal\n");

        var options = new LogFilterOptions { SearchText = "important" };
        var entries = await _service.ReadLogsAsync(options);

        Assert.Single(entries);
        Assert.Contains("important", entries[0].Message);
    }

    [Fact]
    public void ParseLogLine_ValidLine_ReturnsCorrectEntry()
    {
        var line = "2026-06-20 10:30:00.123 [INFO] [default] 应用启动完成";

        var entry = LogReaderService.ParseLogLine(line);

        Assert.NotNull(entry);
        Assert.Equal(LogLevel.Info, entry!.Level);
        Assert.Equal("default", entry.Category);
        Assert.Equal("应用启动完成", entry.Message);
        Assert.Equal(new DateTime(2026, 6, 20, 10, 30, 0, 123), entry.Timestamp);
    }

    [Fact]
    public void ParseLogLine_ErrorLevel_ReturnsCorrectLevel()
    {
        var line = "2026-06-20 10:30:00.000 [ERROR] [system] 磁盘空间不足";

        var entry = LogReaderService.ParseLogLine(line);

        Assert.NotNull(entry);
        Assert.Equal(LogLevel.Error, entry!.Level);
    }

    [Fact]
    public void ParseLogLine_InvalidLine_ReturnsNull()
    {
        Assert.Null(LogReaderService.ParseLogLine(""));
        Assert.Null(LogReaderService.ParseLogLine("   "));
        Assert.Null(LogReaderService.ParseLogLine("not a log line"));
        Assert.Null(LogReaderService.ParseLogLine("2026")); // too short
    }

    [Fact]
    public void ClearAllLogs_DeletesAllLogFiles()
    {
        // 创建测试日志文件
        File.WriteAllText(Path.Combine(_testLogDir, "tttools-20260620.log"), "test");
        File.WriteAllText(Path.Combine(_testLogDir, "tttools-20260619.log"), "test");

        Assert.Equal(2, _service.GetLogFiles().Count);

        _service.ClearAllLogs();

        Assert.Empty(_service.GetLogFiles());
    }

    [Fact]
    public void GetTotalLogSize_ReturnsCorrectSize()
    {
        var content = new string('x', 1024); // 1KB
        File.WriteAllText(Path.Combine(_testLogDir, "tttools-20260620.log"), content);
        File.WriteAllText(Path.Combine(_testLogDir, "tttools-20260619.log"), content);

        var size = _service.GetTotalLogSize();

        Assert.True(size >= 2048);
    }

    [Fact]
    public async Task ReadLogsAsync_WithCategoryFilter_FiltersCorrectly()
    {
        var logPath = Path.Combine(_testLogDir, "tttools-20260620.log");
        await File.WriteAllTextAsync(logPath,
            "2026-06-20 10:00:00.000 [INFO] [auth] auth message\n" +
            "2026-06-20 10:01:00.000 [INFO] [export] export message\n" +
            "2026-06-20 10:02:00.000 [INFO] [auth] another auth\n");

        var options = new LogFilterOptions { Category = "auth" };
        var entries = await _service.ReadLogsAsync(options);

        Assert.Equal(2, entries.Count);
        Assert.All(entries, e => Assert.Equal("auth", e.Category));
    }

    public void Dispose()
    {
        try { Directory.Delete(_testLogDir, recursive: true); } catch { }
    }
}
