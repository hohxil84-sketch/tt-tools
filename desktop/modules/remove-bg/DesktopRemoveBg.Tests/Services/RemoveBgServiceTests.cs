using TTTools.RemoveBg.Models;
using TTTools.RemoveBg.Services;

namespace TTTools.RemoveBg.Tests.Services;

/// <summary>
/// RemoveBgService 单元测试
/// 测试服务构造、默认状态、格式校验等不依赖 Python worker 的逻辑。
/// </summary>
public class RemoveBgServiceTests
{
    [Fact]
    public void Constructor_Default_ShouldSetEngineName()
    {
        // 默认构造函数
        var service = new RemoveBgService();
        Assert.NotNull(service.EngineName);
        Assert.Contains("rembg", service.EngineName);
    }

    [Fact]
    public void Constructor_Default_ShouldNotBeAvailable()
    {
        var service = new RemoveBgService();
        Assert.False(service.IsAvailable);
        Assert.Null(service.AvailabilityError);
    }

    [Fact]
    public void Constructor_Default_ShouldHaveDefaultModel()
    {
        var service = new RemoveBgService();
        Assert.Equal("u2net", service.DefaultModel);
    }

    [Fact]
    public void Constructor_Default_ShouldHaveSupportedFormats()
    {
        var service = new RemoveBgService();
        Assert.NotEmpty(service.SupportedFormats);
        Assert.Contains(".png", service.SupportedFormats);
        Assert.Contains(".jpg", service.SupportedFormats);
        Assert.Contains(".jpeg", service.SupportedFormats);
        Assert.Contains(".bmp", service.SupportedFormats);
    }

    [Fact]
    public void Constructor_WithDependencies_ShouldStoreReferences()
    {
        var pythonPath = @"D:\localPath\venvs\local-worker-remove-bg\Scripts\python.exe";
        var routerPath = "remove_bg_router.py";
        var service = new RemoveBgService(pythonPath, routerPath);

        Assert.False(service.IsAvailable);
        Assert.Null(service.AvailabilityError);
    }

    [Fact]
    public void Constructor_WithNullPythonPath_ShouldThrow()
    {
        Assert.Throws<ArgumentNullException>(() =>
            new RemoveBgService(null!, "router.py"));
    }

    [Fact]
    public void Constructor_WithNullRouterPath_ShouldThrow()
    {
        Assert.Throws<ArgumentNullException>(() =>
            new RemoveBgService("python.exe", null!));
    }

    [Fact]
    public void IsFormatSupported_ValidPng_ShouldReturnTrue()
    {
        var service = new RemoveBgService();
        Assert.True(service.IsFormatSupported("test.png"));
    }

    [Fact]
    public void IsFormatSupported_ValidJpg_ShouldReturnTrue()
    {
        var service = new RemoveBgService();
        Assert.True(service.IsFormatSupported("photo.jpg"));
    }

    [Fact]
    public void IsFormatSupported_ValidWebp_ShouldReturnTrue()
    {
        var service = new RemoveBgService();
        Assert.True(service.IsFormatSupported("image.webp"));
    }

    [Fact]
    public void IsFormatSupported_InvalidFormat_ShouldReturnFalse()
    {
        var service = new RemoveBgService();
        Assert.False(service.IsFormatSupported("document.pdf"));
        Assert.False(service.IsFormatSupported("video.mp4"));
    }

    [Fact]
    public void IsFormatSupported_CaseInsensitive_ShouldWork()
    {
        var service = new RemoveBgService();
        Assert.True(service.IsFormatSupported("IMAGE.PNG"));
        Assert.True(service.IsFormatSupported("Photo.JPG"));
    }

    [Fact]
    public void ProcessAsync_WhenNotStarted_ShouldThrow()
    {
        var service = new RemoveBgService();
        Assert.ThrowsAsync<InvalidOperationException>(async () =>
            await service.ProcessAsync("test.png"));
    }

    [Fact]
    public void Dispose_ShouldNotThrow()
    {
        var service = new RemoveBgService();
        var exception = Record.Exception(() => service.Dispose());
        Assert.Null(exception);
    }
}
