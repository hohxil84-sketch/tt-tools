using System.Collections.ObjectModel;
using System.Windows.Input;
using TTTools.JobSystem.Models;
using TTTools.JobSystem.Services;
using TTShared.JobSystem;
using TTShared.Logging;
using TTShared.UI;

namespace TTTools.JobSystem.ViewModels;

/// <summary>
/// 任务列表 ViewModel
/// 是整个任务系统模块的主控制器，负责：
/// - 管理活动和历史任务列表的展示
/// - 提供过滤、排序、分页功能
/// - 提供重试失败任务、清除历史等操作
/// - 同步任务状态变更到 UI
/// </summary>
public class JobListViewModel : BaseViewModel
{
    private readonly JobManager _jobManager;
    private readonly JobRetryService? _retryService;
    private readonly IJobHistoryStore? _historyStore;
    private readonly AppLogger? _logger;

    /// <summary>当前过滤条件</summary>
    private JobFilterOptions _filter = new();
    private List<JobRecord> _allJobs = new(); // 未过滤的所有任务
    private string _statusMessage = "就绪";
    private bool _isLoading;

    // ==================== 集合属性 ====================

    /// <summary>过滤后的任务列表（用于 UI 绑定）</summary>
    public ObservableCollection<JobDetailViewModel> FilteredJobs { get; } = new();

    /// <summary>任务统计报告</summary>
    public JobReport Report { get; private set; } = new();

    // ==================== 字符串属性 ====================

    /// <summary>当前状态栏消息</summary>
    public string StatusMessage
    {
        get => _statusMessage;
        set => SetProperty(ref _statusMessage, value);
    }

    /// <summary>是否正在加载</summary>
    public bool IsLoading
    {
        get => _isLoading;
        set => SetProperty(ref _isLoading, value);
    }

    /// <summary>过滤状态（可绑定到下拉框等）</summary>
    public JobStatus? FilterStatus
    {
        get => _filter.Status;
        set
        {
            if (_filter.Status != value)
            {
                _filter.Status = value;
                OnPropertyChanged();
                ApplyFilter();
            }
        }
    }

    /// <summary>过滤功能码</summary>
    public string? FilterFeature
    {
        get => _filter.Feature;
        set
        {
            if (_filter.Feature != value)
            {
                _filter.Feature = value;
                OnPropertyChanged();
                ApplyFilter();
            }
        }
    }

    /// <summary>过滤搜索文本</summary>
    public string? FilterSearchText
    {
        get => _filter.SearchText;
        set
        {
            if (_filter.SearchText != value)
            {
                _filter.SearchText = value;
                OnPropertyChanged();
                ApplyFilter();
            }
        }
    }

    // ==================== 计算属性 ====================

    /// <summary>活动任务数</summary>
    public int ActiveJobCount => _jobManager.ActiveJobCount;

    /// <summary>过滤后显示的任务数</summary>
    public int FilteredJobCount => FilteredJobs.Count;

    /// <summary>是否有任务可以清除</summary>
    public bool CanClearHistory => FilteredJobs.Count > 0;

    /// <summary>是否有选中任务可以重试</summary>
    public bool CanRetrySelected => FilteredJobs.Any(j => j.CanRetry && j.IsSelected);

    // ==================== 命令 ====================

    /// <summary>重试选中失败任务命令</summary>
    public ICommand RetrySelectedCommand { get; }

    /// <summary>清除所有历史记录命令</summary>
    public ICommand ClearHistoryCommand { get; }

    /// <summary>刷新任务列表命令</summary>
    public ICommand RefreshCommand { get; }

    /// <summary>显示所有状态任务命令</summary>
    public ICommand ShowAllCommand { get; }

    /// <summary>只显示失败任务命令</summary>
    public ICommand ShowFailedOnlyCommand { get; }

    /// <summary>重试指定任务命令（带参数）</summary>
    public ICommand RetryJobCommand { get; }

    public JobListViewModel(JobManager jobManager,
        JobRetryService? retryService = null,
        IJobHistoryStore? historyStore = null,
        AppLogger? logger = null)
    {
        _jobManager = jobManager ?? throw new ArgumentNullException(nameof(jobManager));
        _retryService = retryService;
        _historyStore = historyStore;
        _logger = logger;

        // 初始化命令
        RetrySelectedCommand = new RelayCommand(RetrySelected, () => CanRetrySelected);
        ClearHistoryCommand = new RelayCommand(async () => await ClearHistoryAsync(), () => CanClearHistory);
        RefreshCommand = new RelayCommand(async () => await RefreshAsync());
        ShowAllCommand = new RelayCommand(() => { FilterStatus = null; });
        ShowFailedOnlyCommand = new RelayCommand(() => { FilterStatus = JobStatus.Failed; });
        RetryJobCommand = new RelayCommand<JobDetailViewModel?>(RetryJob);

        // 订阅 JobManager 事件以实时更新
        _jobManager.JobStatusChanged += OnJobStatusChanged;
        _jobManager.JobCompleted += OnJobCompleted;

        // 同步当前 JobManager 中已有的任务（在订阅事件之前创建的任务）
        SyncFromJobManager();

        // 从历史存储加载历史任务
        if (_historyStore != null)
        {
            _ = LoadHistoryAsync();
        }
    }

    /// <summary>
    /// 默认构造函数（用于设计时）
    /// </summary>
    public JobListViewModel() : this(new JobManager())
    { }

    // ==================== 公共方法 ====================

    /// <summary>
    /// 刷新任务列表（重新从 JobManager 获取活动任务和历史记录）
    /// </summary>
    public async Task RefreshAsync()
    {
        IsLoading = true;
        StatusMessage = "正在刷新任务列表...";

        try
        {
            // 收集所有任务：活动任务 + 历史任务
            var activeJobs = _jobManager.GetActiveJobs();
            var historyJobs = _jobManager.GetHistory();

            _allJobs = new List<JobRecord>();
            _allJobs.AddRange(activeJobs);
            _allJobs.AddRange(historyJobs);

            // 如果配置了历史存储，合并存储中的历史
            if (_historyStore != null)
            {
                var storedHistory = await _historyStore.LoadAsync();
                // 合并去重：以 JobManager 的记录优先
                var existingIds = new HashSet<string>(_allJobs.Select(j => j.Id));
                foreach (var job in storedHistory)
                {
                    if (!existingIds.Contains(job.Id))
                        _allJobs.Add(job);
                }
            }

            ApplyFilter();
            StatusMessage = $"刷新完成：共 {_allJobs.Count} 个任务";
        }
        catch (Exception ex)
        {
            StatusMessage = $"刷新失败：{ex.Message}";
            _logger?.Error($"刷新任务列表失败：{ex.Message}", ex, "job-system");
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>
    /// 重试所有选中的失败任务
    /// </summary>
    public void RetrySelected()
    {
        if (_retryService == null)
        {
            StatusMessage = "重试服务未配置";
            return;
        }

        var selected = FilteredJobs.Where(j => j.IsSelected && j.CanRetry).ToList();
        if (selected.Count == 0)
        {
            StatusMessage = "没有可重试的选中任务";
            return;
        }

        var retriedCount = 0;
        foreach (var jobVm in selected)
        {
            var originalJob = _jobManager.FindJob(jobVm.JobId);
            if (originalJob == null) continue;

            var retryJob = _retryService.Retry(originalJob);
            if (retryJob != null)
            {
                // 手动添加到列表（CreateJob 不触发 JobStatusChanged 事件）
                _allJobs.Add(retryJob);
                retriedCount++;
            }
        }

        if (retriedCount > 0)
            ApplyFilter();
        StatusMessage = $"已创建 {retriedCount} 个重试任务";
    }

    /// <summary>
    /// 重试单个任务
    /// </summary>
    public void RetryJob(JobDetailViewModel? jobVm)
    {
        if (jobVm == null || _retryService == null) return;

        var originalJob = _jobManager.FindJob(jobVm.JobId);
        if (originalJob == null) return;

        var retryJob = _retryService.Retry(originalJob);
        if (retryJob != null)
        {
            // 手动添加到列表（CreateJob 不触发 JobStatusChanged 事件）
            _allJobs.Add(retryJob);
            ApplyFilter();
            StatusMessage = $"已创建重试任务：{retryJob.Name}";
        }
        else
        {
            StatusMessage = $"任务 {jobVm.JobName} 无法重试";
        }
    }

    /// <summary>
    /// 清除所有历史记录
    /// </summary>
    public async Task ClearHistoryAsync()
    {
        if (_historyStore != null)
            await _historyStore.ClearAsync();

        // 从内存列表中移除已完成的任务
        _allJobs.RemoveAll(j => j.IsCompleted);

        ApplyFilter();
        StatusMessage = "历史记录已清除";
        _logger?.Info("任务历史已清除", "job-system");
    }

    // ==================== 私有方法 ====================

    /// <summary>
    /// 应用过滤条件并刷新 FilteredJobs 集合
    /// </summary>
    private void ApplyFilter()
    {
        // 执行过滤
        var filtered = _allJobs.Where(j => _filter.Matches(j)).ToList();

        // 执行排序
        filtered = ApplySort(filtered);

        // 更新 ObservableCollection
        FilteredJobs.Clear();
        foreach (var job in filtered)
        {
            bool canRetry = _retryService?.CanRetry(job) ?? false;
            FilteredJobs.Add(new JobDetailViewModel(job, canRetry));
        }

        // 更新统计报告
        Report = JobReport.FromJobs(_allJobs);

        // 通知属性变更
        OnPropertyChanged(nameof(FilteredJobCount));
        OnPropertyChanged(nameof(CanClearHistory));
        OnPropertyChanged(nameof(CanRetrySelected));
        OnPropertyChanged(nameof(Report));
        OnPropertyChanged(nameof(ActiveJobCount));
    }

    /// <summary>
    /// 对过滤后的任务列表排序
    /// </summary>
    private List<JobRecord> ApplySort(List<JobRecord> jobs)
    {
        var sorted = _filter.SortBy switch
        {
            JobSortBy.CompletedAt => _filter.SortDescending
                ? jobs.OrderByDescending(j => j.CompletedAt ?? DateTime.MinValue)
                : jobs.OrderBy(j => j.CompletedAt ?? DateTime.MinValue),
            JobSortBy.Name => _filter.SortDescending
                ? jobs.OrderByDescending(j => j.Name)
                : jobs.OrderBy(j => j.Name),
            JobSortBy.Status => _filter.SortDescending
                ? jobs.OrderByDescending(j => j.Status)
                : jobs.OrderBy(j => j.Status),
            JobSortBy.Feature => _filter.SortDescending
                ? jobs.OrderByDescending(j => j.Feature)
                : jobs.OrderBy(j => j.Feature),
            _ => _filter.SortDescending // 默认按创建时间
                ? jobs.OrderByDescending(j => j.CreatedAt)
                : jobs.OrderBy(j => j.CreatedAt)
        };

        return sorted.ToList();
    }

    /// <summary>
    /// 任务状态变更处理
    /// </summary>
    private void OnJobStatusChanged(object? sender, JobRecord job)
    {
        // 确保任务在 _allJobs 中
        if (!_allJobs.Any(j => j.Id == job.Id))
            _allJobs.Add(job);

        ApplyFilter();
        StatusMessage = $"任务状态更新：{job.Name} → {job.Status}";
    }

    /// <summary>
    /// 任务完成处理：持久化到历史存储
    /// </summary>
    private void OnJobCompleted(object? sender, JobRecord job)
    {
        if (_historyStore != null)
        {
            _ = _historyStore.SaveAsync(job);
        }

        StatusMessage = $"任务完成：{job.Name} → {job.Status}";
    }

    /// <summary>
    /// 从 JobManager 同步当前已有任务（活动 + 历史）
    /// 用于在构造 VM 时加载已在 JobManager 中的任务。
    /// </summary>
    private void SyncFromJobManager()
    {
        var activeJobs = _jobManager.GetActiveJobs();
        var historyJobs = _jobManager.GetHistory();

        foreach (var job in activeJobs)
        {
            if (_allJobs.All(j => j.Id != job.Id))
                _allJobs.Add(job);
        }
        foreach (var job in historyJobs)
        {
            if (_allJobs.All(j => j.Id != job.Id))
                _allJobs.Add(job);
        }

        if (_allJobs.Count > 0)
            ApplyFilter();
    }

    /// <summary>
    /// 从历史存储加载任务历史
    /// </summary>
    private async Task LoadHistoryAsync()
    {
        if (_historyStore == null) return;

        try
        {
            var storedHistory = await _historyStore.LoadAsync();
            foreach (var job in storedHistory)
            {
                if (!_allJobs.Any(j => j.Id == job.Id))
                    _allJobs.Add(job);
            }

            if (storedHistory.Count > 0)
            {
                ApplyFilter();
                StatusMessage = $"已加载 {storedHistory.Count} 条历史记录";
            }
        }
        catch (Exception ex)
        {
            _logger?.Error($"加载历史记录失败：{ex.Message}", ex, "job-system");
        }
    }
}
