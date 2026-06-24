using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace TTShared.Auth;

/// <summary>
/// 认证状态枚举
/// </summary>
public enum AuthStatus
{
    /// <summary>未登录</summary>
    LoggedOut,
    /// <summary>登录中</summary>
    LoggingIn,
    /// <summary>已登录</summary>
    LoggedIn,
    /// <summary>令牌刷新中</summary>
    Refreshing,
    /// <summary>登录失败</summary>
    LoginFailed
}

/// <summary>
/// 用户信息（对应 OpenAPI UserInfo）
/// </summary>
public class UserInfo : INotifyPropertyChanged
{
    private string _id = string.Empty;
    private string _account = string.Empty;
    private string? _displayName;
    private string _planCode = "free";

    /// <summary>用户 ID</summary>
    public string Id { get => _id; set { _id = value; OnPropertyChanged(); } }
    /// <summary>登录账号</summary>
    public string Account { get => _account; set { _account = value; OnPropertyChanged(); } }
    /// <summary>展示名称</summary>
    public string? DisplayName { get => _displayName; set { _displayName = value; OnPropertyChanged(); } }
    /// <summary>当前套餐编码</summary>
    public string PlanCode { get => _planCode; set { _planCode = value; OnPropertyChanged(); } }
    /// <summary>是否已登录</summary>
    public bool IsLoggedIn => !string.IsNullOrEmpty(Id);

    public event PropertyChangedEventHandler? PropertyChanged;
    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
}

/// <summary>
/// 设备信息（对应 OpenAPI DeviceInfo）
/// </summary>
public class DeviceInfo : INotifyPropertyChanged
{
    private string _id = string.Empty;
    private string _status = "unknown";
    private bool _isNew;

    /// <summary>设备 ID</summary>
    public string Id { get => _id; set { _id = value; OnPropertyChanged(); } }
    /// <summary>设备状态：active / blocked / removed</summary>
    public string Status { get => _status; set { _status = value; OnPropertyChanged(); } }
    /// <summary>是否新绑定设备</summary>
    public bool IsNew { get => _isNew; set { _isNew = value; OnPropertyChanged(); } }

    public event PropertyChangedEventHandler? PropertyChanged;
    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
}

/// <summary>
/// 认证状态管理器
/// 负责管理登录状态、令牌生命周期、用户和设备信息。
/// 通过事件通知 UI 层状态变更。
/// </summary>
public class AuthState : INotifyPropertyChanged
{
    private readonly TokenStorage _tokenStorage;
    private AuthStatus _status = AuthStatus.LoggedOut;
    private UserInfo _user = new();
    private DeviceInfo _device = new();
    private string? _accessToken;
    private string? _refreshToken;
    private DateTime _tokenExpiry = DateTime.MinValue;
    private string? _lastError;

    /// <summary>当前认证状态</summary>
    public AuthStatus Status
    {
        get => _status;
        private set { _status = value; OnPropertyChanged(); OnPropertyChanged(nameof(IsLoggedIn)); OnPropertyChanged(nameof(IsAuthenticating)); }
    }

    /// <summary>当前用户信息</summary>
    public UserInfo User => _user;

    /// <summary>当前设备信息</summary>
    public DeviceInfo Device => _device;

    /// <summary>是否已登录</summary>
    public bool IsLoggedIn => Status == AuthStatus.LoggedIn && !string.IsNullOrEmpty(_accessToken);

    /// <summary>是否正在认证（登录或刷新）</summary>
    public bool IsAuthenticating => Status == AuthStatus.LoggingIn || Status == AuthStatus.Refreshing;

    /// <summary>当前 access token（可能为 null）</summary>
    public string? AccessToken => _accessToken;

    /// <summary>当前 refresh token（可能为 null）</summary>
    public string? RefreshTokenValue => _refreshToken;

    /// <summary>令牌过期时间</summary>
    public DateTime TokenExpiry => _tokenExpiry;

    /// <summary>最近一次错误消息</summary>
    public string? LastError
    {
        get => _lastError;
        private set { _lastError = value; OnPropertyChanged(); }
    }

    /// <summary>认证状态变更事件</summary>
    public event EventHandler<AuthStatus>? AuthStatusChanged;

    /// <summary>登录成功事件</summary>
    public event EventHandler? LoggedIn;

    /// <summary>登出事件</summary>
    public event EventHandler? LoggedOut;

    public event PropertyChangedEventHandler? PropertyChanged;

    /// <summary>
    /// 全局共享的 AuthState 单例。
    /// 桌面端各模块通过此实例共享登录状态，避免各自创建独立实例。
    /// </summary>
    public static AuthState Shared { get; } = new AuthState();

    public AuthState() : this(new TokenStorage()) { }

    public AuthState(TokenStorage tokenStorage)
    {
        _tokenStorage = tokenStorage;
        // 启动时尝试从安全存储恢复令牌
        RestoreTokens();
    }

    /// <summary>
    /// 设置登录状态（由 API client 在登录成功后调用）
    /// </summary>
    /// <param name="accessToken">访问令牌</param>
    /// <param name="refreshToken">刷新令牌</param>
    /// <param name="expiresIn">过期时间（秒）</param>
    /// <param name="user">用户信息</param>
    /// <param name="device">设备信息</param>
    public void SetLoggedIn(string accessToken, string refreshToken, int expiresIn,
        UserInfo user, DeviceInfo device)
    {
        _accessToken = accessToken;
        _refreshToken = refreshToken;
        _tokenExpiry = DateTime.UtcNow.AddSeconds(expiresIn);
        _user = user;
        _device = device;
        LastError = null;
        Status = AuthStatus.LoggedIn;

        // 持久化令牌到安全存储
        _tokenStorage.SaveTokens(accessToken, refreshToken);

        AuthStatusChanged?.Invoke(this, AuthStatus.LoggedIn);
        LoggedIn?.Invoke(this, EventArgs.Empty);
    }

    /// <summary>
    /// 更新令牌（刷新成功后调用）
    /// </summary>
    public void UpdateTokens(string accessToken, string refreshToken, int expiresIn)
    {
        _accessToken = accessToken;
        _refreshToken = refreshToken;
        _tokenExpiry = DateTime.UtcNow.AddSeconds(expiresIn);
        LastError = null;
        Status = AuthStatus.LoggedIn;

        _tokenStorage.SaveTokens(accessToken, refreshToken);

        AuthStatusChanged?.Invoke(this, AuthStatus.LoggedIn);
    }

    /// <summary>
    /// 设置登录失败
    /// </summary>
    public void SetLoginFailed(string error)
    {
        LastError = error;
        Status = AuthStatus.LoginFailed;
        AuthStatusChanged?.Invoke(this, AuthStatus.LoginFailed);
    }

    /// <summary>
    /// 设置登录中状态
    /// </summary>
    public void SetLoggingIn()
    {
        LastError = null;
        Status = AuthStatus.LoggingIn;
        AuthStatusChanged?.Invoke(this, AuthStatus.LoggingIn);
    }

    /// <summary>
    /// 设置刷新中状态
    /// </summary>
    public void SetRefreshing()
    {
        Status = AuthStatus.Refreshing;
        AuthStatusChanged?.Invoke(this, AuthStatus.Refreshing);
    }

    /// <summary>
    /// 退出登录
    /// </summary>
    public void Logout()
    {
        _accessToken = null;
        _refreshToken = null;
        _tokenExpiry = DateTime.MinValue;
        _user = new UserInfo();
        _device = new DeviceInfo();
        LastError = null;
        Status = AuthStatus.LoggedOut;

        _tokenStorage.ClearTokens();

        AuthStatusChanged?.Invoke(this, AuthStatus.LoggedOut);
        LoggedOut?.Invoke(this, EventArgs.Empty);
    }

    /// <summary>
    /// 判断令牌是否即将过期（5分钟内过期）
    /// </summary>
    public bool IsTokenExpiringSoon()
    {
        return _tokenExpiry != DateTime.MinValue &&
               DateTime.UtcNow.AddMinutes(5) >= _tokenExpiry;
    }

    /// <summary>
    /// 判断令牌是否已过期
    /// </summary>
    public bool IsTokenExpired()
    {
        return _tokenExpiry != DateTime.MinValue &&
               DateTime.UtcNow >= _tokenExpiry;
    }

    /// <summary>
    /// 从安全存储恢复令牌（启动时调用）
    /// </summary>
    private void RestoreTokens()
    {
        var (accessToken, refreshToken) = _tokenStorage.LoadTokens();
        if (!string.IsNullOrEmpty(accessToken) && !string.IsNullOrEmpty(refreshToken))
        {
            _accessToken = accessToken;
            _refreshToken = refreshToken;
            // 恢复时标记为需要刷新，实际验证由首次 API 调用触发
            _tokenExpiry = DateTime.UtcNow.AddMinutes(-1); // 标记为已过期，触发刷新
            Status = AuthStatus.LoggedOut; // 直到刷新成功前视为未登录
        }
    }

    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
}
