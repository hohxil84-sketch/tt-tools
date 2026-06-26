using System.Collections.ObjectModel;
using System.Timers;
using System.Windows.Input;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;
using TTShared.Logging;
using TTShared.UI;
using Timer = System.Timers.Timer;

namespace TTTools.AiRenderClient.ViewModels;

/// <summary>
/// 下拉选项条目（WPF 绑定需要真实属性，不能用 named ValueTuple）
/// </summary>
public record ComboOption(string Value, string Display);

/// <summary>
/// 云端效果图生成模块主 ViewModel
/// 管理效果图生成任务的创建、状态轮询、结果展示和历史记录。
/// 本模块不直接调用第三方 AI，全部通过云端 provider-runtime 完成。
/// </summary>
public class AiRenderViewModel : BaseViewModel
{
    private readonly CloudApiClient? _cloudApiClient;
    private readonly AuthState? _authState;
    private readonly AppLogger? _logger;
    private readonly HttpClient _httpClient = new() { Timeout = TimeSpan.FromSeconds(30) };

    /// <summary>图片本地存储目录</summary>
    private static readonly string OutputDir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "TTTools", "ai-render-output");

    private bool _isRunning;
    private string _statusMessage = "就绪 - 填写效果图需求后点击创建任务";
    private string? _errorMessage;
    private CancellationTokenSource? _currentCts;
    private Timer? _pollingTimer;

    // ---- 输入参数 ----
    private string _selectedScene = "poster_design";
    private string _prompt = string.Empty;
    private string _inputFileIdsText = string.Empty;
    private string _selectedStyle = "modern";
    private string _selectedSize = "1024x1024";

    // ---- 当前任务状态 ----
    private string _currentTaskId = string.Empty;
    private string _taskStatus = string.Empty;
    private string _provider = string.Empty;
    private string _model = string.Empty;
    private decimal _estimatedCost;
    private int _creditsCharged;
    private string _providerCallId = string.Empty;

    // ---- 大图预览 ----
    private string? _previewImageUrl;
    private bool _isPreviewOpen;

    /// <summary>当前预览的大图 URL</summary>
    public string? PreviewImageUrl
    {
        get => _previewImageUrl;
        set
        {
            if (SetProperty(ref _previewImageUrl, value))
                OnPropertyChanged(nameof(HasPreviewImage));
        }
    }

    /// <summary>大图预览弹窗是否打开</summary>
    public bool IsPreviewOpen
    {
        get => _isPreviewOpen;
        set => SetProperty(ref _isPreviewOpen, value);
    }

    /// <summary>是否有可预览的图片</summary>
    public bool HasPreviewImage => !string.IsNullOrEmpty(PreviewImageUrl);

    /// <summary>当前任务的生成结果文件列表（URL 已替换为本地路径）</summary>
    public ObservableCollection<ResultFileDto> ResultFiles { get; } = new();

    /// <summary>图片本地缓存：file_id → 本地文件路径</summary>
    private readonly Dictionary<string, string> _localFileCache = new();

    /// <summary>任务历史记录列表</summary>
    public ObservableCollection<AiRenderHistoryItem> HistoryItems { get; } = new();

    // ---- 预设数据 ----

    /// <summary>可用的场景类型列表（中文名称）</summary>
    public static List<ComboOption> SceneTypeList { get; } = new()
    {
        new("poster_design", "海报设计"),
        new("interior_design", "室内设计"),
        new("product_showcase", "产品展示"),
        new("packaging_design", "包装设计"),
        new("banner_design", "横幅 / 展板"),
        new("flyer_design", "传单 / 折页"),
        new("business_card", "名片设计"),
        new("social_media", "社交媒体配图"),
    };

    /// <summary>可用的风格列表（中文名称）</summary>
    public static List<ComboOption> StyleList { get; } = new()
    {
        new("modern", "现代风格"),
        new("minimalist", "极简风格"),
        new("chinese", "中式风格"),
        new("european", "欧式风格"),
        new("japanese", "日式风格"),
        new("vintage", "复古风格"),
        new("tech", "科技感"),
        new("natural", "自然清新"),
    };

    /// <summary>可用的输出尺寸列表</summary>
    public static List<ComboOption> SizeList { get; } = new()
    {
        new("1024x1024", "1024 × 1024 (方形)"),
        new("1920x1080", "1920 × 1080 (横版)"),
        new("1080x1920", "1080 × 1920 (竖版)"),
        new("2048x2048", "2048 × 2048 (高清方形)"),
        new("1280x720", "1280 × 720 (宽屏)"),
        new("800x1200", "800 × 1200 (竖版小)"),
    };
    // ========== 输入属性 ==========

    /// <summary>当前选择的场景类型</summary>
    public string SelectedScene
    {
        get => _selectedScene;
        set => SetProperty(ref _selectedScene, value);
    }

    /// <summary>效果图生成提示词，描述期望的视觉效果</summary>
    public string Prompt
    {
        get => _prompt;
        set => SetProperty(ref _prompt, value);
    }

    /// <summary>输入文件 ID 文本（逗号分隔的 UUID 列表）</summary>
    public string InputFileIdsText
    {
        get => _inputFileIdsText;
        set => SetProperty(ref _inputFileIdsText, value);
    }

    /// <summary>当前选择的风格参考</summary>
    public string SelectedStyle
    {
        get => _selectedStyle;
        set => SetProperty(ref _selectedStyle, value);
    }

    /// <summary>当前选择的输出尺寸</summary>
    public string SelectedSize
    {
        get => _selectedSize;
        set => SetProperty(ref _selectedSize, value);
    }

    // ========== 结果/任务属性 ==========

    /// <summary>当前查看的任务 ID</summary>
    public string CurrentTaskId
    {
        get => _currentTaskId;
        set => SetProperty(ref _currentTaskId, value);
    }

    /// <summary>任务当前状态（queued / running / succeeded / failed）</summary>
    public string TaskStatus
    {
        get => _taskStatus;
        set
        {
            if (SetProperty(ref _taskStatus, value))
            {
                OnPropertyChanged(nameof(IsTaskRunning));
                OnPropertyChanged(nameof(IsTaskCompleted));
                OnPropertyChanged(nameof(IsTaskFailed));
                OnPropertyChanged(nameof(HasTaskResult));
                OnPropertyChanged(nameof(TaskStatusDisplay));
            }
        }
    }

    /// <summary>使用的 AI Provider</summary>
    public string Provider
    {
        get => _provider;
        set => SetProperty(ref _provider, value);
    }

    /// <summary>使用的 AI 模型</summary>
    public string Model
    {
        get => _model;
        set => SetProperty(ref _model, value);
    }

    /// <summary>估算成本（云端返回，仅用于展示）</summary>
    public decimal EstimatedCost
    {
        get => _estimatedCost;
        set => SetProperty(ref _estimatedCost, value);
    }

    /// <summary>扣除的 AI 额度（云端返回，仅用于展示）</summary>
    public int CreditsCharged
    {
        get => _creditsCharged;
        set => SetProperty(ref _creditsCharged, value);
    }

    /// <summary>Provider 调用 ID</summary>
    public string ProviderCallId
    {
        get => _providerCallId;
        set => SetProperty(ref _providerCallId, value);
    }

    // ========== 状态属性 ==========

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

    /// <summary>是否有当前任务</summary>
    public bool HasTaskResult => !string.IsNullOrEmpty(CurrentTaskId);

    /// <summary>任务是否正在处理中（排队或运行中）</summary>
    public bool IsTaskRunning => TaskStatus is "queued" or "running";

    /// <summary>任务是否已完成</summary>
    public bool IsTaskCompleted => TaskStatus == "succeeded";

    /// <summary>任务是否已失败</summary>
    public bool IsTaskFailed => TaskStatus == "failed";

    /// <summary>任务状态的中文显示</summary>
    public string TaskStatusDisplay => TaskStatus switch
    {
        "queued" => "排队中...",
        "running" => "生成中...",
        "succeeded" => "已完成",
        "failed" => "失败",
        _ => string.Empty
    };

    /// <summary>是否正在调用云端 API</summary>
    public bool IsRunning
    {
        get => _isRunning;
        set
        {
            if (SetProperty(ref _isRunning, value))
            {
                OnPropertyChanged(nameof(CanCreateTask));
                OnPropertyChanged(nameof(CanRefreshStatus));
            }
        }
    }

    /// <summary>是否可以创建任务</summary>
    public bool CanCreateTask => !IsRunning && !string.IsNullOrWhiteSpace(Prompt);

    /// <summary>是否可以手动刷新状态</summary>
    public bool CanRefreshStatus => !IsRunning && IsTaskRunning;

    /// <summary>是否正在轮询任务状态</summary>
    public bool IsPolling => _pollingTimer?.Enabled ?? false;

    /// <summary>历史记录数量</summary>
    public int HistoryCount => HistoryItems.Count;

    // ========== 命令 ==========

    public ICommand CreateTaskCommand { get; }
    public ICommand RefreshStatusCommand { get; }
    public ICommand ClearCommand { get; }
    public ICommand SelectHistoryItemCommand { get; }
    public ICommand OpenResultFileCommand { get; }
    public ICommand ClosePreviewCommand { get; }
    public ICommand SaveResultFileCommand { get; }
    public ICommand OpenOutputFolderCommand { get; }

    public AiRenderViewModel(
        CloudApiClient? cloudApiClient,
        AuthState? authState,
        AppLogger? logger = null)
    {
        _cloudApiClient = cloudApiClient;
        _authState = authState;
        _logger = logger;

        // 初始化命令
        CreateTaskCommand = new RelayCommand(CreateTaskAsync, () => CanCreateTask);
        RefreshStatusCommand = new RelayCommand(RefreshStatusAsync, () => CanRefreshStatus);
        ClearCommand = new RelayCommand(Clear);
        SelectHistoryItemCommand = new RelayCommand<AiRenderHistoryItem?>(SelectHistoryItem);
        OpenResultFileCommand = new RelayCommand<ResultFileDto?>(OpenResultFile);
        ClosePreviewCommand = new RelayCommand(ClosePreview);
        SaveResultFileCommand = new RelayCommand<ResultFileDto?>(SaveResultFile);
        OpenOutputFolderCommand = new RelayCommand(OpenOutputFolder);

        // 监听属性变更以刷新命令状态
        PropertyChanged += (_, e) =>
        {
            if (e.PropertyName is nameof(Prompt) or nameof(IsRunning))
                RefreshCommandStates();
            if (e.PropertyName is nameof(TaskStatus))
                RefreshCommandStates();
        };

        // 监听历史列表变更
        HistoryItems.CollectionChanged += (_, _) =>
        {
            OnPropertyChanged(nameof(HistoryCount));
        };
    }

    /// <summary>
    /// 默认构造函数（用于设计时视图预览）
    /// </summary>
    public AiRenderViewModel() : this(null, null) { }

    // ========== 核心任务创建逻辑 ==========

    /// <summary>
    /// 调用云端 API 创建效果图生成任务。
    /// 客户端只提交场景类型、提示词、输入文件、风格和尺寸等业务参数，
    /// 不提交 user_id、plan_code、provider、model 等决策字段。
    /// </summary>
    private async void CreateTaskAsync()
    {
        if (_cloudApiClient == null)
        {
            ErrorMessage = "云端 API 客户端未配置";
            StatusMessage = "任务创建失败 - API 客户端不可用";
            return;
        }

        // 检查登录状态
        if (_authState != null && !_authState.IsLoggedIn)
        {
            ErrorMessage = "请先登录后再使用效果图生成功能";
            StatusMessage = "未登录 - 请先登录";
            return;
        }

        // 校验必填字段
        if (string.IsNullOrWhiteSpace(Prompt))
        {
            ErrorMessage = "请输入效果图描述提示词";
            return;
        }

        IsRunning = true;
        ErrorMessage = null;
        StatusMessage = "正在创建效果图生成任务...";

        _currentCts = new CancellationTokenSource();

        try
        {
            // 解析输入文件 ID 列表
            var inputFileIds = ParseInputFileIds();

            // 构建请求（严格对应 OpenAPI ai-render.yaml 定义的字段）
            var request = new CreateAiRenderTaskRequest
            {
                SceneType = SelectedScene,
                Prompt = Prompt.Trim(),
                InputFileIds = inputFileIds,
                Style = string.IsNullOrWhiteSpace(SelectedStyle) ? null : SelectedStyle,
                Size = string.IsNullOrWhiteSpace(SelectedSize) ? null : SelectedSize,
                // client_request_id 由 CloudApiClient 自动填充
            };

            var response = await _cloudApiClient.CreateAiRenderTaskAsync(request, _currentCts.Token);

            if (response?.IsSuccess == true && response.Data != null)
            {
                var data = response.Data;

                // 更新当前任务状态（不清空旧结果，等新结果回来再替换）
                CurrentTaskId = data.TaskId;
                TaskStatus = data.Status;

                // 添加到历史记录
                var historyItem = new AiRenderHistoryItem
                {
                    TaskId = data.TaskId,
                    SceneType = SelectedScene,
                    Prompt = Prompt.Trim(),
                    Status = data.Status,
                    EstimatedCredits = data.EstimatedCredits,
                    CreatedAt = DateTime.Now,
                    RequestId = response.RequestId ?? string.Empty
                };

                System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    HistoryItems.Insert(0, historyItem));

                StatusMessage = $"任务已创建 - ID: {data.TaskId[..8]}..., 预估消耗 {data.EstimatedCredits} 额度";
                _logger?.Info(
                    $"效果图任务创建成功: task_id={data.TaskId}, scene_type={SelectedScene}, " +
                    $"status={data.Status}, request_id={response.RequestId}",
                    "desktop-ai-render-client");

                // 自动开始轮询任务状态
                StartPolling();
            }
            else
            {
                var errCode = response?.Error?.Code ?? "unknown";
                var errMsg = response?.Error?.Message ?? "未知错误";

                ErrorMessage = $"[{errCode}] {errMsg}";
                StatusMessage = $"任务创建失败 - {errCode}";
                _logger?.Warning(
                    $"效果图任务创建失败: code={errCode}, message={errMsg}",
                    "desktop-ai-render-client");
            }
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "任务创建已取消";
            _logger?.Info("效果图任务创建已取消", "desktop-ai-render-client");
        }
        catch (Exception ex)
        {
            ErrorMessage = $"任务创建失败: {ex.Message}";
            StatusMessage = "任务创建出错，请查看错误信息";
            _logger?.Error($"效果图任务创建异常: {ex.Message}", ex, "desktop-ai-render-client");
        }
        finally
        {
            IsRunning = false;
            _currentCts?.Dispose();
            _currentCts = null;
            RefreshCommandStates();
        }
    }

    // ========== 任务状态查询 ==========

    /// <summary>
    /// 手动刷新当前任务状态。
    /// 调用 GET /api/v1/ai/render/tasks/{task_id} 获取最新任务状态和结果。
    /// </summary>
    private async void RefreshStatusAsync()
    {
        if (_cloudApiClient == null || string.IsNullOrEmpty(CurrentTaskId)) return;

        await QueryAndUpdateTaskStatus(CurrentTaskId);
    }

    /// <summary>
    /// 查询指定任务 ID 的状态并更新 ViewModel 属性。
    /// </summary>
    private async Task QueryAndUpdateTaskStatus(string taskId)
    {
        if (_cloudApiClient == null) return;

        try
        {
            var response = await _cloudApiClient.GetAiRenderTaskAsync(taskId);

            if (response?.IsSuccess == true && response.Data != null)
            {
                var data = response.Data;

                // 更新任务状态
                var previousStatus = TaskStatus;
                TaskStatus = data.Status;

                // 更新结果文件（下载到本地后替换 URL 为本地路径）
                ResultFiles.Clear();
                if (data.ResultFiles != null)
                {
                    foreach (var file in data.ResultFiles)
                    {
                        // 下载图片到本地存储
                        var localFile = await DownloadToLocalAsync(file);
                        if (localFile != null)
                        {
                            file.Url = localFile;  // 替换为本地路径
                        }
                        ResultFiles.Add(file);
                    }
                }

                // 更新 Provider 信息
                Provider = data.Provider ?? string.Empty;
                Model = data.Model ?? string.Empty;
                EstimatedCost = data.EstimatedCost ?? 0;
                CreditsCharged = data.CreditsCharged ?? 0;
                ProviderCallId = data.ProviderCallId ?? string.Empty;

                // 更新历史记录中的状态
                var historyItem = HistoryItems.FirstOrDefault(h => h.TaskId == taskId);
                if (historyItem != null)
                {
                    historyItem.Status = data.Status;
                    historyItem.Provider = data.Provider ?? string.Empty;
                    historyItem.Model = data.Model ?? string.Empty;
                    historyItem.CreditsCharged = data.CreditsCharged ?? 0;
                    // 触发 UI 刷新历史列表
                    var index = HistoryItems.IndexOf(historyItem);
                    if (index >= 0)
                    {
                        HistoryItems.RemoveAt(index);
                        HistoryItems.Insert(index, historyItem);
                    }
                }

                // 如果任务已完成或失败，停止轮询
                if (data.Status is "succeeded" or "failed")
                {
                    StopPolling();

                    if (data.Status == "succeeded")
                    {
                        StatusMessage = $"生成成功 - 使用 {data.Provider}/{data.Model}，扣除 {data.CreditsCharged} 额度";
                        _logger?.Info(
                            $"效果图任务完成: task_id={taskId}, provider={data.Provider}, " +
                            $"credits_charged={data.CreditsCharged}",
                            "desktop-ai-render-client");
                    }
                    else
                    {
                        StatusMessage = $"任务失败 - {taskId[..8]}...";
                        _logger?.Warning(
                            $"效果图任务失败: task_id={taskId}",
                            "desktop-ai-render-client");
                    }
                }
                else if (data.Status != previousStatus)
                {
                    StatusMessage = $"任务状态更新 - {TaskStatusDisplay}";
                }
            }
        }
        catch (Exception ex)
        {
            _logger?.Warning(
                $"查询效果图任务状态异常: task_id={taskId}, error={ex.Message}",
                "desktop-ai-render-client");
        }
    }

    // ========== 任务状态轮询 ==========

    /// <summary>
    /// 启动定时轮询当前任务状态（每 3 秒一次）。
    /// 当任务进入终态（succeeded / failed）时自动停止。
    /// </summary>
    private void StartPolling()
    {
        StopPolling();

        _pollingTimer = new Timer(3000); // 每 3 秒轮询一次
        _pollingTimer.Elapsed += OnPollingTimerElapsed;
        _pollingTimer.AutoReset = true;
        _pollingTimer.Start();

        OnPropertyChanged(nameof(IsPolling));
        _logger?.Info($"开始轮询任务状态: task_id={CurrentTaskId}", "desktop-ai-render-client");
    }

    /// <summary>
    /// 停止任务状态轮询
    /// </summary>
    private void StopPolling()
    {
        if (_pollingTimer != null)
        {
            _pollingTimer.Stop();
            _pollingTimer.Elapsed -= OnPollingTimerElapsed;
            _pollingTimer.Dispose();
            _pollingTimer = null;
        }

        OnPropertyChanged(nameof(IsPolling));
        RefreshCommandStates();
    }

    /// <summary>
    /// 轮询定时器回调：在 UI 线程上查询任务状态。
    /// </summary>
    private async void OnPollingTimerElapsed(object? sender, ElapsedEventArgs e)
    {
        // 确保在 UI 线程执行
        if (System.Windows.Application.Current?.Dispatcher != null)
        {
            await System.Windows.Application.Current.Dispatcher.InvokeAsync(
                async () => await QueryAndUpdateTaskStatus(CurrentTaskId));
        }
    }

    // ========== 辅助操作 ==========

    /// <summary>
    /// 清除当前输入和结果
    /// </summary>
    private void Clear()
    {
        StopPolling();

        Prompt = string.Empty;
        InputFileIdsText = string.Empty;
        SelectedScene = "poster_design";
        SelectedStyle = "modern";
        SelectedSize = "1024x1024";

        CurrentTaskId = string.Empty;
        TaskStatus = string.Empty;
        ResultFiles.Clear();
        Provider = string.Empty;
        Model = string.Empty;
        EstimatedCost = 0;
        CreditsCharged = 0;
        ProviderCallId = string.Empty;

        ErrorMessage = null;
        StatusMessage = "就绪 - 填写效果图需求后点击创建任务";
        RefreshCommandStates();
    }

    /// <summary>
    /// 选择历史记录项，恢复对应任务到当前视图
    /// </summary>
    private void SelectHistoryItem(AiRenderHistoryItem? item)
    {
        if (item == null) return;

        StopPolling();

        CurrentTaskId = item.TaskId;
        Prompt = item.Prompt;
        SelectedScene = item.SceneType;
        TaskStatus = item.Status;
        Provider = item.Provider;
        Model = item.Model;
        CreditsCharged = item.CreditsCharged;

        StatusMessage = $"已加载历史任务 - {item.SceneTypeDisplay} / {item.TaskId[..8]}...";

        // 总是重新查询任务以恢复结果文件（进行中任务会启动轮询）
        _ = QueryAndUpdateTaskStatus(item.TaskId);
        if (item.Status is "queued" or "running")
        {
            StartPolling();
        }
    }

    /// <summary>
    /// 在客户端内预览结果大图（弹出预览窗口）
    /// </summary>
    private void OpenResultFile(ResultFileDto? file)
    {
        if (file == null || string.IsNullOrWhiteSpace(file.Url))
        {
            StatusMessage = "该文件暂无预览链接";
            return;
        }

        PreviewImageUrl = file.Url;
        IsPreviewOpen = true;
        StatusMessage = $"正在预览: {file.FileId}";
    }

    /// <summary>
    /// 关闭大图预览弹窗
    /// </summary>
    private void ClosePreview()
    {
        IsPreviewOpen = false;
        PreviewImageUrl = null;
    }

    /// <summary>
    /// 将结果图片另存为用户指定路径
    /// </summary>
    private void SaveResultFile(ResultFileDto? file)
    {
        if (file == null || string.IsNullOrWhiteSpace(file.Url)) return;

        try
        {
            var dialog = new Microsoft.Win32.SaveFileDialog
            {
                FileName = $"{file.FileId}",
                DefaultExt = file.MimeType switch
                {
                    "image/jpeg" or "image/jpg" => ".jpg",
                    "image/webp" => ".webp",
                    _ => ".png"
                },
                Filter = "图片文件|*.png;*.jpg;*.jpeg;*.webp|所有文件|*.*"
            };

            if (dialog.ShowDialog() == true)
            {
                File.Copy(file.Url, dialog.FileName, overwrite: true);
                StatusMessage = $"已保存到: {dialog.FileName}";
            }
        }
        catch (Exception ex)
        {
            StatusMessage = $"保存失败: {ex.Message}";
        }
    }

    /// <summary>
    /// 在资源管理器中打开图片本地存储目录
    /// </summary>
    private void OpenOutputFolder()
    {
        try
        {
            Directory.CreateDirectory(OutputDir);
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = "explorer.exe",
                Arguments = OutputDir,
                UseShellExecute = true
            });
            StatusMessage = $"已打开目录: {OutputDir}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"打开目录失败: {ex.Message}";
        }
    }

    // ========== 图片本地存储 ==========

    /// <summary>
    /// 将结果文件从远程 URL 下载到本地存储目录，返回本地文件路径。
    /// 已缓存的文件不再重复下载；URL 为空时返回 null。
    /// </summary>
    private async Task<string?> DownloadToLocalAsync(ResultFileDto file)
    {
        if (string.IsNullOrWhiteSpace(file.Url)) return null;

        // 检查缓存
        if (_localFileCache.TryGetValue(file.FileId, out var cached))
        {
            if (File.Exists(cached)) return cached;
            _localFileCache.Remove(file.FileId);
        }

        try
        {
            Directory.CreateDirectory(OutputDir);

            // 从 URL 或本地文件 ID 生成文件名
            var ext = file.MimeType switch
            {
                "image/jpeg" or "image/jpg" => ".jpg",
                "image/webp" => ".webp",
                _ => ".png"
            };
            var localPath = Path.Combine(OutputDir, $"{file.FileId}{ext}");

            // 如果 URL 已经是本地路径，直接使用
            if (File.Exists(file.Url))
            {
                _localFileCache[file.FileId] = file.Url;
                return file.Url;
            }

            // 下载到本地
            var imageBytes = await _httpClient.GetByteArrayAsync(file.Url);
            await File.WriteAllBytesAsync(localPath, imageBytes);

            _localFileCache[file.FileId] = localPath;
            _logger?.Info($"图片已保存到本地: {localPath}", "desktop-ai-render-client");
            return localPath;
        }
        catch (Exception ex)
        {
            _logger?.Warning($"图片下载失败: {file.FileId}, url={file.Url}, error={ex.Message}",
                "desktop-ai-render-client");
            // 下载失败时保留原始 URL（可能仍然可以直接显示）
            return file.Url;
        }
    }

    // ========== 工具方法 ==========

    /// <summary>
    /// 解析输入文件 ID 文本为 UUID 列表。
    /// 支持逗号、换行、空格分隔。
    /// </summary>
    private List<string> ParseInputFileIds()
    {
        if (string.IsNullOrWhiteSpace(InputFileIdsText)) return new List<string>();

        return InputFileIdsText
            .Split(new[] { ',', '\n', '\r', ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries)
            .Select(s => s.Trim())
            .Where(s => !string.IsNullOrWhiteSpace(s))
            .ToList();
    }

    /// <summary>
    /// 刷新命令可执行状态
    /// </summary>
    private void RefreshCommandStates()
    {
        (CreateTaskCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (RefreshStatusCommand as RelayCommand)?.RaiseCanExecuteChanged();

        OnPropertyChanged(nameof(CanCreateTask));
        OnPropertyChanged(nameof(CanRefreshStatus));
    }
}

/// <summary>
/// 效果图生成任务历史记录项
/// 用于在历史列表中展示已创建任务的状态摘要信息
/// </summary>
public class AiRenderHistoryItem
{
    /// <summary>任务 ID</summary>
    public string TaskId { get; set; } = string.Empty;

    /// <summary>场景类型代码</summary>
    public string SceneType { get; set; } = string.Empty;

    /// <summary>生成提示词</summary>
    public string Prompt { get; set; } = string.Empty;

    /// <summary>任务当前状态</summary>
    public string Status { get; set; } = string.Empty;

    /// <summary>使用的 Provider</summary>
    public string Provider { get; set; } = string.Empty;

    /// <summary>使用的模型</summary>
    public string Model { get; set; } = string.Empty;

    /// <summary>预估消耗额度</summary>
    public int EstimatedCredits { get; set; }

    /// <summary>实际扣除的 AI 额度</summary>
    public int CreditsCharged { get; set; }

    /// <summary>任务创建时间</summary>
    public DateTime CreatedAt { get; set; } = DateTime.Now;

    /// <summary>云端请求 ID</summary>
    public string RequestId { get; set; } = string.Empty;

    /// <summary>场景类型展示名称（中文）</summary>
    public string SceneTypeDisplay
    {
        get
        {
            var entry = AiRenderViewModel.SceneTypeList.FirstOrDefault(s => s.Value == SceneType);
            return entry != default ? entry.Display : SceneType;
        }
    }

    /// <summary>状态展示名称（中文）</summary>
    public string StatusDisplay => Status switch
    {
        "queued" => "排队中",
        "running" => "生成中",
        "succeeded" => "已完成",
        "failed" => "失败",
        _ => Status
    };

    /// <summary>状态颜色标识</summary>
    public string StatusColor => Status switch
    {
        "succeeded" => "#38A169",
        "failed" => "#E53E3E",
        "running" => "#3182CE",
        "queued" => "#D69E2E",
        _ => "#718096"
    };

    /// <summary>提示词摘要（截取前 40 字）</summary>
    public string PromptSummary
    {
        get
        {
            if (string.IsNullOrWhiteSpace(Prompt)) return "(空)";
            return Prompt.Length > 40
                ? Prompt[..40] + "..."
                : Prompt;
        }
    }

    /// <summary>格式化时间显示</summary>
    public string TimeDisplay => CreatedAt.ToString("HH:mm:ss");

    /// <summary>费用摘要</summary>
    public string CostSummary => CreditsCharged > 0
        ? $"-{CreditsCharged} 额度 / {Provider}/{Model}"
        : $"预估 {EstimatedCredits} 额度";
}
