using System.Collections.ObjectModel;
using System.Windows.Input;
using Microsoft.Win32;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTShared.Logging;
using TTShared.UI;
using TTTools.ResizeImage.Models;
using TTTools.ResizeImage.Services;

namespace TTTools.ResizeImage.ViewModels;

/// <summary>
/// 图片改尺寸模块主 ViewModel
/// 管理文件选择、改尺寸参数配置、权限校验、处理触发、结果预览的完整流程。
/// 本地付费功能：每次处理前通过云端的 /api/v1/entitlements/check 检查套餐权限。
/// </summary>
public class ResizeImageViewModel : BaseViewModel
{
    private readonly ResizeImageService? _resizeService;
    private readonly AuthState? _authState;
    private readonly FileSystemService _fileSystem;
    private readonly JobManager? _jobManager;
    private readonly AppLogger? _logger;

    private bool _isRunning;
    private string _statusMessage = "请选择文件";
    private string? _errorMessage;
    private int _progressValue;
    private int _progressMax = 100;
    private bool _isServiceAvailable;
    private ResizeImageResult? _selectedResult;
    private CancellationTokenSource? _currentCts;

    // ---- 改尺寸参数 ----
    private string _selectedMode = "fit";
    private string _selectedPreset = ""; // 空字符串 = 自定义
    private int _width = 800;
    private int _height = 600;
    private double _scalePercent = 50.0;
    private int _shortSide = 400;
    private int _longSide = 1200;
    private int _targetDpi = 300;
    private string _selectedResample = "lanczos";
    private bool _keepAspect = true;
    private string _selectedOutputFormat = "original";
    private int _jpegQuality = 92;
    private int _pngCompressLevel = 6;
    private int _webpQuality = 85;
    private double _customDpiX = 300;
    private double _customDpiY = 300;

    /// <summary>已处理的改尺寸结果列表</summary>
    public ObservableCollection<ResizeImageResult> Results { get; } = new();

    /// <summary>待处理图片文件路径列表</summary>
    public ObservableCollection<string> PendingFiles { get; } = new();

    /// <summary>是否有待处理的图片</summary>
    public bool HasPendingFiles => PendingFiles.Count > 0;

    /// <summary>当前选中的结果（显示在预览区）</summary>
    public ResizeImageResult? SelectedResult
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
        ? $"源文件: {SelectedResult.InputFileName}\n" +
          $"尺寸: {SelectedResult.SizeSummary}\n" +
          $"缩放: {SelectedResult.ScaleRatioDisplay}\n" +
          $"输出: {SelectedResult.OutputFormatSummary}\n" +
          $"DPI: {SelectedResult.DpiSummary}\n" +
          $"耗时: {SelectedResult.ElapsedMs:F1} ms"
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

    /// <summary>是否可以开始处理：服务可用 + 未运行 + 有待处理文件</summary>
    public bool CanStart => !IsRunning && _isServiceAvailable && PendingFiles.Count > 0;

    /// <summary>是否可以取消</summary>
    public bool CanCancel => IsRunning;

    /// <summary>改尺寸服务是否可用</summary>
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
    public string ServiceStatusText => _isServiceAvailable ? "改尺寸引擎就绪" : "改尺寸引擎未连接";

    // ---- 改尺寸参数属性 ----

    /// <summary>当前选择的缩放模式</summary>
    public string SelectedMode
    {
        get => _selectedMode;
        set
        {
            if (SetProperty(ref _selectedMode, value))
                UpdateVisibility();
        }
    }

    /// <summary>当前选择的预设名称（空字符串 = 自定义）</summary>
    public string SelectedPreset
    {
        get => _selectedPreset;
        set
        {
            if (SetProperty(ref _selectedPreset, value))
            {
                // 选择预设后自动切换为 FIT 模式，并填入对应宽高
                if (!string.IsNullOrEmpty(value))
                {
                    var preset = AvailablePresets.FirstOrDefault(p => p.Name == value);
                    if (preset != null)
                    {
                        SelectedMode = "fit";
                        Width = preset.Width;
                        Height = preset.Height;
                    }
                }
            }
        }
    }

    public int Width { get => _width; set => SetProperty(ref _width, Math.Max(1, value)); }
    public int Height { get => _height; set => SetProperty(ref _height, Math.Max(1, value)); }
    public double ScalePercent { get => _scalePercent; set => SetProperty(ref _scalePercent, Math.Max(1, value)); }
    public int ShortSide { get => _shortSide; set => SetProperty(ref _shortSide, Math.Max(1, value)); }
    public int LongSide { get => _longSide; set => SetProperty(ref _longSide, Math.Max(1, value)); }
    public int TargetDpi { get => _targetDpi; set => SetProperty(ref _targetDpi, Math.Max(1, value)); }
    public string SelectedResample { get => _selectedResample; set => SetProperty(ref _selectedResample, value); }
    public bool KeepAspect { get => _keepAspect; set => SetProperty(ref _keepAspect, value); }
    public string SelectedOutputFormat { get => _selectedOutputFormat; set { if (SetProperty(ref _selectedOutputFormat, value)) UpdateVisibility(); } }
    public int JpegQuality { get => _jpegQuality; set => SetProperty(ref _jpegQuality, Math.Clamp(value, 1, 100)); }
    public int PngCompressLevel { get => _pngCompressLevel; set => SetProperty(ref _pngCompressLevel, Math.Clamp(value, 0, 9)); }
    public int WebpQuality { get => _webpQuality; set => SetProperty(ref _webpQuality, Math.Clamp(value, 1, 100)); }
    public double CustomDpiX { get => _customDpiX; set => SetProperty(ref _customDpiX, Math.Max(0.1, value)); }
    public double CustomDpiY { get => _customDpiY; set => SetProperty(ref _customDpiY, Math.Max(0.1, value)); }

    // ---- 条件可见性属性（UI 根据这些属性显示/隐藏控件） ----

    public bool ShowWidthHeight => SelectedMode is "fit" or "exact" or "fill";
    public bool ShowScalePercent => SelectedMode == "scale";
    public bool ShowShortSide => SelectedMode == "short_side";
    public bool ShowLongSide => SelectedMode == "long_side";
    public bool ShowTargetDpi => SelectedMode == "custom_dpi";
    public bool ShowKeepAspect => SelectedMode == "exact";
    public bool ShowJpegQuality => SelectedOutputFormat == "jpeg";
    public bool ShowPngCompress => SelectedOutputFormat == "png";
    public bool ShowWebpQuality => SelectedOutputFormat == "webp";

    /// <summary>可用的预设列表</summary>
    public ObservableCollection<PresetInfo> AvailablePresets { get; } = new();

    /// <summary>可用的缩放模式列表（中文名称）</summary>
    public List<SelectOption> ModeList { get; } = new()
    {
        new("fit", "等比适配 - 不超出边界保持比例"),
        new("exact", "精确尺寸 - 拉伸到指定宽高"),
        new("fill", "等比填充 - 填满边界居中裁剪"),
        new("scale", "百分比缩放 - 按比例放大缩小"),
        new("short_side", "短边约束 - 短边对齐长边自适应"),
        new("long_side", "长边约束 - 长边对齐短边自适应"),
        new("custom_dpi", "按 DPI 缩放 - 根据目标 DPI 计算"),
    };

    /// <summary>可用的重采样滤镜列表（中文名称）</summary>
    public List<SelectOption> ResampleList { get; } = new()
    {
        new("lanczos", "Lanczos (推荐，最佳质量)"),
        new("bilinear", "Bilinear (较快，适合缩小)"),
        new("bicubic", "Bicubic (较慢，适合放大)"),
        new("nearest", "Nearest (最快，像素风格)"),
        new("box", "Box (区域平均)"),
        new("hamming", "Hamming (Sinc 插值)"),
    };

    /// <summary>可用的输出格式列表（中文名称）</summary>
    public List<SelectOption> FormatList { get; } = new()
    {
        new("original", "保持原格式"),
        new("png", "PNG - 无损，支持透明"),
        new("jpeg", "JPEG - 有损，文件小"),
        new("bmp", "BMP - 无压缩，Windows 标准"),
        new("tiff", "TIFF - 印刷标准，LZW 压缩"),
        new("webp", "WEBP - Web 优化格式"),
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
    public ICommand SelectPresetCommand { get; }

    public ResizeImageViewModel(
        ResizeImageService? resizeService,
        AuthState? authState,
        FileSystemService fileSystem,
        JobManager? jobManager = null,
        AppLogger? logger = null)
    {
        _resizeService = resizeService;
        _authState = authState;
        _fileSystem = fileSystem ?? throw new ArgumentNullException(nameof(fileSystem));
        _jobManager = jobManager;
        _logger = logger;

        SelectFilesCommand = new RelayCommand(SelectFiles);
        StartProcessingCommand = new RelayCommand(StartProcessingAsync, () => CanStart);
        CancelCommand = new RelayCommand(CancelProcessing, () => CanCancel);
        ClearResultsCommand = new RelayCommand(ClearResults, () => Results.Count > 0 || PendingFiles.Count > 0);
        OpenOutputFileCommand = new RelayCommand(OpenOutputFile, () => HasSelectedResult);
        SelectResultCommand = new RelayCommand<ResizeImageResult?>(r => SelectedResult = r);
        SelectPresetCommand = new RelayCommand<PresetInfo?>(p =>
        {
            if (p != null) SelectedPreset = p.Name;
            else SelectedPreset = "";
        });

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
    /// 默认构造函数（壳层无 DI 时使用，自动创建 ResizeImageService 并尝试连接 worker）
    /// </summary>
    public ResizeImageViewModel() : this(new ResizeImageService(), null, new FileSystemService())
    {
        // 从 Service 获取 AuthState（默认构造的 Service 和 VM 不共享 AuthState 引用）
        // 壳层统一 DI 就位后，AuthState 应由 DI 容器统一注入
    }

    /// <summary>
    /// 初始化改尺寸服务。
    /// 异步启动 worker 进程并进行健康检查，加载可用预设列表。
    /// </summary>
    public async Task InitializeAsync()
    {
        if (_resizeService == null)
        {
            StatusMessage = "改尺寸服务未配置";
            IsServiceAvailable = false;
            return;
        }

        StatusMessage = "正在启动改尺寸引擎...";
        try
        {
            IsServiceAvailable = await _resizeService.StartAsync();
            if (IsServiceAvailable)
            {
                StatusMessage = "请选择文件";

                // 加载可用预设列表
                try
                {
                    var presets = await _resizeService.GetPresetsAsync(useCache: false);
                    AvailablePresets.Clear();
                    foreach (var preset in presets)
                        AvailablePresets.Add(preset);
                }
                catch
                {
                    // 加载预设失败不是致命错误
                }
            }
            else
            {
                StatusMessage = "处理服务不可用，请检查本地环境";
            }
        }
        catch (Exception ex)
        {
            IsServiceAvailable = false;
            StatusMessage = "处理服务不可用，请检查本地环境";
            _logger?.Error($"改尺寸服务初始化失败: {ex.Message}", ex, "desktop-resize-image");
        }
    }

    /// <summary>
    /// 打开文件选择对话框，将选中的图片加入待处理列表。
    /// 不会自动开始处理。
    /// </summary>
    private void SelectFiles()
    {
        var dialog = new OpenFileDialog
        {
            Title = "选择要改尺寸的图片",
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
    /// 拖拽文件到窗口时调用 —— 只加入待处理列表，不自动处理。
    /// </summary>
    /// <param name="filePaths">拖入的文件路径列表</param>
    public void ProcessDroppedFiles(IEnumerable<string> filePaths)
    {
        if (filePaths == null) return;

        var imageFiles = filePaths
            .Where(f => _resizeService?.IsFormatSupported(f) ?? FileSystemService.IsImageFile(f))
            .ToList();

        if (imageFiles.Count == 0)
        {
            StatusMessage = "没有有效的图片文件";
            return;
        }

        AddFilesToPending(imageFiles);
    }

    /// <summary>
    /// 开始处理命令 —— 对待处理列表中的所有图片执行改尺寸处理。
    /// </summary>
    private async void StartProcessingAsync()
    {
        if (PendingFiles.Count == 0) return;
        var files = PendingFiles.ToList();
        await StartProcessingForFilesAsync(files);
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
    /// 对指定文件列表启动改尺寸处理的核心逻辑。
    /// 每个文件处理前都会通过 ResizeService 进行权限检查（C1）。
    /// </summary>
    private async Task StartProcessingForFilesAsync(List<string> filePaths)
    {
        if (_resizeService == null || filePaths.Count == 0) return;

        // 检查登录状态（C1: 未登录直接提示，不发起处理）
        // 优先用 VM 注入的 AuthState，否则用 Service 的 AuthState
        var effectiveAuth = _authState ?? _resizeService.AuthState;
        if (!effectiveAuth.IsLoggedIn)
        {
            ErrorMessage = "请先登录后再使用图片改尺寸功能";
            StatusMessage = "未登录 - 请先登录";
            return;
        }

        IsRunning = true;
        ErrorMessage = null;
        ProgressValue = 0;
        ProgressMax = filePaths.Count;

        _currentCts = new CancellationTokenSource();

        StatusMessage = $"正在处理 0/{filePaths.Count}...";

        try
        {
            for (var i = 0; i < filePaths.Count; i++)
            {
                _currentCts.Token.ThrowIfCancellationRequested();

                var filePath = filePaths[i];
                try
                {
                    var param = BuildParamsFromUI();
                    var result = await _resizeService.ResizeAsync(
                        filePath, outputPath: null, param, _currentCts.Token);

                    // 将结果添加到列表（UI 线程）
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    {
                        Results.Insert(0, result);
                        // 权限拒绝或处理失败时，把原因显示到错误横幅
                        if (!result.IsSuccess && !string.IsNullOrEmpty(result.ErrorMessage))
                            ErrorMessage = result.ErrorMessage;
                        else if (!result.EntitlementAllowed)
                            ErrorMessage = result.EntitlementReason ?? "套餐权限不足";
                    });
                }
                catch (Exception ex)
                {
                    // 单张处理失败不影响其余文件
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    {
                        Results.Insert(0, new ResizeImageResult
                        {
                            IsSuccess = false,
                            ErrorMessage = ex.Message,
                            InputPath = filePath
                        });
                        ErrorMessage = ex.Message;
                    });
                    _logger?.Error(
                        $"第 {i + 1}/{filePaths.Count} 张改尺寸处理失败: {ex.Message}",
                        ex, "desktop-resize-image");
                }

                // 更新进度（UI 线程）
                var current = i + 1;
                System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                {
                    ProgressValue = current;
                    StatusMessage = $"正在处理 {current}/{filePaths.Count}：{Path.GetFileName(filePath)}";
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

            StatusMessage = $"处理完成：成功 {successCount}，失败 {failCount}";

            // 处理完成后清空待处理列表
            PendingFiles.Clear();

            _logger?.Info(
                $"改尺寸处理完成: {successCount} 成功, {failCount} 失败",
                "desktop-resize-image");
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "已取消";
            ProgressValue = 0;
            _logger?.Info("改尺寸处理已取消", "desktop-resize-image");
        }
        catch (Exception ex)
        {
            ErrorMessage = $"处理失败: {ex.Message}";
            StatusMessage = "处理出错，请查看错误信息";
            _logger?.Error($"改尺寸处理异常: {ex.Message}", ex, "desktop-resize-image");
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
    /// 从当前 UI 状态构建 ResizeImageParams。
    /// </summary>
    public ResizeImageParams BuildParamsFromUI()
    {
        return new ResizeImageParams
        {
            Mode = SelectedMode,
            Width = ShowWidthHeight ? Width : null,
            Height = ShowWidthHeight ? Height : null,
            ScalePercent = SelectedMode == "scale" ? ScalePercent : 100.0,
            ShortSide = SelectedMode == "short_side" ? ShortSide : null,
            LongSide = SelectedMode == "long_side" ? LongSide : null,
            TargetDpi = SelectedMode == "custom_dpi" ? TargetDpi : null,
            Resample = SelectedResample,
            KeepAspect = SelectedMode == "exact" ? KeepAspect : true,
            OutputFormat = SelectedOutputFormat,
            JpegQuality = JpegQuality,
            PngCompressLevel = PngCompressLevel,
            WebpQuality = WebpQuality,
            Dpi = (SelectedOutputFormat != "original")
                ? new List<double> { CustomDpiX, CustomDpiY }
                : null,
            Preset = string.IsNullOrEmpty(SelectedPreset) ? null : SelectedPreset,
        };
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
        PendingFiles.Clear();
        SelectedResult = null;
        ErrorMessage = null;
        ProgressValue = 0;
        ProgressMax = 100;
        StatusMessage = "请选择文件";
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
            else
            {
                StatusMessage = $"输出文件不存在: {path}";
            }
        }
        catch (Exception ex)
        {
            StatusMessage = $"打开文件失败: {ex.Message}";
        }
    }

    /// <summary>
    /// 更新条件可见性属性，当模式或格式切换时通知 UI 刷新。
    /// </summary>
    private void UpdateVisibility()
    {
        OnPropertyChanged(nameof(ShowWidthHeight));
        OnPropertyChanged(nameof(ShowScalePercent));
        OnPropertyChanged(nameof(ShowShortSide));
        OnPropertyChanged(nameof(ShowLongSide));
        OnPropertyChanged(nameof(ShowTargetDpi));
        OnPropertyChanged(nameof(ShowKeepAspect));
        OnPropertyChanged(nameof(ShowJpegQuality));
        OnPropertyChanged(nameof(ShowPngCompress));
        OnPropertyChanged(nameof(ShowWebpQuality));
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

/// <summary>
/// 下拉选择项（Value/Display 对），用于 ComboBox 的 ItemsSource。
/// 必须使用类而非命名元组，否则 WPF 反射无法识别 DisplayMemberPath/SelectedValuePath。
/// </summary>
public class SelectOption
{
    public string Value { get; }
    public string Display { get; }

    public SelectOption(string value, string display)
    {
        Value = value;
        Display = display;
    }
}
