using TTShared.JobSystem;

namespace TTShared.Tests.JobSystem;

public class JobManagerTests
{
    [Fact]
    public void CreateJob_ShouldReturnQueuedJob()
    {
        var manager = new JobManager();
        var job = manager.CreateJob("测试任务", "ocr_local");

        Assert.NotNull(job);
        Assert.Equal("测试任务", job.Name);
        Assert.Equal("ocr_local", job.Feature);
        Assert.Equal(JobStatus.Queued, job.Status);
        Assert.False(job.IsCompleted);
        Assert.False(string.IsNullOrEmpty(job.Id));
    }

    [Fact]
    public void CreateJob_ShouldIncludeInputFiles()
    {
        var manager = new JobManager();
        var files = new List<string> { "file1.jpg", "file2.png" };
        var job = manager.CreateJob("批量处理", "resize_image_local_paid", files);

        Assert.Equal(2, job.InputFiles.Count);
        Assert.Contains("file1.jpg", job.InputFiles);
    }

    [Fact]
    public void UpdateJobStatus_ShouldChangeStateAndMoveHistory()
    {
        var manager = new JobManager();
        JobRecord? completedJob = null;
        manager.JobCompleted += (_, j) => completedJob = j;

        var job = manager.CreateJob("任务", "ocr_local");
        manager.UpdateJobStatus(job.Id, JobStatus.Running);
        Assert.Equal(JobStatus.Running, job.Status);

        manager.UpdateJobStatus(job.Id, JobStatus.Succeeded, "处理完成");
        Assert.Equal(JobStatus.Succeeded, job.Status);
        Assert.Equal("处理完成", job.ResultMessage);
        Assert.True(job.IsCompleted);
        Assert.NotNull(completedJob);

        // 成功后应从活动任务中移除
        Assert.Equal(0, manager.ActiveJobCount);
    }

    [Fact]
    public void UpdateJobStatus_Failed_ShouldSetErrorMessage()
    {
        var manager = new JobManager();
        var job = manager.CreateJob("失败任务", "remove_bg_local");
        manager.UpdateJobStatus(job.Id, JobStatus.Failed, "文件格式不支持");

        Assert.Equal(JobStatus.Failed, job.Status);
        Assert.Equal("文件格式不支持", job.ErrorMessage);
        Assert.True(job.HasError);
    }

    [Fact]
    public void CancelJob_ShouldSetCancelledStatus()
    {
        var manager = new JobManager();
        var job = manager.CreateJob("可取消任务", "ocr_local");
        var result = manager.CancelJob(job.Id);

        Assert.True(result);
        Assert.Equal(JobStatus.Cancelled, job.Status);
    }

    [Fact]
    public void CancelJob_ShouldReturnFalse_WhenAlreadyCompleted()
    {
        var manager = new JobManager();
        var job = manager.CreateJob("已完成任务", "ocr_local");
        manager.UpdateJobStatus(job.Id, JobStatus.Succeeded);

        var result = manager.CancelJob(job.Id);
        Assert.False(result);
    }

    [Fact]
    public void UpdateJobProgress_ShouldClampValues()
    {
        var manager = new JobManager();
        var job = manager.CreateJob("进度测试", "ocr_local");

        manager.UpdateJobProgress(job.Id, 50);
        Assert.Equal(50, job.Progress);

        manager.UpdateJobProgress(job.Id, 150); // 应被限制为 100
        Assert.Equal(100, job.Progress);

        manager.UpdateJobProgress(job.Id, -10); // 应被限制为 0
        Assert.Equal(0, job.Progress);
    }

    [Fact]
    public void FindJob_ShouldReturnFromActiveOrHistory()
    {
        var manager = new JobManager();
        var job = manager.CreateJob("查找测试", "ocr_local");
        Assert.Same(job, manager.FindJob(job.Id));

        manager.UpdateJobStatus(job.Id, JobStatus.Succeeded);
        // 完成后仍在历史中可查找
        Assert.Same(job, manager.FindJob(job.Id));
    }

    [Fact]
    public void FindJob_ShouldReturnNull_WhenNotFound()
    {
        var manager = new JobManager();
        Assert.Null(manager.FindJob("non_existent_id"));
    }

    [Fact]
    public void GetActiveJobs_ShouldReturnOnlyActive()
    {
        var manager = new JobManager();
        var j1 = manager.CreateJob("活动任务1", "ocr_local");
        var j2 = manager.CreateJob("活动任务2", "remove_bg_local");

        var active = manager.GetActiveJobs();
        Assert.Equal(2, active.Count);

        manager.UpdateJobStatus(j1.Id, JobStatus.Succeeded);
        Assert.Single(manager.GetActiveJobs());
    }

    [Fact]
    public void GetHistory_ShouldReturnCompletedJobs()
    {
        var manager = new JobManager();
        var job = manager.CreateJob("历史任务", "ocr_local");
        manager.UpdateJobStatus(job.Id, JobStatus.Succeeded);

        var history = manager.GetHistory();
        Assert.Single(history);
        Assert.Equal(job.Id, history[0].Id);
    }

    [Fact]
    public void JobRecord_INotifyPropertyChanged_ShouldFire()
    {
        var job = new JobRecord();
        var changedProps = new List<string>();
        job.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName ?? "");

        job.Status = JobStatus.Running;
        job.Progress = 50;
        job.ErrorMessage = "错误";

        Assert.Contains("Status", changedProps);
        Assert.Contains("Progress", changedProps);
        Assert.Contains("ErrorMessage", changedProps);
    }
}
