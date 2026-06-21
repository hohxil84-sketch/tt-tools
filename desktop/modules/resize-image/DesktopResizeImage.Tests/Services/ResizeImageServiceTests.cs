using System.Net;
using System.Net.Http;
using System.Text.Json;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;
using TTTools.ResizeImage.Models;
using TTTools.ResizeImage.Services;
using TTTools.ResizeImage.Tests.TestHelpers;

namespace TTTools.ResizeImage.Tests.Services;

/// <summary>
/// ResizeImageService 单元测试
/// C1: 覆盖权限 fail closed 所有场景。
/// C2: 使用 CloudApiClient(HttpClient, AuthState) + MockHttpMessageHandler 模拟接口。
/// </summary>
public class ResizeImageServiceTests
{
    /// <summary>
    /// 构建 ResizeImageService 用于测试（不连接真实 Python worker）。
    /// 不调用 StartAsync，因此所有 ResizeAsync 调用都会因服务未启动而失败——
    /// 但权限检查发生在服务可用性检查之前，我们可以测试权限拒绝路径。
    /// </summary>
    private static ResizeImageService CreateService(
        object? entitlementResponse = null,
        HttpStatusCode httpStatus = HttpStatusCode.OK,
        bool isLoggedIn = true)
    {
        var handler = entitlementResponse != null
            ? MockHttpMessageHandler.CreateJsonResponse(entitlementResponse)
            : MockHttpMessageHandler.CreateErrorResponse(httpStatus);

        var httpClient = new HttpClient(handler) { BaseAddress = new Uri("http://test.local") };
        var authState = new AuthState();
        if (isLoggedIn)
        {
            // 设置登录状态
            authState.SetLoggedIn("test_access_token", "test_refresh_token", 1800,
                new UserInfo { Id = "u1", Account = "test", DisplayName = "测试", PlanCode = "standard" },
                new DeviceInfo { Id = "d1", Status = "active", IsNew = false });
        }

        var apiClient = new CloudApiClient(httpClient, authState);
        return new ResizeImageService(
            pythonPath: "C:\\nonexistent\\python.exe",
            routerScriptPath: "C:\\nonexistent\\router.py",
            cloudApiClient: apiClient,
            authState: authState);
    }

    /// <summary>
    /// 构建成功的 entitlement 响应的 JSON 数据。
    /// </summary>
    private static ApiResponse<EntitlementCheckData> CreateEntitlementResponse(bool allowed)
    {
        return new ApiResponse<EntitlementCheckData>
        {
            Success = true,
            Data = new EntitlementCheckData
            {
                Allowed = allowed,
                Feature = "resize_image_local_paid",
                PlanCode = allowed ? "standard" : "free",
                RemainingFreeQuota = allowed ? null : 0,
                Reason = allowed ? null : "免费套餐当日使用次数已用完，请升级套餐",
            },
            Error = null,
            RequestId = "test_req_id",
        };
    }

    // ---- 构造函数的 null 校验（C1: CloudApiClient 和 AuthState 必须非 null） ----

    [Fact]
    public void Constructor_NullCloudApiClient_ShouldThrow()
    {
        Assert.Throws<ArgumentNullException>(() => new ResizeImageService(
            "python", "router", null!, new AuthState()));
    }

    [Fact]
    public void Constructor_NullAuthState_ShouldThrow()
    {
        var apiClient = new CloudApiClient("http://localhost", new AuthState());
        Assert.Throws<ArgumentNullException>(() => new ResizeImageService(
            "python", "router", apiClient, null!));
    }

    [Fact]
    public void Constructor_NullPythonPath_ShouldThrow()
    {
        var apiClient = new CloudApiClient("http://localhost", new AuthState());
        Assert.Throws<ArgumentNullException>(() => new ResizeImageService(
            null!, "router", apiClient, new AuthState()));
    }

    [Fact]
    public void Constructor_NullRouterPath_ShouldThrow()
    {
        var apiClient = new CloudApiClient("http://localhost", new AuthState());
        Assert.Throws<ArgumentNullException>(() => new ResizeImageService(
            "python", null!, apiClient, new AuthState()));
    }

    // ---- 格式校验 ----

    [Fact]
    public void IsFormatSupported_KnownFormat_ShouldReturnTrue()
    {
        var service = new ResizeImageService();
        Assert.True(service.IsFormatSupported("test.png"));
        Assert.True(service.IsFormatSupported("test.JPG"));
        Assert.True(service.IsFormatSupported("test.webp"));
        Assert.True(service.IsFormatSupported("test.TIFF"));
    }

    [Fact]
    public void IsFormatSupported_UnknownFormat_ShouldReturnFalse()
    {
        var service = new ResizeImageService();
        Assert.False(service.IsFormatSupported("test.txt"));
        Assert.False(service.IsFormatSupported("test.pdf"));
        Assert.False(service.IsFormatSupported("test.psd"));
    }

    [Fact]
    public void SupportedFormats_ShouldContainCommonFormats()
    {
        Assert.Contains(".png", ResizeImageService.SupportedFormats);
        Assert.Contains(".jpg", ResizeImageService.SupportedFormats);
        Assert.Contains(".bmp", ResizeImageService.SupportedFormats);
    }

    // ---- 权限检查（C1: fail closed） ----

    /// <summary>权限拒绝（Allowed=false）：返回 EntitlementAllowed=false，不启动 resize</summary>
    [Fact]
    public async Task ResizeAsync_EntitlementDenied_ShouldReturnNotAllowed()
    {
        var service = CreateService(CreateEntitlementResponse(allowed: false));

        var param = new ResizeImageParams { Mode = "fit", Width = 400, Height = 300 };
        // 文件不存在会先报文件不存在错误——但权限检查在文件校验之后
        // 我们需要一个实际存在的文件来测试权限路径
        var tempFile = Path.GetTempFileName();
        try
        {
            // 重命名为图片扩展名以通过格式校验
            var imgPath = Path.ChangeExtension(tempFile, ".png");
            File.Move(tempFile, imgPath);
            tempFile = imgPath;

            var result = await service.ResizeAsync(imgPath, null, param);

            Assert.False(result.EntitlementAllowed);
            Assert.NotNull(result.EntitlementReason);
            Assert.False(result.IsSuccess);
        }
        finally
        {
            if (File.Exists(tempFile)) File.Delete(tempFile);
        }
    }

    /// <summary>权限通过（Allowed=true）：正常流程（但因为服务未 StartAsync 会失败）</summary>
    [Fact]
    public async Task ResizeAsync_EntitlementAllowed_ButServiceNotStarted_ShouldReturnError()
    {
        var service = CreateService(CreateEntitlementResponse(allowed: true));

        var tempFile = Path.GetTempFileName();
        try
        {
            var imgPath = Path.ChangeExtension(tempFile, ".png");
            File.Move(tempFile, imgPath);
            tempFile = imgPath;

            var param = new ResizeImageParams { Mode = "fit", Width = 400, Height = 300 };
            var result = await service.ResizeAsync(imgPath, null, param);

            // 权限应该通过，但服务未启动导致失败
            Assert.True(result.EntitlementAllowed);
            Assert.False(result.IsSuccess);
            Assert.Contains("服务不可用", result.ErrorMessage);
        }
        finally
        {
            if (File.Exists(tempFile)) File.Delete(tempFile);
        }
    }

    /// <summary>未登录：直接拒绝，不调网络</summary>
    [Fact]
    public async Task ResizeAsync_NotLoggedIn_ShouldDenyWithoutNetworkCall()
    {
        var service = CreateService(isLoggedIn: false, entitlementResponse: CreateEntitlementResponse(true));
        // 输入文件不需要存在——未登录检查在文件校验之前

        var param = new ResizeImageParams { Mode = "fit" };
        var result = await service.ResizeAsync("nonexistent.png", null, param);

        Assert.False(result.EntitlementAllowed);
        Assert.Contains("登录", result.EntitlementReason);
        Assert.False(result.IsSuccess);
    }

    /// <summary>文件不存在：报错（权限检查在文件校验之后，但结果正确）</summary>
    [Fact]
    public async Task ResizeAsync_FileNotFound_ShouldReturnError()
    {
        var service = CreateService(CreateEntitlementResponse(allowed: true));

        var param = new ResizeImageParams { Mode = "fit" };
        var result = await service.ResizeAsync("D:\\nonexistent\\file.png", null, param);

        Assert.False(result.IsSuccess);
        Assert.Contains("不存在", result.ErrorMessage);
    }

    /// <summary>不支持的格式：报错</summary>
    [Fact]
    public async Task ResizeAsync_UnsupportedFormat_ShouldReturnError()
    {
        var service = CreateService(CreateEntitlementResponse(allowed: true));

        var tempFile = Path.GetTempFileName();
        try
        {
            var param = new ResizeImageParams { Mode = "fit" };
            var result = await service.ResizeAsync(tempFile, null, param);

            Assert.False(result.IsSuccess);
            Assert.Contains("不支持", result.ErrorMessage);
        }
        finally
        {
            if (File.Exists(tempFile)) File.Delete(tempFile);
        }
    }

    // ---- 401 / null / error 响应拒绝（C1） ----

    /// <summary>HTTP 401：权限拒绝</summary>
    [Fact]
    public async Task ResizeAsync_Http401_ShouldDeny()
    {
        var handler = MockHttpMessageHandler.CreateErrorResponse(HttpStatusCode.Unauthorized);
        var httpClient = new HttpClient(handler) { BaseAddress = new Uri("http://test.local") };
        var authState = new AuthState();
        authState.SetLoggedIn("old_token", "refresh", 0,  // 立即过期，触发 401
            new UserInfo { Id = "u1", Account = "test", DisplayName = "测试", PlanCode = "standard" },
            new DeviceInfo { Id = "d1", Status = "active", IsNew = false });
        var apiClient = new CloudApiClient(httpClient, authState);
        var service = new ResizeImageService("python", "router", apiClient, authState);

        var tempFile = Path.GetTempFileName();
        try
        {
            var imgPath = Path.ChangeExtension(tempFile, ".png");
            File.Move(tempFile, imgPath);
            tempFile = imgPath;

            var param = new ResizeImageParams { Mode = "fit" };
            var result = await service.ResizeAsync(imgPath, null, param);

            Assert.False(result.EntitlementAllowed);
            Assert.False(result.IsSuccess);
        }
        finally
        {
            if (File.Exists(tempFile)) File.Delete(tempFile);
        }
    }

    // ---- Dispose ----

    [Fact]
    public void Dispose_ShouldNotThrow()
    {
        var service = CreateService(CreateEntitlementResponse(true));
        var ex = Record.Exception(() => service.Dispose());
        Assert.Null(ex);
    }

    // ---- 初始状态 ----

    [Fact]
    public void InitialState_ShouldNotBeAvailable()
    {
        var service = CreateService(CreateEntitlementResponse(true));
        Assert.False(service.IsAvailable);
    }
}
