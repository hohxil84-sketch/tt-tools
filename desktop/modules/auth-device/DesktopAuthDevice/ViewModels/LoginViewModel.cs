using System.Windows.Controls;
using System.Windows.Input;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.Settings;
using TTShared.UI;

namespace TTTools.AuthDevice.ViewModels;

/// <summary>
/// 登录界面 ViewModel
/// 负责账号密码输入、调用云端登录 API、更新 AuthState、显示错误信息。
/// 密码通过命令参数传递，不在 ViewModel 中持久保存明文。
/// </summary>
public class LoginViewModel : BaseViewModel
{
    private readonly AuthState _authState;
    private readonly CloudApiClient _apiClient;
    private string _account = string.Empty;
    private bool _isLoggingIn;
    private string? _errorMessage;

    /// <summary>当前输入的账号</summary>
    public string Account
    {
        get => _account;
        set
        {
            if (SetProperty(ref _account, value))
            {
                OnPropertyChanged(nameof(CanLogin));
            }
        }
    }

    /// <summary>是否正在执行登录请求</summary>
    public bool IsLoggingIn
    {
        get => _isLoggingIn;
        set
        {
            if (SetProperty(ref _isLoggingIn, value))
            {
                OnPropertyChanged(nameof(CanLogin));
            }
        }
    }

    /// <summary>登录或网络错误消息</summary>
    public string? ErrorMessage
    {
        get => _errorMessage;
        set => SetProperty(ref _errorMessage, value);
    }

    /// <summary>是否可以点击登录（非登录中、账号不为空）</summary>
    public bool CanLogin => !IsLoggingIn && !string.IsNullOrWhiteSpace(Account);

    /// <summary>登录命令</summary>
    public ICommand LoginCommand { get; }

    /// <summary>登录成功事件</summary>
    public event EventHandler? LoginSucceeded;

    /// <summary>登录失败事件</summary>
    public event EventHandler<string>? LoginFailed;

    public LoginViewModel(AuthState authState, CloudApiClient apiClient)
    {
        _authState = authState ?? throw new ArgumentNullException(nameof(authState));
        _apiClient = apiClient ?? throw new ArgumentNullException(nameof(apiClient));

        LoginCommand = new AsyncRelayCommand<object>(async (parameter) => await LoginAsync(parameter));
    }

    /// <summary>
    /// 默认构造函数。
    /// 使用全局共享 AuthState，确保登录状态在整个应用内可见。
    /// </summary>
    public LoginViewModel() : this(AuthState.Shared,
        new CloudApiClient(AppSettings.Instance.ServerUrl, AuthState.Shared))
    {
    }

    /// <summary>
    /// 执行登录请求。
    /// 密码通过命令参数传入（来自 PasswordBox），不在 ViewModel 中保留。
    /// </summary>
    /// <param name="passwordParameter">来自 UI PasswordBox 的密码字符串</param>
    private async Task LoginAsync(object? passwordParameter)
    {
        if (IsLoggingIn) return;
        if (string.IsNullOrWhiteSpace(Account))
        {
            ErrorMessage = "请输入账号";
            return;
        }

        // 命令参数为 PasswordBox 元素，从其 Password 属性获取真实密码
        var password = (passwordParameter as PasswordBox)?.Password ?? string.Empty;
        if (string.IsNullOrEmpty(password))
        {
            ErrorMessage = "请输入密码";
            return;
        }

        IsLoggingIn = true;
        ErrorMessage = null;
        _authState.SetLoggingIn();

        try
        {
            // 获取设备指纹（基于机器特征生成，不保存任何账户信息）
            var fingerprint = DeviceFingerprint.GetFingerprint();

            // 调用云端登录 API，桌面端不保存明文密码
            var result = await _apiClient.LoginAsync(Account, password, fingerprint);

            if (result?.IsSuccess == true && result.Data != null)
            {
                // 将云端返回的用户和设备数据映射到 AuthState 模型
                var user = new UserInfo
                {
                    Id = result.Data.User.Id,
                    Account = result.Data.User.Account,
                    DisplayName = result.Data.User.DisplayName,
                    PlanCode = result.Data.User.PlanCode
                };
                var device = new DeviceInfo
                {
                    Id = result.Data.Device.Id,
                    Status = result.Data.Device.Status,
                    IsNew = result.Data.Device.IsNew
                };

                _authState.SetLoggedIn(
                    result.Data.AccessToken,
                    result.Data.RefreshToken,
                    result.Data.ExpiresIn,
                    user,
                    device);

                LoginSucceeded?.Invoke(this, EventArgs.Empty);
            }
            else
            {
                var errorMsg = result?.Error?.Message ?? "登录失败，请重试";
                ErrorMessage = errorMsg;
                _authState.SetLoginFailed(errorMsg);
                LoginFailed?.Invoke(this, errorMsg);
            }
        }
        catch (Exception ex)
        {
            var errorMsg = $"网络错误：{ex.Message}";
            ErrorMessage = errorMsg;
            _authState.SetLoginFailed(errorMsg);
            LoginFailed?.Invoke(this, errorMsg);
        }
        finally
        {
            IsLoggingIn = false;
        }
    }
}
