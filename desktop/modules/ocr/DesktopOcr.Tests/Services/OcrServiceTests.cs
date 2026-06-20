using System.Text.Json;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTShared.Logging;
using TTTools.OCR.Models;
using TTTools.OCR.Services;

namespace TTTools.OCR.Tests.Services;

/// <summary>
/// OcrService 单元测试
/// 覆盖服务初始化、文件格式校验、默认构造函数等场景。
/// 注意：完整识别流程需要 Python 环境和 local-worker-ocr，属于集成测试。
/// </summary>
public class OcrServiceTests
{
    /// <summary>默认构造函数应创建有效的 OcrService 实例</summary>
    [Fact]
    public void DefaultConstructor_ShouldCreateValidInstance()
    {
        var service = new OcrService();

        Assert.NotNull(service);
        Assert.False(service.IsAvailable);
        Assert.NotNull(service.SupportedFormats);
        Assert.Contains(".png", service.SupportedFormats);
        Assert.Contains(".jpg", service.SupportedFormats);
        Assert.Contains(".bmp", service.SupportedFormats);
        Assert.Contains(".tiff", service.SupportedFormats);
        Assert.Contains(".webp", service.SupportedFormats);
    }

    /// <summary>构造函数传入有效参数应正确记录</summary>
    [Fact]
    public void Constructor_ShouldStoreParameters()
    {
        var pythonPath = @"D:\localPath\venvs\local-worker-ocr\Scripts\python.exe";
        var routerPath = @"D:\TT Tools\desktop\modules\ocr\DesktopOcr\ocr_router.py";

        var service = new OcrService(pythonPath, routerPath);

        Assert.NotNull(service);
        Assert.Equal("RapidOCR", service.EngineName);
    }

    /// <summary>构造函数传入 null pythonPath 应抛异常</summary>
    [Fact]
    public void Constructor_NullPythonPath_ShouldThrow()
    {
        Assert.Throws<ArgumentNullException>(() =>
            new OcrService(null!, @"D:\test\router.py"));
    }

    /// <summary>构造函数传入 null routerScriptPath 应抛异常</summary>
    [Fact]
    public void Constructor_NullRouterScriptPath_ShouldThrow()
    {
        Assert.Throws<ArgumentNullException>(() =>
            new OcrService(@"D:\python\python.exe", null!));
    }

    /// <summary>默认构造函数创建的服务不应可用</summary>
    [Fact]
    public void DefaultService_IsAvailable_ShouldBeFalse()
    {
        var service = new OcrService();
        Assert.False(service.IsAvailable);
        Assert.Null(service.AvailabilityError);
    }

    /// <summary>支持的格式应包含常见图片格式</summary>
    [Fact]
    public void SupportedFormats_ShouldContainCommonImageFormats()
    {
        var service = new OcrService();

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
    public void IsFormatSupported_ShouldValidateFileExtensions()
    {
        var service = new OcrService();

        Assert.True(service.IsFormatSupported(@"C:\test\image.png"));
        Assert.True(service.IsFormatSupported(@"C:\test\image.JPG"));
        Assert.True(service.IsFormatSupported(@"C:\test\image.TIFF"));
        Assert.True(service.IsFormatSupported(@"C:\test\image.webp"));
        Assert.False(service.IsFormatSupported(@"C:\test\document.pdf"));
        Assert.False(service.IsFormatSupported(@"C:\test\file.txt"));
        Assert.False(service.IsFormatSupported(@"C:\test\image.svg"));
    }

    /// <summary>默认构造函数时 RecognizeAsync 应抛异常（服务未启动）</summary>
    [Fact]
    public async Task RecognizeAsync_WithoutStart_ShouldThrow()
    {
        var service = new OcrService();

        // 服务未启动时应抛异常
        await Assert.ThrowsAsync<InvalidOperationException>(async () =>
            await service.RecognizeAsync(@"C:\test\image.png"));
    }

    /// <summary>PingAsync 在服务未启动时应返回 false</summary>
    [Fact]
    public async Task PingAsync_WithoutStart_ShouldReturnFalse()
    {
        var service = new OcrService();
        var result = await service.PingAsync();
        Assert.False(result);
    }

    /// <summary>RecognizeBatchAsync 在服务未启动时应抛异常</summary>
    [Fact]
    public async Task RecognizeBatchAsync_WithoutStart_ShouldThrow()
    {
        var service = new OcrService();

        await Assert.ThrowsAsync<InvalidOperationException>(async () =>
            await service.RecognizeBatchAsync(
                new List<string> { @"C:\test\image.png" }));
    }

    /// <summary>RecognizeWithJobTrackingAsync 无 JobManager 时应抛异常</summary>
    [Fact]
    public async Task RecognizeWithJobTrackingAsync_NoJobManager_ShouldThrow()
    {
        var service = new OcrService(
            @"D:\python\python.exe",
            @"D:\router.py",
            jobManager: null);

        await Assert.ThrowsAsync<InvalidOperationException>(async () =>
            await service.RecognizeWithJobTrackingAsync(
                new List<string> { @"C:\test\image.png" }));
    }

    /// <summary>EngineName 应返回 RapidOCR</summary>
    [Fact]
    public void EngineName_ShouldReturnRapidOCR()
    {
        var service = new OcrService();
        Assert.Equal("RapidOCR", service.EngineName);
    }

    /// <summary>Dispose 应安全处理（不抛异常）</summary>
    [Fact]
    public void Dispose_ShouldNotThrow()
    {
        var service = new OcrService(
            @"D:\python\python.exe",
            @"D:\router.py");

        var exception = Record.Exception(() => service.Dispose());
        Assert.Null(exception);
    }
}
