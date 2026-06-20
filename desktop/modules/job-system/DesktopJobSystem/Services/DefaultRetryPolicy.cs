using System.Collections.Concurrent;
using TTShared.JobSystem;

namespace TTTools.JobSystem.Services;

/// <summary>
/// 默认重试策略
/// 限制每个失败任务最多重试指定次数，并在内存中记录重试关系。
/// </summary>
public class DefaultRetryPolicy : IRetryPolicy
{
    /// <summary>默认最大重试次数</summary>
    public const int DefaultMaxRetries = 3;

    /// <summary>最大重试次数</summary>
    public int MaxRetryCount { get; }

    /// <summary>
    /// 记录每个原始任务 ID 对应的重试任务 ID 列表
    /// Key = 原始任务 ID（如果是重试任务，key 是其最初的任务 ID）
    /// Value = 该原始任务所有重试任务 ID 列表
    /// </summary>
    private readonly ConcurrentDictionary<string, List<string>> _retryMap = new();

    /// <summary>
    /// 记录每个重试任务 ID 对应的原始任务 ID
    /// </summary>
    private readonly ConcurrentDictionary<string, string> _retryToOriginalMap = new();

    public DefaultRetryPolicy(int maxRetryCount = DefaultMaxRetries)
    {
        MaxRetryCount = Math.Max(0, maxRetryCount);
    }

    /// <summary>
    /// 判断任务是否可以重试
    /// 只有处于 Failed 状态且未超过最大重试次数才能重试。
    /// </summary>
    public bool CanRetry(JobRecord failedJob)
    {
        if (failedJob == null) return false;
        if (failedJob.Status != JobStatus.Failed) return false;
        if (MaxRetryCount <= 0) return false;

        // 找到这个任务的最原始任务 ID
        var originalId = GetOriginalJobId(failedJob.Id);
        var retryCount = GetRetryCount(originalId);

        return retryCount < MaxRetryCount;
    }

    /// <summary>
    /// 获取原始任务已重试的次数
    /// </summary>
    public int GetRetryCount(string originalJobId)
    {
        if (string.IsNullOrEmpty(originalJobId)) return 0;
        var rootId = GetOriginalJobId(originalJobId);
        return _retryMap.TryGetValue(rootId, out var retries) ? retries.Count : 0;
    }

    /// <summary>
    /// 记录一次重试关系
    /// </summary>
    public void RecordRetry(string originalJobId, string retryJobId)
    {
        if (string.IsNullOrEmpty(originalJobId) || string.IsNullOrEmpty(retryJobId))
            return;

        // 找到最原始的任务 ID
        var rootId = GetOriginalJobId(originalJobId);

        _retryToOriginalMap[retryJobId] = rootId;

        _retryMap.AddOrUpdate(
            rootId,
            _ => new List<string> { retryJobId },
            (_, list) =>
            {
                if (!list.Contains(retryJobId))
                    list.Add(retryJobId);
                return list;
            });
    }

    /// <summary>
    /// 获取任务的最原始 ID
    /// 如果该任务本身就是原始任务，返回自身 ID；
    /// 如果是重试任务，追溯其最初的原始任务 ID。
    /// </summary>
    private string GetOriginalJobId(string jobId)
    {
        // 如果该 ID 是某个重试任务，追溯其原始 ID
        if (_retryToOriginalMap.TryGetValue(jobId, out var originalId))
            return GetOriginalJobId(originalId); // 递归追溯

        return jobId;
    }
}
