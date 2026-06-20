using System.Collections.ObjectModel;
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
/// </summary>
public class OcrViewModel : BaseViewModel
{
    private readonly OcrService? _ocrService;
    private readonly FileSystemService _fileSystem;
    private readonly JobManager? _jobManager;
    private readonly AppLogger? _logger;

    private bool _isRunning;
    private string _statusMessage = "就绪 - 选择图片文件开始 OCR 识别";
    private string? _errorMessage;
    private double _textScore = 0.5;
    private int _progressValue;
    private int _progressMax = 100;
    private bool _isServiceAvailable;
    private OcrJobResult? _selectedResult;
    private CancellationTokenSource? _currentCts;

    /// <summary>已识别的 OCR 结果列表</summary>
    public ObservableCollection<OcrJobResult> Results { get; } = new();

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
                OnPropertyChanged(nameof(SelectedTextLineCount));
            }
        }
    }

    /// <summary>是否有选中结果</summary>
    public bool HasSelectedResult => SelectedResult != null;

    /// <summary>选中结果的完整文本</summary>
    public string SelectedTotalText => SelectedResult?.TotalText ?? string.Empty;

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

    /// <summary>是否可以开始识别</summary>
    public bool CanStart => !IsRunning && _isServiceAvailable;

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

    /// <summary>识别置信度阈值 (0.0 ~ 1.0)</summary>
    public double TextScore
    {
        get => _textScore;
        set => SetProperty(ref _textScore, Math.Clamp(value, 0.0, 1.0));
    }

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

    /// <summary>已识别结果数量</summary>
    public int ResultCount => Results.Count;

    /// <summary>成功识别数量</summary>
    public int SuccessCount => Results.Count(r => r.IsSuccess);

    /// <summary>失败识别数量</summary>
    public int FailedCount => Results.Count(r => !r.IsSuccess);

    // ---- 命令 ----

    /// <summary>选择文件命令</summary>
    public ICommand SelectFilesCommand { get; }

    /// <summary>开始识别选中文件命令</summary>
    public ICommand StartRecognitionCommand { get; }

    /// <summary>取消当前识别命令</summary>
    public ICommand CancelCommand { get; }

    /// <summary>清除所有结果命令</summary>
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
        ClearResultsCommand = new RelayCommand(ClearResults, () => Results.Count > 0);
        CopyTextCommand = new RelayCommand(CopySelectedText, () => HasSelectedResult);
        SelectResultCommand = new RelayCommand<OcrJobResult?>(r => SelectedResult = r);

        // 监听结果列表变更以更新命令状态
        Results.CollectionChanged += (_, _) => RefreshCommandStates();
    }

    /// <summary>
    /// 默认构造函数（用于设计时）
    /// </summary>
    public OcrViewModel() : this(null, new FileSystemService()) { }

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
    /// 打开文件选择对话框，选择要识别的图片文件
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
            // 导入选中的文件并进行 OCR 识别
            _ = StartRecognitionForFilesAsync(dialog.FileNames.ToList());
        }
    }

    /// <summary>
    /// 开始识别（通过拖拽文件触发）- 在 View 层由拖拽事件调用
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

        _ = StartRecognitionForFilesAsync(imageFiles);
    }

    /// <summary>
    /// 开始识别命令处理（视图命令绑定） - 委托到 SelectFiles
    /// </summary>
    private void StartRecognitionAsync()
    {
        // 如果有缓存的待处理文件，直接识别
        // 否则打开文件选择对话框
        SelectFiles();
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

        StatusMessage = $"正在识别 {filePaths.Count} 张图片...";

        try
        {
            var results = await _ocrService.RecognizeBatchAsync(
                filePaths,
                TextScore,
                useDml: false,
                (current, total) =>
                {
                    // 在 UI 线程更新进度
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    {
                        ProgressValue = current;
                        StatusMessage = $"正在识别... {current}/{total}";
                    });
                },
                _currentCts.Token);

            // 将结果添加到列表
            foreach (var result in results)
            {
                System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    Results.Insert(0, result));
            }

            // 如果有结果，选中第一个
            if (results.Count > 0)
                SelectedResult = results.FirstOrDefault(r => r.IsSuccess) ?? results[0];

            var successCount = results.Count(r => r.IsSuccess);
            var failCount = results.Count - successCount;

            if (failCount > 0)
                StatusMessage = $"识别完成: {successCount} 成功, {failCount} 失败";
            else
                StatusMessage = $"识别完成: {successCount} 张图片全部成功";

            _logger?.Info(
                $"OCR 识别完成: {successCount} 成功, {failCount} 失败", "desktop-ocr");
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "识别已取消";
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
    /// 清除所有识别结果
    /// </summary>
    private void ClearResults()
    {
        Results.Clear();
        SelectedResult = null;
        ErrorMessage = null;
        ProgressValue = 0;
        StatusMessage = "结果已清除 - 选择图片文件开始 OCR 识别";
        RefreshCommandStates();
    }

    /// <summary>
    /// 复制选中结果的文本到剪贴板
    /// </summary>
    private void CopySelectedText()
    {
        if (SelectedResult == null) return;

        try
        {
            System.Windows.Clipboard.SetText(SelectedResult.TotalText);
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
