using TTShared.Auth;

namespace TTShared.Tests.Auth;

public class AuthStateTests
{
    [Fact]
    public void InitialState_ShouldBeLoggedOut()
    {
        var authState = new AuthState();
        Assert.Equal(AuthStatus.LoggedOut, authState.Status);
        Assert.False(authState.IsLoggedIn);
        Assert.False(authState.IsAuthenticating);
    }

    [Fact]
    public void SetLoggedIn_ShouldUpdateStateAndRaiseEvents()
    {
        var authState = new AuthState();
        AuthStatus? statusEvent = null;
        bool loggedInEvent = false;

        authState.AuthStatusChanged += (_, s) => statusEvent = s;
        authState.LoggedIn += (_, _) => loggedInEvent = true;

        var user = new UserInfo { Id = "u1", Account = "test@test.com", DisplayName = "Test", PlanCode = "standard" };
        var device = new DeviceInfo { Id = "d1", Status = "active", IsNew = true };

        authState.SetLoggedIn("access_token_123", "refresh_token_456", 1800, user, device);

        Assert.Equal(AuthStatus.LoggedIn, authState.Status);
        Assert.True(authState.IsLoggedIn);
        Assert.Equal("access_token_123", authState.AccessToken);
        Assert.Equal("refresh_token_456", authState.RefreshTokenValue);
        Assert.Equal("u1", authState.User.Id);
        Assert.Equal("d1", authState.Device.Id);
        Assert.Equal(AuthStatus.LoggedIn, statusEvent);
        Assert.True(loggedInEvent);
    }

    [Fact]
    public void SetLoginFailed_ShouldSetErrorState()
    {
        var authState = new AuthState();
        authState.SetLoginFailed("账号或密码错误");

        Assert.Equal(AuthStatus.LoginFailed, authState.Status);
        Assert.Equal("账号或密码错误", authState.LastError);
    }

    [Fact]
    public void SetLoggingIn_ShouldSetAuthenticatingState()
    {
        var authState = new AuthState();
        authState.SetLoggingIn();

        Assert.Equal(AuthStatus.LoggingIn, authState.Status);
        Assert.True(authState.IsAuthenticating);
    }

    [Fact]
    public void Logout_ShouldClearAllAndRaiseEvent()
    {
        var authState = new AuthState();
        bool loggedOutEvent = false;
        authState.LoggedOut += (_, _) => loggedOutEvent = true;

        // 先登录
        var user = new UserInfo { Id = "u1" };
        var device = new DeviceInfo { Id = "d1" };
        authState.SetLoggedIn("token1", "refresh1", 1800, user, device);

        // 退出登录
        authState.Logout();

        Assert.Equal(AuthStatus.LoggedOut, authState.Status);
        Assert.Null(authState.AccessToken);
        Assert.Null(authState.RefreshTokenValue);
        Assert.True(string.IsNullOrEmpty(authState.User.Id));
        Assert.True(loggedOutEvent);
    }

    [Fact]
    public void UpdateTokens_ShouldRefreshTokenState()
    {
        var authState = new AuthState();
        var user = new UserInfo { Id = "u1" };
        var device = new DeviceInfo { Id = "d1" };
        authState.SetLoggedIn("old_access", "old_refresh", 1800, user, device);

        authState.UpdateTokens("new_access", "new_refresh", 3600);

        Assert.Equal("new_access", authState.AccessToken);
        Assert.Equal("new_refresh", authState.RefreshTokenValue);
        Assert.Equal(AuthStatus.LoggedIn, authState.Status);
    }

    [Fact]
    public void IsTokenExpired_ShouldReturnFalse_WhenRecentlySet()
    {
        var authState = new AuthState();
        var user = new UserInfo { Id = "u1" };
        var device = new DeviceInfo { Id = "d1" };
        authState.SetLoggedIn("token", "refresh", 1800, user, device);

        Assert.False(authState.IsTokenExpired());
    }

    [Fact]
    public void IsTokenExpiringSoon_ShouldReturnFalse_WhenRecentlySet()
    {
        var authState = new AuthState();
        var user = new UserInfo { Id = "u1" };
        var device = new DeviceInfo { Id = "d1" };
        authState.SetLoggedIn("token", "refresh", 1800, user, device);

        Assert.False(authState.IsTokenExpiringSoon());
    }

    [Fact]
    public void SetRefreshing_ShouldSetRefreshingState()
    {
        var authState = new AuthState();
        authState.SetRefreshing();

        Assert.Equal(AuthStatus.Refreshing, authState.Status);
        Assert.True(authState.IsAuthenticating);
    }
}
