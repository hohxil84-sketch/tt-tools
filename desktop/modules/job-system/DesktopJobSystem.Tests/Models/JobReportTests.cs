using TTTools.JobSystem.Models;
using TTShared.JobSystem;

namespace TTTools.JobSystem.Tests.Models;

public class JobReportTests
{
    [Fact]
    public void FromJobs_EmptyList_ShouldReturnZeroReport()
    {
        var report = JobReport.FromJobs(Array.Empty<JobRecord>());

        Assert.Equal(0, report.Total);
        Assert.Equal(0, report.Succeeded);
        Assert.Equal(0, report.Failed);
        Assert.Equal(0, report.Cancelled);
        Assert.Equal(0, report.Running);
        Assert.Equal(0, report.Queued);
        Assert.Equal(0, report.SuccessRate);
    }

    [Fact]
    public void FromJobs_ShouldCountEachStatus()
    {
        var jobs = new List<JobRecord>
        {
            MakeJob(JobStatus.Succeeded),
            MakeJob(JobStatus.Succeeded),
            MakeJob(JobStatus.Failed),
            MakeJob(JobStatus.Cancelled),
            MakeJob(JobStatus.Running),
            MakeJob(JobStatus.Queued),
            MakeJob(JobStatus.Queued)
        };

        var report = JobReport.FromJobs(jobs);

        Assert.Equal(7, report.Total);
        Assert.Equal(2, report.Succeeded);
        Assert.Equal(1, report.Failed);
        Assert.Equal(1, report.Cancelled);
        Assert.Equal(1, report.Running);
        Assert.Equal(2, report.Queued);
    }

    [Fact]
    public void SuccessRate_AllSucceeded_ShouldBe100()
    {
        var jobs = new List<JobRecord>
        {
            MakeJob(JobStatus.Succeeded),
            MakeJob(JobStatus.Succeeded),
            MakeJob(JobStatus.Succeeded)
        };

        var report = JobReport.FromJobs(jobs);

        Assert.Equal(100, report.SuccessRate);
    }

    [Fact]
    public void SuccessRate_AllFailed_ShouldBe0()
    {
        var jobs = new List<JobRecord>
        {
            MakeJob(JobStatus.Failed),
            MakeJob(JobStatus.Failed)
        };

        var report = JobReport.FromJobs(jobs);

        Assert.Equal(0, report.SuccessRate);
    }

    [Fact]
    public void SuccessRate_MixedResults_ShouldCalculateCorrectly()
    {
        var jobs = new List<JobRecord>
        {
            MakeJob(JobStatus.Succeeded),
            MakeJob(JobStatus.Succeeded),
            MakeJob(JobStatus.Failed),
            MakeJob(JobStatus.Cancelled)
        };

        var report = JobReport.FromJobs(jobs);

        Assert.Equal(50, report.SuccessRate); // 2/4 = 50%
    }

    private static JobRecord MakeJob(JobStatus status)
    {
        return new JobRecord
        {
            Name = "测试任务",
            Feature = "test",
            Status = status,
            CreatedAt = DateTime.UtcNow
        };
    }
}
