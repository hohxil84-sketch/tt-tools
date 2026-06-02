using System.Collections.Concurrent;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace TTShared.JobSystem;

/// <summary>
/// 任务状态枚举
/// </summary>
public enum JobStatus
{
    /// <summary>排队中</summary>
    Queued,
    /// <summary>运行中</summary>
    Running,
    /// <summary>已完成</summary>
    Succeeded,
    /// <summary>已失败</summary>
    Failed,
    /// <summary>已取消</summary>
    Cancelled
}

/// <summary>
/// 任务记录
/// 表示一个本地处理任务的完整状态。
/// </summary>
public class JobRecord : INotifyPropertyChanged
{
    private JobStatus _status = JobStatus.Queued;
    private int _progress;
    private string? _errorMessage;
    private string? _resultMessage;

    /// <summary>任务 ID</summary>
    public string Id { get; set; } = Guid.NewGuid().ToString("N");

    /// <summary>任务名称（用于展示）</summary>
    public string Name { get; set; } = string.Empty;

    /// <summary>功能码</summary>
    public string Feature { get; set; } = string.Empty;

    /// <summary>当前状态</summary>
    public JobStatus Status
    {
        get => _status;
        set { _status = value; OnPropertyChanged(); OnPropertyChanged(nameof(IsCompleted)); }
    }

    /// <summary>进度百分比（0-100）</summary>
    public int Progress
    {
        get => _progress;
        set { _progress = Math.Clamp(value, 0, 100); OnPropertyChanged(); }
    }

    /// <summary>输入文件路径列表</summary>
    public List<string> InputFiles { get; set; } = new();

    /// <summary>输出文件路径列表</summary>
    public List<string> OutputFiles { get; set; } = new();

    /// <summary>错误消息</summary>
    public string? ErrorMessage
    {
        get => _errorMessage;
        set { _errorMessage = value; OnPropertyChanged(); OnPropertyChanged(nameof(HasError)); }
    }

    /// <summary>结果消息</summary>
    public string? ResultMessage
    {
        get => _resultMessage;
        set { _resultMessage = value; OnPropertyChanged(); }
    }

    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    /// <summary>完成时间</summary>
    public DateTime? CompletedAt { get; set; }

    /// <summary>是否已完成（成功、失败或取消）</summary>
    public bool IsCompleted =>
        Status == JobStatus.Succeeded ||
        Status == JobStatus.Failed ||
        Status == JobStatus.Cancelled;

    /// <summary>是否有错误</summary>
    public bool HasError => !string.IsNullOrEmpty(ErrorMessage);

    public event PropertyChangedEventHandler? PropertyChanged;
    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
}

/// <summary>
/// 任务管理器
/// 管理本地处理任务的生命周期：创建、状态更新、历史查询。
/// </summary>
public class JobManager
{
    private readonly ConcurrentDictionary<string, JobRecord> _jobs = new();
    private readonly List<JobRecord> _history = new();
    private readonly object _historyLock = new();
    private const int MaxHistorySize = 500;

    /// <summary>任务状态变更事件</summary>
    public event EventHandler<JobRecord>? JobStatusChanged;

    /// <summary>任务完成事件</summary>
    public event EventHandler<JobRecord>? JobCompleted;

    /// <summary>
    /// 创建新任务
    /// </summary>
    public JobRecord CreateJob(string name, string feature, List<string>? inputFiles = null)
    {
        var job = new JobRecord
        {
            Name = name,
            Feature = feature,
            InputFiles = inputFiles ?? new List<string>(),
            Status = JobStatus.Queued,
            CreatedAt = DateTime.UtcNow
        };

        _jobs[job.Id] = job;
        return job;
    }

    /// <summary>
    /// 更新任务状态
    /// </summary>
    public void UpdateJobStatus(string jobId, JobStatus status, string? message = null)
    {
        if (!_jobs.TryGetValue(jobId, out var job)) return;

        job.Status = status;
        if (!string.IsNullOrEmpty(message))
        {
            if (status == JobStatus.Failed)
                job.ErrorMessage = message;
            else
                job.ResultMessage = message;
        }

        if (job.IsCompleted)
        {
            job.CompletedAt = DateTime.UtcNow;
            MoveToHistory(jobId);
            JobCompleted?.Invoke(this, job);
        }

        JobStatusChanged?.Invoke(this, job);
    }

    /// <summary>
    /// 更新任务进度
    /// </summary>
    public void UpdateJobProgress(string jobId, int progress)
    {
        if (_jobs.TryGetValue(jobId, out var job))
            job.Progress = progress;
    }

    /// <summary>
    /// 取消任务
    /// </summary>
    public bool CancelJob(string jobId)
    {
        if (!_jobs.TryGetValue(jobId, out var job)) return false;
        if (job.IsCompleted) return false;

        UpdateJobStatus(jobId, JobStatus.Cancelled, "任务已取消");
        return true;
    }

    /// <summary>
    /// 获取活动任务列表（未完成的任务）
    /// </summary>
    public List<JobRecord> GetActiveJobs()
        => _jobs.Values.OrderByDescending(j => j.CreatedAt).ToList();

    /// <summary>
    /// 获取任务历史（已完成的任务）
    /// </summary>
    public List<JobRecord> GetHistory()
    {
        lock (_historyLock)
            return _history.OrderByDescending(j => j.CompletedAt ?? j.CreatedAt).ToList();
    }

    /// <summary>
    /// 根据 ID 查找任务（先在活动任务中找，再在历史中找）
    /// </summary>
    public JobRecord? FindJob(string jobId)
    {
        if (_jobs.TryGetValue(jobId, out var job)) return job;
        lock (_historyLock)
            return _history.FirstOrDefault(j => j.Id == jobId);
    }

    /// <summary>
    /// 获取活动任务数量
    /// </summary>
    public int ActiveJobCount => _jobs.Count;

    /// <summary>
    /// 将已完成的任务从活动列表移到历史
    /// </summary>
    private void MoveToHistory(string jobId)
    {
        if (_jobs.TryRemove(jobId, out var job))
        {
            lock (_historyLock)
            {
                _history.Add(job);
                // 限制历史记录数量
                while (_history.Count > MaxHistorySize)
                    _history.RemoveAt(0);
            }
        }
    }
}
