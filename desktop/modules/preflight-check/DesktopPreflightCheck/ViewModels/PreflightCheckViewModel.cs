using System.Collections.ObjectModel;
using System.IO;
using System.Reflection;
using System.Windows.Input;
using Microsoft.Win32;
using TTShared.UI;
using TTShared.Logging;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTTools.PreflightCheck.Models;
using TTTools.PreflightCheck.Services;

namespace TTTools.PreflightCheck.ViewModels;

/// <summary>
/// 印前检查模块主 ViewModel
/// 管理图像文件选择、印前检查触发、检查报告展示、错误处理的完整流程。
/// 印前检查是本地免费功能，不需要云端权限检查。
/// </summary>
public class PreflightCheckViewModel : BaseViewModel
{
    /// <summary>印前检查引擎默认 Python 解释器路径</summary>
    private static readonly string DefaultPythonPath =
        @"D:\localPath\venvs\local-worker-preflight-check\Scripts\python.exe";

    /// <summary>印前检查引擎默认 router 脚本路径（相对于本程序集目录）</summary>
    private static string DefaultRouterPath =>
        Path.Combine(
            Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? ".",
            "preflight_check_router.py");
    private PreflightCheckService? _checkService;
    private readonly FileSystemService _fileSystem;
    private readonly JobManager? _jobManager;
    private readonly AppLogger? _logger;

    private bool _isRunning;
    private string _statusMessage = "请选择文件";
    private string? _errorMessage;
    private int _progressValue;
    private int _progressMax = 100;
    private bool _isServiceAvailable;
    private PreflightCheckReport? _selectedReport;
    private CancellationTokenSource? _currentCts;

    /// <summary>已完成的检查报告列表</summary>
    public ObservableCollection<PreflightCheckReport> Reports { get; } = new();

    /// <summary>待处理文件路径列表</summary>
    public ObservableCollection<string> PendingFiles { get; } = new();

    /// <summary>是否有待处理的文件</summary>
    public bool HasPendingFiles => PendingFiles.Count > 0;

    /// <summary>当前选中的检查报告（显示在详情区）</summary>
    public PreflightCheckReport? SelectedReport
    {
        get => _selectedReport;
        set
        {
            if (SetProperty(ref _selectedReport, value))
            {
                OnPropertyChanged(nameof(HasSelectedReport));
                OnPropertyChanged(nameof(SelectedChecks));
                OnPropertyChanged(nameof(SelectedReportSummary));
            }
        }
    }

    /// <summary>是否有选中的报告</summary>
    public bool HasSelectedReport => SelectedReport != null;

    /// <summary>选中报告的检查项列表（用于 UI 绑定）</summary>
    public ObservableCollection<PreflightCheckResultItem>? SelectedChecks =>
        SelectedReport?.Checks != null
            ? new ObservableCollection<PreflightCheckResultItem>(SelectedReport.Checks)
            : null;

    /// <summary>选中报告的概览摘要</summary>
    public string SelectedReportSummary
    {
        get
        {
            if (SelectedReport == null) return string.Empty;
            return $"错误:{SelectedReport.ErrorCount} 警告:{SelectedReport.WarningCount} 通过:{SelectedReport.PassCount}";
        }
    }

    /// <summary>当前状态栏消息</summary>
    public string StatusMessage
    {
        get => _statusMessage;
        set => SetProperty(ref _statusMessage, value);
    }

    /// <summary>错误消息</summary>
    public string? ErrorMessage
    {
        get => _errorMessage;
        set
        {
            if (SetProperty(ref _errorMessage, value))
                OnPropertyChanged(nameof(HasError));
        }
    }

    /// <summary>是否有错误</summary>
    public bool HasError => !string.IsNullOrEmpty(ErrorMessage);

    /// <summary>是否正在运行检查</summary>
    public bool IsRunning
    {
        get => _isRunning;
        set
        {
            if (SetProperty(ref _isRunning, value))
            {
                OnPropertyChanged(nameof(CanStart));
                OnPropertyChanged(nameof(CanCancel));
            }
        }
    }

    /// <summary>是否可以开始检查：服务可用 + 未运行 + 有待处理文件</summary>
    public bool CanStart => !IsRunning && _isServiceAvailable && PendingFiles.Count > 0;

    /// <summary>是否可以取消</summary>
    public bool CanCancel => IsRunning;

    /// <summary>印前检查服务是否可用</summary>
    public bool IsServiceAvailable
    {
        get => _isServiceAvailable;
        set
        {
            if (SetProperty(ref _isServiceAvailable, value))
            {
                OnPropertyChanged(nameof(CanStart));
                OnPropertyChanged(nameof(ServiceStatusText));
            }
        }
    }

    /// <summary>服务状态文本</summary>
    public string ServiceStatusText => _isServiceAvailable ? "印前检查引擎就绪" : "印前检查引擎未连接";

    /// <summary>进度值 (0-100)</summary>
    public int ProgressValue
    {
        get => _progressValue;
        set => SetProperty(ref _progressValue, value);
    }

    /// <summary>进度最大值</summary>
    public int ProgressMax
    {
        get => _progressMax;
        set => SetProperty(ref _progressMax, value);
    }

    /// <summary>已检查报告数量</summary>
    public int ReportCount => Reports.Count;

    /// <summary>通过检查的报告数量</summary>
    public int PassCount => Reports.Count(r => r.OverallRisk == RiskLevel.Pass);

    /// <summary>有警告的报告数量</summary>
    public int WarningCount => Reports.Count(r => r.OverallRisk == RiskLevel.Warning);

    /// <summary>有错误的报告数量</summary>
    public int ErrorCount => Reports.Count(r => r.OverallRisk == RiskLevel.Error);

    // ==================== 命令 ====================

    /// <summary>选择文件命令</summary>
    public ICommand SelectFilesCommand { get; }

    /// <summary>开始检查选中文件命令</summary>
    public ICommand StartCheckCommand { get; }

    /// <summary>取消当前检查命令</summary>
    public ICommand CancelCommand { get; }

    /// <summary>清除所有报告命令</summary>
    public ICommand ClearReportsCommand { get; }

    /// <summary>复制报告文本命令</summary>
    public ICommand CopyReportCommand { get; }

    /// <summary>选择报告项命令</summary>
    public ICommand SelectReportCommand { get; }

    public PreflightCheckViewModel(PreflightCheckService? checkService, FileSystemService fileSystem,
        JobManager? jobManager = null, AppLogger? logger = null)
    {
        _checkService = checkService;
        _fileSystem = fileSystem ?? throw new ArgumentNullException(nameof(fileSystem));
        _jobManager = jobManager;
        _logger = logger;

        SelectFilesCommand = new RelayCommand(SelectFiles);
        StartCheckCommand = new RelayCommand(StartCheckAsync, () => CanStart);
        CancelCommand = new RelayCommand(CancelCheck, () => CanCancel);
        ClearReportsCommand = new RelayCommand(ClearReports, () => Reports.Count > 0 || PendingFiles.Count > 0);
        CopyReportCommand = new RelayCommand(CopyReportText, () => HasSelectedReport);
        SelectReportCommand = new RelayCommand<PreflightCheckReport?>(r => SelectedReport = r);

        // 监听报告列表变更以更新命令状态
        Reports.CollectionChanged += (_, _) => RefreshCommandStates();
        PendingFiles.CollectionChanged += (_, _) =>
        {
            OnPropertyChanged(nameof(HasPendingFiles));
            OnPropertyChanged(nameof(CanStart));
            RefreshCommandStates();
        };
    }

    /// <summary>
    /// 默认构造函数（用于设计时和 MainWindow 导航）
    /// 自动检测 Python 路径和 router 脚本，创建印前检查服务。
    /// </summary>
    public PreflightCheckViewModel() : this(null, new FileSystemService())
    {
        // 尝试自动创建印前检查服务（使用默认路径）
        var routerPath = DefaultRouterPath;
        if (File.Exists(DefaultPythonPath) && File.Exists(routerPath))
        {
            _checkService = new PreflightCheckService(DefaultPythonPath, routerPath);
        }
        else
        {
            // Python 或 router 脚本不存在时，服务不可用，界面会显示"印前检查引擎未连接"
            StatusMessage = "印前检查引擎未安装或配置不完整，请检查 local-worker-preflight-check 环境";
        }
    }

    /// <summary>
    /// 初始化印前检查服务
    /// 异步启动 worker 进程并进行健康检查。
    /// </summary>
    public async Task InitializeAsync()
    {
        if (_checkService == null)
        {
            StatusMessage = "印前检查服务未配置";
            IsServiceAvailable = false;
            return;
        }

        StatusMessage = "正在启动印前检查引擎...";
        try
        {
            IsServiceAvailable = await _checkService.StartAsync();
            StatusMessage = IsServiceAvailable
                ? "请选择文件"
                : "处理服务不可用，请检查本地环境";
        }
        catch (Exception ex)
        {
            IsServiceAvailable = false;
            StatusMessage = "处理服务不可用，请检查本地环境";
            _logger?.Error($"印前检查服务初始化失败: {ex.Message}", ex, "desktop-preflight-check");
        }
    }

    /// <summary>
    /// 打开文件选择对话框，将选中的文件加入待处理列表。
    /// 不会自动开始检查。
    /// </summary>
    private void SelectFiles()
    {
        var dialog = new OpenFileDialog
        {
            Title = "选择要检查的图像文件",
            Filter = "图像文件|*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tif;*.webp|所有文件|*.*",
            Multiselect = true,
            CheckFileExists = true
        };

        if (dialog.ShowDialog() == true && dialog.FileNames.Length > 0)
        {
            AddFilesToPending(dialog.FileNames);
        }
    }

    /// <summary>
    /// 拖拽文件到窗口时调用 —— 只加入待处理列表，不自动处理。
    /// </summary>
    /// <param name="filePaths">拖入的文件路径列表</param>
    public void CheckDroppedFiles(IEnumerable<string> filePaths)
    {
        if (filePaths == null) return;

        var imageFiles = filePaths
            .Where(f => _checkService?.IsFormatSupported(f) ?? FileSystemService.IsImageFile(f))
            .ToList();

        if (imageFiles.Count == 0)
        {
            StatusMessage = "没有有效的图像文件";
            return;
        }

        AddFilesToPending(imageFiles);
    }

    /// <summary>
    /// 开始检查命令 —— 对待处理列表中的所有文件执行印前检查。
    /// </summary>
    private async void StartCheckAsync()
    {
        if (PendingFiles.Count == 0) return;
        var files = PendingFiles.ToList();
        await StartCheckForFilesAsync(files);
    }

    /// <summary>
    /// 将文件路径加入待处理列表（去重）。
    /// </summary>
    private void AddFilesToPending(IEnumerable<string> filePaths)
    {
        foreach (var path in filePaths)
        {
            if (string.IsNullOrWhiteSpace(path)) continue;
            if (!File.Exists(path)) continue;
            var normalized = Path.GetFullPath(path);
            if (PendingFiles.Any(f => f.Equals(normalized, StringComparison.OrdinalIgnoreCase)))
                continue;
            PendingFiles.Add(normalized);
        }

        ProgressValue = 0;
        ProgressMax = PendingFiles.Count;
        StatusMessage = $"已选择 {PendingFiles.Count} 个文件，点击开始处理";
        ErrorMessage = null;
    }

    /// <summary>
    /// 对指定文件列表执行印前检查的核心逻辑
    /// </summary>
    private async Task StartCheckForFilesAsync(List<string> filePaths)
    {
        if (_checkService == null || filePaths.Count == 0) return;

        IsRunning = true;
        ErrorMessage = null;
        ProgressValue = 0;
        ProgressMax = filePaths.Count;

        _currentCts = new CancellationTokenSource();

        // 将选定文件也做最多500个的限制
        if (filePaths.Count > 500)
        {
            filePaths = filePaths.Take(500).ToList();
            StatusMessage = "一次最多检查 500 个文件，已截取前 500 个";
        }

        StatusMessage = $"正在处理 0/{filePaths.Count}...";

        try
        {
            var reports = await _checkService.CheckBatchAsync(
                filePaths,
                (current, total) =>
                {
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    {
                        ProgressValue = current;
                        var fileName = current > 0 && current <= filePaths.Count
                            ? Path.GetFileName(filePaths[current - 1])
                            : "";
                        StatusMessage = $"正在处理 {current}/{total}：{fileName}";
                    });
                },
                _currentCts.Token);

            // 将报告添加到列表（最新的在最前面）
            foreach (var report in reports)
            {
                System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    Reports.Insert(0, report));
            }

            // 如果有报告，选中第一个
            if (reports.Count > 0)
            {
                // 优先选中风险最高的
                SelectedReport = reports.FirstOrDefault(r => r.OverallRisk == RiskLevel.Error)
                    ?? reports.FirstOrDefault(r => r.OverallRisk == RiskLevel.Warning)
                    ?? reports[0];
            }

            var errorCount = reports.Count(r => r.OverallRisk == RiskLevel.Error);
            var warnCount = reports.Count(r => r.OverallRisk == RiskLevel.Warning);
            var passCount = reports.Count(r => r.OverallRisk == RiskLevel.Pass);

            if (errorCount > 0)
                StatusMessage = $"处理完成：成功 {passCount}，失败 {errorCount}（警告 {warnCount}）";
            else if (warnCount > 0)
                StatusMessage = $"处理完成：成功 {passCount}，失败 0（警告 {warnCount}）";
            else
                StatusMessage = $"处理完成：成功 {passCount}，失败 0";

            // 处理完成后清空待处理列表
            PendingFiles.Clear();

            _logger?.Info(
                $"印前检查完成: {passCount} 通过, {warnCount} 警告, {errorCount} 错误",
                "desktop-preflight-check");
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "已取消";
            ProgressValue = 0;
            _logger?.Info("印前检查已取消", "desktop-preflight-check");
        }
        catch (Exception ex)
        {
            ErrorMessage = $"检查失败: {ex.Message}";
            StatusMessage = "检查出错，请查看错误信息";
            _logger?.Error($"印前检查异常: {ex.Message}", ex, "desktop-preflight-check");
        }
        finally
        {
            IsRunning = false;
            _currentCts?.Dispose();
            _currentCts = null;
            RefreshCommandStates();
        }
    }

    /// <summary>
    /// 取消当前检查任务
    /// </summary>
    private void CancelCheck()
    {
        _currentCts?.Cancel();
        StatusMessage = "正在取消...";
    }

    /// <summary>
    /// 清除所有检查报告
    /// </summary>
    private void ClearReports()
    {
        Reports.Clear();
        PendingFiles.Clear();
        SelectedReport = null;
        ErrorMessage = null;
        ProgressValue = 0;
        ProgressMax = 100;
        StatusMessage = "请选择文件";
        RefreshCommandStates();
    }

    /// <summary>
    /// 复制选中报告的文本摘要到剪贴板
    /// </summary>
    private void CopyReportText()
    {
        if (SelectedReport == null) return;

        try
        {
            var text = BuildReportText(SelectedReport);
            System.Windows.Clipboard.SetText(text);
            StatusMessage = "已复制检查报告文本到剪贴板";
        }
        catch (Exception ex)
        {
            StatusMessage = $"复制失败: {ex.Message}";
        }
    }

    /// <summary>
    /// 构建报告的纯文本格式
    /// </summary>
    private static string BuildReportText(PreflightCheckReport report)
    {
        var lines = new List<string>
        {
            $"文件: {report.FileName}",
            $"路径: {report.FilePath}",
            $"格式: {report.FileFormat} | 尺寸: {report.ImageSizeDisplay} | DPI: {report.DpiDisplay}",
            $"颜色模式: {report.ColorModeDisplay} | 透明通道: {(report.HasTransparency ? "有" : "无")}",
            $"文件大小: {report.FileSizeDisplay}",
            $"",
            $"整体评估: {report.OverallRiskDisplay}",
            $"错误: {report.ErrorCount} | 警告: {report.WarningCount} | 通过: {report.PassCount}",
            $"综合建议: {report.OverallMessage}",
            $"",
            "--- 详细检查结果 ---"
        };

        foreach (var check in report.Checks)
        {
            lines.Add($"[{check.RiskIcon}] {check.ItemDisplayName}: {check.Message}");
        }

        // 错误项详情
        var errors = report.Checks.Where(c => c.IsError).ToList();
        if (errors.Count > 0)
        {
            lines.Add("");
            lines.Add("--- 严重风险项 ---");
            foreach (var err in errors)
            {
                lines.Add($"❌ {err.ItemDisplayName}: {err.Message}");
            }
        }

        return string.Join(Environment.NewLine, lines);
    }

    /// <summary>
    /// 刷新命令可执行状态
    /// </summary>
    private void RefreshCommandStates()
    {
        OnPropertyChanged(nameof(ReportCount));
        OnPropertyChanged(nameof(PassCount));
        OnPropertyChanged(nameof(WarningCount));
        OnPropertyChanged(nameof(ErrorCount));

        (StartCheckCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (CancelCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (ClearReportsCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (CopyReportCommand as RelayCommand)?.RaiseCanExecuteChanged();
    }
}
