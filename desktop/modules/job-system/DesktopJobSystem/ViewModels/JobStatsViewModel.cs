using System.Windows.Input;
using TTTools.JobSystem.Models;
using TTShared.UI;

namespace TTTools.JobSystem.ViewModels;

/// <summary>
/// 任务统计 ViewModel
/// 从 JobReport 模型生成 UI 友好的统计展示，
/// 支持按状态快速过滤任务列表。
/// </summary>
public class JobStatsViewModel : BaseViewModel
{
    private JobReport _report = new();

    // ==================== 统计数字属性 ====================

    /// <summary>任务总数</summary>
    public int Total => _report.Total;

    /// <summary>排队中数量</summary>
    public int Queued => _report.Queued;

    /// <summary>运行中数量</summary>
    public int Running => _report.Running;

    /// <summary>成功数量</summary>
    public int Succeeded => _report.Succeeded;

    /// <summary>失败数量</summary>
    public int Failed => _report.Failed;

    /// <summary>已取消数量</summary>
    public int Cancelled => _report.Cancelled;

    /// <summary>活跃任务数（排队 + 运行）</summary>
    public int ActiveCount => Queued + Running;

    /// <summary>已完成数（成功 + 失败 + 取消）</summary>
    public int CompletedCount => Succeeded + Failed + Cancelled;

    // ==================== 百分比属性 ====================

    /// <summary>成功率（百分比文本）</summary>
    public string SuccessRateDisplay => $"{_report.SuccessRate}%";

    /// <summary>失败率（百分比文本）</summary>
    public string FailureRateDisplay =>
        _report.Total > 0 ? $"{Math.Round((double)_report.Failed / _report.Total * 100, 1)}%" : "0%";

    // ==================== 状态文本 ====================

    /// <summary>统计摘要文本</summary>
    public string Summary =>
        $"共 {Total} 个任务 | 活跃 {ActiveCount} | 成功 {Succeeded} | 失败 {Failed}";

    /// <summary>是否有失败任务</summary>
    public bool HasFailed => Failed > 0;

    /// <summary>是否有活跃任务</summary>
    public bool HasActive => ActiveCount > 0;

    // ==================== 命令 ====================

    /// <summary>显示失败任务命令（由父级处理）</summary>
    public ICommand ShowFailedCommand { get; }

    /// <summary>显示活跃任务命令（由父级处理）</summary>
    public ICommand ShowActiveCommand { get; }

    /// <summary>显示全部任务命令（由父级处理）</summary>
    public ICommand ShowAllCommand { get; }

    public JobStatsViewModel()
    {
        ShowFailedCommand = new RelayCommand(() =>
            ShowFailedRequested?.Invoke(this, EventArgs.Empty));
        ShowActiveCommand = new RelayCommand(() =>
            ShowActiveRequested?.Invoke(this, EventArgs.Empty));
        ShowAllCommand = new RelayCommand(() =>
            ShowAllRequested?.Invoke(this, EventArgs.Empty));
    }

    // ==================== 事件 ====================

    /// <summary>请求显示失败任务</summary>
    public event EventHandler? ShowFailedRequested;

    /// <summary>请求显示活跃任务</summary>
    public event EventHandler? ShowActiveRequested;

    /// <summary>请求显示全部任务</summary>
    public event EventHandler? ShowAllRequested;

    // ==================== 公共方法 ====================

    /// <summary>
    /// 从 JobReport 更新统计数据
    /// </summary>
    public void UpdateFromReport(JobReport report)
    {
        _report = report ?? throw new ArgumentNullException(nameof(report));

        // 通知所有属性变更
        OnPropertyChanged(nameof(Total));
        OnPropertyChanged(nameof(Queued));
        OnPropertyChanged(nameof(Running));
        OnPropertyChanged(nameof(Succeeded));
        OnPropertyChanged(nameof(Failed));
        OnPropertyChanged(nameof(Cancelled));
        OnPropertyChanged(nameof(ActiveCount));
        OnPropertyChanged(nameof(CompletedCount));
        OnPropertyChanged(nameof(SuccessRateDisplay));
        OnPropertyChanged(nameof(FailureRateDisplay));
        OnPropertyChanged(nameof(Summary));
        OnPropertyChanged(nameof(HasFailed));
        OnPropertyChanged(nameof(HasActive));
    }
}
