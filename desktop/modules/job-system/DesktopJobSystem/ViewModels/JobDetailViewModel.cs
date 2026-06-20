using System.Windows.Input;
using TTShared.JobSystem;
using TTShared.UI;

namespace TTTools.JobSystem.ViewModels;

/// <summary>
/// 任务详情 ViewModel
/// 包装 JobRecord，提供 UI 友好的属性访问和操作命令。
/// 用于任务的详细展示和交互。
/// </summary>
public class JobDetailViewModel : BaseViewModel
{
    private readonly JobRecord _job;
    private bool _isSelected;
    private readonly bool _canRetry;

    // ==================== 只读属性（来自 JobRecord） ====================

    /// <summary>任务 ID</summary>
    public string JobId => _job.Id;

    /// <summary>任务名称</summary>
    public string JobName => _job.Name;

    /// <summary>功能码</summary>
    public string Feature => _job.Feature;

    /// <summary>任务状态</summary>
    public JobStatus Status => _job.Status;

    /// <summary>进度百分比（0-100）</summary>
    public int Progress => _job.Progress;

    /// <summary>输入文件数量</summary>
    public int InputFileCount => _job.InputFiles?.Count ?? 0;

    /// <summary>输出文件数量</summary>
    public int OutputFileCount => _job.OutputFiles?.Count ?? 0;

    /// <summary>错误消息</summary>
    public string? ErrorMessage => _job.ErrorMessage;

    /// <summary>结果消息</summary>
    public string? ResultMessage => _job.ResultMessage;

    /// <summary>创建时间</summary>
    public DateTime CreatedAt => _job.CreatedAt;

    /// <summary>完成时间</summary>
    public DateTime? CompletedAt => _job.CompletedAt;

    // ==================== 计算属性 ====================

    /// <summary>状态的中文显示文本</summary>
    public string StatusDisplay => Status switch
    {
        JobStatus.Queued => "排队中",
        JobStatus.Running => "运行中",
        JobStatus.Succeeded => "已完成",
        JobStatus.Failed => "已失败",
        JobStatus.Cancelled => "已取消",
        _ => Status.ToString()
    };

    /// <summary>状态对应的图标（用于 UI 展示）</summary>
    public string StatusIcon => Status switch
    {
        JobStatus.Queued => "⏳",
        JobStatus.Running => "🔄",
        JobStatus.Succeeded => "✅",
        JobStatus.Failed => "❌",
        JobStatus.Cancelled => "🚫",
        _ => "❓"
    };

    /// <summary>进度显示文本（含百分比）</summary>
    public string ProgressDisplay => $"{Progress}%";

    /// <summary>是否已完成（成功、失败或取消）</summary>
    public bool IsCompleted => _job.IsCompleted;

    /// <summary>是否有错误</summary>
    public bool HasError => _job.HasError;

    /// <summary>是否正在运行</summary>
    public bool IsRunning => Status == JobStatus.Running;

    /// <summary>是否排队中</summary>
    public bool IsQueued => Status == JobStatus.Queued;

    /// <summary>创建时间的友好格式</summary>
    public string CreatedAtDisplay => FormatTime(CreatedAt);

    /// <summary>完成时间的友好格式</summary>
    public string CompletedAtDisplay =>
        CompletedAt.HasValue ? FormatTime(CompletedAt.Value) : "—";

    /// <summary>任务时长显示（创建到完成的时间跨度）</summary>
    public string DurationDisplay
    {
        get
        {
            if (!CompletedAt.HasValue) return "—";
            var duration = CompletedAt.Value - CreatedAt;
            if (duration.TotalSeconds < 60)
                return $"{duration.TotalSeconds:F0} 秒";
            if (duration.TotalMinutes < 60)
                return $"{duration.TotalMinutes:F0} 分 {duration.Seconds:F0} 秒";
            return $"{duration.TotalHours:F0} 时 {duration.Minutes:F0} 分";
        }
    }

    // ==================== 可绑定属性 ====================

    /// <summary>是否被选中（可绑定）</summary>
    public bool IsSelected
    {
        get => _isSelected;
        set => SetProperty(ref _isSelected, value);
    }

    /// <summary>是否可以重试</summary>
    public bool CanRetry => _canRetry && Status == JobStatus.Failed;

    // ==================== 命令 ====================

    /// <summary>切换选中状态命令</summary>
    public ICommand ToggleSelectCommand { get; }

    public JobDetailViewModel(JobRecord job, bool canRetry = false)
    {
        _job = job ?? throw new ArgumentNullException(nameof(job));
        _canRetry = canRetry;

        ToggleSelectCommand = new RelayCommand(ToggleSelect);

        // 订阅 JobRecord 属性变更以同步到 UI
        _job.PropertyChanged += OnJobPropertyChanged;
    }

    /// <summary>
    /// 切换选中状态
    /// </summary>
    public void ToggleSelect()
    {
        IsSelected = !IsSelected;
    }

    /// <summary>
    /// 获取底层的 JobRecord
    /// </summary>
    public JobRecord GetJobRecord() => _job;

    /// <summary>
    /// 订阅 JobRecord 属性变更，转发到 ViewModel
    /// </summary>
    private void OnJobPropertyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        // 转发底层模型的所有属性变更
        switch (e.PropertyName)
        {
            case nameof(JobRecord.Status):
                OnPropertyChanged(nameof(Status));
                OnPropertyChanged(nameof(StatusDisplay));
                OnPropertyChanged(nameof(StatusIcon));
                OnPropertyChanged(nameof(IsCompleted));
                OnPropertyChanged(nameof(IsRunning));
                OnPropertyChanged(nameof(IsQueued));
                OnPropertyChanged(nameof(CanRetry));
                break;
            case nameof(JobRecord.Progress):
                OnPropertyChanged(nameof(Progress));
                OnPropertyChanged(nameof(ProgressDisplay));
                break;
            case nameof(JobRecord.ErrorMessage):
                OnPropertyChanged(nameof(ErrorMessage));
                OnPropertyChanged(nameof(HasError));
                break;
            case nameof(JobRecord.ResultMessage):
                OnPropertyChanged(nameof(ResultMessage));
                break;
            case nameof(JobRecord.CompletedAt):
                OnPropertyChanged(nameof(CompletedAt));
                OnPropertyChanged(nameof(CompletedAtDisplay));
                OnPropertyChanged(nameof(DurationDisplay));
                break;
            case nameof(JobRecord.InputFiles):
                OnPropertyChanged(nameof(InputFileCount));
                break;
            case nameof(JobRecord.OutputFiles):
                OnPropertyChanged(nameof(OutputFileCount));
                break;
        }
    }

    /// <summary>
    /// 格式化时间用于友好展示
    /// </summary>
    private static string FormatTime(DateTime time)
    {
        var localTime = time.ToLocalTime();
        var now = DateTime.Now;
        if (localTime.Date == now.Date)
            return $"今天 {localTime:HH:mm:ss}";
        if (localTime.Date == now.Date.AddDays(-1))
            return $"昨天 {localTime:HH:mm:ss}";
        if (localTime.Year == now.Year)
            return localTime.ToString("MM-dd HH:mm");
        return localTime.ToString("yyyy-MM-dd HH:mm");
    }
}
