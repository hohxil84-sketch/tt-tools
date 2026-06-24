using System.Collections.ObjectModel;
using System.Windows.Input;
using TTTools.ExportSettings.Models;
using TTTools.ExportSettings.Services;
using TTShared.Logging;
using TTShared.UI;

namespace TTTools.ExportSettings.ViewModels;

/// <summary>
/// 日志查看器 ViewModel
/// 管理日志条目的加载、过滤、搜索和清除。
/// </summary>
public class LogViewerViewModel : BaseViewModel
{
    private readonly LogReaderService _logReader;
    private readonly AppLogger? _appLogger;

    /// <summary>日志条目集合</summary>
    public ObservableCollection<LogDisplayEntry> LogEntries { get; } = new();

    /// <summary>过滤选项</summary>
    private LogFilterOptions _filterOptions = new();
    public LogFilterOptions FilterOptions
    {
        get => _filterOptions;
        set => SetProperty(ref _filterOptions, value);
    }

    /// <summary>选中的日志条目</summary>
    private LogDisplayEntry? _selectedEntry;
    public LogDisplayEntry? SelectedEntry
    {
        get => _selectedEntry;
        set => SetProperty(ref _selectedEntry, value);
    }

    /// <summary>是否正在加载</summary>
    private bool _isLoading;
    public bool IsLoading
    {
        get => _isLoading;
        set => SetProperty(ref _isLoading, value);
    }

    /// <summary>状态文本</summary>
    private string _statusText = "就绪";
    public string StatusText
    {
        get => _statusText;
        set => SetProperty(ref _statusText, value);
    }

    /// <summary>当前显示条目数</summary>
    private int _displayCount;
    public int DisplayCount
    {
        get => _displayCount;
        set => SetProperty(ref _displayCount, value);
    }

    /// <summary>日志目录总大小</summary>
    private string _totalSizeText = string.Empty;
    public string TotalSizeText
    {
        get => _totalSizeText;
        set => SetProperty(ref _totalSizeText, value);
    }

    /// <summary>级别过滤选项（用于 UI 绑定）</summary>
    public ObservableCollection<LogLevelFilterItem> LevelFilters { get; } = new()
    {
        new LogLevelFilterItem { Label = "全部", Level = null },
        new LogLevelFilterItem { Label = "DEBUG", Level = LogLevel.Debug },
        new LogLevelFilterItem { Label = "INFO", Level = LogLevel.Info },
        new LogLevelFilterItem { Label = "WARNING", Level = LogLevel.Warning },
        new LogLevelFilterItem { Label = "ERROR", Level = LogLevel.Error },
        new LogLevelFilterItem { Label = "FATAL", Level = LogLevel.Fatal }
    };

    /// <summary>选中的级别过滤索引</summary>
    private int _selectedLevelFilterIndex;
    public int SelectedLevelFilterIndex
    {
        get => _selectedLevelFilterIndex;
        set
        {
            if (SetProperty(ref _selectedLevelFilterIndex, value))
            {
                FilterOptions.MinLevel = LevelFilters[value].Level;
            }
        }
    }

    /// <summary>刷新命令</summary>
    public ICommand RefreshCommand { get; }

    /// <summary>清除日志命令</summary>
    public ICommand ClearLogsCommand { get; }

    /// <summary>导出日志命令</summary>
    public ICommand ExportLogsCommand { get; }

    /// <summary>应用搜索关键词命令</summary>
    public ICommand SearchCommand { get; }

    public LogViewerViewModel(LogReaderService? logReader = null, AppLogger? appLogger = null)
    {
        _logReader = logReader ?? new LogReaderService();
        _appLogger = appLogger;

        RefreshCommand = new AsyncRelayCommand(RefreshAsync);
        ClearLogsCommand = new RelayCommand(ClearLogs);
        ExportLogsCommand = new RelayCommand(ExportLogs);
        SearchCommand = new RelayCommand<string>(ApplySearch);
    }

    /// <summary>
    /// 默认构造函数（用于设计时和 XAML 实例化）
    /// </summary>
    public LogViewerViewModel() : this(null, null) { }

    /// <summary>
    /// 刷新日志列表
    /// </summary>
    public async Task RefreshAsync()
    {
        IsLoading = true;
        StatusText = "正在加载日志...";

        try
        {
            var entries = await _logReader.ReadLogsAsync(FilterOptions);
            LogEntries.Clear();
            foreach (var entry in entries)
            {
                LogEntries.Add(entry);
            }

            DisplayCount = LogEntries.Count;
            StatusText = $"已加载 {DisplayCount} 条日志";
            UpdateTotalSize();
        }
        catch (Exception ex)
        {
            StatusText = $"加载失败：{ex.Message}";
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>
    /// 清除所有日志文件
    /// </summary>
    private void ClearLogs()
    {
        _logReader.ClearAllLogs();
        LogEntries.Clear();
        DisplayCount = 0;
        StatusText = "日志已清除";
        UpdateTotalSize();
    }

    /// <summary>
    /// 导出日志到文件
    /// 实际集成时使用 SaveFileDialog。
    /// </summary>
    public void ExportLogs()
    {
        // 实际 WPF 中使用 SaveFileDialog 选择导出路径
        // 此处提供方法供 View 层调用
    }

    /// <summary>
    /// 导出日志到指定文件路径（供 View 层调用）
    /// </summary>
    public async Task ExportLogsToFileAsync(string filePath)
    {
        try
        {
            var entries = await _logReader.ReadLogsAsync(FilterOptions, maxEntries: 0);
            using var writer = new StreamWriter(filePath, false, Encoding.UTF8);
            foreach (var entry in entries)
            {
                await writer.WriteLineAsync(
                    $"{entry.TimestampFormatted} [{entry.LevelText}] [{entry.Category}] {entry.Message}");
                if (entry.HasException)
                    await writer.WriteLineAsync($"  Exception: {entry.Exception}");
            }

            StatusText = $"日志已导出到 {filePath}";
        }
        catch (Exception ex)
        {
            StatusText = $"导出失败：{ex.Message}";
        }
    }

    /// <summary>
    /// 应用搜索关键词
    /// </summary>
    private void ApplySearch(string? searchText)
    {
        FilterOptions.SearchText = string.IsNullOrWhiteSpace(searchText) ? null : searchText;
    }

    /// <summary>
    /// 更新日志目录总大小显示
    /// </summary>
    private void UpdateTotalSize()
    {
        var bytes = _logReader.GetTotalLogSize();
        TotalSizeText = bytes switch
        {
            < 1024 => $"{bytes} B",
            < 1024 * 1024 => $"{bytes / 1024.0:F1} KB",
            _ => $"{bytes / (1024.0 * 1024.0):F1} MB"
        };
    }
}

/// <summary>
/// 日志级别过滤项（用于 UI 下拉绑定）
/// </summary>
public class LogLevelFilterItem
{
    public string Label { get; set; } = string.Empty;
    public LogLevel? Level { get; set; }
}
