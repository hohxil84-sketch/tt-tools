using TTTools.JobSystem.Services;
using TTShared.JobSystem;

namespace TTTools.JobSystem.Tests.Services;

public class JobHistoryStoreTests : IDisposable
{
    private readonly string _testStoragePath;

    public JobHistoryStoreTests()
    {
        _testStoragePath = Path.Combine(Path.GetTempPath(),
            $"tttools_job_history_test_{Guid.NewGuid():N}.json");
    }

    public void Dispose()
    {
        // 清理测试文件
        if (File.Exists(_testStoragePath))
        {
            try { File.Delete(_testStoragePath); } catch { /* 忽略清理错误 */ }
        }
    }

    [Fact]
    public async Task SaveAsync_ShouldPersistCompletedJob()
    {
        using var store = new JobHistoryStore(_testStoragePath, 100);
        var job = CreateCompletedJob("job-1", JobStatus.Succeeded);

        await store.SaveAsync(job);
        var loaded = await store.LoadAsync();

        Assert.Single(loaded);
        Assert.Equal("job-1", loaded[0].Id);
        Assert.Equal(JobStatus.Succeeded, loaded[0].Status);
    }

    [Fact]
    public async Task SaveAsync_ShouldNotPersistActiveJob()
    {
        using var store = new JobHistoryStore(_testStoragePath, 100);
        var job = new JobRecord
        {
            Id = "active-job",
            Name = "运行中任务",
            Status = JobStatus.Running,
            Feature = "test",
            CreatedAt = DateTime.UtcNow
        };

        await store.SaveAsync(job);
        // 加载后应该为空（活动任务不持久化）
        var loaded = await store.LoadAsync();

        Assert.Empty(loaded);
    }

    [Fact]
    public async Task SaveMultipleJobs_ShouldPersistAll()
    {
        using var store = new JobHistoryStore(_testStoragePath, 100);

        for (int i = 0; i < 5; i++)
        {
            var job = CreateCompletedJob($"job-{i}", JobStatus.Succeeded);
            await store.SaveAsync(job);
        }

        var loaded = await store.LoadAsync();
        Assert.Equal(5, loaded.Count);
        Assert.Equal(5, store.Count);
    }

    [Fact]
    public async Task SaveAsync_ShouldEnforceMaxHistorySize()
    {
        const int maxSize = 3;
        using var store = new JobHistoryStore(_testStoragePath, maxSize);

        for (int i = 0; i < 5; i++)
        {
            var job = CreateCompletedJob($"job-{i}", JobStatus.Succeeded,
                completedAt: DateTime.UtcNow.AddMinutes(-(5 - i))); // 递增完成时间
            await store.SaveAsync(job);
        }

        var loaded = await store.LoadAsync();
        Assert.Equal(maxSize, loaded.Count);
        Assert.Equal(maxSize, store.Count);
    }

    [Fact]
    public async Task ClearAsync_ShouldRemoveAllHistory()
    {
        using var store = new JobHistoryStore(_testStoragePath, 100);
        await store.SaveAsync(CreateCompletedJob("job-1", JobStatus.Succeeded));
        await store.SaveAsync(CreateCompletedJob("job-2", JobStatus.Failed));
        Assert.Equal(2, store.Count);

        await store.ClearAsync();
        Assert.Equal(0, store.Count);

        var loaded = await store.LoadAsync();
        Assert.Empty(loaded);
    }

    [Fact]
    public async Task LoadAsync_ShouldReturnInCompletionOrder()
    {
        using var store = new JobHistoryStore(_testStoragePath, 100);
        var older = CreateCompletedJob("older", JobStatus.Succeeded,
            completedAt: new DateTime(2026, 1, 1));
        var newer = CreateCompletedJob("newer", JobStatus.Succeeded,
            completedAt: new DateTime(2026, 6, 1));

        await store.SaveAsync(older);
        await store.SaveAsync(newer);

        var loaded = await store.LoadAsync();
        Assert.Equal("newer", loaded[0].Id); // 较新的在前
        Assert.Equal("older", loaded[1].Id);
    }

    [Fact]
    public async Task SaveAsync_NullJob_ShouldThrowArgumentNullException()
    {
        using var store = new JobHistoryStore(_testStoragePath, 100);
        await Assert.ThrowsAsync<ArgumentNullException>(() => store.SaveAsync(null!));
    }

    [Fact]
    public async Task SaveAsync_ShouldPreserveAllFields()
    {
        using var store = new JobHistoryStore(_testStoragePath, 100);
        var job = new JobRecord
        {
            Id = "full-job",
            Name = "完整测试任务",
            Feature = "ocr_local_paid",
            Status = JobStatus.Failed,
            Progress = 75,
            InputFiles = new List<string> { "input1.jpg", "input2.png" },
            OutputFiles = new List<string> { "output1.pdf" },
            ErrorMessage = "文件格式不支持",
            ResultMessage = "处理中止",
            CreatedAt = new DateTime(2026, 6, 20, 10, 0, 0, DateTimeKind.Utc),
            CompletedAt = new DateTime(2026, 6, 20, 10, 5, 0, DateTimeKind.Utc)
        };

        await store.SaveAsync(job);
        var loaded = await store.LoadAsync();
        var restored = loaded[0];

        Assert.Equal(job.Id, restored.Id);
        Assert.Equal(job.Name, restored.Name);
        Assert.Equal(job.Feature, restored.Feature);
        Assert.Equal(job.Status, restored.Status);
        Assert.Equal(job.Progress, restored.Progress);
        Assert.Equal(job.InputFiles.Count, restored.InputFiles.Count);
        Assert.Equal(job.OutputFiles.Count, restored.OutputFiles.Count);
        Assert.Equal(job.ErrorMessage, restored.ErrorMessage);
        Assert.Equal(job.ResultMessage, restored.ResultMessage);
        Assert.Equal(job.CreatedAt, restored.CreatedAt);
        Assert.Equal(job.CompletedAt, restored.CompletedAt);
    }

    [Fact]
    public async Task LoadAsync_NonExistentFile_ShouldReturnEmptyList()
    {
        using var store = new JobHistoryStore(_testStoragePath, 100);
        var loaded = await store.LoadAsync();
        Assert.Empty(loaded);
    }

    // ==================== Helpers ====================

    private static JobRecord CreateCompletedJob(string id, JobStatus status,
        DateTime? completedAt = null)
    {
        return new JobRecord
        {
            Id = id,
            Name = $"测试任务 {id}",
            Feature = "ocr_local",
            Status = status,
            Progress = 100,
            CreatedAt = DateTime.UtcNow.AddHours(-1),
            CompletedAt = completedAt ?? DateTime.UtcNow
        };
    }
}
