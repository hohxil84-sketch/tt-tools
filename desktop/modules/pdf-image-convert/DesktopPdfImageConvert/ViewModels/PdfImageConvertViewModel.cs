using System.Collections.ObjectModel;
using System.Windows.Input;
using Microsoft.Win32;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTShared.Logging;
using TTShared.UI;
using TTTools.PdfImageConvert.Models;
using TTTools.PdfImageConvert.Services;

namespace TTTools.PdfImageConvert.ViewModels;

/// <summary>
/// PDF/图片互转模块主 ViewModel
/// 管理文件选择、转换方向配置、权限校验、处理触发、结果预览的完整流程。
/// 本地付费功能：每次处理前通过云端的 /api/v1/entitlements/check 检查套餐权限。
/// </summary>
public class PdfImageConvertViewModel : BaseViewModel
{
    private readonly PdfImageConvertService? _convertService;
    private readonly AuthState? _authState;
    private readonly FileSystemService _fileSystem;
    private readonly JobManager? _jobManager;
    private readonly AppLogger? _logger;

    private bool _isRunning;
    private string _statusMessage = "就绪 - 选择文件开始转换";
    private string? _errorMessage;
    private int _progressValue;
    private int _progressMax = 100;
    private bool _isServiceAvailable;
    private PdfImageConvertResult? _selectedResult;
    private CancellationTokenSource? _currentCts;

    // ---- 转换参数 ----
    private string _selectedDirection = "pdf_to_images";
    private string _selectedOutputFormat = "png";
    private int _dpi = 200;
    private int _jpegQuality = 92;
    private int _pageStart = 1;
    private int _pageEnd = 0; // 0 = 全部页面
    private int _pageLimit;

    /// <summary>已处理的转换结果列表</summary>
    public ObservableCollection<PdfImageConvertResult> Results { get; } = new();

    /// <summary>当前选中的结果（显示在预览区）</summary>
    public PdfImageConvertResult? SelectedResult
    {
        get => _selectedResult;
        set
        {
            if (SetProperty(ref _selectedResult, value))
            {
                OnPropertyChanged(nameof(HasSelectedResult));
                OnPropertyChanged(nameof(SelectedPreviewText));
            }
        }
    }

    /// <summary>是否有选中结果</summary>
    public bool HasSelectedResult => SelectedResult != null;

    /// <summary>选中结果的预览文本</summary>
    public string SelectedPreviewText => SelectedResult != null
        ? $"文件: {SelectedResult.InputFileName}\n" +
          $"方向: {SelectedResult.DirectionDisplay}\n" +
          $"页数: {SelectedResult.PagesSummary}\n" +
          $"输出: {SelectedResult.OutputFormatDisplay} ({SelectedResult.OutputSizeDisplay})\n" +
          $"耗时: {SelectedResult.ElapsedMsDisplay}"
        : string.Empty;

    // ---- 状态属性 ----

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

    /// <summary>是否正在运行处理</summary>
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

    /// <summary>是否可以开始处理</summary>
    public bool CanStart => !IsRunning && _isServiceAvailable;

    /// <summary>是否可以取消</summary>
    public bool CanCancel => IsRunning;

    /// <summary>转换服务是否可用</summary>
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
    public string ServiceStatusText => _isServiceAvailable ? "转换引擎就绪" : "转换引擎未连接";

    // ---- 转换参数属性 ----

    /// <summary>当前选择的转换方向</summary>
    public string SelectedDirection
    {
        get => _selectedDirection;
        set
        {
            if (SetProperty(ref _selectedDirection, value))
                UpdateVisibility();
        }
    }

    /// <summary>当前选择的输出格式</summary>
    public string SelectedOutputFormat
    {
        get => _selectedOutputFormat;
        set
        {
            if (SetProperty(ref _selectedOutputFormat, value))
                UpdateVisibility();
        }
    }

    /// <summary>PDF 渲染 DPI（72-600）</summary>
    public int Dpi
    {
        get => _dpi;
        set => SetProperty(ref _dpi, Math.Clamp(value, 72, 600));
    }

    /// <summary>JPEG 输出质量（1-100）</summary>
    public int JpegQuality
    {
        get => _jpegQuality;
        set => SetProperty(ref _jpegQuality, Math.Clamp(value, 1, 100));
    }

    /// <summary>PDF→图片时的起始页码（1-based）</summary>
    public int PageStart
    {
        get => _pageStart;
        set => SetProperty(ref _pageStart, Math.Max(1, value));
    }

    /// <summary>PDF→图片时的结束页码（1-based），0 表示全部</summary>
    public int PageEnd
    {
        get => _pageEnd;
        set => SetProperty(ref _pageEnd, Math.Max(0, value));
    }

    /// <summary>最多转换页数（0 表示不限制）</summary>
    public int PageLimit
    {
        get => _pageLimit;
        set => SetProperty(ref _pageLimit, Math.Max(0, value));
    }

    // ---- 条件可见性属性（UI 根据这些属性显示/隐藏控件） ----

    /// <summary>是否 PDF→图片 方向（显示 DPI/格式/页码参数）</summary>
    public bool IsPdfToImages => SelectedDirection == "pdf_to_images";

    /// <summary>是否显示 JPEG 质量参数</summary>
    public bool ShowJpegQuality => SelectedOutputFormat == "jpeg";

    // ---- 可用选项列表 ----

    /// <summary>可用的转换方向列表</summary>
    public static List<(string Value, string Display)> DirectionList { get; } = new()
    {
        ("pdf_to_images", "PDF 转图片 - 将 PDF 每页渲染为独立图片"),
        ("images_to_pdf", "图片转 PDF - 将多张图片合并为一个 PDF"),
    };

    /// <summary>可用的输出格式列表（仅 PDF→图片时使用）</summary>
    public static List<(string Value, string Display)> FormatList { get; } = new()
    {
        ("png", "PNG - 无损压缩，支持透明"),
        ("jpeg", "JPEG - 有损压缩，文件较小"),
    };

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

    /// <summary>已处理结果数量</summary>
    public int ResultCount => Results.Count;

    /// <summary>成功处理数量</summary>
    public int SuccessCount => Results.Count(r => r.IsSuccess);

    /// <summary>失败处理数量</summary>
    public int FailedCount => Results.Count(r => !r.IsSuccess);

    // ---- 命令 ----

    public ICommand SelectFilesCommand { get; }
    public ICommand StartProcessingCommand { get; }
    public ICommand CancelCommand { get; }
    public ICommand ClearResultsCommand { get; }
    public ICommand OpenOutputFileCommand { get; }
    public ICommand SelectResultCommand { get; }

    public PdfImageConvertViewModel(
        PdfImageConvertService? convertService,
        AuthState? authState,
        FileSystemService fileSystem,
        JobManager? jobManager = null,
        AppLogger? logger = null)
    {
        _convertService = convertService;
        _authState = authState;
        _fileSystem = fileSystem ?? throw new ArgumentNullException(nameof(fileSystem));
        _jobManager = jobManager;
        _logger = logger;

        SelectFilesCommand = new RelayCommand(SelectFiles);
        StartProcessingCommand = new RelayCommand(StartProcessingAsync, () => CanStart);
        CancelCommand = new RelayCommand(CancelProcessing, () => CanCancel);
        ClearResultsCommand = new RelayCommand(ClearResults, () => Results.Count > 0);
        OpenOutputFileCommand = new RelayCommand(OpenOutputFile, () => HasSelectedResult);
        SelectResultCommand = new RelayCommand<PdfImageConvertResult?>(r => SelectedResult = r);

        // 监听结果列表变更以更新命令状态
        Results.CollectionChanged += (_, _) => RefreshCommandStates();
    }

    /// <summary>
    /// 默认构造函数（用于设计时）
    /// </summary>
    public PdfImageConvertViewModel() : this(null, null, new FileSystemService()) { }

    /// <summary>
    /// 初始化转换服务。
    /// 异步启动 worker 进程并进行健康检查。
    /// </summary>
    public async Task InitializeAsync()
    {
        if (_convertService == null)
        {
            StatusMessage = "PDF/图片互转服务未配置";
            IsServiceAvailable = false;
            return;
        }

        StatusMessage = "正在启动转换引擎...";
        try
        {
            IsServiceAvailable = await _convertService.StartAsync();
            if (IsServiceAvailable)
            {
                StatusMessage = "转换引擎就绪 - 选择文件开始转换";
            }
            else
            {
                StatusMessage = $"转换引擎启动失败: {_convertService.AvailabilityError}";
            }
        }
        catch (Exception ex)
        {
            IsServiceAvailable = false;
            StatusMessage = $"转换引擎启动失败: {ex.Message}";
            _logger?.Error($"PDF/图片互转服务初始化失败: {ex.Message}", ex, "desktop-pdf-image-convert");
        }
    }

    /// <summary>
    /// 打开文件选择对话框。
    /// PDF→图片：选择 PDF 文件。
    /// 图片→PDF：选择多张图片文件。
    /// </summary>
    private void SelectFiles()
    {
        var isPdfToImages = IsPdfToImages;

        var dialog = new OpenFileDialog
        {
            Title = isPdfToImages ? "选择要转换的 PDF 文件" : "选择要合并为 PDF 的图片",
            Filter = isPdfToImages
                ? "PDF 文件|*.pdf|所有文件|*.*"
                : "图片文件|*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tif;*.webp|所有文件|*.*",
            Multiselect = !isPdfToImages, // 图片转 PDF 允许多选
            CheckFileExists = true,
        };

        if (dialog.ShowDialog() == true && dialog.FileNames.Length > 0)
        {
            _ = StartProcessingForFilesAsync(dialog.FileNames.ToList());
        }
    }

    /// <summary>
    /// 开始处理（通过拖拽文件触发）- 在 View 层由拖拽事件调用。
    /// </summary>
    /// <param name="filePaths">拖入的文件路径列表</param>
    public void ProcessDroppedFiles(IEnumerable<string> filePaths)
    {
        if (filePaths == null) return;

        var validFiles = filePaths
            .Where(f => _convertService?.IsFormatSupported(f) ?? false)
            .ToList();

        if (validFiles.Count == 0)
        {
            StatusMessage = "没有有效的文件（需要 PDF 或图片文件）";
            return;
        }

        // 根据第一个文件类型自动判断转换方向
        if (validFiles.Count == 1)
        {
            var firstFile = validFiles[0];
            if (_convertService?.IsPdfFormatSupported(firstFile) == true)
            {
                SelectedDirection = "pdf_to_images";
            }
            else
            {
                // 单张图片也可以转 PDF，但更合理的可能是 PDF→图片
                // 这里保持用户当前选择，仅自动判断单 PDF 的情况
            }
        }

        _ = StartProcessingForFilesAsync(validFiles);
    }

    /// <summary>
    /// 开始处理命令处理（视图命令绑定）。
    /// </summary>
    private void StartProcessingAsync()
    {
        SelectFiles();
    }

    /// <summary>
    /// 对指定文件列表启动转换处理的核心逻辑。
    /// 每个文件处理前都会通过 PdfImageConvertService 进行权限检查（C1）。
    /// </summary>
    private async Task StartProcessingForFilesAsync(List<string> filePaths)
    {
        if (_convertService == null || filePaths.Count == 0) return;

        // 检查登录状态（C1: 未登录直接提示，不发起处理）
        if (_authState != null && !_authState.IsLoggedIn)
        {
            ErrorMessage = "请先登录后再使用 PDF/图片互转功能";
            StatusMessage = "未登录 - 请先登录";
            return;
        }

        IsRunning = true;
        ErrorMessage = null;
        ProgressValue = 0;
        ProgressMax = filePaths.Count;

        _currentCts = new CancellationTokenSource();

        StatusMessage = $"正在处理 {filePaths.Count} 个文件...";

        try
        {
            var isPdfToImages = IsPdfToImages;

            if (isPdfToImages)
            {
                // PDF 转图片：每个 PDF 文件独立处理
                for (var i = 0; i < filePaths.Count; i++)
                {
                    _currentCts.Token.ThrowIfCancellationRequested();

                    var filePath = filePaths[i];
                    try
                    {
                        var param = BuildParamsFromUI();
                        var result = await _convertService.ConvertAsync(
                            filePath, outputPath: null, param, null, _currentCts.Token);

                        System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                            Results.Insert(0, result));
                    }
                    catch (Exception ex)
                    {
                        System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                            Results.Insert(0, new PdfImageConvertResult
                            {
                                IsSuccess = false,
                                ErrorMessage = ex.Message,
                                InputPath = filePath,
                            }));
                        _logger?.Error(
                            $"第 {i + 1}/{filePaths.Count} 个 PDF 转换失败: {ex.Message}",
                            ex, "desktop-pdf-image-convert");
                    }

                    var current = i + 1;
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    {
                        ProgressValue = current;
                        StatusMessage = $"正在处理... {current}/{filePaths.Count}";
                    });
                }
            }
            else
            {
                // 图片转 PDF：将所有图片合并为一个 PDF
                if (filePaths.Count > 100)
                {
                    ErrorMessage = $"图片数量超过上限（100张），当前: {filePaths.Count}";
                    return;
                }

                try
                {
                    var param = BuildParamsFromUI();
                    var result = await _convertService.ConvertAsync(
                        filePaths[0], outputPath: null, param,
                        inputPaths: filePaths,
                        ct: _currentCts.Token);

                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                        Results.Insert(0, result));
                }
                catch (Exception ex)
                {
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                        Results.Insert(0, new PdfImageConvertResult
                        {
                            IsSuccess = false,
                            ErrorMessage = ex.Message,
                            InputPath = filePaths[0],
                        }));
                    _logger?.Error(
                        $"图片转 PDF 失败: {ex.Message}",
                        ex, "desktop-pdf-image-convert");
                }

                System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                {
                    ProgressValue = filePaths.Count;
                    StatusMessage = $"处理完成";
                });
            }

            // 如果有结果，选中第一个
            if (Results.Count > 0)
            {
                var firstSuccess = Results.FirstOrDefault(r => r.IsSuccess);
                SelectedResult = firstSuccess ?? Results[0];
            }

            var successCount = Results.Count(r => r.IsSuccess);
            var failCount = Results.Count - successCount;

            if (failCount > 0)
                StatusMessage = $"处理完成: {successCount} 成功, {failCount} 失败";
            else
                StatusMessage = $"处理完成: {successCount} 个任务全部成功";

            _logger?.Info(
                $"PDF/图片互转处理完成: {successCount} 成功, {failCount} 失败",
                "desktop-pdf-image-convert");
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "处理已取消";
            _logger?.Info("PDF/图片互转处理已取消", "desktop-pdf-image-convert");
        }
        catch (Exception ex)
        {
            ErrorMessage = $"处理失败: {ex.Message}";
            StatusMessage = "处理出错，请查看错误信息";
            _logger?.Error($"PDF/图片互转处理异常: {ex.Message}", ex, "desktop-pdf-image-convert");
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
    /// 从当前 UI 状态构建 PdfImageConvertParams。
    /// </summary>
    public PdfImageConvertParams BuildParamsFromUI()
    {
        var param = new PdfImageConvertParams
        {
            Direction = SelectedDirection,
            OutputFormat = SelectedOutputFormat,
            Dpi = Dpi,
            JpegQuality = JpegQuality,
        };

        // 页码范围：PageStart > 0 且 PageEnd >= PageStart 时才设置
        if (IsPdfToImages && PageStart > 0 && PageEnd >= PageStart)
        {
            param.PageRange = new List<int> { PageStart, PageEnd };
        }

        // 页面限制
        if (IsPdfToImages && PageLimit > 0)
        {
            param.PageLimit = PageLimit;
        }

        return param;
    }

    /// <summary>
    /// 取消当前处理任务。
    /// </summary>
    private void CancelProcessing()
    {
        _currentCts?.Cancel();
        StatusMessage = "正在取消...";
    }

    /// <summary>
    /// 清除所有处理结果。
    /// </summary>
    private void ClearResults()
    {
        Results.Clear();
        SelectedResult = null;
        ErrorMessage = null;
        ProgressValue = 0;
        StatusMessage = "结果已清除 - 选择文件开始转换";
        RefreshCommandStates();
    }

    /// <summary>
    /// 在文件资源管理器中打开输出文件所在目录。
    /// </summary>
    private void OpenOutputFile()
    {
        if (SelectedResult == null || string.IsNullOrEmpty(SelectedResult.OutputPath)) return;

        try
        {
            var path = SelectedResult.OutputPath;
            if (File.Exists(path))
            {
                System.Diagnostics.Process.Start("explorer.exe", $"/select,\"{path}\"");
            }
            else if (Directory.Exists(path))
            {
                System.Diagnostics.Process.Start("explorer.exe", path);
            }
            else
            {
                StatusMessage = $"输出路径不存在: {path}";
            }
        }
        catch (Exception ex)
        {
            StatusMessage = $"打开文件失败: {ex.Message}";
        }
    }

    /// <summary>
    /// 更新条件可见性属性，当方向或格式切换时通知 UI 刷新。
    /// </summary>
    private void UpdateVisibility()
    {
        OnPropertyChanged(nameof(IsPdfToImages));
        OnPropertyChanged(nameof(ShowJpegQuality));
    }

    /// <summary>
    /// 刷新命令可执行状态。
    /// </summary>
    private void RefreshCommandStates()
    {
        OnPropertyChanged(nameof(ResultCount));
        OnPropertyChanged(nameof(SuccessCount));
        OnPropertyChanged(nameof(FailedCount));

        (StartProcessingCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (CancelCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (ClearResultsCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (OpenOutputFileCommand as RelayCommand)?.RaiseCanExecuteChanged();
    }
}
