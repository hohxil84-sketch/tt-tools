using System.Collections.ObjectModel;
using System.Timers;
using System.Windows;
using System.Windows.Input;
using Microsoft.Win32;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;
using TTShared.Logging;
using TTShared.UI;
using Timer = System.Timers.Timer;

namespace TTTools.AiImageToolsClient.ViewModels;

/// <summary>
/// 云端 AI 图片工具主 ViewModel
/// 管理五种云端 AI 图片工具的任务创建、状态轮询、结果展示和历史记录。
/// 本模块不直接调用第三方 AI，全部通过云端 provider-runtime 完成。
///
/// 支持的子功能：
/// - upscale_image_cloud：高清修复
/// - vectorize_image_cloud：转矢量
/// - ai_edit_image_cloud：AI 改图
/// - remove_bg_cloud：云端高级抠图
/// - ocr_cloud：云端高级 OCR
/// </summary>
public class AiImageToolsViewModel : BaseViewModel
{
    private readonly CloudApiClient? _cloudApiClient;
    private readonly AuthState? _authState;
    private readonly AppLogger? _logger;

    // ---- 处理状态 ----
    private bool _isProcessing;
    private string _statusMessage = "就绪 - 选择功能类型和图片后点击「开始处理」";
    private string? _errorMessage;
    private CancellationTokenSource? _currentCts;
    private Timer? _pollingTimer;

    // ---- 功能选择 ----
    private string _selectedFeature = "upscale_image_cloud";

    // ---- AI 改图参数 ----
    private string _editPrompt = string.Empty;

    // ---- 转矢量参数 ----
    private string _vectorOutputFormat = "svg";

    // ---- OCR 参数 ----
    private string _ocrLanguage = "auto";

    // ---- 高清修复参数 ----
    private int _upscaleFactor = 2;

    // ---- 当前任务跟踪 ----
    private string _currentTaskId = string.Empty;
    private string _taskStatus = string.Empty;
    private string _taskFeature = string.Empty;
    private string _provider = string.Empty;
    private string _model = string.Empty;
    private decimal _estimatedCost;
    private int _creditsCharged;
    private string _providerCallId = string.Empty;
    private int _estimatedCredits;

    /// <summary>当前任务的输入文件列表（用于前后对比展示）</summary>
    public ObservableCollection<PendingFileItem> PendingFiles { get; } = new();

    /// <summary>当前任务的处理结果文件列表</summary>
    public ObservableCollection<ResultFileDto> ResultFiles { get; } = new();

    /// <summary>任务历史记录列表</summary>
    public ObservableCollection<AiImageToolHistoryItem> HistoryItems { get; } = new();

    // ---- 功能选择列表 ----

    /// <summary>可用的 AI 图片工具功能列表（中文名称）</summary>
    public static List<(string Value, string Display, string Description)> FeatureList { get; } = new()
    {
        ("upscale_image_cloud", "🔍 高清修复", "提升图片分辨率，增强清晰度"),
        ("vectorize_image_cloud", "📐 转矢量", "将位图转换为 SVG/PDF/EPS 矢量格式"),
        ("ai_edit_image_cloud", "✨ AI 改图", "通过 AI 提示词编辑和修改图片内容"),
        ("remove_bg_cloud", "✂️ 高级抠图", "云端 AI 精准去除背景"),
        ("ocr_cloud", "📝 高级 OCR", "云端 AI 文字识别，保留排版结构"),
    };

    /// <summary>转矢量支持的输出格式</summary>
    public static List<(string Value, string Display)> VectorFormatList { get; } = new()
    {
        ("svg", "SVG（矢量图形）"),
        ("pdf", "PDF（便携文档）"),
        ("eps", "EPS（封装 PostScript）"),
    };

    /// <summary>OCR 支持的语言</summary>
    public static List<(string Value, string Display)> OcrLanguageList { get; } = new()
    {
        ("auto", "自动检测"),
        ("zh", "中文"),
        ("en", "英文"),
        ("ja", "日文"),
        ("ko", "韩文"),
        ("zh+en", "中文 + 英文"),
    };

    /// <summary>高清修复支持的放大倍率</summary>
    public static List<(int Value, string Display)> UpscaleFactorList { get; } = new()
    {
        (2, "2× 放大"),
        (3, "3× 放大"),
        (4, "4× 放大"),
    };

    // ========== 功能选择属性 ==========

    /// <summary>当前选择的功能码</summary>
    public string SelectedFeature
    {
        get => _selectedFeature;
        set
        {
            if (SetProperty(ref _selectedFeature, value))
            {
                OnPropertyChanged(nameof(IsEditFeature));
                OnPropertyChanged(nameof(IsVectorizeFeature));
                OnPropertyChanged(nameof(IsOcrFeature));
                OnPropertyChanged(nameof(IsUpscaleFeature));
                OnPropertyChanged(nameof(IsRemoveBgFeature));
                OnPropertyChanged(nameof(ShowBeforeAfter));
            }
        }
    }

    /// <summary>当前功能的展示名称</summary>
    public string SelectedFeatureDisplay
    {
        get
        {
            var entry = FeatureList.FirstOrDefault(f => f.Value == SelectedFeature);
            return entry != default ? entry.Display : SelectedFeature;
        }
    }

    /// <summary>是否选择了 AI 改图功能（需要 prompt 输入框）</summary>
    public bool IsEditFeature => SelectedFeature == "ai_edit_image_cloud";

    /// <summary>是否选择了转矢量功能（需要输出格式选择）</summary>
    public bool IsVectorizeFeature => SelectedFeature == "vectorize_image_cloud";

    /// <summary>是否选择了 OCR 功能（需要语言选择）</summary>
    public bool IsOcrFeature => SelectedFeature == "ocr_cloud";

    /// <summary>是否选择了高清修复功能</summary>
    public bool IsUpscaleFeature => SelectedFeature == "upscale_image_cloud";

    /// <summary>是否选择了高级抠图功能</summary>
    public bool IsRemoveBgFeature => SelectedFeature == "remove_bg_cloud";

    /// <summary>是否显示前后对比（高清修复和高级抠图）</summary>
    public bool ShowBeforeAfter => IsUpscaleFeature || IsRemoveBgFeature;

    /// <summary>AI 改图提示词（仅 ai_edit_image_cloud 使用）</summary>
    public string EditPrompt
    {
        get => _editPrompt;
        set => SetProperty(ref _editPrompt, value);
    }

    /// <summary>转矢量输出格式（仅 vectorize_image_cloud 使用）</summary>
    public string VectorOutputFormat
    {
        get => _vectorOutputFormat;
        set => SetProperty(ref _vectorOutputFormat, value);
    }

    /// <summary>OCR 识别语言（仅 ocr_cloud 使用）</summary>
    public string OcrLanguage
    {
        get => _ocrLanguage;
        set => SetProperty(ref _ocrLanguage, value);
    }

    /// <summary>高清修复放大倍率（仅 upscale_image_cloud 使用）</summary>
    public int UpscaleFactor
    {
        get => _upscaleFactor;
        set => SetProperty(ref _upscaleFactor, value);
    }

    // ========== 结果/任务属性 ==========

    /// <summary>当前任务 ID</summary>
    public string CurrentTaskId
    {
        get => _currentTaskId;
        set => SetProperty(ref _currentTaskId, value);
    }

    /// <summary>任务当前状态</summary>
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
                OnPropertyChanged(nameof(ShowOcrResult));
            }
        }
    }

    /// <summary>任务功能码</summary>
    public string TaskFeature
    {
        get => _taskFeature;
        set => SetProperty(ref _taskFeature, value);
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

    /// <summary>估算成本（仅展示）</summary>
    public decimal EstimatedCost
    {
        get => _estimatedCost;
        set => SetProperty(ref _estimatedCost, value);
    }

    /// <summary>扣除的 AI 额度（仅展示）</summary>
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

    /// <summary>预估消耗额度（创建任务时返回）</summary>
    public int EstimatedCredits
    {
        get => _estimatedCredits;
        set => SetProperty(ref _estimatedCredits, value);
    }

    // ---- OCR 结果文本 ----
    private string _ocrResultText = string.Empty;

    /// <summary>OCR 识别结果文本（保留排版，支持多行）</summary>
    public string OcrResultText
    {
        get => _ocrResultText;
        set => SetProperty(ref _ocrResultText, value);
    }

    // ---- 积分余额显示 ----
    private int _currentBalance;
    private string _currentPlanCode = string.Empty;

    /// <summary>当前积分余额</summary>
    public int CurrentBalance
    {
        get => _currentBalance;
        set => SetProperty(ref _currentBalance, value);
    }

    /// <summary>当前套餐代码</summary>
    public string CurrentPlanCode
    {
        get => _currentPlanCode;
        set => SetProperty(ref _currentPlanCode, value);
    }

    /// <summary>余额展示文本</summary>
    public string BalanceDisplay
        => CurrentPlanCode != null
            ? $"套餐: {CurrentPlanCode} | 余额: {CurrentBalance} 积分"
            : "未登录";

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

    /// <summary>任务是否正在处理中</summary>
    public bool IsTaskRunning => TaskStatus is "queued" or "running";

    /// <summary>任务是否已完成</summary>
    public bool IsTaskCompleted => TaskStatus == "succeeded";

    /// <summary>任务是否已失败</summary>
    public bool IsTaskFailed => TaskStatus == "failed";

    /// <summary>是否显示 OCR 结果区域</summary>
    public bool ShowOcrResult => IsTaskCompleted && TaskFeature == "ocr_cloud" && !string.IsNullOrEmpty(OcrResultText);

    /// <summary>任务状态中文显示</summary>
    public string TaskStatusDisplay => TaskStatus switch
    {
        "queued" => "排队中...",
        "running" => "处理中...",
        "succeeded" => "已完成",
        "failed" => "失败",
        _ => string.Empty
    };

    /// <summary>是否正在调用云端 API</summary>
    public bool IsProcessing
    {
        get => _isProcessing;
        set
        {
            if (SetProperty(ref _isProcessing, value))
            {
                OnPropertyChanged(nameof(CanStartProcessing));
                OnPropertyChanged(nameof(CanRefreshStatus));
            }
        }
    }

    /// <summary>是否可以开始处理</summary>
    public bool CanStartProcessing => !IsProcessing && PendingFiles.Count > 0;

    /// <summary>是否可以手动刷新状态</summary>
    public bool CanRefreshStatus => !IsProcessing && IsTaskRunning;

    /// <summary>是否正在轮询</summary>
    public bool IsPolling => _pollingTimer?.Enabled ?? false;

    /// <summary>历史记录数量</summary>
    public int HistoryCount => HistoryItems.Count;

    /// <summary>待处理文件数量</summary>
    public int PendingFileCount => PendingFiles.Count;

    // ========== 命令 ==========

    public ICommand AddFilesCommand { get; }
    public ICommand RemoveFileCommand { get; }
    public ICommand ClearPendingCommand { get; }
    public ICommand StartProcessingCommand { get; }
    public ICommand RefreshStatusCommand { get; }
    public ICommand ClearCommand { get; }
    public ICommand SelectHistoryItemCommand { get; }
    public ICommand OpenResultFileCommand { get; }
    public ICommand RefreshBalanceCommand { get; }
    public ICommand DownloadResultFileCommand { get; }

    public AiImageToolsViewModel(
        CloudApiClient? cloudApiClient,
        AuthState? authState,
        AppLogger? logger = null)
    {
        _cloudApiClient = cloudApiClient;
        _authState = authState;
        _logger = logger;

        // 初始化命令
        AddFilesCommand = new RelayCommand(AddFiles);
        RemoveFileCommand = new RelayCommand<PendingFileItem?>(RemoveFile);
        ClearPendingCommand = new RelayCommand(ClearPending);
        StartProcessingCommand = new RelayCommand(StartProcessingAsync, () => CanStartProcessing);
        RefreshStatusCommand = new RelayCommand(RefreshStatusAsync, () => CanRefreshStatus);
        ClearCommand = new RelayCommand(Clear);
        SelectHistoryItemCommand = new RelayCommand<AiImageToolHistoryItem?>(SelectHistoryItem);
        OpenResultFileCommand = new RelayCommand<ResultFileDto?>(OpenResultFile);
        RefreshBalanceCommand = new RelayCommand(RefreshBalanceAsync);
        DownloadResultFileCommand = new RelayCommand<ResultFileDto?>(DownloadResultFile);

        // 监听属性变更以刷新命令状态
        PropertyChanged += (_, e) =>
        {
            if (e.PropertyName is nameof(IsProcessing) or nameof(PendingFiles))
                RefreshCommandStates();
            if (e.PropertyName is nameof(TaskStatus))
                RefreshCommandStates();
            if (e.PropertyName is nameof(SelectedFeature))
                OnPropertyChanged(nameof(SelectedFeatureDisplay));
        };

        // 监听待处理列表变更
        PendingFiles.CollectionChanged += (_, _) =>
        {
            OnPropertyChanged(nameof(PendingFileCount));
            OnPropertyChanged(nameof(CanStartProcessing));
            RefreshCommandStates();
        };

        // 监听历史列表变更
        HistoryItems.CollectionChanged += (_, _) =>
        {
            OnPropertyChanged(nameof(HistoryCount));
        };
    }

    /// <summary>默认构造函数（设计时预览）</summary>
    public AiImageToolsViewModel() : this(null, null) { }

    // ========== 文件管理 ==========

    /// <summary>打开文件选择对话框，将选中的图片文件添加到待处理列表</summary>
    private void AddFiles()
    {
        var dialog = new OpenFileDialog
        {
            Title = "选择图片文件",
            Filter = "图片文件|*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tif;*.webp;*.gif|所有文件|*.*",
            Multiselect = true
        };

        if (dialog.ShowDialog() == true)
        {
            foreach (var filePath in dialog.FileNames)
            {
                // 避免重复添加
                if (!PendingFiles.Any(f => f.FilePath == filePath))
                {
                    PendingFiles.Add(new PendingFileItem
                    {
                        FilePath = filePath,
                        FileName = Path.GetFileName(filePath),
                        FileSize = new FileInfo(filePath).Length,
                        AddedAt = DateTime.Now
                    });
                }
            }
            StatusMessage = $"已添加 {dialog.FileNames.Length} 个文件到待处理列表，共 {PendingFiles.Count} 个文件";
        }
    }

    /// <summary>从待处理列表中移除指定文件</summary>
    private void RemoveFile(PendingFileItem? item)
    {
        if (item != null)
            PendingFiles.Remove(item);
    }

    /// <summary>清空待处理列表</summary>
    private void ClearPending()
    {
        PendingFiles.Clear();
        StatusMessage = "待处理列表已清空";
    }

    // ========== 积分余额查询 ==========

    /// <summary>手动刷新积分余额</summary>
    private async void RefreshBalanceAsync()
    {
        if (_cloudApiClient == null)
        {
            StatusMessage = "云端 API 客户端未配置";
            return;
        }

        try
        {
            var response = await _cloudApiClient.GetCreditBalanceAsync();
            if (response?.IsSuccess == true && response.Data != null)
            {
                CurrentBalance = response.Data.Balance;
                CurrentPlanCode = response.Data.PlanId;
                OnPropertyChanged(nameof(BalanceDisplay));
                StatusMessage = $"余额已更新 - 套餐: {CurrentPlanCode}, 余额: {CurrentBalance} 积分";
            }
        }
        catch (Exception ex)
        {
            _logger?.Warning($"刷新余额失败: {ex.Message}", "desktop-ai-image-tools-client");
        }
    }

    // ========== 核心处理逻辑 ==========

    /// <summary>
    /// 开始处理：检查登录、套餐权限、积分余额，然后调用云端接口创建任务。
    /// 只有用户主动点击「开始处理」才会提交任务，不会在添加文件时自动提交。
    /// </summary>
    private async void StartProcessingAsync()
    {
        if (_cloudApiClient == null)
        {
            ErrorMessage = "云端 API 客户端未配置";
            StatusMessage = "处理失败 - API 客户端不可用";
            return;
        }

        // ---- 第1步：检查登录状态 ----
        if (_authState != null && !_authState.IsLoggedIn)
        {
            ErrorMessage = "请先登录后再使用 AI 图片工具功能";
            StatusMessage = "未登录 - 请先登录";
            return;
        }

        // ---- 第2步：检查是否有待处理文件 ----
        if (PendingFiles.Count == 0)
        {
            ErrorMessage = "请先添加需要处理的图片文件";
            return;
        }

        // ---- 第3步：检查功能特定参数 ----
        if (IsEditFeature && string.IsNullOrWhiteSpace(EditPrompt))
        {
            ErrorMessage = "AI 改图需要输入编辑提示词（Prompt）";
            return;
        }

        IsProcessing = true;
        ErrorMessage = null;
        StatusMessage = "正在检查套餐权限和积分余额...";

        _currentCts = new CancellationTokenSource();

        try
        {
            // ---- 第4步：检查套餐权限 ----
            var featureCode = SelectedFeature; // 功能码直接作为 feature code
            var entitlementResponse = await _cloudApiClient.CheckEntitlementAsync(
                featureCode, "single", ct: _currentCts.Token);

            if (entitlementResponse?.IsSuccess == true && entitlementResponse.Data != null)
            {
                if (!entitlementResponse.Data.Allowed)
                {
                    ErrorMessage = $"当前套餐不支持此功能：{entitlementResponse.Data.Reason ?? "权限不足，请升级套餐"}";
                    StatusMessage = "权限不足 - 无法处理";
                    _logger?.Warning(
                        $"AI 图片工具权限检查失败: feature={featureCode}, reason={entitlementResponse.Data.Reason}",
                        "desktop-ai-image-tools-client");
                    return;
                }
            }
            else
            {
                var errMsg = entitlementResponse?.Error?.Message ?? "权限检查服务不可用";
                ErrorMessage = $"权限检查失败：{errMsg}";
                StatusMessage = "服务不可用 - 权限检查失败";
                return;
            }

            // ---- 第5步：检查积分余额 ----
            var balanceResponse = await _cloudApiClient.GetCreditBalanceAsync(ct: _currentCts.Token);
            if (balanceResponse?.IsSuccess == true && balanceResponse.Data != null)
            {
                CurrentBalance = balanceResponse.Data.Balance;
                CurrentPlanCode = balanceResponse.Data.PlanId;
                OnPropertyChanged(nameof(BalanceDisplay));

                if (balanceResponse.Data.Balance <= 0)
                {
                    ErrorMessage = $"积分余额不足（当前余额: {balanceResponse.Data.Balance}），请充值后再使用";
                    StatusMessage = "积分不足 - 无法处理";
                    _logger?.Warning(
                        $"AI 图片工具积分不足: balance={balanceResponse.Data.Balance}, plan={balanceResponse.Data.PlanId}",
                        "desktop-ai-image-tools-client");
                    return;
                }
            }
            else
            {
                var errMsg = balanceResponse?.Error?.Message ?? "积分查询服务不可用";
                ErrorMessage = $"积分查询失败：{errMsg}";
                StatusMessage = "服务不可用 - 积分查询失败";
                return;
            }

            // ---- 第6步：构建 options 参数 ----
            var options = BuildOptions();

            // ---- 第7步：收集输入文件 ID（使用本地路径作为标识，后续需替换为云文件 UUID） ----
            var inputFileIds = PendingFiles
                .Select(f => f.FilePath) // 当前使用本地文件路径作为输入标识
                .ToList();

            // ---- 第8步：调用云端 API 创建任务 ----
            StatusMessage = $"正在创建{SelectedFeatureDisplay}任务...";

            var request = new CreateAiImageToolTaskRequest
            {
                Feature = SelectedFeature,
                InputFileIds = inputFileIds,
                Options = options,
                // client_request_id 由 CloudApiClient 自动填充
            };

            var response = await _cloudApiClient.CreateAiImageToolTaskAsync(request, _currentCts.Token);

            if (response?.IsSuccess == true && response.Data != null)
            {
                var data = response.Data;

                // 更新当前任务状态
                CurrentTaskId = data.TaskId;
                TaskStatus = data.Status;
                TaskFeature = data.Feature;
                EstimatedCredits = data.EstimatedCredits;
                ResultFiles.Clear();
                OcrResultText = string.Empty;

                // 添加到历史记录
                var historyItem = new AiImageToolHistoryItem
                {
                    TaskId = data.TaskId,
                    Feature = SelectedFeature,
                    InputFileNames = PendingFiles.Select(f => f.FileName).ToList(),
                    Status = data.Status,
                    EstimatedCredits = data.EstimatedCredits,
                    CreatedAt = DateTime.Now,
                    RequestId = response.RequestId ?? string.Empty
                };

                // 在 UI 线程添加历史记录（测试环境中直接添加）
                if (System.Windows.Application.Current?.Dispatcher != null)
                    System.Windows.Application.Current.Dispatcher.Invoke(() =>
                        HistoryItems.Insert(0, historyItem));
                else
                    HistoryItems.Insert(0, historyItem);

                StatusMessage = $"任务已创建 - ID: {data.TaskId[..8]}..., 预估消耗 {data.EstimatedCredits} 额度";
                _logger?.Info(
                    $"AI 图片工具任务创建成功: task_id={data.TaskId}, feature={SelectedFeature}, " +
                    $"file_count={PendingFiles.Count}, status={data.Status}",
                    "desktop-ai-image-tools-client");

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
                    $"AI 图片工具任务创建失败: code={errCode}, message={errMsg}",
                    "desktop-ai-image-tools-client");
            }
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "处理已取消";
            _logger?.Info("AI 图片工具处理已取消", "desktop-ai-image-tools-client");
        }
        catch (Exception ex)
        {
            ErrorMessage = $"处理失败: {ex.Message}";
            StatusMessage = "处理出错，请查看错误信息";
            _logger?.Error($"AI 图片工具处理异常: {ex.Message}", ex, "desktop-ai-image-tools-client");
        }
        finally
        {
            IsProcessing = false;
            _currentCts?.Dispose();
            _currentCts = null;
            RefreshCommandStates();
        }
    }

    /// <summary>根据当前选择的功能构建 options 字典</summary>
    private Dictionary<string, object>? BuildOptions()
    {
        return SelectedFeature switch
        {
            "upscale_image_cloud" => new Dictionary<string, object>
            {
                ["scale_factor"] = UpscaleFactor
            },
            "vectorize_image_cloud" => new Dictionary<string, object>
            {
                ["output_format"] = VectorOutputFormat
            },
            "ai_edit_image_cloud" => new Dictionary<string, object>
            {
                ["prompt"] = EditPrompt.Trim()
            },
            "ocr_cloud" => new Dictionary<string, object>
            {
                ["language"] = OcrLanguage
            },
            _ => null
        };
    }

    // ========== 任务状态查询 ==========

    /// <summary>手动刷新当前任务状态</summary>
    private async void RefreshStatusAsync()
    {
        if (_cloudApiClient == null || string.IsNullOrEmpty(CurrentTaskId)) return;
        await QueryAndUpdateTaskStatus(CurrentTaskId);
    }

    /// <summary>查询指定任务 ID 的状态并更新 ViewModel 属性</summary>
    private async Task QueryAndUpdateTaskStatus(string taskId)
    {
        if (_cloudApiClient == null) return;

        try
        {
            var response = await _cloudApiClient.GetAiImageToolTaskAsync(taskId);

            if (response?.IsSuccess == true && response.Data != null)
            {
                var data = response.Data;

                var previousStatus = TaskStatus;
                TaskStatus = data.Status;
                TaskFeature = data.Feature;

                // 更新结果文件
                ResultFiles.Clear();
                if (data.ResultFiles != null)
                {
                    foreach (var file in data.ResultFiles)
                        ResultFiles.Add(file);
                }

                // 更新 OCR 文本结果（保留排版，多行展示）
                if (data.ResultJson != null)
                {
                    // 优先处理 text_lines 格式（后端返回的结构化 OCR 结果）
                    if (data.ResultJson.TryGetValue("text_lines", out var textLinesObj) &&
                        textLinesObj is System.Text.Json.JsonElement textLinesElement &&
                        textLinesElement.ValueKind == System.Text.Json.JsonValueKind.Array)
                    {
                        var lines = new List<string>();
                        foreach (var line in textLinesElement.EnumerateArray())
                        {
                            if (line.TryGetProperty("text", out var lineText))
                                lines.Add(lineText.GetString() ?? string.Empty);
                        }
                        OcrResultText = string.Join(Environment.NewLine, lines);
                    }
                    // 兼容其他格式：单个 text 字段
                    else if (data.ResultJson.TryGetValue("text", out var textObj) && textObj is System.Text.Json.JsonElement textElem &&
                             textElem.ValueKind == System.Text.Json.JsonValueKind.String)
                    {
                        OcrResultText = textElem.GetString() ?? string.Empty;
                    }
                    else if (data.ResultJson.TryGetValue("text", out var textStrObj) && textStrObj is string textStr)
                    {
                        OcrResultText = textStr;
                    }
                    // 兼容 full_text 格式
                    else if (data.ResultJson.TryGetValue("full_text", out var fullTextObj) && fullTextObj is System.Text.Json.JsonElement fullTextElem &&
                             fullTextElem.ValueKind == System.Text.Json.JsonValueKind.String)
                    {
                        OcrResultText = fullTextElem.GetString() ?? string.Empty;
                    }
                    else if (data.ResultJson.TryGetValue("full_text", out var fullTextStrObj) && fullTextStrObj is string fullTextStr)
                    {
                        OcrResultText = fullTextStr;
                    }
                    // 兼容 content 格式
                    else if (data.ResultJson.TryGetValue("content", out var contentObj) && contentObj is System.Text.Json.JsonElement contentElem &&
                             contentElem.ValueKind == System.Text.Json.JsonValueKind.String)
                    {
                        OcrResultText = contentElem.GetString() ?? string.Empty;
                    }
                    else if (data.ResultJson.TryGetValue("content", out var contentStrObj) && contentStrObj is string contentStr)
                    {
                        OcrResultText = contentStr;
                    }
                }

                // 更新 Provider 信息
                Provider = data.Provider ?? string.Empty;
                Model = data.Model ?? string.Empty;
                EstimatedCost = data.EstimatedCost ?? 0;
                CreditsCharged = data.CreditsCharged ?? 0;
                ProviderCallId = data.ProviderCallId ?? string.Empty;

                // 更新历史记录
                var historyItem = HistoryItems.FirstOrDefault(h => h.TaskId == taskId);
                if (historyItem != null)
                {
                    historyItem.Status = data.Status;
                    historyItem.Provider = data.Provider ?? string.Empty;
                    historyItem.Model = data.Model ?? string.Empty;
                    historyItem.CreditsCharged = data.CreditsCharged ?? 0;
                    // 触发 UI 刷新
                    var index = HistoryItems.IndexOf(historyItem);
                    if (index >= 0)
                    {
                        HistoryItems.RemoveAt(index);
                        HistoryItems.Insert(index, historyItem);
                    }
                }

                // 任务终态处理
                if (data.Status is "succeeded" or "failed")
                {
                    StopPolling();

                    if (data.Status == "succeeded")
                    {
                        StatusMessage = $"处理成功 - 使用 {data.Provider}/{data.Model}，扣除 {data.CreditsCharged} 额度";
                        OnPropertyChanged(nameof(ShowOcrResult));
                        OnPropertyChanged(nameof(ShowBeforeAfter));
                        _logger?.Info(
                            $"AI 图片工具任务完成: task_id={taskId}, feature={data.Feature}, " +
                            $"credits_charged={data.CreditsCharged}",
                            "desktop-ai-image-tools-client");
                    }
                    else
                    {
                        StatusMessage = $"任务失败 - {taskId[..8]}...";
                        _logger?.Warning(
                            $"AI 图片工具任务失败: task_id={taskId}",
                            "desktop-ai-image-tools-client");
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
                $"查询 AI 图片工具任务状态异常: task_id={taskId}, error={ex.Message}",
                "desktop-ai-image-tools-client");
        }
    }

    // ========== 任务状态轮询 ==========

    /// <summary>启动定时轮询（每 3 秒）</summary>
    private void StartPolling()
    {
        StopPolling();

        _pollingTimer = new Timer(3000);
        _pollingTimer.Elapsed += OnPollingTimerElapsed;
        _pollingTimer.AutoReset = true;
        _pollingTimer.Start();

        OnPropertyChanged(nameof(IsPolling));
    }

    /// <summary>停止轮询</summary>
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

    /// <summary>轮询回调：在 UI 线程上查询任务状态</summary>
    private async void OnPollingTimerElapsed(object? sender, ElapsedEventArgs e)
    {
        if (System.Windows.Application.Current?.Dispatcher != null)
        {
            await System.Windows.Application.Current.Dispatcher.InvokeAsync(
                async () => await QueryAndUpdateTaskStatus(CurrentTaskId));
        }
    }

    // ========== 辅助操作 ==========

    /// <summary>清除当前输入和结果</summary>
    private void Clear()
    {
        StopPolling();

        SelectedFeature = "upscale_image_cloud";
        EditPrompt = string.Empty;
        VectorOutputFormat = "svg";
        OcrLanguage = "auto";
        UpscaleFactor = 2;

        PendingFiles.Clear();
        CurrentTaskId = string.Empty;
        TaskStatus = string.Empty;
        TaskFeature = string.Empty;
        ResultFiles.Clear();
        OcrResultText = string.Empty;
        Provider = string.Empty;
        Model = string.Empty;
        EstimatedCost = 0;
        CreditsCharged = 0;
        EstimatedCredits = 0;
        ProviderCallId = string.Empty;

        ErrorMessage = null;
        StatusMessage = "就绪 - 选择功能类型和图片后点击「开始处理」";
        RefreshCommandStates();
    }

    /// <summary>选择历史记录项，恢复对应任务到当前视图</summary>
    private void SelectHistoryItem(AiImageToolHistoryItem? item)
    {
        if (item == null) return;

        StopPolling();

        CurrentTaskId = item.TaskId;
        SelectedFeature = item.Feature;
        TaskStatus = item.Status;
        TaskFeature = item.Feature;
        Provider = item.Provider;
        Model = item.Model;
        CreditsCharged = item.CreditsCharged;
        ResultFiles.Clear();
        OcrResultText = string.Empty;

        StatusMessage = $"已加载历史任务 - {item.FeatureDisplay} / {item.TaskId[..8]}...";

        // 如果历史任务仍处于进行中状态，可继续轮询
        if (item.Status is "queued" or "running")
        {
            _ = QueryAndUpdateTaskStatus(item.TaskId);
        }
    }

    /// <summary>在浏览器中打开结果文件</summary>
    private void OpenResultFile(ResultFileDto? file)
    {
        if (file == null || string.IsNullOrWhiteSpace(file.Url)) return;

        try
        {
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = file.Url,
                UseShellExecute = true
            });
            StatusMessage = $"正在打开结果文件: {file.FileId}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"打开文件失败: {ex.Message}";
        }
    }

    /// <summary>下载结果文件到本地</summary>
    private void DownloadResultFile(ResultFileDto? file)
    {
        if (file == null || string.IsNullOrWhiteSpace(file.Url))
        {
            StatusMessage = "无法下载：文件 URL 为空";
            return;
        }

        try
        {
            var dialog = new SaveFileDialog
            {
                Title = "保存结果文件",
                FileName = $"{file.FileId}_{DateTime.Now:yyyyMMddHHmmss}",
                DefaultExt = file.MimeType switch
                {
                    "image/png" => ".png",
                    "image/jpeg" => ".jpg",
                    "image/svg+xml" => ".svg",
                    "application/pdf" => ".pdf",
                    "application/postscript" => ".eps",
                    _ => ".bin"
                }
            };

            if (dialog.ShowDialog() == true)
            {
                // 使用 Process.Start 下载（简化实现，生产环境应使用 HttpClient 下载）
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = file.Url,
                    UseShellExecute = true
                });
                StatusMessage = $"已触发下载: {Path.GetFileName(dialog.FileName)}";
            }
        }
        catch (Exception ex)
        {
            StatusMessage = $"下载失败: {ex.Message}";
        }
    }

    // ========== 工具方法 ==========

    /// <summary>刷新命令可执行状态</summary>
    private void RefreshCommandStates()
    {
        (StartProcessingCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (RefreshStatusCommand as RelayCommand)?.RaiseCanExecuteChanged();
        OnPropertyChanged(nameof(CanStartProcessing));
        OnPropertyChanged(nameof(CanRefreshStatus));
    }
}

/// <summary>
/// 待处理文件项
/// 代表用户选择但尚未提交处理的本地图片文件
/// </summary>
public class PendingFileItem
{
    /// <summary>文件完整路径</summary>
    public string FilePath { get; set; } = string.Empty;

    /// <summary>文件名（含扩展名）</summary>
    public string FileName { get; set; } = string.Empty;

    /// <summary>文件大小（字节）</summary>
    public long FileSize { get; set; }

    /// <summary>添加时间</summary>
    public DateTime AddedAt { get; set; } = DateTime.Now;

    /// <summary>文件大小展示（人类可读）</summary>
    public string FileSizeDisplay
    {
        get
        {
            if (FileSize < 1024) return $"{FileSize} B";
            if (FileSize < 1024 * 1024) return $"{FileSize / 1024.0:F1} KB";
            return $"{FileSize / (1024.0 * 1024.0):F1} MB";
        }
    }

    /// <summary>添加时间展示</summary>
    public string AddedAtDisplay => AddedAt.ToString("HH:mm:ss");
}

/// <summary>
/// AI 图片工具任务历史记录项
/// </summary>
public class AiImageToolHistoryItem
{
    /// <summary>任务 ID</summary>
    public string TaskId { get; set; } = string.Empty;

    /// <summary>功能码</summary>
    public string Feature { get; set; } = string.Empty;

    /// <summary>输入文件名列表</summary>
    public List<string> InputFileNames { get; set; } = new();

    /// <summary>任务状态</summary>
    public string Status { get; set; } = string.Empty;

    /// <summary>使用的 Provider</summary>
    public string Provider { get; set; } = string.Empty;

    /// <summary>使用的模型</summary>
    public string Model { get; set; } = string.Empty;

    /// <summary>预估消耗额度</summary>
    public int EstimatedCredits { get; set; }

    /// <summary>实际扣除额度</summary>
    public int CreditsCharged { get; set; }

    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; set; } = DateTime.Now;

    /// <summary>云端请求 ID</summary>
    public string RequestId { get; set; } = string.Empty;

    /// <summary>功能展示名称（中文）</summary>
    public string FeatureDisplay
    {
        get
        {
            var entry = AiImageToolsViewModel.FeatureList.FirstOrDefault(f => f.Value == Feature);
            return entry != default ? entry.Display : Feature;
        }
    }

    /// <summary>状态展示名称（中文）</summary>
    public string StatusDisplay => Status switch
    {
        "queued" => "排队中",
        "running" => "处理中",
        "succeeded" => "已完成",
        "failed" => "失败",
        _ => Status
    };

    /// <summary>状态颜色</summary>
    public string StatusColor => Status switch
    {
        "succeeded" => "#38A169",
        "failed" => "#E53E3E",
        "running" => "#3182CE",
        "queued" => "#D69E2E",
        _ => "#718096"
    };

    /// <summary>输入文件摘要</summary>
    public string InputFilesSummary
        => InputFileNames.Count > 0
            ? string.Join(", ", InputFileNames.Take(3)) + (InputFileNames.Count > 3 ? $" 等 {InputFileNames.Count} 个文件" : "")
            : "(无文件)";

    /// <summary>时间展示</summary>
    public string TimeDisplay => CreatedAt.ToString("HH:mm:ss");

    /// <summary>费用摘要</summary>
    public string CostSummary => CreditsCharged > 0
        ? $"-{CreditsCharged} 额度 / {Provider}/{Model}"
        : $"预估 {EstimatedCredits} 额度";
}
