using TTShared.JobSystem;

namespace TTTools.JobSystem.Models;

/// <summary>
/// 任务查询过滤条件
/// 支持按状态、功能码、日期范围、文本搜索过滤，
/// 以及按不同字段排序和分页。
/// </summary>
public class JobFilterOptions
{
    /// <summary>按状态过滤（null 表示不过滤）</summary>
    public JobStatus? Status { get; set; }

    /// <summary>按功能码过滤（null 表示不过滤）</summary>
    public string? Feature { get; set; }

    /// <summary>按任务名称模糊搜索（null 或空表示不过滤）</summary>
    public string? SearchText { get; set; }

    /// <summary>创建时间起始（null 表示不限制）</summary>
    public DateTime? From { get; set; }

    /// <summary>创建时间截止（null 表示不限制）</summary>
    public DateTime? To { get; set; }

    /// <summary>排序字段</summary>
    public JobSortBy SortBy { get; set; } = JobSortBy.CreatedAt;

    /// <summary>是否降序排列</summary>
    public bool SortDescending { get; set; } = true;

    /// <summary>分页：每页数量（0 表示不分页）</summary>
    public int PageSize { get; set; } = 0;

    /// <summary>分页：页码（0-based，仅在 PageSize > 0 时生效）</summary>
    public int Page { get; set; } = 0;

    /// <summary>
    /// 判断指定任务是否满足当前过滤条件
    /// </summary>
    public bool Matches(JobRecord job)
    {
        // 状态过滤
        if (Status.HasValue && job.Status != Status.Value)
            return false;

        // 功能码过滤
        if (!string.IsNullOrWhiteSpace(Feature) &&
            !string.Equals(job.Feature, Feature, StringComparison.OrdinalIgnoreCase))
            return false;

        // 文本搜索（任务名称包含搜索词）
        if (!string.IsNullOrWhiteSpace(SearchText) &&
            (string.IsNullOrEmpty(job.Name) ||
             !job.Name.Contains(SearchText, StringComparison.OrdinalIgnoreCase)))
            return false;

        // 日期范围过滤
        if (From.HasValue && job.CreatedAt < From.Value)
            return false;
        if (To.HasValue && job.CreatedAt > To.Value)
            return false;

        return true;
    }
}

/// <summary>
/// 任务列表排序字段
/// </summary>
public enum JobSortBy
{
    /// <summary>按创建时间</summary>
    CreatedAt,
    /// <summary>按完成时间</summary>
    CompletedAt,
    /// <summary>按任务名称</summary>
    Name,
    /// <summary>按任务状态</summary>
    Status,
    /// <summary>按功能码</summary>
    Feature
}
