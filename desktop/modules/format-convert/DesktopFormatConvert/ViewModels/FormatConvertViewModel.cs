using System.Collections.ObjectModel;
using System.Globalization;
using System.Windows.Data;
using System.Windows.Input;
using Microsoft.Win32;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTShared.Logging;
using TTShared.UI;
using TTTools.FormatConvert.Models;
using TTTools.FormatConvert.Services;

namespace TTTools.FormatConvert.ViewModels;

/// <summary>
/// 图片格式转换/压缩/裁剪/旋转模块主 ViewModel
/// 管理文件选择、操作参数配置、处理触发、结果预览的完整流程。
/// 本地免费功能：无需套餐权限校验，不消耗云端 AI 额度。
/// </summary>
public class FormatConvertViewModel : BaseViewModel
{
    private readonly FormatConvertService? _convertService;
    private readonly FileSystemService _fileSystem;
    private readonly JobManager? _jobManager;
    private readonly AppLogger? _logger;

    private bool _isRunning;
    private string _statusMessage = "就绪 - 选择图片文件开始处理";
    private string? _errorMessage;
    private int _progressValue;
    private int _progressMax = 100;
    private bool _isServiceAvailable;
    private FormatConvertResult? _selectedResult;
    private CancellationTokenSource? _currentCts;

    // ---- 当前选中的操作类型 ----
    private string _selectedOperation = "compress";

    // ---- 格式转换参数 ----
    private string _selectedTargetFormat = "original";
    private int _convertQuality = 85;
    private int _pngCompress = 6;
    private int _webpQuality = 85;
    private bool _preserveAlpha = true;

    // ---- 压缩参数 ----
    private int _compressQuality = 75;
    private string _compressTargetFormat = "original";
    private int _compressPngLevel = 9;
    private long? _maxSizeBytes;
    private bool _useMaxSize;

    // ---- 裁剪参数 ----
    private bool _useAnchorMode; // false=坐标模式, true=锚点模式
    private int _cropLeft;
    private int _cropTop;
    private int _cropWidth = 400;
    private int _cropHeight = 300;
    private string _selectedAnchor = "center";

    // ---- 旋转参数 ----
    private double _rotateAngle = 90.0;
    private bool _expandCanvas = true;
    // 直角旋转快捷选择（null 表示自定义角度）
    private double? _selectedQuickAngle = 90.0;

    /// <summary>已处理的结果列表</summary>
    public ObservableCollection<FormatConvertResult> Results { get; } = new();

    /// <summary>当前选中的结果（显示在预览区）</summary>
    public FormatConvertResult? SelectedResult
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
          $"操作: {SelectedResult.OperationType}\n" +
          $"尺寸: {SelectedResult.SizeSummary}\n" +
          $"输出: {SelectedResult.OutputFormatSummary}\n" +
          $"压缩比: {SelectedResult.CompressionRatioDisplay}\n" +
          $"耗时: {SelectedResult.ElapsedDisplay}"
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

    /// <summary>格式转换服务是否可用</summary>
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
    public string ServiceStatusText => _isServiceAvailable ? "格式转换引擎就绪" : "格式转换引擎未连接";

    // ---- 操作类型属性 ----

    /// <summary>当前选择的操作类型</summary>
    public string SelectedOperation
    {
        get => _selectedOperation;
        set
        {
            if (SetProperty(ref _selectedOperation, value))
                UpdateOperationVisibility();
        }
    }

    // 条件可见性属性
    public bool ShowConvertParams => SelectedOperation == "convert_format";
    public bool ShowCompressParams => SelectedOperation == "compress";
    public bool ShowCropParams => SelectedOperation == "crop";
    public bool ShowRotateParams => SelectedOperation == "rotate";

    // ---- 格式转换参数属性 ----

    public string SelectedTargetFormat
    {
        get => _selectedTargetFormat;
        set
        {
            if (SetProperty(ref _selectedTargetFormat, value))
                UpdateQualityVisibility();
        }
    }

    public int ConvertQuality { get => _convertQuality; set => SetProperty(ref _convertQuality, Math.Clamp(value, 1, 100)); }
    public int PngCompress { get => _pngCompress; set => SetProperty(ref _pngCompress, Math.Clamp(value, 0, 9)); }
    public int WebpQuality { get => _webpQuality; set => SetProperty(ref _webpQuality, Math.Clamp(value, 1, 100)); }
    public bool PreserveAlpha { get => _preserveAlpha; set => SetProperty(ref _preserveAlpha, value); }

    // 条件可见性：格式转换质量设置
    public bool ShowConvertJpegQuality => _selectedTargetFormat is "jpeg" or "webp" or "original";
    public bool ShowConvertPngCompress => _selectedTargetFormat is "png";
    public bool ShowConvertWebpQuality => _selectedTargetFormat is "webp";

    // ---- 压缩参数属性 ----

    public int CompressQuality { get => _compressQuality; set => SetProperty(ref _compressQuality, Math.Clamp(value, 1, 100)); }
    public string CompressTargetFormat { get => _compressTargetFormat; set => SetProperty(ref _compressTargetFormat, value); }
    public int CompressPngLevel { get => _compressPngLevel; set => SetProperty(ref _compressPngLevel, Math.Clamp(value, 0, 9)); }
    public bool UseMaxSize
    {
        get => _useMaxSize;
        set
        {
            if (SetProperty(ref _useMaxSize, value))
                OnPropertyChanged(nameof(ShowMaxSize));
        }
    }
    public long? MaxSizeBytes
    {
        get => _maxSizeBytes;
        set => SetProperty(ref _maxSizeBytes, value);
    }
    /// <summary>最大文件大小 MB 显示值</summary>
    public double MaxSizeMB
    {
        get => _maxSizeBytes.HasValue ? _maxSizeBytes.Value / (1024.0 * 1024.0) : 0;
        set
        {
            if (value > 0)
                MaxSizeBytes = (long)(value * 1024 * 1024);
            else
                MaxSizeBytes = null;
        }
    }

    public bool ShowMaxSize => _useMaxSize;

    // ---- 裁剪参数属性 ----

    /// <summary>裁剪模式：false=坐标模式, true=锚点模式</summary>
    public bool UseAnchorMode
    {
        get => _useAnchorMode;
        set
        {
            if (SetProperty(ref _useAnchorMode, value))
            {
                OnPropertyChanged(nameof(ShowCoordinateCrop));
                OnPropertyChanged(nameof(ShowAnchorCrop));
            }
        }
    }
    public int CropLeft { get => _cropLeft; set => SetProperty(ref _cropLeft, Math.Max(0, value)); }
    public int CropTop { get => _cropTop; set => SetProperty(ref _cropTop, Math.Max(0, value)); }
    public int CropWidth { get => _cropWidth; set => SetProperty(ref _cropWidth, Math.Max(1, value)); }
    public int CropHeight { get => _cropHeight; set => SetProperty(ref _cropHeight, Math.Max(1, value)); }
    public string SelectedAnchor { get => _selectedAnchor; set => SetProperty(ref _selectedAnchor, value); }

    public bool ShowCoordinateCrop => !_useAnchorMode;
    public bool ShowAnchorCrop => _useAnchorMode;

    // ---- 旋转参数属性 ----

    public double RotateAngle { get => _rotateAngle; set => SetProperty(ref _rotateAngle, Math.Clamp(value, -360, 360)); }
    public bool ExpandCanvas { get => _expandCanvas; set => SetProperty(ref _expandCanvas, value); }

    /// <summary>直角旋转快捷选择（null 表示自定义角度）</summary>
    public double? SelectedQuickAngle
    {
        get => _selectedQuickAngle;
        set
        {
            if (SetProperty(ref _selectedQuickAngle, value))
            {
                if (value.HasValue)
                {
                    RotateAngle = value.Value;
                    OnPropertyChanged(nameof(IsCustomAngle));
                }
                OnPropertyChanged(nameof(IsQuickAngleSelected));
            }
        }
    }
    public bool IsCustomAngle => !_selectedQuickAngle.HasValue;
    public bool IsQuickAngleSelected => _selectedQuickAngle.HasValue;

    // ---- 进度和统计 ----

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

    // ---- 静态资源（供 XAML 绑定） ----

    /// <summary>可用的输出格式列表（中文名称）</summary>
    public static List<(string Value, string Display)> FormatList =>
        FormatConvertService.OutputFormatList;

    /// <summary>压缩专用输出格式列表（original / png / jpeg / webp）</summary>
    public static List<(string Value, string Display)> CompressFormatList { get; } = new()
    {
        ("original", "保持原格式"),
        ("jpeg", "JPEG - 有损，文件小"),
        ("png", "PNG - 无损压缩"),
        ("webp", "WEBP - Web 优化格式"),
    };

    /// <summary>可用的裁剪锚点列表</summary>
    public static List<(string Value, string Display)> AnchorList =>
        FormatConvertService.AnchorList;

    /// <summary>Bool 取反转换器（锚点模式/坐标模式切换）</summary>
    public static IValueConverter InvertBoolConverter { get; } = new InvertBoolConverter();

    // ---- 命令 ----

    public ICommand SelectFilesCommand { get; }
    public ICommand StartProcessingCommand { get; }
    public ICommand CancelCommand { get; }
    public ICommand ClearResultsCommand { get; }
    public ICommand OpenOutputFileCommand { get; }
    public ICommand SelectResultCommand { get; }
    public ICommand SelectOperationCommand { get; }
    public ICommand SelectQuickAngleCommand { get; }

    public FormatConvertViewModel(
        FormatConvertService? convertService,
        FileSystemService fileSystem,
        JobManager? jobManager = null,
        AppLogger? logger = null)
    {
        _convertService = convertService;
        _fileSystem = fileSystem ?? throw new ArgumentNullException(nameof(fileSystem));
        _jobManager = jobManager;
        _logger = logger;

        SelectFilesCommand = new RelayCommand(SelectFiles);
        StartProcessingCommand = new RelayCommand(StartProcessingAsync, () => CanStart);
        CancelCommand = new RelayCommand(CancelProcessing, () => CanCancel);
        ClearResultsCommand = new RelayCommand(ClearResults, () => Results.Count > 0);
        OpenOutputFileCommand = new RelayCommand(OpenOutputFile, () => HasSelectedResult);
        SelectResultCommand = new RelayCommand<FormatConvertResult?>(r => SelectedResult = r);
        SelectOperationCommand = new RelayCommand<string>(op => SelectedOperation = op ?? "compress");
        SelectQuickAngleCommand = new RelayCommand<string?>(angleStr =>
        {
            if (string.IsNullOrEmpty(angleStr))
                SelectedQuickAngle = null; // 自定义角度
            else if (double.TryParse(angleStr, out var angle))
                SelectedQuickAngle = angle;
        });

        // 监听结果列表变更以更新命令状态
        Results.CollectionChanged += (_, _) => RefreshCommandStates();
    }

    /// <summary>
    /// 默认构造函数（用于设计时）
    /// </summary>
    public FormatConvertViewModel() : this(null, new FileSystemService()) { }

    /// <summary>
    /// 初始化格式转换服务。
    /// 异步启动 worker 进程并进行健康检查。
    /// </summary>
    public async Task InitializeAsync()
    {
        if (_convertService == null)
        {
            StatusMessage = "格式转换服务未配置";
            IsServiceAvailable = false;
            return;
        }

        StatusMessage = "正在启动格式转换引擎...";
        try
        {
            IsServiceAvailable = await _convertService.StartAsync();
            if (IsServiceAvailable)
            {
                StatusMessage = "格式转换引擎就绪 - 选择图片文件开始处理";
            }
            else
            {
                StatusMessage = $"格式转换引擎启动失败: {_convertService.AvailabilityError}";
            }
        }
        catch (Exception ex)
        {
            IsServiceAvailable = false;
            StatusMessage = $"格式转换引擎启动失败: {ex.Message}";
            _logger?.Error($"格式转换服务初始化失败: {ex.Message}", ex, "desktop-format-convert");
        }
    }

    /// <summary>
    /// 打开文件选择对话框，选择要处理的图片文件。
    /// </summary>
    private void SelectFiles()
    {
        var dialog = new OpenFileDialog
        {
            Title = "选择要处理的图片",
            Filter = "图片文件|*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tif;*.webp;*.gif;*.ico|所有文件|*.*",
            Multiselect = true,
            CheckFileExists = true
        };

        if (dialog.ShowDialog() == true && dialog.FileNames.Length > 0)
        {
            _ = StartProcessingForFilesAsync(dialog.FileNames.ToList());
        }
    }

    /// <summary>
    /// 开始处理命令处理（视图命令绑定）。
    /// </summary>
    private void StartProcessingAsync()
    {
        SelectFiles();
    }

    /// <summary>
    /// 通过拖拽文件触发处理——在 View 层由拖拽事件调用。
    /// </summary>
    /// <param name="filePaths">拖入的文件路径列表</param>
    public void ProcessDroppedFiles(IEnumerable<string> filePaths)
    {
        if (filePaths == null) return;

        var imageFiles = filePaths
            .Where(f => _convertService?.IsFormatSupported(f) ?? FileSystemService.IsImageFile(f))
            .ToList();

        if (imageFiles.Count == 0)
        {
            StatusMessage = "没有有效的图片文件";
            return;
        }

        _ = StartProcessingForFilesAsync(imageFiles);
    }

    /// <summary>
    /// 对指定文件列表启动处理的核心逻辑。
    /// 根据当前选中的操作类型执行对应的处理。
    /// </summary>
    private async Task StartProcessingForFilesAsync(List<string> filePaths)
    {
        if (_convertService == null || filePaths.Count == 0) return;

        IsRunning = true;
        ErrorMessage = null;
        ProgressValue = 0;
        ProgressMax = filePaths.Count;

        _currentCts = new CancellationTokenSource();

        var opNames = new Dictionary<string, string>
        {
            ["convert_format"] = "格式转换",
            ["compress"] = "压缩",
            ["crop"] = "裁剪",
            ["rotate"] = "旋转",
        };
        var opDisplayName = opNames.GetValueOrDefault(_selectedOperation, _selectedOperation);

        StatusMessage = $"正在{opDisplayName} {filePaths.Count} 张图片...";

        try
        {
            for (var i = 0; i < filePaths.Count; i++)
            {
                _currentCts.Token.ThrowIfCancellationRequested();

                var filePath = filePaths[i];
                try
                {
                    FormatConvertResult result = _selectedOperation switch
                    {
                        "convert_format" => await _convertService.ConvertFormatAsync(
                            filePath, null, BuildConvertParams(), _currentCts.Token),
                        "compress" => await _convertService.CompressAsync(
                            filePath, null, BuildCompressParams(), _currentCts.Token),
                        "crop" => await _convertService.CropAsync(
                            filePath, null, BuildCropParams(), _currentCts.Token),
                        "rotate" => await _convertService.RotateAsync(
                            filePath, null, BuildRotateParams(), _currentCts.Token),
                        _ => new FormatConvertResult
                        {
                            IsSuccess = false,
                            InputPath = filePath,
                            OperationType = _selectedOperation,
                            ErrorMessage = $"不支持的操作类型: {_selectedOperation}"
                        },
                    };

                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                        Results.Insert(0, result));
                }
                catch (Exception ex)
                {
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                        Results.Insert(0, new FormatConvertResult
                        {
                            IsSuccess = false,
                            ErrorMessage = ex.Message,
                            InputPath = filePath,
                            OperationType = _selectedOperation,
                        }));
                    _logger?.Error(
                        $"第 {i + 1}/{filePaths.Count} 张{opDisplayName}处理失败: {ex.Message}",
                        ex, "desktop-format-convert");
                }

                var current = i + 1;
                System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                {
                    ProgressValue = current;
                    StatusMessage = $"正在{opDisplayName}... {current}/{filePaths.Count}";
                });
            }

            if (Results.Count > 0)
            {
                var firstSuccess = Results.FirstOrDefault(r => r.IsSuccess);
                SelectedResult = firstSuccess ?? Results[0];
            }

            var successCount = Results.Count(r => r.IsSuccess);
            var failCount = Results.Count - successCount;

            if (failCount > 0)
                StatusMessage = $"{opDisplayName}完成: {successCount} 成功, {failCount} 失败";
            else
                StatusMessage = $"{opDisplayName}完成: {successCount} 张图片全部成功";

            _logger?.Info(
                $"{opDisplayName}处理完成: {successCount} 成功, {failCount} 失败",
                "desktop-format-convert");
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "处理已取消";
            _logger?.Info("处理已取消", "desktop-format-convert");
        }
        catch (Exception ex)
        {
            ErrorMessage = $"处理失败: {ex.Message}";
            StatusMessage = "处理出错，请查看错误信息";
            _logger?.Error($"处理异常: {ex.Message}", ex, "desktop-format-convert");
        }
        finally
        {
            IsRunning = false;
            _currentCts?.Dispose();
            _currentCts = null;
            RefreshCommandStates();
        }
    }

    // ===== 从 UI 状态构建参数对象 =====

    private FormatConvertParams BuildConvertParams()
    {
        return new FormatConvertParams
        {
            TargetFormat = SelectedTargetFormat,
            Quality = ConvertQuality,
            PngCompress = PngCompress,
            WebpQuality = WebpQuality,
            PreserveAlpha = PreserveAlpha,
        };
    }

    private CompressParams BuildCompressParams()
    {
        return new CompressParams
        {
            Quality = CompressQuality,
            TargetFormat = CompressTargetFormat,
            PngCompress = CompressPngLevel,
            MaxSizeBytes = UseMaxSize ? MaxSizeBytes : null,
        };
    }

    private CropParams BuildCropParams()
    {
        return new CropParams
        {
            Left = UseAnchorMode ? 0 : CropLeft,
            Top = UseAnchorMode ? 0 : CropTop,
            Width = CropWidth,
            Height = CropHeight,
            Anchor = UseAnchorMode ? SelectedAnchor : null,
        };
    }

    private RotateParams BuildRotateParams()
    {
        return new RotateParams
        {
            Angle = RotateAngle,
            Expand = ExpandCanvas,
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
        SelectedResult = null;
        ErrorMessage = null;
        ProgressValue = 0;
        StatusMessage = "结果已清除 - 选择图片文件开始处理";
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
    /// 更新操作类型切换时的条件可见性属性。
    /// </summary>
    private void UpdateOperationVisibility()
    {
        OnPropertyChanged(nameof(ShowConvertParams));
        OnPropertyChanged(nameof(ShowCompressParams));
        OnPropertyChanged(nameof(ShowCropParams));
        OnPropertyChanged(nameof(ShowRotateParams));
    }

    /// <summary>
    /// 更新格式转换目标格式切换时的条件可见性属性。
    /// </summary>
    private void UpdateQualityVisibility()
    {
        OnPropertyChanged(nameof(ShowConvertJpegQuality));
        OnPropertyChanged(nameof(ShowConvertPngCompress));
        OnPropertyChanged(nameof(ShowConvertWebpQuality));
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
/// Boolean 取反转换器，用于 XAML 绑定。
/// 例如：UseAnchorMode=true 时隐藏坐标裁剪参数。
/// </summary>
public class InvertBoolConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is bool boolValue)
            return !boolValue;
        return value;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is bool boolValue)
            return !boolValue;
        return value;
    }
}
