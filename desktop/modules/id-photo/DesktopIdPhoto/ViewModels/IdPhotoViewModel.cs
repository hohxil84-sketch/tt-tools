using System.Collections.ObjectModel;
using System.Linq;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Microsoft.Win32;
using TTShared.UI;
using TTShared.Logging;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTTools.IdPhoto.Models;
using TTTools.IdPhoto.Services;

namespace TTTools.IdPhoto.ViewModels;

/// <summary>
/// 证件照换底色模块主 ViewModel
/// 管理图片文件选择、底色选择、规格选择、处理触发、结果展示、导出保存的完整流程。
/// 证件照换底色是本地免费功能，不需要云端权限检查。
/// </summary>
public class IdPhotoViewModel : BaseViewModel
{
    private readonly IdPhotoService? _idPhotoService;
    private readonly FileSystemService _fileSystem;
    private readonly JobManager? _jobManager;
    private readonly AppLogger? _logger;

    private bool _isRunning;
    private string _statusMessage = "请选择文件";
    private string? _errorMessage;
    private int _progressValue;
    private int _progressMax = 100;
    private bool _isServiceAvailable;
    private IdPhotoResult? _selectedResult;
    private string? _currentInputPath;

    // 可选参数
    private PhotoSpecItem? _selectedSpec;
    private BackgroundColorItem? _selectedBackgroundColor;
    private int _dpi = 300;
    private bool _autoDetectBackground = true;
    private bool _edgeFeather = true;

    private CancellationTokenSource? _currentCts;
    private BitmapImage? _inputImageThumbnail;

    /// <summary>已完成的处理结果列表</summary>
    public ObservableCollection<IdPhotoResult> Results { get; } = new();

    /// <summary>可选的证件照规格列表</summary>
    public ObservableCollection<PhotoSpecItem> AvailableSpecs { get; } = new();

    /// <summary>可选的背景色列表</summary>
    public ObservableCollection<BackgroundColorItem> AvailableBackgroundColors { get; } = new();

    /// <summary>当前选中的结果（显示在预览区）</summary>
    public IdPhotoResult? SelectedResult
    {
        get => _selectedResult;
        set
        {
            if (SetProperty(ref _selectedResult, value))
            {
                OnPropertyChanged(nameof(HasSelectedResult));
                OnPropertyChanged(nameof(SelectedInputFileName));
                OnPropertyChanged(nameof(SelectedSizeSummary));
                OnPropertyChanged(nameof(SelectedSpecSummary));
                OnPropertyChanged(nameof(SelectedBackgroundSummary));
                OnPropertyChanged(nameof(SelectedMaskMethod));
            }
        }
    }

    /// <summary>是否有选中结果</summary>
    public bool HasSelectedResult => SelectedResult != null;

    /// <summary>选中结果的输入文件名</summary>
    public string SelectedInputFileName => SelectedResult?.InputFileName ?? string.Empty;

    /// <summary>选中结果的尺寸</summary>
    public string SelectedSizeSummary => SelectedResult?.SizeSummary ?? string.Empty;

    /// <summary>选中结果的规格</summary>
    public string SelectedSpecSummary => SelectedResult?.SpecSummary ?? string.Empty;

    /// <summary>选中结果的底色</summary>
    public string SelectedBackgroundSummary => SelectedResult?.BackgroundSummary ?? string.Empty;

    /// <summary>选中结果的遮罩方法</summary>
    public string SelectedMaskMethod => SelectedResult?.MaskMethodSummary ?? string.Empty;

    /// <summary>当前选中输入图片的路径</summary>
    public string? CurrentInputPath
    {
        get => _currentInputPath;
        set
        {
            if (SetProperty(ref _currentInputPath, value))
            {
                OnPropertyChanged(nameof(HasInputFile));
                OnPropertyChanged(nameof(InputFileName));
                OnPropertyChanged(nameof(InputFileFormat));
            }
        }
    }

    /// <summary>是否有输入文件</summary>
    public bool HasInputFile => !string.IsNullOrEmpty(CurrentInputPath);

    /// <summary>当前输入文件名</summary>
    public string InputFileName =>
        string.IsNullOrEmpty(CurrentInputPath) ? "未选择文件" : Path.GetFileName(CurrentInputPath);

    /// <summary>输入图片缩略图（用于预览）</summary>
    public BitmapImage? InputImageThumbnail
    {
        get => _inputImageThumbnail;
        set => SetProperty(ref _inputImageThumbnail, value);
    }

    /// <summary>当前输入文件的格式（扩展名大写，不含点）</summary>
    public string InputFileFormat =>
        string.IsNullOrEmpty(CurrentInputPath)
            ? ""
            : Path.GetExtension(CurrentInputPath).TrimStart('.').ToUpper();

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
    public bool CanStart => !IsRunning && _isServiceAvailable && HasInputFile;

    /// <summary>是否可以取消</summary>
    public bool CanCancel => IsRunning;

    /// <summary>证件照服务是否可用</summary>
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
    public string ServiceStatusText => _isServiceAvailable ? "证件照引擎就绪" : "证件照引擎未连接";

    /// <summary>当前选中的规格</summary>
    public PhotoSpecItem? SelectedSpec
    {
        get => _selectedSpec;
        set
        {
            if (SetProperty(ref _selectedSpec, value))
            {
                OnPropertyChanged(nameof(HasSelectedSpec));
                OnPropertyChanged(nameof(SelectedSpecText));
            }
        }
    }

    /// <summary>是否选择了规格</summary>
    public bool HasSelectedSpec => SelectedSpec != null;

    /// <summary>选中规格文本</summary>
    public string SelectedSpecText => SelectedSpec?.DisplayText ?? "请选择规格";

    /// <summary>当前选中的底色</summary>
    public BackgroundColorItem? SelectedBackgroundColor
    {
        get => _selectedBackgroundColor;
        set
        {
            if (SetProperty(ref _selectedBackgroundColor, value))
            {
                OnPropertyChanged(nameof(HasSelectedBackground));
                OnPropertyChanged(nameof(SelectedBackgroundText));
                OnPropertyChanged(nameof(BackgroundColorPreview));
            }
        }
    }

    /// <summary>是否选择了底色</summary>
    public bool HasSelectedBackground => SelectedBackgroundColor != null;

    /// <summary>选中底色文本</summary>
    public string SelectedBackgroundText => SelectedBackgroundColor?.DisplayText ?? "请选择底色";

    /// <summary>背景色预览画刷（用于 UI 色块）</summary>
    public Brush? BackgroundColorPreview => SelectedBackgroundColor?.ToBrush();

    /// <summary>输出格式选项</summary>
    public class FormatOption
    {
        public string Value { get; set; } = "";
        public string Display { get; set; } = "";
    }

    /// <summary>输出格式选择列表</summary>
    public static List<FormatOption> AvailableFormats { get; } = new()
    {
        new FormatOption { Value = "png", Display = "PNG - 无损" },
        new FormatOption { Value = "jpeg", Display = "JPEG - 体积小" },
        new FormatOption { Value = "bmp", Display = "BMP - 无压缩" },
    };

    private string _outputFormat = "png";

    /// <summary>当前选中的输出格式</summary>
    public string OutputFormat
    {
        get => _outputFormat;
        set => SetProperty(ref _outputFormat, value);
    }

    /// <summary>目标 DPI (72~600)</summary>
    public int Dpi
    {
        get => _dpi;
        set => SetProperty(ref _dpi, Math.Clamp(value, 72, 600));
    }

    /// <summary>是否自动检测背景色</summary>
    public bool AutoDetectBackground
    {
        get => _autoDetectBackground;
        set => SetProperty(ref _autoDetectBackground, value);
    }

    private bool _renameOnExport;

    /// <summary>导出时是否自动重命名（年月日_尺寸_底色.扩展名）</summary>
    public bool RenameOnExport
    {
        get => _renameOnExport;
        set => SetProperty(ref _renameOnExport, value);
    }

    /// <summary>是否边缘羽化</summary>
    public bool EdgeFeather
    {
        get => _edgeFeather;
        set => SetProperty(ref _edgeFeather, value);
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

    /// <summary>已处理结果数量</summary>
    public int ResultCount => Results.Count;

    /// <summary>成功处理数量</summary>
    public int SuccessCount => Results.Count(r => r.IsSuccess);

    /// <summary>失败处理数量</summary>
    public int FailedCount => Results.Count(r => !r.IsSuccess);

    // ---- 命令 ----

    /// <summary>选择输入文件命令</summary>
    public ICommand SelectFileCommand { get; }

    /// <summary>开始处理命令</summary>
    public ICommand StartProcessCommand { get; }

    /// <summary>取消当前处理命令</summary>
    public ICommand CancelCommand { get; }

    /// <summary>保存导出结果命令</summary>
    public ICommand ExportResultCommand { get; }

    /// <summary>清除所有结果命令</summary>
    public ICommand ClearResultsCommand { get; }

    /// <summary>选择结果项命令</summary>
    public ICommand SelectResultCommand { get; }

    /// <summary>选择底色命令</summary>
    public ICommand SelectBackgroundColorCommand { get; }

    public IdPhotoViewModel(IdPhotoService? idPhotoService, FileSystemService fileSystem,
        JobManager? jobManager = null, AppLogger? logger = null)
    {
        _idPhotoService = idPhotoService;
        _fileSystem = fileSystem ?? throw new ArgumentNullException(nameof(fileSystem));
        _jobManager = jobManager;
        _logger = logger;

        SelectFileCommand = new RelayCommand(SelectFile);
        StartProcessCommand = new RelayCommand(StartProcessAsync, () => CanStart);
        CancelCommand = new RelayCommand(CancelProcess, () => CanCancel);
        ExportResultCommand = new RelayCommand(ExportResult, () => HasSelectedResult);
        ClearResultsCommand = new RelayCommand(ClearResults, () => Results.Count > 0);
        SelectResultCommand = new RelayCommand<IdPhotoResult?>(r => SelectedResult = r);
        SelectBackgroundColorCommand = new RelayCommand<BackgroundColorItem?>(c =>
        {
            if (c != null) SelectedBackgroundColor = c;
        });

        // 监听结果列表变更以更新命令状态
        Results.CollectionChanged += (_, _) => RefreshCommandStates();

        // 初始化硬编码默认规格和底色，确保 UI 不为空
        // （后续 InitializeAsync 成功后会从 worker 加载动态数据覆盖）
        InitializeDefaultSpecs();
        InitializeDefaultColors();

        // 默认选择第一个规格（1寸）和第一个底色（白色）
        SelectedSpec = AvailableSpecs.FirstOrDefault();
        SelectedBackgroundColor = AvailableBackgroundColors.FirstOrDefault();
    }

    /// <summary>
    /// 默认构造函数（用于设计时和 MainWindow 导航）
    /// </summary>
    public IdPhotoViewModel() : this(new IdPhotoService(), new FileSystemService())
    {
    }

    /// <summary>
    /// 初始化硬编码默认证件照规格列表
    /// 确保即使 Python worker 未启动，UI 也始终有可选项
    /// </summary>
    private void InitializeDefaultSpecs()
    {
        AvailableSpecs.Clear();
        // 名称必须与 local-worker/modules/id-photo/specifications.py 的 _SPEC_DEFINITIONS 一致
        AvailableSpecs.Add(new PhotoSpecItem { Name = "1寸", WidthMm = 25, HeightMm = 35, WidthPx = 295, HeightPx = 413, Dpi = 300 });
        AvailableSpecs.Add(new PhotoSpecItem { Name = "小1寸", WidthMm = 22, HeightMm = 32, WidthPx = 260, HeightPx = 378, Dpi = 300 });
        AvailableSpecs.Add(new PhotoSpecItem { Name = "大一寸", WidthMm = 33, HeightMm = 48, WidthPx = 390, HeightPx = 567, Dpi = 300 });
        AvailableSpecs.Add(new PhotoSpecItem { Name = "2寸", WidthMm = 35, HeightMm = 49, WidthPx = 413, HeightPx = 579, Dpi = 300 });
        AvailableSpecs.Add(new PhotoSpecItem { Name = "小2寸", WidthMm = 33, HeightMm = 48, WidthPx = 390, HeightPx = 567, Dpi = 300 });
        AvailableSpecs.Add(new PhotoSpecItem { Name = "大二寸", WidthMm = 35, HeightMm = 53, WidthPx = 413, HeightPx = 626, Dpi = 300 });
        AvailableSpecs.Add(new PhotoSpecItem { Name = "5寸", WidthMm = 89, HeightMm = 127, WidthPx = 1050, HeightPx = 1500, Dpi = 300 });
        AvailableSpecs.Add(new PhotoSpecItem { Name = "6寸", WidthMm = 102, HeightMm = 152, WidthPx = 1200, HeightPx = 1800, Dpi = 300 });
    }

    /// <summary>
    /// 初始化硬编码默认背景色列表
    /// 确保即使 Python worker 未启动，UI 也始终有可选项
    /// 色值必须与 local-worker/modules/id-photo/specifications.py 中的 BACKGROUND_COLORS 保持一致
    /// </summary>
    private void InitializeDefaultColors()
    {
        AvailableBackgroundColors.Clear();
        AvailableBackgroundColors.Add(new BackgroundColorItem { Name = "白色", Key = "white", R = 255, G = 255, B = 255, Hex = "#FFFFFF" });
        AvailableBackgroundColors.Add(new BackgroundColorItem { Name = "红色", Key = "red", R = 219, G = 0, B = 0, Hex = "#DB0000" });
        AvailableBackgroundColors.Add(new BackgroundColorItem { Name = "蓝色", Key = "blue", R = 67, G = 142, B = 219, Hex = "#438EDB" });
        AvailableBackgroundColors.Add(new BackgroundColorItem { Name = "浅蓝", Key = "light_blue", R = 100, G = 170, B = 235, Hex = "#64AAEB" });
        AvailableBackgroundColors.Add(new BackgroundColorItem { Name = "深红", Key = "dark_red", R = 180, G = 0, B = 0, Hex = "#B40000" });
        AvailableBackgroundColors.Add(new BackgroundColorItem { Name = "灰色", Key = "gray", R = 200, G = 200, B = 200, Hex = "#C8C8C8" });
        AvailableBackgroundColors.Add(new BackgroundColorItem { Name = "天蓝", Key = "sky_blue", R = 135, G = 206, B = 235, Hex = "#87CEEB" });
        AvailableBackgroundColors.Add(new BackgroundColorItem { Name = "米色", Key = "beige", R = 245, G = 245, B = 220, Hex = "#F5F5DC" });
        AvailableBackgroundColors.Add(new BackgroundColorItem { Name = "深蓝", Key = "dark_blue", R = 0, G = 51, B = 153, Hex = "#003399" });
        AvailableBackgroundColors.Add(new BackgroundColorItem { Name = "浅红", Key = "light_red", R = 255, G = 100, B = 100, Hex = "#FF6464" });
    }

    /// <summary>
    /// 初始化证件照服务
    /// 异步启动 worker 进程、健康检查、加载规格和底色列表。
    /// </summary>
    public async Task InitializeAsync()
    {
        if (_idPhotoService == null)
        {
            StatusMessage = "证件照服务未配置";
            IsServiceAvailable = false;
            return;
        }

        StatusMessage = "正在启动证件照引擎...";
        try
        {
            IsServiceAvailable = await _idPhotoService.StartAsync();
            if (IsServiceAvailable)
            {
                // StartAsync 内部已通过 LoadSpecsAndColorsAsync 缓存了数据
                // 直接使用缓存（useCache: true），避免重复调用 worker 导致返回空列表覆盖默认值
                try
                {
                    var specs = await _idPhotoService.GetSpecsAsync(useCache: true);
                    // 只有 worker 返回非空数据时才替换硬编码默认值，
                    // 防止 worker 异常返回空列表导致下拉框变空白
                    if (specs.Count > 0)
                    {
                        System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                        {
                            AvailableSpecs.Clear();
                            foreach (var spec in specs)
                                AvailableSpecs.Add(spec);
                        });
                    }
                }
                catch (Exception ex)
                {
                    _logger?.Warning($"加载规格列表失败: {ex.Message}", "desktop-id-photo");
                }

                // 加载底色列表（同样使用缓存 + 非空保护）
                try
                {
                    var colors = await _idPhotoService.GetBackgroundColorsAsync(useCache: true);
                    if (colors.Count > 0)
                    {
                        System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                        {
                            AvailableBackgroundColors.Clear();
                            foreach (var color in colors)
                                AvailableBackgroundColors.Add(color);
                        });
                    }
                }
                catch (Exception ex)
                {
                    _logger?.Warning($"加载底色列表失败: {ex.Message}", "desktop-id-photo");
                }

                StatusMessage = "请选择文件";
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
            _logger?.Error($"证件照服务初始化失败: {ex.Message}", ex, "desktop-id-photo");
        }

        RefreshCommandStates();
    }

    /// <summary>
    /// 打开文件选择对话框，选择要处理的证件照图片
    /// </summary>
    private void SelectFile()
    {
        var dialog = new OpenFileDialog
        {
            Title = "选择证件照图片",
            Filter = "图片文件|*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tif;*.webp|所有文件|*.*",
            Multiselect = false,
            CheckFileExists = true
        };

        if (dialog.ShowDialog() == true && !string.IsNullOrEmpty(dialog.FileName))
        {
            CurrentInputPath = dialog.FileName;
            LoadThumbnail(dialog.FileName);
            StatusMessage = $"已选择：{InputFileName}，点击开始处理";
            ErrorMessage = null;

            RefreshCommandStates();
        }
    }

    /// <summary>
    /// 开始处理命令（视图命令绑定）
    /// </summary>
    private void StartProcessAsync()
    {
        _ = ProcessCurrentFileAsync();
    }

    /// <summary>
    /// 处理通过拖拽放入的文件 - 在 View 层由拖拽事件调用
    /// </summary>
    /// <param name="filePaths">拖入的文件路径列表（取第一张图片）</param>
    public void ProcessDroppedFile(IEnumerable<string> filePaths)
    {
        if (filePaths == null) return;

        var imageFile = filePaths
            .Where(f => _idPhotoService?.IsFormatSupported(f) ?? FileSystemService.IsImageFile(f))
            .FirstOrDefault();

        if (imageFile == null)
        {
            StatusMessage = "没有有效的图片文件";
            return;
        }

        CurrentInputPath = imageFile;
        LoadThumbnail(imageFile);
        StatusMessage = $"已选择：{Path.GetFileName(imageFile)}，点击开始处理";
        ErrorMessage = null;
        RefreshCommandStates();
    }

    /// <summary>
    /// 对当前选中的输入文件执行证件照换底色处理的核心逻辑
    /// </summary>
    private async Task ProcessCurrentFileAsync()
    {
        if (_idPhotoService == null || string.IsNullOrEmpty(CurrentInputPath)) return;

        // 确认规格和底色已选择
        if (SelectedSpec == null)
        {
            ErrorMessage = "请先选择证件照规格";
            return;
        }
        if (SelectedBackgroundColor == null)
        {
            ErrorMessage = "请先选择目标底色";
            return;
        }

        IsRunning = true;
        ErrorMessage = null;
        ProgressValue = 0;

        _currentCts = new CancellationTokenSource();

        StatusMessage = $"正在处理 1/1：{InputFileName}";

        try
        {
            var result = await _idPhotoService.ProcessAsync(
                CurrentInputPath,
                outputPath: null, // 自动生成临时路径
                background: SelectedBackgroundColor.Key,
                specName: SelectedSpec.Name,
                dpi: Dpi,
                autoDetectBackground: AutoDetectBackground,
                edgeFeather: EdgeFeather,
                outputFormat: OutputFormat,
                ct: _currentCts.Token);

            // 更新进度
            System.Windows.Application.Current?.Dispatcher.Invoke(() =>
            {
                ProgressValue = 100;

                if (result.IsSuccess)
                {
                    Results.Insert(0, result);
                    SelectedResult = result;
                    StatusMessage = "处理完成：成功 1，失败 0";
                }
                else
                {
                    Results.Insert(0, result);
                    SelectedResult = result;
                    ErrorMessage = result.ErrorMessage;
                    StatusMessage = "处理完成：成功 0，失败 1";
                }
            });

            _logger?.Info(
                $"证件照处理{(result.IsSuccess ? "成功" : "失败")}: {InputFileName}",
                "desktop-id-photo");
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "已取消";
            ProgressValue = 0;
            _logger?.Info("证件照处理已取消", "desktop-id-photo");
        }
        catch (Exception ex)
        {
            ErrorMessage = $"处理失败: {ex.Message}";
            StatusMessage = "处理出错，请查看错误信息";

            var failedResult = new IdPhotoResult
            {
                IsSuccess = false,
                ErrorMessage = ex.Message,
                InputPath = CurrentInputPath
            };
            System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                Results.Insert(0, failedResult));

            _logger?.Error($"证件照处理异常: {ex.Message}", ex, "desktop-id-photo");
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
    /// 取消当前处理任务
    /// </summary>
    private void CancelProcess()
    {
        _currentCts?.Cancel();
        StatusMessage = "正在取消...";
    }

    /// <summary>
    /// 导出保存选中的处理结果到文件
    /// </summary>
    private void ExportResult()
    {
        if (SelectedResult == null || !SelectedResult.IsSuccess) return;

        var ext = OutputFormat == "jpeg" ? ".jpg" : $".{OutputFormat}";
        var formatFilter = OutputFormat switch
        {
            "png" => "PNG 图片|*.png",
            "jpeg" => "JPEG 图片|*.jpg|JPEG 图片|*.jpeg",
            "bmp" => "BMP 图片|*.bmp",
            _ => "所有文件|*.*"
        };

        // 重命名勾选时自动生成文件名：年月日_尺寸_底色.扩展名
        var defaultName = RenameOnExport
            ? $"{DateTime.Now:yyyy-MM-dd}_{SelectedSpec?.Name ?? ""}_{SelectedBackgroundColor?.Name ?? ""}{ext}"
            : Path.GetFileNameWithoutExtension(SelectedResult.InputPath) + "_证件照";

        var dialog = new SaveFileDialog
        {
            Title = "导出证件照",
            FileName = defaultName,
            DefaultExt = ext,
            Filter = $"{formatFilter}|所有文件|*.*",
            OverwritePrompt = true
        };

        if (dialog.ShowDialog() == true)
        {
            try
            {
                File.Copy(SelectedResult.OutputPath, dialog.FileName, overwrite: true);
                StatusMessage = $"已导出到: {Path.GetFileName(dialog.FileName)}";
            }
            catch (Exception ex)
            {
                ErrorMessage = $"导出失败: {ex.Message}";
                StatusMessage = "导出失败，请查看错误信息";
            }
        }
    }

    /// <summary>
    /// 清除所有处理结果
    /// </summary>
    private void ClearResults()
    {
        Results.Clear();
        SelectedResult = null;
        ErrorMessage = null;
        ProgressValue = 0;
        ProgressMax = 100;
        CurrentInputPath = null;
        InputImageThumbnail = null;
        StatusMessage = "请选择文件";
        RefreshCommandStates();
    }

    /// <summary>
    /// 从文件路径加载缩略图（解码宽度 200px），用于输入预览
    /// </summary>
    /// <param name="filePath">图片文件路径</param>
    private void LoadThumbnail(string filePath)
    {
        try
        {
            var bitmap = new BitmapImage();
            bitmap.BeginInit();
            bitmap.UriSource = new Uri(filePath);
            bitmap.DecodePixelWidth = 200; // 缩略图宽度，保持宽高比
            bitmap.CacheOption = BitmapCacheOption.OnLoad;
            bitmap.EndInit();
            bitmap.Freeze(); // 冻结后可跨线程访问
            InputImageThumbnail = bitmap;
        }
        catch
        {
            InputImageThumbnail = null;
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
        OnPropertyChanged(nameof(HasInputFile));
        OnPropertyChanged(nameof(CanStart));

        (StartProcessCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (CancelCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (ExportResultCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (ClearResultsCommand as RelayCommand)?.RaiseCanExecuteChanged();
    }
}
