using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Input;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;
using TTShared.Logging;
using TTShared.UI;

namespace TTTools.AiCopyClient.ViewModels;

/// <summary>
/// 下拉选项条目（WPF 绑定需要真实属性，不能用 named ValueTuple）
/// </summary>
public record ComboOption(string Value, string Display);

/// <summary>
/// 云端文案生成模块主 ViewModel
/// 管理文案生成请求参数、调用 CloudApiClient.GenerateAiCopyAsync、展示结果和扣费信息。
/// 本模块不直接调用第三方 AI，全部通过云端 provider-runtime 完成。
/// </summary>
public class AiCopyViewModel : BaseViewModel
{
    private readonly CloudApiClient? _cloudApiClient;
    private readonly AuthState? _authState;
    private readonly AppLogger? _logger;

    private bool _isRunning;
    private string _statusMessage = "就绪 - 填写文案需求后点击生成";
    private string? _errorMessage;
    private CancellationTokenSource? _currentCts;

    // ---- 输入参数 ----
    private string _selectedScene = "poster";
    private string _productName = string.Empty;
    private string _targetAudience = string.Empty;
    private string _selectedTone = "direct";
    private string _selectedPlatform = "offline_poster";
    private string _extraRequirements = string.Empty;
    private string _newSellingPoint = string.Empty;

    // ---- 预估信息 ----
    private int _estimatedMinCredits;
    private int _estimatedMaxCredits;
    private string _estimatedLatency = string.Empty;
    private string _estimateSummary = string.Empty;

    // ---- 生成结果 ----
    private string _generatedText = string.Empty;
    private string _selectedVariant = string.Empty;
    private string _provider = string.Empty;
    private string _model = string.Empty;
    private decimal _estimatedCost;
    private int _creditsCharged;
    private string _providerCallId = string.Empty;

    /// <summary>已生成的文案历史列表</summary>
    public ObservableCollection<AiCopyHistoryItem> HistoryItems { get; } = new();

    /// <summary>当前卖点列表（可编辑）</summary>
    public ObservableCollection<string> SellingPoints { get; } = new();

    /// <summary>生成的文案变体列表</summary>
    public ObservableCollection<string> Variants { get; } = new();

    // ---- 预设数据 ----

    /// <summary>可用的场景列表（中文名称）</summary>
    public static List<ComboOption> SceneList { get; } = new()
    {
        new("poster", "海报 / 宣传单"),
        new("flyer", "传单 / 折页"),
        new("social_media", "社交媒体通用"),
        new("wechat", "微信朋友圈 / 公众号"),
        new("xiaohongshu", "小红书"),
        new("douyin", "抖音"),
        new("email", "邮件营销"),
        new("website", "网站 / 落地页"),
    };

    /// <summary>可用的语气列表（中文名称）</summary>
    public static List<ComboOption> ToneList { get; } = new()
    {
        new("direct", "直接有力 - 强调行动号召"),
        new("professional", "专业正式 - 适合 B2B 场景"),
        new("friendly", "亲切友好 - 拉近客户距离"),
        new("humorous", "幽默风趣 - 轻松有趣"),
        new("urgent", "紧迫促销 - 限时特惠"),
        new("warm", "温暖走心 - 情感共鸣"),
    };

    /// <summary>可用的平台列表（中文名称）</summary>
    public static List<ComboOption> PlatformList { get; } = new()
    {
        new("offline_poster", "线下海报 / 印刷品"),
        new("wechat_moment", "微信朋友圈"),
        new("xiaohongshu", "小红书"),
        new("douyin", "抖音"),
        new("weibo", "微博"),
        new("email", "邮件"),
        new("website", "网站"),
        new("print", "印刷物料"),
    };

    // ========== 输入属性 ==========

    /// <summary>当前选择的场景类型</summary>
    public string SelectedScene
    {
        get => _selectedScene;
        set => SetProperty(ref _selectedScene, value);
    }

    /// <summary>产品名称 / 服务名称</summary>
    public string ProductName
    {
        get => _productName;
        set => SetProperty(ref _productName, value);
    }

    /// <summary>目标受众</summary>
    public string TargetAudience
    {
        get => _targetAudience;
        set => SetProperty(ref _targetAudience, value);
    }

    /// <summary>当前选择的语气</summary>
    public string SelectedTone
    {
        get => _selectedTone;
        set => SetProperty(ref _selectedTone, value);
    }

    /// <summary>当前选择的发布平台</summary>
    public string SelectedPlatform
    {
        get => _selectedPlatform;
        set => SetProperty(ref _selectedPlatform, value);
    }

    /// <summary>额外需求（自由文本）</summary>
    public string ExtraRequirements
    {
        get => _extraRequirements;
        set => SetProperty(ref _extraRequirements, value);
    }

    /// <summary>新增卖点的临时文本</summary>
    public string NewSellingPoint
    {
        get => _newSellingPoint;
        set => SetProperty(ref _newSellingPoint, value);
    }

    // ========== 结果属性 ==========

    /// <summary>生成的主文案</summary>
    public string GeneratedText
    {
        get => _generatedText;
        set
        {
            if (SetProperty(ref _generatedText, value))
            {
                OnPropertyChanged(nameof(HasGeneratedText));
                OnPropertyChanged(nameof(HasResult));
            }
        }
    }

    /// <summary>当前选中的变体文案（用于预览区展示）</summary>
    public string SelectedVariant
    {
        get => _selectedVariant;
        set => SetProperty(ref _selectedVariant, value);
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

    /// <summary>是否有生成结果</summary>
    public bool HasResult => !string.IsNullOrEmpty(GeneratedText);

    /// <summary>是否有生成的文案文本（用于复制按钮）</summary>
    public bool HasGeneratedText => !string.IsNullOrEmpty(GeneratedText);

    /// <summary>预估最小扣点</summary>
    public int EstimatedMinCredits
    {
        get => _estimatedMinCredits;
        set => SetProperty(ref _estimatedMinCredits, value);
    }

    /// <summary>预估最大扣点</summary>
    public int EstimatedMaxCredits
    {
        get => _estimatedMaxCredits;
        set => SetProperty(ref _estimatedMaxCredits, value);
    }

    /// <summary>预估耗时显示文本</summary>
    public string EstimatedLatency
    {
        get => _estimatedLatency;
        set => SetProperty(ref _estimatedLatency, value);
    }

    /// <summary>预估摘要（完整展示文本）</summary>
    public string EstimateSummary
    {
        get => _estimateSummary;
        set => SetProperty(ref _estimateSummary, value);
    }

    /// <summary>是否有预估信息可展示</summary>
    public bool HasEstimate => !string.IsNullOrEmpty(EstimateSummary);

    /// <summary>是否正在调用云端生成</summary>
    public bool IsRunning
    {
        get => _isRunning;
        set
        {
            if (SetProperty(ref _isRunning, value))
            {
                OnPropertyChanged(nameof(CanGenerate));
                OnPropertyChanged(nameof(CanCancel));
            }
        }
    }

    /// <summary>是否可以生成</summary>
    public bool CanGenerate => !IsRunning && !string.IsNullOrWhiteSpace(ProductName);

    /// <summary>是否可以取消</summary>
    public bool CanCancel => IsRunning;

    /// <summary>是否有卖点</summary>
    public bool HasSellingPoints => SellingPoints.Count > 0;

    /// <summary>是否可以添加当前卖点</summary>
    public bool CanAddSellingPoint => !string.IsNullOrWhiteSpace(NewSellingPoint);

    /// <summary>历史记录数量</summary>
    public int HistoryCount => HistoryItems.Count;

    // ========== 命令 ==========

    public ICommand GenerateCommand { get; }
    public ICommand CancelCommand { get; }
    public ICommand ClearCommand { get; }
    public ICommand CopyTextCommand { get; }
    public ICommand AddSellingPointCommand { get; }
    public ICommand RemoveSellingPointCommand { get; }
    public ICommand SelectHistoryItemCommand { get; }
    public ICommand SelectVariantCommand { get; }

    public AiCopyViewModel(
        CloudApiClient? cloudApiClient,
        AuthState? authState,
        AppLogger? logger = null)
    {
        _cloudApiClient = cloudApiClient;
        _authState = authState;
        _logger = logger;

        // 初始化命令
        GenerateCommand = new RelayCommand(GenerateAsync, () => CanGenerate);
        CancelCommand = new RelayCommand(Cancel, () => CanCancel);
        ClearCommand = new RelayCommand(Clear);
        CopyTextCommand = new RelayCommand(CopyText, () => HasGeneratedText);
        AddSellingPointCommand = new RelayCommand(AddSellingPoint, () => CanAddSellingPoint);
        RemoveSellingPointCommand = new RelayCommand<string>(RemoveSellingPoint);
        SelectHistoryItemCommand = new RelayCommand<AiCopyHistoryItem?>(SelectHistoryItem);
        SelectVariantCommand = new RelayCommand<string?>(v =>
        {
            if (v != null) SelectedVariant = v;
        });

        // 监听属性变更以刷新命令状态
        PropertyChanged += (_, e) =>
        {
            if (e.PropertyName is nameof(ProductName) or nameof(IsRunning))
                RefreshCommandStates();
            if (e.PropertyName is nameof(NewSellingPoint))
                RefreshCommandStates();
            if (e.PropertyName is nameof(GeneratedText))
                RefreshCommandStates();
        };

        // 监听卖点列表变更
        SellingPoints.CollectionChanged += (_, _) =>
        {
            OnPropertyChanged(nameof(HasSellingPoints));
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
    public AiCopyViewModel() : this(null, null) { }

    // ========== 卖点管理 ==========

    /// <summary>
    /// 添加当前输入的卖点到列表
    /// </summary>
    private void AddSellingPoint()
    {
        var text = NewSellingPoint?.Trim();
        if (string.IsNullOrWhiteSpace(text)) return;

        // 避免重复添加
        if (!SellingPoints.Contains(text))
        {
            SellingPoints.Add(text);
        }
        NewSellingPoint = string.Empty;
    }

    /// <summary>
    /// 从列表移除指定卖点
    /// </summary>
    private void RemoveSellingPoint(string? sellingPoint)
    {
        if (sellingPoint != null && SellingPoints.Contains(sellingPoint))
            SellingPoints.Remove(sellingPoint);
    }

    // ========== 核心生成逻辑 ==========

    /// <summary>
    /// 调用云端 API 生成文案。
    /// 客户端只提交场景、产品名称、卖点等业务参数，不提交 user_id、plan_code、provider、model 等决策字段。
    /// </summary>
    private async void GenerateAsync()
    {
        if (_cloudApiClient == null)
        {
            ErrorMessage = "云端 API 客户端未配置";
            StatusMessage = "生成失败 - API 客户端不可用";
            return;
        }

        // 检查登录状态
        if (_authState != null && !_authState.IsLoggedIn)
        {
            ErrorMessage = "请先登录后再使用文案生成功能";
            StatusMessage = "未登录 - 请先登录";
            return;
        }

        // 校验必填字段
        if (string.IsNullOrWhiteSpace(ProductName))
        {
            ErrorMessage = "请输入产品名称或服务名称";
            return;
        }

        IsRunning = true;
        ErrorMessage = null;
        StatusMessage = "正在获取预估...";

        _currentCts = new CancellationTokenSource();

        try
        {
            // 先调预估接口
            try
            {
                var estResp = await _cloudApiClient.EstimateAiCopyAsync(new AiCopyEstimateRequest
                {
                    Scene = SelectedScene,
                    ProductName = ProductName.Trim(),
                    SellingPoints = SellingPoints.ToList(),
                    ClientRequestId = Guid.NewGuid().ToString(),
                }, _currentCts.Token);
                if (estResp?.IsSuccess == true && estResp.Data != null)
                {
                    EstimatedMinCredits = estResp.Data.MinCredits;
                    EstimatedMaxCredits = estResp.Data.EstimatedMaxCredits;
                    EstimatedLatency = estResp.Data.EstimatedLatency?.Display ?? "";
                    EstimateSummary = $"预计消耗 {EstimatedMinCredits}-{EstimatedMaxCredits} 点"
                        + (string.IsNullOrEmpty(EstimatedLatency) ? "" : $" · {EstimatedLatency}");
                    StatusMessage = EstimateSummary;
                }
            }
            catch { /* 预估失败不阻塞 */ }

            // 构建请求（严格对应 OpenAPI ai-copy.yaml 定义的字段）
            var request = new AiCopyGenerateRequest
            {
                Scene = SelectedScene,
                ProductName = ProductName.Trim(),
                SellingPoints = SellingPoints.ToList(),
                TargetAudience = string.IsNullOrWhiteSpace(TargetAudience) ? null : TargetAudience.Trim(),
                Tone = SelectedTone,
                Platform = string.IsNullOrWhiteSpace(SelectedPlatform) ? null : SelectedPlatform,
                ExtraRequirements = string.IsNullOrWhiteSpace(ExtraRequirements) ? null : ExtraRequirements.Trim(),
                // client_request_id 由 CloudApiClient 自动填充
            };

            var response = await _cloudApiClient.GenerateAiCopyAsync(request, _currentCts.Token);

            if (response?.IsSuccess == true && response.Data != null)
            {
                var data = response.Data;

                // 更新结果展示
                GeneratedText = data.Text;
                Variants.Clear();
                if (data.Variants != null)
                {
                    foreach (var v in data.Variants)
                        Variants.Add(v);
                }

                Provider = data.Provider;
                Model = data.Model;
                EstimatedCost = data.EstimatedCost;
                CreditsCharged = data.CreditsCharged;
                ProviderCallId = data.ProviderCallId;

                // 保存到历史记录
                var historyItem = new AiCopyHistoryItem
                {
                    Scene = SelectedScene,
                    ProductName = ProductName.Trim(),
                    GeneratedText = data.Text,
                    Provider = data.Provider,
                    Model = data.Model,
                    CreditsCharged = data.CreditsCharged,
                    CreatedAt = DateTime.Now,
                    RequestId = response.RequestId ?? string.Empty
                };

                // UI 线程添加历史记录
                System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                    HistoryItems.Insert(0, historyItem));

                StatusMessage = $"生成成功 - 使用 {data.Provider}/{data.Model}，扣除 {data.CreditsCharged} 额度";
                _logger?.Info(
                    $"文案生成成功: scene={SelectedScene}, provider={data.Provider}, model={data.Model}, " +
                    $"credits_charged={data.CreditsCharged}, request_id={response.RequestId}",
                    "desktop-ai-copy-client");
            }
            else
            {
                var errCode = response?.Error?.Code ?? "unknown";
                var errMsg = response?.Error?.Message ?? "未知错误";

                ErrorMessage = $"[{errCode}] {errMsg}";
                StatusMessage = $"生成失败 - {errCode}";
                _logger?.Warning(
                    $"文案生成失败: code={errCode}, message={errMsg}",
                    "desktop-ai-copy-client");
            }
        }
        catch (OperationCanceledException)
        {
            StatusMessage = "生成已取消";
            _logger?.Info("文案生成已取消", "desktop-ai-copy-client");
        }
        catch (Exception ex)
        {
            ErrorMessage = $"生成失败: {ex.Message}";
            StatusMessage = "生成出错，请查看错误信息";
            _logger?.Error($"文案生成异常: {ex.Message}", ex, "desktop-ai-copy-client");
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
    /// 取消当前生成请求
    /// </summary>
    private void Cancel()
    {
        _currentCts?.Cancel();
        StatusMessage = "正在取消...";
    }

    /// <summary>
    /// 清除当前输入和结果
    /// </summary>
    private void Clear()
    {
        ProductName = string.Empty;
        TargetAudience = string.Empty;
        ExtraRequirements = string.Empty;
        NewSellingPoint = string.Empty;
        SellingPoints.Clear();
        SelectedScene = "poster";
        SelectedTone = "direct";
        SelectedPlatform = "offline_poster";

        GeneratedText = string.Empty;
        Variants.Clear();
        SelectedVariant = string.Empty;
        Provider = string.Empty;
        Model = string.Empty;
        EstimatedCost = 0;
        CreditsCharged = 0;
        ProviderCallId = string.Empty;

        ErrorMessage = null;
        StatusMessage = "就绪 - 填写文案需求后点击生成";
        RefreshCommandStates();
    }

    /// <summary>
    /// 将当前生成的文案复制到剪贴板
    /// </summary>
    private void CopyText()
    {
        var textToCopy = !string.IsNullOrWhiteSpace(SelectedVariant)
            ? SelectedVariant
            : GeneratedText;

        if (string.IsNullOrWhiteSpace(textToCopy)) return;

        try
        {
            Clipboard.SetText(textToCopy);
            StatusMessage = "文案已复制到剪贴板";
        }
        catch (Exception ex)
        {
            StatusMessage = $"复制失败: {ex.Message}";
        }
    }

    /// <summary>
    /// 选择历史记录项，恢复对应结果到当前视图
    /// </summary>
    private void SelectHistoryItem(AiCopyHistoryItem? item)
    {
        if (item == null) return;

        GeneratedText = item.GeneratedText;
        Provider = item.Provider;
        Model = item.Model;
        CreditsCharged = item.CreditsCharged;
        Variants.Clear();
        StatusMessage = $"已加载历史记录 - {item.SceneDisplay} / {item.ProductName}";
    }

    /// <summary>
    /// 刷新命令可执行状态
    /// </summary>
    private void RefreshCommandStates()
    {
        (GenerateCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (CancelCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (CopyTextCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (AddSellingPointCommand as RelayCommand)?.RaiseCanExecuteChanged();

        OnPropertyChanged(nameof(CanGenerate));
        OnPropertyChanged(nameof(CanCancel));
        OnPropertyChanged(nameof(CanAddSellingPoint));
        OnPropertyChanged(nameof(HasResult));
        OnPropertyChanged(nameof(HasGeneratedText));
    }
}

/// <summary>
/// 文案生成历史记录项
/// 用于在历史列表中展示已生成文案的摘要信息
/// </summary>
public class AiCopyHistoryItem
{
    /// <summary>场景代码</summary>
    public string Scene { get; set; } = string.Empty;

    /// <summary>产品名称</summary>
    public string ProductName { get; set; } = string.Empty;

    /// <summary>生成的文案</summary>
    public string GeneratedText { get; set; } = string.Empty;

    /// <summary>使用的 Provider</summary>
    public string Provider { get; set; } = string.Empty;

    /// <summary>使用的模型</summary>
    public string Model { get; set; } = string.Empty;

    /// <summary>扣除的 AI 额度</summary>
    public int CreditsCharged { get; set; }

    /// <summary>生成时间</summary>
    public DateTime CreatedAt { get; set; } = DateTime.Now;

    /// <summary>云端请求 ID</summary>
    public string RequestId { get; set; } = string.Empty;

    /// <summary>场景展示名称（中文）</summary>
    public string SceneDisplay
    {
        get
        {
            var sceneEntry = AiCopyViewModel.SceneList.FirstOrDefault(s => s.Value == Scene);
            return sceneEntry != default ? sceneEntry.Display : Scene;
        }
    }

    /// <summary>文案摘要（截取前 50 字）</summary>
    public string TextSummary
    {
        get
        {
            if (string.IsNullOrWhiteSpace(GeneratedText)) return "(空)";
            return GeneratedText.Length > 50
                ? GeneratedText[..50] + "..."
                : GeneratedText;
        }
    }

    /// <summary>格式化时间显示</summary>
    public string TimeDisplay => CreatedAt.ToString("HH:mm:ss");

    /// <summary>扣费摘要</summary>
    public string CostSummary => $"-{CreditsCharged} 额度 / {Provider}/{Model}";
}
