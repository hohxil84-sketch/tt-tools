using System.ComponentModel;
using System.Net.Http;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;
using TTTools.AuthDevice.Tests.TestHelpers;
using TTTools.AuthDevice.ViewModels;

namespace TTTools.AuthDevice.Tests.ViewModels;

/// <summary>
/// DeviceStatusViewModel 单元测试
/// 覆盖设备状态展示、刷新、登出清除、属性变更通知等场景。
/// </summary>
public class DeviceStatusViewModelTests
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

    /// <summary>未登录状态的初始值</summary>
    [Fact]
    public void InitialState_ShouldHaveDefaults_WhenNotLoggedIn()
    {
        var authState = new AuthState();
        var apiClient = CreateMockApiClient(new ApiResponse<CurrentDeviceDto>
        {
            Success = true,
            Data = new CurrentDeviceDto
            {
                Id = "dev-001",
                DeviceFingerprint = "fp-hash",
                DeviceName = "TEST-PC",
                Status = "active"
            },
            Error = null,
            RequestId = "req_001"
        });
        var vm = new DeviceStatusViewModel(authState, apiClient);

        Assert.Equal(string.Empty, vm.DeviceId);
        Assert.Equal(string.Empty, vm.DeviceName);
        Assert.Equal("unknown", vm.Status);
        Assert.False(vm.IsBound);
        Assert.Null(vm.BoundAt);
        Assert.Null(vm.LastSeenAt);
        Assert.False(vm.IsLoading);
        Assert.Null(vm.ErrorMessage);
    }

    /// <summary>已登录时从本地 AuthState 读取设备信息</summary>
    [Fact]
    public void Constructor_ShouldReadFromAuthState_WhenLoggedIn()
    {
        var authState = new AuthState();
        // 模拟已登录状态
        authState.SetLoggedIn("token", "refresh", 1800,
            new UserInfo { Id = "u1", Account = "test@test.com" },
            new DeviceInfo { Id = "dev-local", Status = "active", IsNew = false });

        var apiClient = CreateMockApiClient(new ApiResponse<CurrentDeviceDto>
        {
            Success = true,
            Data = new CurrentDeviceDto
            {
                Id = "dev-001",
                DeviceFingerprint = "fp-hash",
                DeviceName = "TEST-PC",
                Status = "active",
                BoundAt = "2026-06-20T08:00:00Z",
                LastSeenAt = "2026-06-20T09:00:00Z"
            },
            Error = null,
            RequestId = "req_001"
        });

        var vm = new DeviceStatusViewModel(authState, apiClient);

        // 构造时从本地 AuthState 读取
        Assert.Equal("dev-local", vm.DeviceId);
        Assert.Equal("active", vm.Status);
        Assert.True(vm.IsBound);
    }

    /// <summary>StatusDisplay 中文展示</summary>
    [Theory]
    [InlineData("active", "已绑定")]
    [InlineData("blocked", "已禁用")]
    [InlineData("removed", "已移除")]
    [InlineData("unknown", "未知")]
    [InlineData("bogus", "未知")]
    public void StatusDisplay_ShouldReturnChineseLabel(string status, string expected)
    {
        var authState = new AuthState();
        authState.SetLoggedIn("token", "refresh", 1800,
            new UserInfo { Id = "u1" },
            new DeviceInfo { Id = "d1", Status = status, IsNew = false });
        var apiClient = CreateMockApiClient(new ApiResponse<CurrentDeviceDto>
        {
            Success = true, Data = new CurrentDeviceDto { Id = "d1", Status = status }, Error = null, RequestId = "req"
        });
        var vm = new DeviceStatusViewModel(authState, apiClient);

        // 注意：Status 从本地 AuthState 读取，因此 StatusDisplay 应匹配
        Assert.Equal(expected, vm.StatusDisplay);
    }

    /// <summary>Status 更新时 IsBound 同步更新</summary>
    [Fact]
    public void IsBound_ShouldBeTrue_WhenStatusIsActive()
    {
        var authState = new AuthState();
        var apiClient = CreateMockApiClient(new ApiResponse<CurrentDeviceDto>
        {
            Success = true, Data = new CurrentDeviceDto { Id = "d1", Status = "active" }, Error = null, RequestId = "req"
        });
        var vm = new DeviceStatusViewModel(authState, apiClient);

        // 未登录时 IsBound 为 false
        Assert.False(vm.IsBound);

        // 通过 AuthState 更新设备状态到 active
        authState.SetLoggedIn("token", "refresh", 1800,
            new UserInfo { Id = "u1" },
            new DeviceInfo { Id = "d1", Status = "active", IsNew = false });
        // 重新构造 vm
        vm = new DeviceStatusViewModel(authState, apiClient);

        Assert.True(vm.IsBound);
    }

    /// <summary>RefreshCommand 不应为 null</summary>
    [Fact]
    public void RefreshCommand_ShouldNotBeNull()
    {
        var vm = new DeviceStatusViewModel();
        Assert.NotNull(vm.RefreshCommand);
    }

    /// <summary>构造时 AuthState 为 null 应抛出异常</summary>
    [Fact]
    public void Constructor_ShouldThrow_WhenAuthStateIsNull()
    {
        var apiClient = CreateMockApiClient(new ApiResponse<CurrentDeviceDto>
        {
            Success = true, Data = new CurrentDeviceDto(), Error = null, RequestId = "req"
        });
        Assert.Throws<ArgumentNullException>(() => new DeviceStatusViewModel(null!, apiClient));
    }

    /// <summary>登出后应清除设备信息</summary>
    [Fact]
    public void Logout_ShouldClearDeviceInfo()
    {
        var authState = new AuthState();
        authState.SetLoggedIn("token", "refresh", 1800,
            new UserInfo { Id = "u1" },
            new DeviceInfo { Id = "d1", Status = "active", IsNew = false });
        var apiClient = CreateMockApiClient(new ApiResponse<CurrentDeviceDto>
        {
            Success = true, Data = new CurrentDeviceDto { Id = "d1", Status = "active" }, Error = null, RequestId = "req"
        });
        var vm = new DeviceStatusViewModel(authState, apiClient);

        // 登出
        authState.Logout();

        Assert.Equal(string.Empty, vm.DeviceId);
        Assert.Equal("unknown", vm.Status);
        Assert.False(vm.IsBound);
    }

    /// <summary>属性变更通知测试</summary>
    [Fact]
    public void DeviceId_ShouldRaisePropertyChanged()
    {
        var vm = new DeviceStatusViewModel();
        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName!);

        vm.DeviceId = "dev-new";

        Assert.Contains(nameof(DeviceStatusViewModel.DeviceId), changedProps);
    }
}
