using TTTools.JobSystem.Models;
using TTShared.JobSystem;

namespace TTTools.JobSystem.Tests.Models;

public class JobFilterOptionsTests
{
    [Fact]
    public void Matches_NoFilter_ShouldMatchAll()
    {
        var filter = new JobFilterOptions();
        var job = CreateJob(JobStatus.Queued, "ocr_local");

        Assert.True(filter.Matches(job));
    }

    [Fact]
    public void Matches_StatusFilter_ShouldMatchOnlySpecifiedStatus()
    {
        var filter = new JobFilterOptions { Status = JobStatus.Failed };
        var failedJob = CreateJob(JobStatus.Failed, "ocr_local");
        var queuedJob = CreateJob(JobStatus.Queued, "ocr_local");

        Assert.True(filter.Matches(failedJob));
        Assert.False(filter.Matches(queuedJob));
    }

    [Fact]
    public void Matches_FeatureFilter_ShouldMatchOnlySpecifiedFeature()
    {
        var filter = new JobFilterOptions { Feature = "remove_bg_local" };
        var matchingJob = CreateJob(JobStatus.Succeeded, "remove_bg_local");
        var nonMatchingJob = CreateJob(JobStatus.Succeeded, "ocr_local");

        Assert.True(filter.Matches(matchingJob));
        Assert.False(filter.Matches(nonMatchingJob));
    }

    [Fact]
    public void Matches_FeatureFilter_ShouldBeCaseInsensitive()
    {
        var filter = new JobFilterOptions { Feature = "REMOVE_BG_LOCAL" };
        var job = CreateJob(JobStatus.Succeeded, "remove_bg_local");

        Assert.True(filter.Matches(job));
    }

    [Fact]
    public void Matches_SearchText_ShouldMatchNameContains()
    {
        var filter = new JobFilterOptions { SearchText = "海报" };
        var matchingJob = CreateJob(JobStatus.Queued, "ai_copy_cloud", "生成海报文案");
        var nonMatchingJob = CreateJob(JobStatus.Queued, "ai_copy_cloud", "生成宣传单");

        Assert.True(filter.Matches(matchingJob));
        Assert.False(filter.Matches(nonMatchingJob));
    }

    [Fact]
    public void Matches_SearchText_ShouldBeCaseInsensitive()
    {
        var filter = new JobFilterOptions { SearchText = "POSTER" };
        var job = CreateJob(JobStatus.Queued, "ai_copy_cloud", "Poster Design");

        Assert.True(filter.Matches(job));
    }

    [Fact]
    public void Matches_DateRange_ShouldFilterByCreatedAt()
    {
        var filter = new JobFilterOptions
        {
            From = new DateTime(2026, 6, 1),
            To = new DateTime(2026, 6, 15)
        };

        var inRange = CreateJobWithDate(JobStatus.Succeeded, "test", new DateTime(2026, 6, 10));
        var beforeRange = CreateJobWithDate(JobStatus.Succeeded, "test", new DateTime(2026, 5, 20));
        var afterRange = CreateJobWithDate(JobStatus.Succeeded, "test", new DateTime(2026, 6, 20));

        Assert.True(filter.Matches(inRange));
        Assert.False(filter.Matches(beforeRange));
        Assert.False(filter.Matches(afterRange));
    }

    [Fact]
    public void Matches_CombinedFilters_ShouldMatchAllConditions()
    {
        var filter = new JobFilterOptions
        {
            Status = JobStatus.Failed,
            Feature = "ocr_local",
            SearchText = "测试"
        };

        var matching = CreateJob(JobStatus.Failed, "ocr_local", "测试任务");
        var wrongStatus = CreateJob(JobStatus.Succeeded, "ocr_local", "测试任务");
        var wrongFeature = CreateJob(JobStatus.Failed, "remove_bg_local", "测试任务");
        var wrongName = CreateJob(JobStatus.Failed, "ocr_local", "其他任务");

        Assert.True(filter.Matches(matching));
        Assert.False(filter.Matches(wrongStatus));
        Assert.False(filter.Matches(wrongFeature));
        Assert.False(filter.Matches(wrongName));
    }

    [Fact]
    public void Matches_NullFeatureAndSearchText_ShouldNotFilter()
    {
        var filter = new JobFilterOptions { Feature = null, SearchText = null };
        var job = CreateJob(JobStatus.Succeeded, "ocr_local", "测试");

        Assert.True(filter.Matches(job));
    }

    [Fact]
    public void Matches_EmptySearchText_ShouldNotFilter()
    {
        var filter = new JobFilterOptions { SearchText = "" };
        var job = CreateJob(JobStatus.Succeeded, "ocr_local", "测试");

        Assert.True(filter.Matches(job));
    }

    [Fact]
    public void Matches_NullJobName_ShouldNotMatchSearchText()
    {
        var filter = new JobFilterOptions { SearchText = "搜索" };
        var job = new JobRecord
        {
            Name = null!,
            Feature = "test",
            Status = JobStatus.Queued,
            CreatedAt = DateTime.UtcNow
        };

        Assert.False(filter.Matches(job));
    }

    // ==================== Helpers ====================

    private static JobRecord CreateJob(JobStatus status, string feature, string name = "测试任务")
    {
        return new JobRecord
        {
            Name = name,
            Feature = feature,
            Status = status,
            CreatedAt = DateTime.UtcNow
        };
    }

    private static JobRecord CreateJobWithDate(JobStatus status, string feature, DateTime createdAt)
    {
        return new JobRecord
        {
            Name = "测试任务",
            Feature = feature,
            Status = status,
            CreatedAt = createdAt
        };
    }
}
