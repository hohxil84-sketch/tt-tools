using System.Collections.ObjectModel;
using System.Windows.Input;
using System.Windows.Media;
using Microsoft.Win32;
using TTShared.UI;
using TTShared.Logging;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTTools.RemoveBg.Models;
using TTTools.RemoveBg.Services;

namespace TTTools.RemoveBg.ViewModels;

/// <summary>
/// 智能抠图模块主 ViewModel
/// 管理图片文件选择、抠图处理触发、结果预览、参数配置的完整流程。
/// 智能抠图是本地免费功能，不需要云端权限检查。
/// </summary>
public class RemoveBgViewModel : BaseViewModel
{
    private readonly RemoveBgService? _removeBgService;
    private readonly FileSystemService _fileSystem;
    private readonly JobManager? _jobManager;
    private readonly AppLogger? _logger;

    private bool _isRunning;
    private string _statusMessage = "请选择文件";
    private string? _errorMessage;
    private int _progressValue;
    private int _progressMax = 100;
    private bool _isServiceAvailable;
    private RemoveBgResult? _selectedResult;
    private CancellationTokenSource? _currentCts;

    // ---- 抠图参数 ----

    private string _selectedModelName = "u2net";
    private bool _alphaMatting;
    private bool _outputRgba = true;
    private bool _synthesizeBackground;
    private int _bgRed = 255;
    private int _bgGreen = 255;
    private int _bgBlue = 255;
    private string _outputDirectory = string.Empty;

    /// <summary>已处理的抠图结果列表</summary>
    public ObservableCollection<RemoveBgResult> Results { get; } = new();

    /// <summary>待处理图片文件列表（含缩略图等展示信息）</summary>
    public ObservableCollection<PendingFileInfo> PendingFiles { get; } = new();

    /// <summary>是否有待处理的图片</summary>
    public bool HasPendingFiles => PendingFiles.Count > 0;

    /// <summary>当前选中的结果（显示在预览区）</summary>
    public RemoveBgResult? SelectedResult
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
    public string SelectedPreviewText
    {
        get
        {
            if (SelectedResult == null) return string.Empty;
            if (!SelectedResult.IsSuccess)
                return $"✕ 抠图失败\n\n错误信息: {SelectedResult.ErrorMessage ?? "未知错误"}\n\n源文件: {SelectedResult.InputFileName}";
            return $"模型: {SelectedResult.ModelSummary}\n尺寸: {SelectedResult.SizeSummary}\n格式: {SelectedResult.OutputFormatSummary}\n前景占比: {SelectedResult.ForegroundRatioSummary}";
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

    /// <summary>是否可以开始处理：未运行 + 有待处理文件（服务按需初始化，不阻塞按钮）</summary>
    public bool CanStart => !IsRunning && PendingFiles.Count > 0;

    /// <summary>是否可以取消</summary>
    public bool CanCancel => IsRunning;

    /// <summary>抠图服务是否可用</summary>
    public bool IsServiceAvailable
    {
        get => _isServiceAvailable;
        set
        {
            if (SetProperty(ref _isServiceAvailable, value))
            {
                OnPropertyChanged(nameof(CanStart));
                OnPropertyChanged(nameof(ServiceStatusText));
                // 手动刷新命令可执行状态，确保按钮 IsEnabled 立即响应
                RefreshCommandStates();
            }
        }
    }

    /// <summary>服务状态文本</summary>
    public string ServiceStatusText => _isServiceAvailable ? "抠图引擎就绪" : "抠图引擎未连接";

    // ---- 抠图参数属性 ----

    /// <summary>当前选择的模型名称</summary>
    public string SelectedModelName
    {
        get => _selectedModelName;
        set => SetProperty(ref _selectedModelName, value);
    }

    /// <summary>是否启用 Alpha Matting 精细化边缘</summary>
    public bool AlphaMatting
    {
        get => _alphaMatting;
        set => SetProperty(ref _alphaMatting, value);
    }

    /// <summary>是否输出 RGBA 透明 PNG</summary>
    public bool OutputRgba
    {
        get => _outputRgba;
        set
        {
            if (SetProperty(ref _outputRgba, value))
            {
                OnPropertyChanged(nameof(ShowBackgroundColorPicker));
            }
        }
    }

    /// <summary>是否合成纯色背景</summary>
    public bool SynthesizeBackground
    {
        get => _synthesizeBackground;
        set
        {
            if (SetProperty(ref _synthesizeBackground, value))
            {
                OnPropertyChanged(nameof(ShowBackgroundColorPicker));
            }
        }
    }

    /// <summary>背景色 R 分量 (0-255)</summary>
    public int BgRed
    {
        get => _bgRed;
        set => SetProperty(ref _bgRed, Math.Clamp(value, 0, 255));
    }

    /// <summary>背景色 G 分量 (0-255)</summary>
    public int BgGreen
    {
        get => _bgGreen;
        set => SetProperty(ref _bgGreen, Math.Clamp(value, 0, 255));
    }

    /// <summary>背景色 B 分量 (0-255)</summary>
    public int BgBlue
    {
        get => _bgBlue;
        set => SetProperty(ref _bgBlue, Math.Clamp(value, 0, 255));
    }

    /// <summary>输出目录（用户选择图片处理后的保存位置）</summary>
    public string OutputDirectory
    {
        get => _outputDirectory;
        set
        {
            if (SetProperty(ref _outputDirectory, value))
                OnPropertyChanged(nameof(OutputDirectoryDisplay));
        }
    }

    /// <summary>输出目录显示文本</summary>
    public string OutputDirectoryDisplay =>
        string.IsNullOrEmpty(_outputDirectory) ? "默认（源文件目录）" : _outputDirectory;

    /// <summary>背景色预览（WPF 颜色）</summary>
    public Color BackgroundColorPreview
    {
        get => Color.FromRgb((byte)BgRed, (byte)BgGreen, (byte)BgBlue);
        set
        {
            BgRed = value.R;
            BgGreen = value.G;
            BgBlue = value.B;
        }
    }

    /// <summary>是否显示背景色选择器（仅在合成背景时显示）</summary>
    public bool ShowBackgroundColorPicker => SynthesizeBackground;

    /// <summary>可用的模型列表</summary>
    public ObservableCollection<RemoveBgModelInfo> AvailableModels { get; } = new();

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

    /// <summary>选择文件命令</summary>
    public ICommand SelectFilesCommand { get; }

    /// <summary>开始抠图处理命令</summary>
    public ICommand StartProcessingCommand { get; }

    /// <summary>取消当前处理命令</summary>
    public ICommand CancelCommand { get; }

    /// <summary>清除所有结果和待处理文件命令</summary>
    public ICommand ClearResultsCommand { get; }

    /// <summary>清除所有待处理文件命令</summary>
    public ICommand ClearPendingCommand { get; }

    /// <summary>打开输出文件命令</summary>
    public ICommand OpenOutputFileCommand { get; }

    /// <summary>选择结果项命令</summary>
    public ICommand SelectResultCommand { get; }

    /// <summary>移除单个待处理文件命令</summary>
    public ICommand RemovePendingFileCommand { get; }

    /// <summary>设置白色背景命令</summary>
    public ICommand SetWhiteBackgroundCommand { get; }

    /// <summary>设置红色背景命令</summary>
    public ICommand SetRedBackgroundCommand { get; }

    /// <summary>设置蓝色背景命令</summary>
    public ICommand SetBlueBackgroundCommand { get; }

    /// <summary>选择输出目录命令</summary>
    public ICommand SelectOutputDirectoryCommand { get; }

    public RemoveBgViewModel(RemoveBgService? removeBgService, FileSystemService fileSystem,
        JobManager? jobManager = null, AppLogger? logger = null)
    {
        _removeBgService = removeBgService;
        _fileSystem = fileSystem ?? throw new ArgumentNullException(nameof(fileSystem));
        _jobManager = jobManager;
        _logger = logger;

        SelectFilesCommand = new RelayCommand(SelectFiles);
        StartProcessingCommand = new RelayCommand(StartProcessingAsync, () => CanStart);
        CancelCommand = new RelayCommand(CancelProcessing, () => CanCancel);
        ClearResultsCommand = new RelayCommand(ClearResults, () => Results.Count > 0 || PendingFiles.Count > 0);
        ClearPendingCommand = new RelayCommand(ClearPending, () => PendingFiles.Count > 0);
        OpenOutputFileCommand = new RelayCommand(OpenOutputFile, () => HasSelectedResult);
        SelectResultCommand = new RelayCommand<RemoveBgResult?>(r => SelectedResult = r);
        RemovePendingFileCommand = new RelayCommand<PendingFileInfo?>(RemovePendingFile);
        SetWhiteBackgroundCommand = new RelayCommand(() => SetBackgroundColor(255, 255, 255));
        SetRedBackgroundCommand = new RelayCommand(() => SetBackgroundColor(255, 0, 0));
        SetBlueBackgroundCommand = new RelayCommand(() => SetBackgroundColor(0, 0, 255));
        SelectOutputDirectoryCommand = new RelayCommand(SelectOutputDirectory);

        // 构造时填充默认模型列表（硬编码兜底，不依赖 worker）
        PopulateDefaultModels();

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
    /// 默认构造函数（用于设计时）
    /// </summary>
    public RemoveBgViewModel() : this(null, new FileSystemService()) { }

    /// <summary>
    /// 初始化抠图服务
    /// 异步启动 worker 进程并进行健康检查，尝试从 worker 加载模型列表覆盖默认值。
    /// 无论 worker 是否启动成功，默认模型列表都已就绪。
    /// </summary>
    public async Task InitializeAsync()
    {
        if (_removeBgService == null)
        {
            StatusMessage = "抠图服务未配置";
            IsServiceAvailable = false;
            return;
        }

        StatusMessage = "正在启动抠图引擎...";
        try
        {
            IsServiceAvailable = await _removeBgService.StartAsync();
            if (IsServiceAvailable)
            {
                StatusMessage = "请选择文件";

                // 尝试从 worker 加载模型列表，覆盖默认值
                try
                {
                    var models = await _removeBgService.GetModelsAsync(useCache: false);
                    if (models.Count > 0)
                    {
                        AvailableModels.Clear();
                        foreach (var model in models)
                            AvailableModels.Add(model);
                    }
                }
                catch
                {
                    // 加载失败不覆盖默认列表，已在构造时填充
                }
            }
            else
            {
                StatusMessage = "处理服务不可用，请检查本地环境（模型列表仍可用）";
            }
        }
        catch (Exception ex)
        {
            IsServiceAvailable = false;
            StatusMessage = "处理服务不可用，请检查本地环境（模型列表仍可用）";
            _logger?.Error($"抠图服务初始化失败: {ex.Message}", ex, "desktop-remove-bg");
        }

        // 确保初始化完成后命令状态刷新
        RefreshCommandStates();
    }

    /// <summary>
    /// 填充默认模型列表（硬编码兜底，不依赖 Python worker）。
    /// 如果 worker 可用，后续 InitializeAsync 会用远程列表覆盖。
    /// </summary>
    private void PopulateDefaultModels()
    {
        var defaults = new List<RemoveBgModelInfo>
        {
            new() { Name = "u2net", Description = "默认模型，质量最佳，约 168 MB", IsDefault = true },
            new() { Name = "u2netp", Description = "轻量模型，速度快，约 4.4 MB", IsDefault = false },
            new() { Name = "u2net_human_seg", Description = "人像专用分割模型", IsDefault = false },
            new() { Name = "isnet-general-use", Description = "ISNet 通用模型，较新架构", IsDefault = false },
            new() { Name = "silueta", Description = "轻量级模型，适合简单场景", IsDefault = false },
        };
        AvailableModels.Clear();
        foreach (var m in defaults)
            AvailableModels.Add(m);
    }

    /// <summary>
    /// 打开文件选择对话框，将选中的图片加入待处理列表。
    /// 不会自动开始处理。
    /// </summary>
    private void SelectFiles()
    {
        var dialog = new OpenFileDialog
        {
            Title = "选择要抠图的图片",
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
            .Where(f => _removeBgService?.IsFormatSupported(f) ?? FileSystemService.IsImageFile(f))
            .ToList();

        if (imageFiles.Count == 0)
        {
            StatusMessage = "没有有效的图片文件";
            return;
        }

        AddFilesToPending(imageFiles);
    }

    /// <summary>
    /// 打开文件夹选择对话框，让用户选择抠图结果的输出目录。
    /// 使用 Win32 SHBrowseForFolder API，避免依赖 WinForms。
    /// </summary>
    private void SelectOutputDirectory()
    {
        var result = Win32FolderBrowser.Browse("选择抠图结果的输出目录", _outputDirectory);
        if (!string.IsNullOrEmpty(result))
            OutputDirectory = result;
    }

    /// <summary>
    /// 开始处理命令 —— 对待处理列表中的所有图片执行抠图处理。
    /// 如果服务尚未初始化，先按需启动服务。
    /// </summary>
    private async void StartProcessingAsync()
    {
        if (PendingFiles.Count == 0) return;

        // 按需初始化服务：如果服务尚未可用，先尝试启动
        if (!_isServiceAvailable && _removeBgService != null)
        {
            StatusMessage = "正在启动抠图引擎...";
            try
            {
                IsServiceAvailable = await _removeBgService.StartAsync();
                if (IsServiceAvailable)
                {
                    // 尝试从 worker 加载模型列表
                    try
                    {
                        var models = await _removeBgService.GetModelsAsync(useCache: false);
                        if (models.Count > 0)
                        {
                            AvailableModels.Clear();
                            foreach (var m in models)
                                AvailableModels.Add(m);
                        }
                    }
                    catch { }
                }
            }
            catch (Exception ex)
            {
                _logger?.Error($"抠图服务启动失败: {ex.Message}", ex, "desktop-remove-bg");
            }

            if (!_isServiceAvailable)
            {
                ErrorMessage = "抠图引擎启动失败，请检查 Python 环境和 rembg 是否正确安装。\n"
                    + "默认路径: D:\\localPath\\venvs\\local-worker-remove-bg\\Scripts\\python.exe";
                StatusMessage = "处理服务不可用";
                return;
            }
        }

        if (!_isServiceAvailable)
        {
            ErrorMessage = "抠图服务未配置，无法开始处理";
            StatusMessage = "服务不可用";
            return;
        }

        var files = PendingFiles.Select(f => f.FilePath).ToList();
        await StartProcessingForFilesAsync(files);
    }

    /// <summary>
    /// 将文件路径加入待处理列表（去重），并为每个文件异步加载缩略图。
    /// </summary>
    private void AddFilesToPending(IEnumerable<string> filePaths)
    {
        foreach (var path in filePaths)
        {
            if (string.IsNullOrWhiteSpace(path)) continue;
            if (!File.Exists(path)) continue;
            var normalized = Path.GetFullPath(path);
            if (PendingFiles.Any(f => f.FilePath.Equals(normalized, StringComparison.OrdinalIgnoreCase)))
                continue;

            var fileInfo = new FileInfo(normalized);
            var pendingFile = new PendingFileInfo
            {
                FilePath = normalized,
                FileSizeDisplay = FormatFileSize(fileInfo.Length),
            };

            // 异步加载缩略图（fire-and-forget，不阻塞 UI）
            _ = pendingFile.LoadThumbnailAsync();

            PendingFiles.Add(pendingFile);
        }

        ProgressValue = 0;
        ProgressMax = PendingFiles.Count;
        StatusMessage = $"已选择 {PendingFiles.Count} 个文件，点击开始处理";
        ErrorMessage = null;
    }

    /// <summary>
    /// 根据用户选择的输出目录生成输出文件路径。
    /// 文件名为 "原文件名_remove_bg.png"，放在用户指定目录下。
    /// </summary>
    private string GenerateOutputPath(string inputPath)
    {
        var fileName = Path.GetFileNameWithoutExtension(inputPath);
        var ext = OutputRgba || SynthesizeBackground ? ".png" : ".jpg";
        var outputFileName = $"{fileName}_remove_bg{ext}";

        if (!string.IsNullOrEmpty(_outputDirectory) && Directory.Exists(_outputDirectory))
            return Path.Combine(_outputDirectory, outputFileName);

        // 默认保存到源文件同目录
        return Path.Combine(Path.GetDirectoryName(inputPath)!, outputFileName);
    }

    /// <summary>
    /// 格式化文件大小为可读字符串
    /// </summary>
    private static string FormatFileSize(long bytes)
    {
        if (bytes < 1024) return $"{bytes} B";
        if (bytes < 1024 * 1024) return $"{bytes / 1024.0:F1} KB";
        if (bytes < 1024 * 1024 * 1024) return $"{bytes / (1024.0 * 1024.0):F1} MB";
        return $"{bytes / (1024.0 * 1024.0 * 1024.0):F2} GB";
    }

    /// <summary>
    /// 对指定文件列表启动抠图处理的核心逻辑
    /// </summary>
    private async Task StartProcessingForFilesAsync(List<string> filePaths)
    {
        if (_removeBgService == null || filePaths.Count == 0) return;

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
                    // 生成输出路径（如果用户选择了输出目录，则保存到该目录）
                    var outputPath = GenerateOutputPath(filePath);

                    RemoveBgResult result;
                    if (_synthesizeBackground)
                    {
                        // 合成纯色背景模式
                        var compositeColor = new List<int> { BgRed, BgGreen, BgBlue };
                        result = await _removeBgService.ProcessAsync(
                            filePath,
                            outputPath: outputPath,
                            modelName: SelectedModelName,
                            alphaMatting: AlphaMatting,
                            outputRgba: false,
                            compositeColor: compositeColor,
                            ct: _currentCts.Token);
                    }
                    else
                    {
                        // RGBA 透明输出模式
                        result = await _removeBgService.ProcessAsync(
                            filePath,
                            outputPath: outputPath,
                            modelName: SelectedModelName,
                            alphaMatting: AlphaMatting,
                            outputRgba: OutputRgba,
                            ct: _currentCts.Token);
                    }

                    // 将结果添加到列表（UI 线程）
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                        Results.Insert(0, result));
                }
                catch (Exception ex)
                {
                    // 单张处理失败不影响其余文件
                    System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                        Results.Insert(0, new RemoveBgResult
                        {
                            IsSuccess = false,
                            ErrorMessage = ex.Message,
                            InputPath = filePath
                        }));
                    _logger?.Error(
                        $"第 {i + 1}/{filePaths.Count} 张抠图处理失败: {ex.Message}",
                        ex, "desktop-remove-bg");
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
                $"抠图处理完成: {successCount} 成功, {failCount} 失败", "desktop-remove-bg");
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "已取消";
            ProgressValue = 0;
            _logger?.Info("抠图处理已取消", "desktop-remove-bg");
        }
        catch (Exception ex)
        {
            ErrorMessage = $"处理失败: {ex.Message}";
            StatusMessage = "处理出错，请查看错误信息";
            _logger?.Error($"抠图处理异常: {ex.Message}", ex, "desktop-remove-bg");
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
    private void CancelProcessing()
    {
        _currentCts?.Cancel();
        StatusMessage = "正在取消...";
    }

    /// <summary>
    /// 清除所有处理结果和待处理文件
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
    /// 清除所有待处理文件（不删除已处理结果）
    /// </summary>
    private void ClearPending()
    {
        PendingFiles.Clear();
        ProgressValue = 0;
        ProgressMax = 100;
        StatusMessage = "请选择文件";
        RefreshCommandStates();
    }

    /// <summary>
    /// 从待处理列表中移除单个文件
    /// </summary>
    private void RemovePendingFile(PendingFileInfo? file)
    {
        if (file != null)
            PendingFiles.Remove(file);

        if (PendingFiles.Count == 0)
        {
            ProgressValue = 0;
            ProgressMax = 100;
            StatusMessage = "请选择文件";
        }
        else
        {
            ProgressMax = PendingFiles.Count;
            StatusMessage = $"已选择 {PendingFiles.Count} 个文件，点击开始处理";
        }
    }

    /// <summary>
    /// 在文件资源管理器中打开输出文件
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
    /// 设置背景色
    /// </summary>
    private void SetBackgroundColor(int r, int g, int b)
    {
        BgRed = r;
        BgGreen = g;
        BgBlue = b;
        SynthesizeBackground = true;
        OnPropertyChanged(nameof(BackgroundColorPreview));
    }

    /// <summary>
    /// 刷新命令可执行状态
    /// </summary>
    private void RefreshCommandStates()
    {
        OnPropertyChanged(nameof(ResultCount));
        OnPropertyChanged(nameof(SuccessCount));
        OnPropertyChanged(nameof(FailedCount));

        (StartProcessingCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (CancelCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (ClearResultsCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (ClearPendingCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (OpenOutputFileCommand as RelayCommand)?.RaiseCanExecuteChanged();
    }
}
