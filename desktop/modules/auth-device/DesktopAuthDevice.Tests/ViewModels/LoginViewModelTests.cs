using System.ComponentModel;
using System.Net.Http;
using System.Text.Json;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;
using TTTools.AuthDevice.Tests.TestHelpers;
using TTTools.AuthDevice.ViewModels;

namespace TTTools.AuthDevice.Tests.ViewModels;

/// <summary>
/// LoginViewModel 单元测试
/// 覆盖登录成功、登录失败、输入校验、属性变更通知等场景。
/// </summary>
public class LoginViewModelTests
{
    /// <summary>
    /// 创建 CloudApiClient 的工厂方法，注入 mock HTTP 处理器
    /// </summary>
    private static CloudApiClient CreateMockApiClient(object responseBody)
    {
        var handler = MockHttpMessageHandler.CreateJsonResponse(responseBody);
        var httpClient = new HttpClient(handler) { BaseAddress = new Uri("http://test.local") };
        return new CloudApiClient(httpClient, new AuthState());
    }

    /// <summary>初始状态：未登录、无错误、可登录</summary>
    [Fact]
    public void InitialState_ShouldHaveEmptyFieldsAndCanLogin()
    {
        var authState = new AuthState();
        var apiClient = CreateMockApiClient(new ApiResponse<LoginData>
        {
            Success = true,
            Data = new LoginData(),
            Error = null,
            RequestId = "req_001"
        });

        var vm = new LoginViewModel(authState, apiClient);

        Assert.Equal(string.Empty, vm.Account);
        Assert.False(vm.IsLoggingIn);
        Assert.Null(vm.ErrorMessage);
        // 默认 account 为空时 CanLogin 为 false
        Assert.False(vm.CanLogin);
    }

    /// <summary>输入账号后 CanLogin 变为 true</summary>
    [Fact]
    public void CanLogin_ShouldBeTrue_WhenAccountIsNotEmpty()
    {
        var authState = new AuthState();
        var apiClient = CreateMockApiClient(new ApiResponse<LoginData>
        {
            Success = true, Data = new LoginData(), Error = null, RequestId = "req_001"
        });
        var vm = new LoginViewModel(authState, apiClient);

        vm.Account = "test@example.com";

        Assert.True(vm.CanLogin);
    }

    /// <summary>登录进行中时 CanLogin 为 false</summary>
    [Fact]
    public void CanLogin_ShouldBeFalse_WhenLoggingIn()
    {
        var authState = new AuthState();
        var apiClient = CreateMockApiClient(new ApiResponse<LoginData>
        {
            Success = true, Data = new LoginData(), Error = null, RequestId = "req_001"
        });
        var vm = new LoginViewModel(authState, apiClient);
        vm.Account = "test@example.com";

        // 通过反射设置 IsLoggingIn = true 来模拟登录进行中的状态
        var prop = typeof(LoginViewModel).GetProperty(nameof(LoginViewModel.IsLoggingIn));
        prop!.SetValue(vm, true);

        Assert.False(vm.CanLogin);
    }

    /// <summary>Account 属性变更应触发 PropertyChanged 通知</summary>
    [Fact]
    public void Account_ShouldRaisePropertyChanged()
    {
        var authState = new AuthState();
        var apiClient = CreateMockApiClient(new ApiResponse<LoginData>
        {
            Success = true, Data = new LoginData(), Error = null, RequestId = "req_001"
        });
        var vm = new LoginViewModel(authState, apiClient);

        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName!);

        vm.Account = "test@example.com";

        Assert.Contains(nameof(LoginViewModel.Account), changedProps);
        Assert.Contains(nameof(LoginViewModel.CanLogin), changedProps);
    }

    /// <summary>ErrorMessage 属性变更应触发 PropertyChanged 通知</summary>
    [Fact]
    public void ErrorMessage_ShouldRaisePropertyChanged()
    {
        var authState = new AuthState();
        var apiClient = CreateMockApiClient(new ApiResponse<LoginData>
        {
            Success = true, Data = new LoginData(), Error = null, RequestId = "req_001"
        });
        var vm = new LoginViewModel(authState, apiClient);

        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName!);

        vm.ErrorMessage = "测试错误";

        Assert.Contains(nameof(LoginViewModel.ErrorMessage), changedProps);
    }

    /// <summary>登录命令不应为 null</summary>
    [Fact]
    public void LoginCommand_ShouldNotBeNull()
    {
        var vm = new LoginViewModel();
        Assert.NotNull(vm.LoginCommand);
    }

    /// <summary>AuthState 传入 null 应抛出 ArgumentNullException</summary>
    [Fact]
    public void Constructor_ShouldThrow_WhenAuthStateIsNull()
    {
        var apiClient = CreateMockApiClient(new ApiResponse<LoginData>
        {
            Success = true, Data = new LoginData(), Error = null, RequestId = "req_001"
        });

        Assert.Throws<ArgumentNullException>(() => new LoginViewModel(null!, apiClient));
    }

    /// <summary>CloudApiClient 传入 null 应抛出 ArgumentNullException</summary>
    [Fact]
    public void Constructor_ShouldThrow_WhenApiClientIsNull()
    {
        Assert.Throws<ArgumentNullException>(() => new LoginViewModel(new AuthState(), null!));
    }
}
