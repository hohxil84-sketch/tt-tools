using System.Windows.Input;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.Settings;
using TTShared.UI;

namespace TTTools.AuthDevice.ViewModels;

/// <summary>
/// 设备绑定状态展示 ViewModel
/// 显示当前设备的绑定信息（设备名、状态、绑定时间、最近活跃时间）。
/// 依赖 AuthState 获取当前设备信息，通过 CloudApiClient 拉取最新状态。
/// </summary>
public class DeviceStatusViewModel : BaseViewModel
{
    private readonly AuthState _authState;
    private readonly CloudApiClient _apiClient;
    private string _deviceId = string.Empty;
    private string _deviceName = string.Empty;
    private string _status = "unknown";
    private string? _boundAt;
    private string? _lastSeenAt;
    private bool _isLoading;
    private string? _errorMessage;

    /// <summary>设备 ID</summary>
    public string DeviceId
    {
        get => _deviceId;
        set => SetProperty(ref _deviceId, value);
    }

    /// <summary>设备名称</summary>
    public string DeviceName
    {
        get => _deviceName;
        set => SetProperty(ref _deviceName, value);
    }

    /// <summary>设备状态：active / blocked / removed</summary>
    public string Status
    {
        get => _status;
        set
        {
            if (SetProperty(ref _status, value))
            {
                OnPropertyChanged(nameof(IsBound));
                OnPropertyChanged(nameof(StatusDisplay));
            }
        }
    }

    /// <summary>设备绑定时间（UTC ISO 字符串）</summary>
    public string? BoundAt
    {
        get => _boundAt;
        set => SetProperty(ref _boundAt, value);
    }

    /// <summary>设备最近活跃时间（UTC ISO 字符串）</summary>
    public string? LastSeenAt
    {
        get => _lastSeenAt;
        set => SetProperty(ref _lastSeenAt, value);
    }

    /// <summary>是否正在加载设备状态</summary>
    public bool IsLoading
    {
        get => _isLoading;
        set => SetProperty(ref _isLoading, value);
    }

    /// <summary>错误消息</summary>
    public string? ErrorMessage
    {
        get => _errorMessage;
        set => SetProperty(ref _errorMessage, value);
    }

    /// <summary>设备是否已绑定（status 为 active 时视为已绑定）</summary>
    public bool IsBound => Status == "active";

    /// <summary>状态的中文展示文本</summary>
    public string StatusDisplay => Status switch
    {
        "active" => "已绑定",
        "blocked" => "已禁用",
        "removed" => "已移除",
        _ => "未知"
    };

    /// <summary>刷新设备状态命令</summary>
    public ICommand RefreshCommand { get; }

    /// <summary>
    /// 构造函数，注入 AuthState 和 CloudApiClient 依赖
    /// </summary>
    public DeviceStatusViewModel(AuthState authState, CloudApiClient apiClient)
    {
        _authState = authState ?? throw new ArgumentNullException(nameof(authState));
        _apiClient = apiClient ?? throw new ArgumentNullException(nameof(apiClient));

        RefreshCommand = new AsyncRelayCommand(async () => await RefreshDeviceStatusAsync());

        // 订阅 AuthState 的登录和登出事件，自动更新设备信息
        _authState.LoggedIn += (_, _) => _ = RefreshDeviceStatusAsync();
        _authState.LoggedOut += (_, _) => ClearDeviceInfo();
        _authState.PropertyChanged += (_, e) =>
        {
            if (e.PropertyName == nameof(AuthState.Device))
                UpdateFromLocalDevice();
        };

        // 启动时如果已登录，从本地 AuthState 读取已有设备信息
        if (_authState.IsLoggedIn)
        {
            UpdateFromLocalDevice();
        }
    }

    /// <summary>
    /// 默认构造函数，使用全局共享 AuthState
    /// </summary>
    public DeviceStatusViewModel() : this(AuthState.Shared,
        new CloudApiClient(AppSettings.Instance.ServerUrl, AuthState.Shared))
    {
    }

    /// <summary>
    /// 从云端拉取最新设备状态（GET /api/v1/devices/current）
    /// </summary>
    private async Task RefreshDeviceStatusAsync()
    {
        if (!_authState.IsLoggedIn) return;

        IsLoading = true;
        ErrorMessage = null;

        try
        {
            var result = await _apiClient.GetCurrentDeviceAsync();

            if (result?.IsSuccess == true && result.Data != null)
            {
                DeviceId = result.Data.Id;
                DeviceName = result.Data.DeviceName;
                Status = result.Data.Status;
                BoundAt = result.Data.BoundAt;
                LastSeenAt = result.Data.LastSeenAt;
            }
            else if (result?.Error != null)
            {
                ErrorMessage = result.Error.Message;
                // 云端请求失败时，使用本地缓存的设备信息作为降级展示
                UpdateFromLocalDevice();
            }
        }
        catch (Exception ex)
        {
            ErrorMessage = $"获取设备状态失败：{ex.Message}";
            // 网络错误时降级展示本地缓存
            UpdateFromLocalDevice();
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>
    /// 从本地 AuthState.Device 更新展示信息（降级兜底）
    /// </summary>
    private void UpdateFromLocalDevice()
    {
        var device = _authState.Device;
        if (!string.IsNullOrEmpty(device.Id))
        {
            DeviceId = device.Id;
            Status = device.Status;
        }
    }

    /// <summary>
    /// 登出时清除设备展示信息
    /// </summary>
    private void ClearDeviceInfo()
    {
        DeviceId = string.Empty;
        DeviceName = string.Empty;
        Status = "unknown";
        BoundAt = null;
        LastSeenAt = null;
        ErrorMessage = null;
    }
}
