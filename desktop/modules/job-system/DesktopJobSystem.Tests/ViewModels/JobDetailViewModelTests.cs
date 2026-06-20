using TTTools.JobSystem.ViewModels;
using TTShared.JobSystem;

namespace TTTools.JobSystem.Tests.ViewModels;

public class JobDetailViewModelTests
{
    [Fact]
    public void Constructor_ShouldWrapAllJobProperties()
    {
        var job = new JobRecord
        {
            Id = "test-1",
            Name = "测试任务",
            Feature = "ocr_local",
            Status = JobStatus.Running,
            Progress = 50,
            CreatedAt = new DateTime(2026, 6, 20, 10, 0, 0, DateTimeKind.Utc)
        };

        var vm = new JobDetailViewModel(job);

        Assert.Equal("test-1", vm.JobId);
        Assert.Equal("测试任务", vm.JobName);
        Assert.Equal("ocr_local", vm.Feature);
        Assert.Equal(JobStatus.Running, vm.Status);
        Assert.Equal(50, vm.Progress);
        Assert.Equal("运行中", vm.StatusDisplay);
        Assert.Equal("🔄", vm.StatusIcon);
        Assert.Equal("50%", vm.ProgressDisplay);
        Assert.False(vm.IsCompleted);
        Assert.True(vm.IsRunning);
    }

    [Fact]
    public void StatusDisplay_ShouldReturnChineseForEachStatus()
    {
        var testCases = new[]
        {
            (JobStatus.Queued, "排队中"),
            (JobStatus.Running, "运行中"),
            (JobStatus.Succeeded, "已完成"),
            (JobStatus.Failed, "已失败"),
            (JobStatus.Cancelled, "已取消")
        };

        foreach (var (status, expected) in testCases)
        {
            var job = new JobRecord { Status = status, Name = "test", Feature = "test" };
            var vm = new JobDetailViewModel(job);
            Assert.Equal(expected, vm.StatusDisplay);
        }
    }

    [Fact]
    public void DurationDisplay_WithoutCompletedAt_ShouldReturnDash()
    {
        var job = new JobRecord
        {
            Name = "test",
            Feature = "test",
            Status = JobStatus.Running
        };
        var vm = new JobDetailViewModel(job);

        Assert.Equal("—", vm.DurationDisplay);
    }

    [Fact]
    public void DurationDisplay_ShortDuration_ShouldShowSeconds()
    {
        var job = new JobRecord
        {
            Name = "test",
            Feature = "test",
            Status = JobStatus.Succeeded,
            CreatedAt = new DateTime(2026, 1, 1, 10, 0, 0, DateTimeKind.Utc),
            CompletedAt = new DateTime(2026, 1, 1, 10, 0, 30, DateTimeKind.Utc) // 30秒
        };
        var vm = new JobDetailViewModel(job);

        Assert.Contains("30", vm.DurationDisplay);
        Assert.Contains("秒", vm.DurationDisplay);
    }

    [Fact]
    public void CanRetry_ShouldOnlyBeTrue_WhenFailedAndAllowed()
    {
        var failedJob = new JobRecord
        {
            Name = "失败",
            Feature = "test",
            Status = JobStatus.Failed
        };
        var canRetryVm = new JobDetailViewModel(failedJob, canRetry: true);
        var cannotRetryVm = new JobDetailViewModel(failedJob, canRetry: false);

        Assert.True(canRetryVm.CanRetry);
        Assert.False(cannotRetryVm.CanRetry);
    }

    [Fact]
    public void CanRetry_ShouldBeFalse_WhenNotFailed_EvenIfAllowed()
    {
        var successJob = new JobRecord
        {
            Name = "成功",
            Feature = "test",
            Status = JobStatus.Succeeded
        };
        var vm = new JobDetailViewModel(successJob, canRetry: true);

        Assert.False(vm.CanRetry); // 只有失败任务才能重试
    }

    [Fact]
    public void ToggleSelect_ShouldToggleIsSelected()
    {
        var job = new JobRecord { Name = "test", Feature = "test", Status = JobStatus.Queued };
        var vm = new JobDetailViewModel(job);

        Assert.False(vm.IsSelected);
        vm.ToggleSelect();
        Assert.True(vm.IsSelected);
        vm.ToggleSelect();
        Assert.False(vm.IsSelected);
    }

    [Fact]
    public void PropertyChanged_ShouldForwardFromJobRecord()
    {
        var job = new JobRecord
        {
            Name = "原始",
            Feature = "test",
            Status = JobStatus.Queued
        };
        var vm = new JobDetailViewModel(job);
        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName ?? "");

        job.Status = JobStatus.Running;
        Assert.Contains(nameof(vm.Status), changedProps);
        Assert.Contains(nameof(vm.StatusDisplay), changedProps);
        Assert.Contains(nameof(vm.IsRunning), changedProps);

        job.Progress = 75;
        Assert.Contains(nameof(vm.Progress), changedProps);
        Assert.Contains(nameof(vm.ProgressDisplay), changedProps);

        job.ErrorMessage = "错误";
        Assert.Contains(nameof(vm.ErrorMessage), changedProps);
    }

    [Fact]
    public void GetJobRecord_ShouldReturnOriginalJob()
    {
        var job = new JobRecord { Name = "test", Feature = "test", Status = JobStatus.Queued };
        var vm = new JobDetailViewModel(job);

        Assert.Same(job, vm.GetJobRecord());
    }

    [Fact]
    public void NullJob_ShouldThrowArgumentNullException()
    {
        Assert.Throws<ArgumentNullException>(() => new JobDetailViewModel(null!));
    }
}
