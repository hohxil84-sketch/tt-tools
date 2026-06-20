using TTShared.Logging;

namespace TTTools.ExportSettings.Models;

/// <summary>
/// 日志过滤选项
/// 支持按日期范围、级别、类别、关键词过滤日志条目。
/// </summary>
public class LogFilterOptions
{
    /// <summary>开始日期（可选，过滤此日期之后的日志）</summary>
    public DateTime? StartDate { get; set; }

    /// <summary>结束日期（可选，过滤此日期之前的日志）</summary>
    public DateTime? EndDate { get; set; }

    /// <summary>最低日志级别（过滤低于此级别的日志）</summary>
    public LogLevel? MinLevel { get; set; }

    /// <summary>类别过滤（精确匹配）</summary>
    public string? Category { get; set; }

    /// <summary>关键词搜索（在消息中搜索）</summary>
    public string? SearchText { get; set; }

    /// <summary>
    /// 判断日志条目是否匹配过滤条件
    /// </summary>
    public bool Matches(LogDisplayEntry entry)
    {
        // 日期范围过滤
        if (StartDate.HasValue && entry.Timestamp < StartDate.Value)
            return false;
        if (EndDate.HasValue && entry.Timestamp > EndDate.Value.AddDays(1))
            return false;

        // 级别过滤
        if (MinLevel.HasValue && entry.Level < MinLevel.Value)
            return false;

        // 类别过滤
        if (!string.IsNullOrWhiteSpace(Category) &&
            !string.Equals(entry.Category, Category, StringComparison.OrdinalIgnoreCase))
            return false;

        // 关键词搜索
        if (!string.IsNullOrWhiteSpace(SearchText) &&
            !entry.Message.Contains(SearchText, StringComparison.OrdinalIgnoreCase) &&
            !(entry.Exception?.Contains(SearchText, StringComparison.OrdinalIgnoreCase) ?? false))
            return false;

        return true;
    }
}
