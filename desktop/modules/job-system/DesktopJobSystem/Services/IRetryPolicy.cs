using TTShared.JobSystem;

namespace TTTools.JobSystem.Services;

/// <summary>
/// 重试策略接口
/// 定义任务重试的规则：是否可重试、重试次数、记录重试关系。
/// </summary>
public interface IRetryPolicy
{
    /// <summary>
    /// 判断指定失败任务是否可以重试
    /// </summary>
    /// <param name="failedJob">失败的任务记录</param>
    /// <returns>如果可以重试返回 true</returns>
    bool CanRetry(JobRecord failedJob);

    /// <summary>
    /// 获取某个原始任务已经重试的次数
    /// </summary>
    /// <param name="originalJobId">原始任务 ID</param>
    int GetRetryCount(string originalJobId);

    /// <summary>
    /// 记录一次重试关系
    /// </summary>
    /// <param name="originalJobId">原始任务 ID</param>
    /// <param name="retryJobId">重试任务 ID</param>
    void RecordRetry(string originalJobId, string retryJobId);

    /// <summary>
    /// 最大重试次数
    /// </summary>
    int MaxRetryCount { get; }
}
