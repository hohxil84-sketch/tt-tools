using TTTools.JobSystem.Models;
using TTTools.JobSystem.ViewModels;
using TTShared.JobSystem;

namespace TTTools.JobSystem.Tests.ViewModels;

public class JobStatsViewModelTests
{
    [Fact]
    public void UpdateFromReport_ShouldUpdateAllProperties()
    {
        var jobs = new List<JobRecord>
        {
            MakeJob(JobStatus.Succeeded),
            MakeJob(JobStatus.Succeeded),
            MakeJob(JobStatus.Failed),
            MakeJob(JobStatus.Queued)
        };
        var report = JobReport.FromJobs(jobs);
        var vm = new JobStatsViewModel();

        vm.UpdateFromReport(report);

        Assert.Equal(4, vm.Total);
        Assert.Equal(2, vm.Succeeded);
        Assert.Equal(1, vm.Failed);
        Assert.Equal(1, vm.Queued);
        Assert.Equal(0, vm.Running);
        Assert.Equal(0, vm.Cancelled);
        Assert.Equal(1, vm.ActiveCount); // 只有 Queued
        Assert.Equal(3, vm.CompletedCount); // Succeeded + Failed
        Assert.True(vm.HasFailed);
        Assert.True(vm.HasActive);
    }

    [Fact]
    public void UpdateFromReport_AllSucceeded_ShouldShow100Percent()
    {
        var jobs = new List<JobRecord>
        {
            MakeJob(JobStatus.Succeeded),
            MakeJob(JobStatus.Succeeded)
        };
        var report = JobReport.FromJobs(jobs);
        var vm = new JobStatsViewModel();
        vm.UpdateFromReport(report);

        Assert.Equal("100%", vm.SuccessRateDisplay);
        Assert.Equal("100%", vm.SuccessRateDisplay);
    }

    [Fact]
    public void UpdateFromReport_NoFailed_ShouldHaveHasFailedFalse()
    {
        var jobs = new List<JobRecord>
        {
            MakeJob(JobStatus.Succeeded),
            MakeJob(JobStatus.Queued)
        };
        var report = JobReport.FromJobs(jobs);
        var vm = new JobStatsViewModel();
        vm.UpdateFromReport(report);

        Assert.False(vm.HasFailed);
    }

    [Fact]
    public void UpdateFromReport_NoActive_ShouldHaveHasActiveFalse()
    {
        var jobs = new List<JobRecord>
        {
            MakeJob(JobStatus.Succeeded),
            MakeJob(JobStatus.Failed)
        };
        var report = JobReport.FromJobs(jobs);
        var vm = new JobStatsViewModel();
        vm.UpdateFromReport(report);

        Assert.False(vm.HasActive);
    }

    [Fact]
    public void UpdateFromReport_Null_ShouldThrow()
    {
        var vm = new JobStatsViewModel();
        Assert.Throws<ArgumentNullException>(() => vm.UpdateFromReport(null!));
    }

    [Fact]
    public void ShowFailedCommand_ShouldFireEvent()
    {
        var vm = new JobStatsViewModel();
        var fired = false;
        vm.ShowFailedRequested += (_, _) => fired = true;

        vm.ShowFailedCommand.Execute(null);
        Assert.True(fired);
    }

    [Fact]
    public void ShowActiveCommand_ShouldFireEvent()
    {
        var vm = new JobStatsViewModel();
        var fired = false;
        vm.ShowActiveRequested += (_, _) => fired = true;

        vm.ShowActiveCommand.Execute(null);
        Assert.True(fired);
    }

    [Fact]
    public void ShowAllCommand_ShouldFireEvent()
    {
        var vm = new JobStatsViewModel();
        var fired = false;
        vm.ShowAllRequested += (_, _) => fired = true;

        vm.ShowAllCommand.Execute(null);
        Assert.True(fired);
    }

    [Fact]
    public void FailureRateDisplay_AllFailed_ShouldBe100()
    {
        var jobs = new List<JobRecord>
        {
            MakeJob(JobStatus.Failed),
            MakeJob(JobStatus.Failed)
        };
        var report = JobReport.FromJobs(jobs);
        var vm = new JobStatsViewModel();
        vm.UpdateFromReport(report);

        Assert.Equal("100%", vm.FailureRateDisplay);
    }

    [Fact]
    public void FailureRateDisplay_NoJobs_ShouldBe0()
    {
        var report = JobReport.FromJobs(Array.Empty<JobRecord>());
        var vm = new JobStatsViewModel();
        vm.UpdateFromReport(report);

        Assert.Equal("0%", vm.FailureRateDisplay);
    }

    [Fact]
    public void Summary_ShouldContainKeyNumbers()
    {
        var jobs = new List<JobRecord>
        {
            MakeJob(JobStatus.Succeeded), MakeJob(JobStatus.Succeeded),
            MakeJob(JobStatus.Failed)
        };
        var report = JobReport.FromJobs(jobs);
        var vm = new JobStatsViewModel();
        vm.UpdateFromReport(report);

        Assert.Contains("3", vm.Summary); // Total
        Assert.Contains("2", vm.Summary); // Succeeded
        Assert.Contains("1", vm.Summary); // Failed
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
