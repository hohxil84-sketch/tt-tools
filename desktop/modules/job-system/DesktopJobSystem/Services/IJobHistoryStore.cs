using TTShared.JobSystem;

namespace TTTools.JobSystem.Services;

/// <summary>
/// 任务历史持久化存储接口
/// 定义任务记录的保存、加载和清除操作。
/// </summary>
public interface IJobHistoryStore
{
    /// <summary>
    /// 保存一条已完成的任务记录
    /// </summary>
    Task SaveAsync(JobRecord job);

    /// <summary>
    /// 加载所有历史任务记录
    /// </summary>
    Task<List<JobRecord>> LoadAsync();

    /// <summary>
    /// 清除所有历史记录
    /// </summary>
    Task ClearAsync();

    /// <summary>
    /// 当前历史记录数量
    /// </summary>
    int Count { get; }
}
