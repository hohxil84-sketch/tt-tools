using TTTools.JobSystem.Services;
using TTShared.JobSystem;

namespace TTTools.JobSystem.Tests.Services;

public class JobRetryServiceTests
{
    [Fact]
    public void Retry_ShouldCreateNewJob_WhenFailedJobCanBeRetried()
    {
        var manager = new JobManager();
        var policy = new DefaultRetryPolicy(3);
        var service = new JobRetryService(manager, policy);

        var failedJob = manager.CreateJob("测试任务", "ocr_local");
        manager.UpdateJobStatus(failedJob.Id, JobStatus.Failed, "处理出错");

        var retryJob = service.Retry(failedJob);

        Assert.NotNull(retryJob);
        Assert.NotEqual(failedJob.Id, retryJob.Id);
        Assert.Equal(JobStatus.Queued, retryJob.Status);
        Assert.Equal(failedJob.Feature, retryJob.Feature);
    }

    [Fact]
    public void Retry_ShouldIncludeRetryCountInName()
    {
        var manager = new JobManager();
        var service = new JobRetryService(manager);

        var failedJob = manager.CreateJob("图片处理", "remove_bg_local");
        manager.UpdateJobStatus(failedJob.Id, JobStatus.Failed);

        var retryJob = service.Retry(failedJob);

        Assert.NotNull(retryJob);
        Assert.Contains("第1次重试", retryJob.Name);
    }

    [Fact]
    public void Retry_ShouldCopyInputFiles()
    {
        var manager = new JobManager();
        var service = new JobRetryService(manager);

        var failedJob = manager.CreateJob("批量处理", "resize_image_local_paid",
            new List<string> { "file1.jpg", "file2.png" });
        manager.UpdateJobStatus(failedJob.Id, JobStatus.Failed);

        var retryJob = service.Retry(failedJob);

        Assert.NotNull(retryJob);
        Assert.Equal(2, retryJob.InputFiles.Count);
        Assert.Contains("file1.jpg", retryJob.InputFiles);
        Assert.Contains("file2.png", retryJob.InputFiles);
    }

    [Fact]
    public void Retry_ShouldReturnNull_WhenNotFailed()
    {
        var manager = new JobManager();
        var service = new JobRetryService(manager);

        var runningJob = manager.CreateJob("运行中", "ocr_local");
        manager.UpdateJobStatus(runningJob.Id, JobStatus.Running);

        Assert.Null(service.Retry(runningJob));
    }

    [Fact]
    public void Retry_ShouldReturnNull_WhenSucceeded()
    {
        var manager = new JobManager();
        var service = new JobRetryService(manager);

        var successJob = manager.CreateJob("成功任务", "ocr_local");
        manager.UpdateJobStatus(successJob.Id, JobStatus.Succeeded);

        Assert.Null(service.Retry(successJob));
    }

    [Fact]
    public void Retry_ShouldReturnNull_WhenCancelled()
    {
        var manager = new JobManager();
        var service = new JobRetryService(manager);

        var cancelledJob = manager.CreateJob("已取消", "ocr_local");
        manager.UpdateJobStatus(cancelledJob.Id, JobStatus.Cancelled);

        Assert.Null(service.Retry(cancelledJob));
    }

    [Fact]
    public void Retry_ShouldReturnNull_WhenExceedsMaxRetryCount()
    {
        var policy = new DefaultRetryPolicy(2);
        var manager = new JobManager();
        var service = new JobRetryService(manager, policy);

        var failedJob = manager.CreateJob("失败任务", "ocr_local");
        manager.UpdateJobStatus(failedJob.Id, JobStatus.Failed);

        // 第一次重试
        var retry1 = service.Retry(failedJob);
        Assert.NotNull(retry1);
        manager.UpdateJobStatus(retry1.Id, JobStatus.Failed);

        // 第二次重试
        var retry2 = service.Retry(retry1);
        Assert.NotNull(retry2);

        // 第三次重试（超过 max=2）
        var retry3 = service.Retry(retry2);
        Assert.Null(retry3);
    }

    [Fact]
    public void GetRetryCount_ShouldTrackAcrossRetries()
    {
        var manager = new JobManager();
        var service = new JobRetryService(manager);

        var failedJob = manager.CreateJob("原始任务", "ocr_local");
        manager.UpdateJobStatus(failedJob.Id, JobStatus.Failed);

        Assert.Equal(0, service.GetRetryCount(failedJob.Id));

        var retryJob = service.Retry(failedJob);
        Assert.Equal(1, service.GetRetryCount(failedJob.Id));
        Assert.Equal(1, service.GetRetryCount(retryJob!.Id)); // 追溯原始任务
    }

    [Fact]
    public void CanRetry_ShouldReturnFalse_WhenNotFailed()
    {
        var manager = new JobManager();
        var service = new JobRetryService(manager);

        var successJob = manager.CreateJob("成功", "ocr_local");
        manager.UpdateJobStatus(successJob.Id, JobStatus.Succeeded);

        Assert.False(service.CanRetry(successJob));
    }

    [Fact]
    public void CanRetry_ShouldReturnTrue_WhenFailed()
    {
        var manager = new JobManager();
        var service = new JobRetryService(manager);

        var failedJob = manager.CreateJob("失败", "ocr_local");
        manager.UpdateJobStatus(failedJob.Id, JobStatus.Failed);

        Assert.True(service.CanRetry(failedJob));
    }

    [Fact]
    public void CanRetry_ShouldReturnFalse_WhenMaxRetriesReached()
    {
        var policy = new DefaultRetryPolicy(1);
        var manager = new JobManager();
        var service = new JobRetryService(manager, policy);

        var failedJob = manager.CreateJob("失败", "ocr_local");
        manager.UpdateJobStatus(failedJob.Id, JobStatus.Failed);

        var retry = service.Retry(failedJob);
        Assert.NotNull(retry);
        manager.UpdateJobStatus(retry.Id, JobStatus.Failed);

        // 已达到最大重试次数
        Assert.False(service.CanRetry(retry));
    }

    [Fact]
    public void Retry_ShouldFireJobRetriedEvent()
    {
        var manager = new JobManager();
        var service = new JobRetryService(manager);
        JobRecord? eventOriginal = null;
        JobRecord? eventRetry = null;
        service.JobRetried += (_, pair) =>
        {
            eventOriginal = pair.Original;
            eventRetry = pair.Retry;
        };

        var failedJob = manager.CreateJob("事件测试", "ocr_local");
        manager.UpdateJobStatus(failedJob.Id, JobStatus.Failed);

        var retryJob = service.Retry(failedJob);

        Assert.NotNull(eventOriginal);
        Assert.NotNull(eventRetry);
        Assert.Equal(failedJob.Id, eventOriginal!.Id);
        Assert.Equal(retryJob!.Id, eventRetry!.Id);
    }

    [Fact]
    public void DefaultRetryPolicy_MaxRetriesZero_ShouldNeverRetry()
    {
        var policy = new DefaultRetryPolicy(0);
        var manager = new JobManager();
        var service = new JobRetryService(manager, policy);

        var failedJob = manager.CreateJob("失败", "ocr_local");
        manager.UpdateJobStatus(failedJob.Id, JobStatus.Failed);

        Assert.False(service.CanRetry(failedJob));
        Assert.Null(service.Retry(failedJob));
    }

    [Fact]
    public void Retry_NullJob_ShouldThrowArgumentNullException()
    {
        var manager = new JobManager();
        var service = new JobRetryService(manager);

        Assert.Throws<ArgumentNullException>(() => service.Retry(null!));
    }
}
