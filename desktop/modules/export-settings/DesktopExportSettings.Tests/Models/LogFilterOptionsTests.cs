using TTTools.ExportSettings.Models;
using TTShared.Logging;

namespace TTTools.ExportSettings.Tests.Models;

/// <summary>
/// LogFilterOptions 模型单元测试
/// </summary>
public class LogFilterOptionsTests
{
    [Fact]
    public void Matches_NoFilters_ReturnsTrue()
    {
        var options = new LogFilterOptions();
        var entry = CreateEntry(LogLevel.Info, "test", "default");

        Assert.True(options.Matches(entry));
    }

    [Fact]
    public void Matches_MinLevel_FiltersLowerLevels()
    {
        var options = new LogFilterOptions { MinLevel = LogLevel.Warning };
        var infoEntry = CreateEntry(LogLevel.Info, "test");
        var warningEntry = CreateEntry(LogLevel.Warning, "test");
        var errorEntry = CreateEntry(LogLevel.Error, "test");

        Assert.False(options.Matches(infoEntry));
        Assert.True(options.Matches(warningEntry));
        Assert.True(options.Matches(errorEntry));
    }

    [Fact]
    public void Matches_Category_FiltersByExactMatch()
    {
        var options = new LogFilterOptions { Category = "auth" };
        var authEntry = CreateEntry(LogLevel.Info, "登录成功", "auth");
        var defaultEntry = CreateEntry(LogLevel.Info, "任务完成", "default");

        Assert.True(options.Matches(authEntry));
        Assert.False(options.Matches(defaultEntry));
    }

    [Fact]
    public void Matches_SearchText_SearchesInMessage()
    {
        var options = new LogFilterOptions { SearchText = "error" };
        var matchEntry = CreateEntry(LogLevel.Info, "An error occurred");
        var noMatchEntry = CreateEntry(LogLevel.Info, "Everything is fine");

        Assert.True(options.Matches(matchEntry));
        Assert.False(options.Matches(noMatchEntry));
    }

    [Fact]
    public void Matches_SearchText_SearchesInException()
    {
        var options = new LogFilterOptions { SearchText = "NullReference" };
        var entry = new LogDisplayEntry
        {
            Timestamp = DateTime.Now,
            Level = LogLevel.Error,
            Message = "操作失败",
            Category = "default",
            Exception = "System.NullReferenceException: Object reference not set..."
        };

        Assert.True(options.Matches(entry));
    }

    [Fact]
    public void Matches_SearchText_CaseInsensitive()
    {
        var options = new LogFilterOptions { SearchText = "ERROR" };
        var entry = CreateEntry(LogLevel.Error, "An error occurred");

        Assert.True(options.Matches(entry));
    }

    [Fact]
    public void Matches_DateRange_FiltersByDate()
    {
        var options = new LogFilterOptions
        {
            StartDate = new DateTime(2026, 6, 15),
            EndDate = new DateTime(2026, 6, 20)
        };

        var beforeEntry = new LogDisplayEntry { Timestamp = new DateTime(2026, 6, 14), Level = LogLevel.Info, Message = "before" };
        var inRangeEntry = new LogDisplayEntry { Timestamp = new DateTime(2026, 6, 18), Level = LogLevel.Info, Message = "in range" };
        var afterEntry = new LogDisplayEntry { Timestamp = new DateTime(2026, 6, 22), Level = LogLevel.Info, Message = "after" };

        Assert.False(options.Matches(beforeEntry));
        Assert.True(options.Matches(inRangeEntry));
        Assert.False(options.Matches(afterEntry));
    }

    private static LogDisplayEntry CreateEntry(LogLevel level, string message, string category = "default")
        => new()
        {
            Timestamp = DateTime.Now,
            Level = level,
            Message = message,
            Category = category
        };
}
