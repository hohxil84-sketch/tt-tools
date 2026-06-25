using System.Collections.ObjectModel;
using System.Reflection;
using System.Windows.Input;
using Microsoft.Win32;
using TTShared.UI;
using TTShared.Logging;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTTools.OCR.Models;
using TTTools.OCR.Services;

namespace TTTools.OCR.ViewModels;

/// <summary>
/// OCR 模块主 ViewModel
/// 管理图片文件选择、OCR 识别触发、结果展示、错误处理的完整流程。
/// OCR 是本地免费功能，不需要云端权限检查。
///
/// 工作流程：
///   1. 点击"选择图片"→ 打开文件对话框，图片加入待识别列表（不自动识别）
///   2. 点击"开始识别"→ 对待识别列表中的图片逐张执行 OCR
///   3. 可拖动置信度滑块实时调整低置信度遮罩
///   4. 右侧详情展示格式化文本（按原图坐标排版）
/// </summary>
public class OcrViewModel : BaseViewModel
{
    /// <summary>OCR 引擎默认 Python 解释器路径</summary>
    private static readonly string DefaultPythonPath =
        @"D:\localPath\venvs\local-worker-ocr\Scripts\python.exe";

    /// <summary>OCR 引擎默认 router 脚本路径（相对于本程序集目录）</summary>
    private static string DefaultRouterPath =>
        Path.Combine(
            Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? ".",
            "ocr_router.py");

    private OcrService? _ocrService;
    private readonly FileSystemService _fileSystem;
    private readonly JobManager? _jobManager;
    private readonly AppLogger? _logger;

    private bool _isRunning;
    private string _statusMessage = "就绪 - 选择图片文件开始 OCR 识别";
    private string? _errorMessage;
    private int _textScorePercent = 50;
    private int _progressValue;
    private int _progressMax = 100;
    private bool _isServiceAvailable;
    private OcrJobResult? _selectedResult;
    private CancellationTokenSource? _currentCts;

    /// <summary>已识别的 OCR 结果列表</summary>
    public ObservableCollection<OcrJobResult> Results { get; } = new();

    /// <summary>待识别图片文件路径列表</summary>
    public ObservableCollection<string> PendingFiles { get; } = new();

    /// <summary>当前执行中的结果（显示在预览区）</summary>
    public OcrJobResult? SelectedResult
    {
        get => _selectedResult;
        set
        {
            if (SetProperty(ref _selectedResult, value))
            {
                OnPropertyChanged(nameof(HasSelectedResult));
                OnPropertyChanged(nameof(SelectedTotalText));
                OnPropertyChanged(nameof(SelectedFormattedText));
                OnPropertyChanged(nameof(SelectedTextLineCount));
            }
        }
    }

    /// <summary>是否有选中结果</summary>
    public bool HasSelectedResult => SelectedResult != null;

    /// <summary>选中结果的完整文本（简单拼接）</summary>
    public string SelectedTotalText => SelectedResult?.TotalText ?? string.Empty;

    /// <summary>选中结果的格式化文本（按坐标排版，优先使用）</summary>
    public string SelectedFormattedText =>
        !string.IsNullOrEmpty(SelectedResult?.FormattedText)
            ? SelectedResult.FormattedText
            : SelectedResult?.TotalText ?? string.Empty;

    /// <summary>选中结果的文字行数</summary>
    public int SelectedTextLineCount => SelectedResult?.LineCount ?? 0;

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

    /// <summary>是否有待识别的图片</summary>
    public bool HasPendingFiles => PendingFiles.Count > 0;

    /// <summary>是否正在运行识别</summary>
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

    /// <summary>是否可以开始识别：服务可用 + 未运行 + 有待识别图片</summary>
    public bool CanStart => !IsRunning && _isServiceAvailable && PendingFiles.Count > 0;

    /// <summary>是否可以取消</summary>
    public bool CanCancel => IsRunning;

    /// <summary>OCR 服务是否可用</summary>
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
    public string ServiceStatusText => _isServiceAvailable ? "OCR 引擎就绪" : "OCR 引擎未连接";

    /// <summary>识别置信度阈值 (0 ~ 100，百分比)</summary>
    public int TextScorePercent
    {
        get => _textScorePercent;
        set
        {
            if (SetProperty(ref _textScorePercent, Math.Clamp(value, 0, 100)))
            {
                // 更新所有已有结果的置信度阈值，触发遮罩刷新
                var threshold = TextScore;
                foreach (var result in Results)
                    result.ConfidenceThreshold = threshold;

                // 强制刷新选中结果的展示行绑定
                OnPropertyChanged(nameof(SelectedResult));
            }
        }
    }

    /// <summary>内部使用的置信度阈值 (0.0 ~ 1.0)，由 TextScorePercent 自动换算</summary>
    private double TextScore => _textScorePercent / 100.0;

    /// <summary>进度值</summary>
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

    /// <summary>已识别结果数量</summary>
    public int ResultCount => Results.Count;

    /// <summary>成功识别数量</summary>
    public int SuccessCount => Results.Count(r => r.IsSuccess);

    /// <summary>失败识别数量</summary>
    public int FailedCount => Results.Count(r => !r.IsSuccess);

    // ---- 命令 ----

    /// <summary>选择文件命令（只加入待识别列表，不自动识别）</summary>
    public ICommand SelectFilesCommand { get; }

    /// <summary>开始识别命令（对待识别列表中的所有图片执行 OCR）</summary>
    public ICommand StartRecognitionCommand { get; }

    /// <summary>取消当前识别命令</summary>
    public ICommand CancelCommand { get; }

    /// <summary>清除所有结果和待识别列表命令</summary>
    public ICommand ClearResultsCommand { get; }

    /// <summary>复制选中结果文本命令</summary>
    public ICommand CopyTextCommand { get; }

    /// <summary>选择结果项命令</summary>
    public ICommand SelectResultCommand { get; }

    public OcrViewModel(OcrService? ocrService, FileSystemService fileSystem,
        JobManager? jobManager = null, AppLogger? logger = null)
    {
        _ocrService = ocrService;
        _fileSystem = fileSystem ?? throw new ArgumentNullException(nameof(fileSystem));
        _jobManager = jobManager;
        _logger = logger;

        SelectFilesCommand = new RelayCommand(SelectFiles);
        StartRecognitionCommand = new RelayCommand(StartRecognitionAsync, () => CanStart);
        CancelCommand = new RelayCommand(CancelRecognition, () => CanCancel);
        ClearResultsCommand = new RelayCommand(ClearResults, () => Results.Count > 0 || PendingFiles.Count > 0);
        CopyTextCommand = new RelayCommand(CopySelectedText, () => HasSelectedResult);
        SelectResultCommand = new RelayCommand<OcrJobResult?>(r => SelectedResult = r);

        // 监听结果列表变更以更新命令状态
        Results.CollectionChanged += (_, _) => RefreshCommandStates();
        PendingFiles.CollectionChanged += (_, _) =>
        {
            OnPropertyChanged(nameof(HasPendingFiles));
            OnPropertyChanged(nameof(CanStart));
            RefreshCommandStates();
        };
    }

    /// <summary>
    /// 默认构造函数：自动检测 Python 环境和 router 脚本路径，
    /// 使模块在无外部依赖注入时也可自给自足运行。
    /// </summary>
    public OcrViewModel() : this(null, new FileSystemService())
    {
        // 尝试自动创建 OCR 服务（使用默认路径）
        var routerPath = DefaultRouterPath;
        if (File.Exists(DefaultPythonPath) && File.Exists(routerPath))
        {
            _ocrService = new OcrService(DefaultPythonPath, routerPath);
        }
        else
        {
            // Python 或 router 脚本不存在时，服务不可用，界面会显示"OCR 引擎未连接"
            StatusMessage = "OCR 引擎未安装或配置不完整，请检查 local-worker-ocr 环境";
        }
    }

    /// <summary>
    /// 初始化 OCR 服务
    /// 异步启动 worker 进程并进行健康检查。
    /// </summary>
    public async Task InitializeAsync()
    {
        if (_ocrService == null)
        {
            StatusMessage = "OCR 服务未配置";
            IsServiceAvailable = false;
            return;
        }

        StatusMessage = "正在启动 OCR 引擎...";
        try
        {
            IsServiceAvailable = await _ocrService.StartAsync();
            StatusMessage = IsServiceAvailable
                ? "OCR 引擎就绪 - 选择图片文件开始识别"
                : $"OCR 引擎启动失败: {_ocrService.AvailabilityError}";
        }
        catch (Exception ex)
        {
            IsServiceAvailable = false;
            StatusMessage = $"OCR 引擎启动失败: {ex.Message}";
            _logger?.Error($"OCR 服务初始化失败: {ex.Message}", ex, "desktop-ocr");
        }
    }

    /// <summary>
    /// 打开文件选择对话框，将选中的图片加入待识别列表。
    /// 不会自动开始 OCR 识别。
    /// </summary>
    private void SelectFiles()
    {
        var dialog = new OpenFileDialog
        {
            Title = "选择要识别的图片",
            Filter = "图片文件|*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tif;*.webp|所有文件|*.*",
            Multiselect = true,
            CheckFileExists = true
        };

        if (dialog.ShowDialog() == true && dialog.FileNames.Length > 0)
        {
            AddFilesToPending(dialog.FileNames);
        }
    }

    /// <summary>
    /// 拖拽图片到 OCR 区域时调用 —— 只加入待识别列表，不自动识别。
    /// </summary>
    /// <param name="filePaths">拖入的文件路径列表</param>
    public void RecognizeDroppedFiles(IEnumerable<string> filePaths)
    {
        if (filePaths == null) return;

        var imageFiles = filePaths
            .Where(f => _ocrService?.IsFormatSupported(f) ?? FileSystemService.IsImageFile(f))
            .ToList();

        if (imageFiles.Count == 0)
        {
            StatusMessage = "没有有效的图片文件";
            return;
        }

        AddFilesToPending(imageFiles);
    }

    /// <summary>
    /// 将文件路径加入待识别列表（去重）
    /// </summary>
    private void AddFilesToPending(IEnumerable<string> filePaths)
    {
        var addedCount = 0;
        var skippedCount = 0;

        foreach (var path in filePaths)
        {
            if (string.IsNullOrWhiteSpace(path)) continue;
            if (!File.Exists(path))
            {
                skippedCount++;
                continue;
            }

            var normalizedPath = Path.GetFullPath(path);
            if (PendingFiles.Contains(normalizedPath, StringComparer.OrdinalIgnoreCase))
            {
                skippedCount++;
                continue;
            }

            PendingFiles.Add(normalizedPath);
            addedCount++;
        }

        // 更新状态和进度
        ProgressValue = 0;
        ProgressMax = PendingFiles.Count;
        StatusMessage = $"已选择 {PendingFiles.Count} 张图片，点击\"开始识别\"";
        ErrorMessage = null;

        _logger?.Info(
            $"文件加入待识别列表：新增 {addedCount}，跳过 {skippedCount}，共 {PendingFiles.Count} 张",
            "desktop-ocr");
    }

    /// <summary>
    /// 开始识别命令 —— 对待识别列表中所有图片执行 OCR 识别。
    /// </summary>
    private async void StartRecognitionAsync()
    {
        if (PendingFiles.Count == 0) return;

        var filesToRecognize = PendingFiles.ToList();
        await StartRecognitionForFilesAsync(filesToRecognize);
    }

    /// <summary>
    /// 对指定文件列表启动 OCR 识别的核心逻辑
    /// </summary>
    private async Task StartRecognitionForFilesAsync(List<string> filePaths)
    {
        if (_ocrService == null || filePaths.Count == 0) return;

        IsRunning = true;
        ErrorMessage = null;
        ProgressValue = 0;
        ProgressMax = filePaths.Count;

        _currentCts = new CancellationTokenSource();
        var threshold = TextScore;

        StatusMessage = $"正在识别 0/{filePaths.Count}...";

        try
        {
            var results = await _ocrService.RecognizeBatchAsync(
                filePaths,
                maskBelowScore: threshold,
                useDml: false,
                onImageStart: (index, total, fileName) =>
                {
                    // 每张开始时：显示"正在识别 X/total：文件名"
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    {
                        StatusMessage = $"正在识别 {index + 1}/{total}：{fileName}";
                    });
                },
                onImageComplete: (completed, total) =>
                {
                    // 每张完成时：更新进度值
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    {
                        ProgressValue = completed;
                    });
                },
                ct: _currentCts.Token);

            // 将结果添加到列表（设置置信度阈值）
            foreach (var result in results)
            {
                result.ConfidenceThreshold = threshold;
                System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    Results.Insert(0, result));
            }

            // 如果有结果，选中第一个成功的
            if (results.Count > 0)
                SelectedResult = results.FirstOrDefault(r => r.IsSuccess) ?? results[0];

            var successCount = results.Count(r => r.IsSuccess);
            var failCount = results.Count - successCount;

            if (failCount > 0)
                StatusMessage = $"识别完成: {successCount} 成功, {failCount} 失败";
            else
                StatusMessage = $"识别完成: {successCount} 张图片全部成功";

            // 识别完成后清空待识别列表
            PendingFiles.Clear();

            _logger?.Info(
                $"OCR 批���识别完成: {successCount} 成功, {failCount} 失败", "desktop-ocr");
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "识别已取消";
            ProgressValue = 0;
            _logger?.Info("OCR 识别已取消", "desktop-ocr");
        }
        catch (Exception ex)
        {
            ErrorMessage = $"识别失败: {ex.Message}";
            StatusMessage = "识别出错，请查看错误信息";
            _logger?.Error($"OCR 识别异常: {ex.Message}", ex, "desktop-ocr");
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
    /// 取消当前识别任务
    /// </summary>
    private void CancelRecognition()
    {
        _currentCts?.Cancel();
        StatusMessage = "正在取消...";
    }

    /// <summary>
    /// 清除所有识别结果、待识别列表和进度
    /// </summary>
    private void ClearResults()
    {
        Results.Clear();
        PendingFiles.Clear();
        SelectedResult = null;
        ErrorMessage = null;
        ProgressValue = 0;
        ProgressMax = 100;
        StatusMessage = "结果已清除 - 选择图片文件开始 OCR 识别";
        RefreshCommandStates();
    }

    /// <summary>
    /// 复制选中结果的文本到剪贴板
    /// 优先复制格式化文本，其次复制 total_text
    /// </summary>
    private void CopySelectedText()
    {
        if (SelectedResult == null) return;

        var textToCopy = !string.IsNullOrEmpty(SelectedResult.FormattedText)
            ? SelectedResult.FormattedText
            : SelectedResult.TotalText;

        try
        {
            System.Windows.Clipboard.SetText(textToCopy);
            StatusMessage = "已复制识别文本到剪贴板";
        }
        catch (Exception ex)
        {
            StatusMessage = $"复制失败: {ex.Message}";
        }
    }

    /// <summary>
    /// 刷新命令可执行状态
    /// </summary>
    private void RefreshCommandStates()
    {
        OnPropertyChanged(nameof(ResultCount));
        OnPropertyChanged(nameof(SuccessCount));
        OnPropertyChanged(nameof(FailedCount));

        (StartRecognitionCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (CancelCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (ClearResultsCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (CopyTextCommand as RelayCommand)?.RaiseCanExecuteChanged();
    }
}
