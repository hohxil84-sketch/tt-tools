using TTTools.JobSystem.Services;
using TTTools.JobSystem.ViewModels;
using TTShared.JobSystem;

namespace TTTools.JobSystem.Tests.ViewModels;

public class JobListViewModelTests
{
    [Fact]
    public async Task RefreshAsync_ShouldLoadActiveAndHistoryJobs()
    {
        var manager = new JobManager();
        manager.CreateJob("活动任务", "ocr_local");
        var completed = manager.CreateJob("已完成", "remove_bg_local");
        manager.UpdateJobStatus(completed.Id, JobStatus.Succeeded);

        var vm = new JobListViewModel(manager);
        await vm.RefreshAsync();

        Assert.Equal(2, vm.FilteredJobCount);
    }

    [Fact]
    public void JobStatusChanged_ShouldAddNewJob()
    {
        var manager = new JobManager();
        var vm = new JobListViewModel(manager);

        // CreateJob 不触发事件，需要通过 UpdateJobStatus 触发
        var job = manager.CreateJob("新任务", "ocr_local");
        manager.UpdateJobStatus(job.Id, JobStatus.Running); // 触发 JobStatusChanged

        Assert.Equal(1, vm.FilteredJobCount);
    }

    [Fact]
    public void FilterStatus_ShouldFilterCorrectly()
    {
        var manager = new JobManager();
        var failed = manager.CreateJob("失败任务", "ocr_local");
        manager.UpdateJobStatus(failed.Id, JobStatus.Failed, "错误");
        manager.CreateJob("排队任务", "ocr_local");

        var vm = new JobListViewModel(manager);
        vm.FilterStatus = JobStatus.Failed;

        Assert.Equal(1, vm.FilteredJobCount);
    }

    [Fact]
    public void FilterFeature_ShouldFilterCorrectly()
    {
        var manager = new JobManager();
        manager.CreateJob("OCR 任务", "ocr_local");
        manager.CreateJob("抠图任务", "remove_bg_local");

        var vm = new JobListViewModel(manager);
        vm.FilterFeature = "remove_bg_local";

        Assert.Equal(1, vm.FilteredJobCount);
    }

    [Fact]
    public void FilterSearchText_ShouldFilterByName()
    {
        var manager = new JobManager();
        manager.CreateJob("海报生成", "ai_copy_cloud");
        manager.CreateJob("宣传单文案", "ai_copy_cloud");

        var vm = new JobListViewModel(manager);
        vm.FilterSearchText = "海报";

        Assert.Equal(1, vm.FilteredJobCount);
    }

    [Fact]
    public void FilterStatus_Null_ShouldShowAll()
    {
        var manager = new JobManager();
        manager.CreateJob("任务1", "ocr_local");
        manager.CreateJob("任务2", "remove_bg_local");

        var vm = new JobListViewModel(manager);
        vm.FilterStatus = null; // 默认就是 null

        Assert.Equal(2, vm.FilteredJobCount);
    }

    [Fact]
    public async Task ClearHistoryAsync_ShouldRemoveCompletedJobs()
    {
        var manager = new JobManager();
        var active = manager.CreateJob("活动任务", "ocr_local");
        var completed = manager.CreateJob("已完成", "remove_bg_local");
        manager.UpdateJobStatus(completed.Id, JobStatus.Succeeded);

        var vm = new JobListViewModel(manager);
        // 先刷新以初始化 _allJobs
        await vm.RefreshAsync();
        Assert.Equal(2, vm.FilteredJobCount);

        await vm.ClearHistoryAsync();

        Assert.Equal(1, vm.FilteredJobCount); // 只有活动任务保留
    }

    [Fact]
    public async Task RetrySelected_ShouldCreateRetryJobs()
    {
        var manager = new JobManager();
        var retryService = new JobRetryService(manager);
        var vm = new JobListViewModel(manager, retryService: retryService);

        // 创建并标记失败任务
        var failed = manager.CreateJob("失败任务", "ocr_local");
        manager.UpdateJobStatus(failed.Id, JobStatus.Failed, "处理错误");

        // 直接通过 retryService 创建重试任务
        var originalJob = manager.FindJob(failed.Id);
        Assert.NotNull(originalJob);
        var retryJob = retryService.Retry(originalJob);
        Assert.NotNull(retryJob);

        // 重试任务应该在 manager 中（活动任务）
        Assert.Equal(1, manager.ActiveJobCount);

        // 刷新 VM 来同步 JobManager 状态
        await vm.RefreshAsync();

        // 应有 2 个任务：原始失败（历史）+ 重试排队（活动）
        Assert.Equal(2, vm.FilteredJobCount);
    }

    [Fact]
    public void ActiveJobCount_ShouldReflectManagerState()
    {
        var manager = new JobManager();
        var vm = new JobListViewModel(manager);

        Assert.Equal(0, vm.ActiveJobCount);

        manager.CreateJob("任务1", "ocr_local");
        Assert.Equal(1, vm.ActiveJobCount);

        manager.CreateJob("任务2", "remove_bg_local");
        Assert.Equal(2, vm.ActiveJobCount);

        var job = manager.CreateJob("任务3", "resize_image_local_paid");
        manager.UpdateJobStatus(job.Id, JobStatus.Succeeded);
        Assert.Equal(2, vm.ActiveJobCount); // 完成后移出活动列表
    }

    [Fact]
    public void JobReport_ShouldBeUpdatedOnRefresh()
    {
        var manager = new JobManager();
        manager.CreateJob("排队", "ocr_local");
        var done = manager.CreateJob("完成", "ocr_local");
        manager.UpdateJobStatus(done.Id, JobStatus.Succeeded);

        var vm = new JobListViewModel(manager);

        Assert.NotNull(vm.Report);
        Assert.Equal(1, vm.Report.Succeeded);
        Assert.Equal(1, vm.Report.Queued);
    }

    [Fact]
    public void DefaultConstructor_ShouldNotThrow()
    {
        var vm = new JobListViewModel();
        Assert.NotNull(vm);
        Assert.Equal(0, vm.FilteredJobCount);
    }
}
