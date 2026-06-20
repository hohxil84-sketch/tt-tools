using TTTools.PreflightCheck.Services;

namespace TTTools.PreflightCheck.Tests.Services;

/// <summary>
/// PreflightCheckService 单元测试
/// 覆盖服务构造、默认状态、格式支持检查、资源释放等场景。
/// 注：与 Python worker 的集成测试需要在桌面端完整运行时进行。
/// </summary>
public class PreflightCheckServiceTests
{
    /// <summary>默认构造函数应创建有效实例</summary>
    [Fact]
    public void DefaultConstructor_ShouldCreateValidInstance()
    {
        using var service = new PreflightCheckService();

        Assert.NotNull(service);
        Assert.False(service.IsAvailable);
        Assert.Null(service.AvailabilityError);
        Assert.NotNull(service.SupportedFormats);
    }

    /// <summary>带参数构造函数应正确初始化</summary>
    [Fact]
    public void ParameterizedConstructor_ShouldInitializeCorrectly()
    {
        var pythonPath = @"D:\localPath\venvs\local-worker-preflight-check\Scripts\python.exe";
        var routerPath = @"D:\tt-tools\desktop\modules\preflight-check\DesktopPreflightCheck\preflight_check_router.py";

        using var service = new PreflightCheckService(pythonPath, routerPath);

        Assert.NotNull(service);
        Assert.False(service.IsAvailable); // 尚未启动
        Assert.Equal("PreflightChecker", service.CheckerName);
        Assert.NotNull(service.SupportedFormats);
    }

    /// <summary>SupportedFormats 应包含所有支持的图像格式</summary>
    [Fact]
    public void SupportedFormats_ShouldContainExpectedFormats()
    {
        using var service = new PreflightCheckService();

        Assert.Contains(".png", service.SupportedFormats);
        Assert.Contains(".jpg", service.SupportedFormats);
        Assert.Contains(".jpeg", service.SupportedFormats);
        Assert.Contains(".bmp", service.SupportedFormats);
        Assert.Contains(".tiff", service.SupportedFormats);
        Assert.Contains(".tif", service.SupportedFormats);
        Assert.Contains(".webp", service.SupportedFormats);
    }

    /// <summary>IsFormatSupported 应正确判断支持的文件格式</summary>
    [Fact]
    public void IsFormatSupported_ShouldValidateCorrectly()
    {
        using var service = new PreflightCheckService();

        Assert.True(service.IsFormatSupported(@"C:\test\image.png"));
        Assert.True(service.IsFormatSupported(@"C:\test\image.JPG"));
        Assert.True(service.IsFormatSupported(@"C:\test\image.tiff"));
        Assert.True(service.IsFormatSupported(@"C:\test\image.webp"));
        Assert.False(service.IsFormatSupported(@"C:\test\image.ico"));
        Assert.False(service.IsFormatSupported(@"C:\test\image.pdf"));
        Assert.False(service.IsFormatSupported(@"C:\test\image.gif"));
        Assert.False(service.IsFormatSupported(@"C:\test\image.psd"));
    }

    /// <summary>服务未启动时 CheckAsync 应抛出异常</summary>
    [Fact]
    public async Task CheckAsync_WhenNotAvailable_ShouldThrow()
    {
        using var service = new PreflightCheckService();

        await Assert.ThrowsAsync<InvalidOperationException>(
            () => service.CheckAsync(@"C:\test\image.png"));
    }

    /// <summary>文件不存在时 CheckAsync 应抛出异常</summary>
    [Fact]
    public async Task CheckAsync_FileNotFound_ShouldThrow()
    {
        // 使用参数化构造函数（有 LocalRuntimeClient），但未启动
        var pythonPath = @"D:\nonexistent\python.exe";
        var routerPath = @"D:\nonexistent\router.py";

        using var service = new PreflightCheckService(pythonPath, routerPath);

        // 服务未启动，直接调用 CheckAsync 应该抛出
        await Assert.ThrowsAsync<InvalidOperationException>(
            () => service.CheckAsync(@"C:\test\nonexistent.png"));
    }

    /// <summary>Dispose 应正确清理资源</summary>
    [Fact]
    public void Dispose_ShouldNotThrow()
    {
        var service = new PreflightCheckService();

        // 不应抛出异常
        var exception = Record.Exception(() => service.Dispose());
        Assert.Null(exception);
    }

    /// <summary>默认构造函数的 CheckerName 应为 PreflightChecker</summary>
    [Fact]
    public void CheckerName_ShouldBeCorrect()
    {
        using var service = new PreflightCheckService();
        Assert.Equal("PreflightChecker", service.CheckerName);
    }
}
