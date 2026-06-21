using System.Collections.ObjectModel;
using System.Windows.Input;
using System.Windows.Media;
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
    private string _statusMessage = "就绪 - 选择图片开始证件照换底色";
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
            }
        }
    }

    /// <summary>是否有输入文件</summary>
    public bool HasInputFile => !string.IsNullOrEmpty(CurrentInputPath);

    /// <summary>当前输入文件名</summary>
    public string InputFileName =>
        string.IsNullOrEmpty(CurrentInputPath) ? "未选择文件" : Path.GetFileName(CurrentInputPath);

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
    }

    /// <summary>
    /// 默认构造函数（用于设计时）
    /// </summary>
    public IdPhotoViewModel() : this(null, new FileSystemService())
    {
        // 设计时无需额外初始化
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
                // 加载规格列表
                try
                {
                    var specs = await _idPhotoService.GetSpecsAsync(useCache: false);
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    {
                        AvailableSpecs.Clear();
                        foreach (var spec in specs)
                            AvailableSpecs.Add(spec);
                    });
                }
                catch (Exception ex)
                {
                    _logger?.Warning($"加载规格列表失败: {ex.Message}", "desktop-id-photo");
                }

                // 加载底色列表
                try
                {
                    var colors = await _idPhotoService.GetBackgroundColorsAsync(useCache: false);
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    {
                        AvailableBackgroundColors.Clear();
                        foreach (var color in colors)
                            AvailableBackgroundColors.Add(color);
                    });
                }
                catch (Exception ex)
                {
                    _logger?.Warning($"加载底色列表失败: {ex.Message}", "desktop-id-photo");
                }

                StatusMessage = "证件照引擎就绪 - 选择图片、规格和底色开始处理";
            }
            else
            {
                StatusMessage = $"证件照引擎启动失败: {_idPhotoService.AvailabilityError}";
            }
        }
        catch (Exception ex)
        {
            IsServiceAvailable = false;
            StatusMessage = $"证件照引擎启动失败: {ex.Message}";
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
            StatusMessage = $"已选择: {InputFileName}";
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
        _ = ProcessCurrentFileAsync();
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

        StatusMessage = $"正在处理... {InputFileName}";

        try
        {
            var result = await _idPhotoService.ProcessAsync(
                CurrentInputPath,
                outputPath: null, // 自动生成输出路径
                background: SelectedBackgroundColor.Key,
                specName: SelectedSpec.Name,
                dpi: Dpi,
                autoDetectBackground: AutoDetectBackground,
                edgeFeather: EdgeFeather,
                _currentCts.Token);

            // 更新进度
            System.Windows.Application.Current?.Dispatcher.Invoke(() =>
            {
                ProgressValue = 100;

                if (result.IsSuccess)
                {
                    Results.Insert(0, result);
                    SelectedResult = result;
                    StatusMessage = $"处理完成: {result.SpecSummary}, {result.BackgroundSummary}";
                }
                else
                {
                    Results.Insert(0, result);
                    SelectedResult = result;
                    ErrorMessage = result.ErrorMessage;
                    StatusMessage = "处理失败，请查看错误信息";
                }
            });

            _logger?.Info(
                $"证件照处理{(result.IsSuccess ? "成功" : "失败")}: {InputFileName}",
                "desktop-id-photo");
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "处理已取消";
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

        var dialog = new SaveFileDialog
        {
            Title = "导出证件照",
            FileName = Path.GetFileNameWithoutExtension(SelectedResult.InputPath) + "_证件照",
            DefaultExt = ".png",
            Filter = "PNG 图片|*.png|JPEG 图片|*.jpg|所有文件|*.*",
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
        StatusMessage = "结果已清除 - 选择图片开始证件照换底色";
        RefreshCommandStates();
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
