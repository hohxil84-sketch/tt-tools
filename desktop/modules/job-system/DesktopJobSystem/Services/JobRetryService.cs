using TTShared.JobSystem;
using TTShared.Logging;

namespace TTTools.JobSystem.Services;

/// <summary>
/// 任务重试服务
/// 对失败任务执行重试操作：检查重试策略、创建重试任务、
/// 记录重试关系并通知调用方。
/// </summary>
public class JobRetryService
{
    private readonly JobManager _jobManager;
    private readonly IRetryPolicy _retryPolicy;
    private readonly AppLogger? _logger;

    /// <summary>
    /// 重试任务创建成功事件。参数为 (原始任务, 新重试任务)。
    /// </summary>
    public event EventHandler<(JobRecord Original, JobRecord Retry)>? JobRetried;

    public JobRetryService(JobManager jobManager, IRetryPolicy? retryPolicy = null,
        AppLogger? logger = null)
    {
        _jobManager = jobManager ?? throw new ArgumentNullException(nameof(jobManager));
        _retryPolicy = retryPolicy ?? new DefaultRetryPolicy();
        _logger = logger;
    }

    /// <summary>
    /// 重试一个失败的任务
    /// 检查重试策略后，创建新的 Quoued 状态任务，保留原始输入文件。
    /// </summary>
    /// <param name="failedJob">要重试的失败任务</param>
    /// <returns>新创建的重试任务；如果不满足重试条件则返回 null</returns>
    public JobRecord? Retry(JobRecord failedJob)
    {
        if (failedJob == null) throw new ArgumentNullException(nameof(failedJob));

        // 检查重试策略
        if (!_retryPolicy.CanRetry(failedJob))
        {
            _logger?.Warning(
                $"任务 {failedJob.Id} 不满足重试条件：状态={failedJob.Status}，" +
                $"已重试次数={_retryPolicy.GetRetryCount(failedJob.Id)}，" +
                $"最大重试次数={_retryPolicy.MaxRetryCount}",
                "job-system");
            return null;
        }

        // 生成重试任务名称
        var retryCount = _retryPolicy.GetRetryCount(failedJob.Id) + 1;
        var retryName = GenerateRetryName(failedJob.Name, retryCount);

        // 通过 JobManager 创建新的排队任务
        var retryJob = _jobManager.CreateJob(
            retryName,
            failedJob.Feature,
            new List<string>(failedJob.InputFiles)); // 复制输入文件列表

        // 记录重试关系
        _retryPolicy.RecordRetry(failedJob.Id, retryJob.Id);

        _logger?.Info(
            $"任务重试：原始={failedJob.Id} → 重试={retryJob.Id}，" +
            $"第 {retryCount} 次重试，任务名={retryName}",
            "job-system");

        JobRetried?.Invoke(this, (failedJob, retryJob));
        return retryJob;
    }

    /// <summary>
    /// 获取某个任务已重试的次数
    /// </summary>
    public int GetRetryCount(string jobId)
        => _retryPolicy.GetRetryCount(jobId);

    /// <summary>
    /// 判断任务是否可以重试
    /// </summary>
    public bool CanRetry(JobRecord job)
        => _retryPolicy.CanRetry(job);

    /// <summary>
    /// 生成重试任务名称
    /// 格式：原名称 + "（第N次重试）"
    /// 如果名称已包含重试后缀，则替换为新的。
    /// </summary>
    private static string GenerateRetryName(string originalName, int retryCount)
    {
        if (string.IsNullOrWhiteSpace(originalName))
            return $"重试任务（第{retryCount}次）";

        // 移除已有的重试后缀
        var cleanName = originalName;
        var retrySuffixPattern = "（第";
        var idx = cleanName.LastIndexOf(retrySuffixPattern, StringComparison.Ordinal);
        if (idx > 0)
        {
            var endIdx = cleanName.IndexOf("次重试）", idx, StringComparison.Ordinal);
            if (endIdx > idx)
                cleanName = cleanName[..idx].TrimEnd();
        }

        return $"{cleanName}（第{retryCount}次重试）";
    }
}
