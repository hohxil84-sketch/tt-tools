using TTTools.FormatConvert.Services;

namespace TTTools.FormatConvert.Tests.Services;

/// <summary>
/// FormatConvertService 单元测试
/// 本地免费功能：不需要 CloudApiClient 和 AuthState，不需要权限校验。
/// 测试构造函数、格式验证、初始状态和 Dispose 行为。
/// </summary>
public class FormatConvertServiceTests
{
    // ---- 构造函数的 null 校验 ----

    [Fact]
    public void Constructor_NullPythonPath_ShouldThrow()
    {
        Assert.Throws<ArgumentNullException>(() => new FormatConvertService(
            null!, "router.py"));
    }

    [Fact]
    public void Constructor_NullRouterScriptPath_ShouldThrow()
    {
        Assert.Throws<ArgumentNullException>(() => new FormatConvertService(
            "python.exe", null!));
    }

    [Fact]
    public void Constructor_WithValidArgs_ShouldNotThrow()
    {
        var ex = Record.Exception(() => new FormatConvertService("python.exe", "router.py"));
        Assert.Null(ex);
    }

    [Fact]
    public void DefaultConstructor_ShouldNotThrow()
    {
        var ex = Record.Exception(() => new FormatConvertService());
        Assert.Null(ex);
    }

    // ---- 格式支持校验 ----

    [Fact]
    public void IsFormatSupported_KnownFormat_ShouldReturnTrue()
    {
        var service = new FormatConvertService();
        Assert.True(service.IsFormatSupported("test.png"));
        Assert.True(service.IsFormatSupported("test.JPG"));
        Assert.True(service.IsFormatSupported("test.jpeg"));
        Assert.True(service.IsFormatSupported("test.webp"));
        Assert.True(service.IsFormatSupported("test.TIFF"));
        Assert.True(service.IsFormatSupported("test.tif"));
        Assert.True(service.IsFormatSupported("test.bmp"));
        Assert.True(service.IsFormatSupported("test.gif"));
        Assert.True(service.IsFormatSupported("test.ICO"));
    }

    [Fact]
    public void IsFormatSupported_UnknownFormat_ShouldReturnFalse()
    {
        var service = new FormatConvertService();
        Assert.False(service.IsFormatSupported("test.txt"));
        Assert.False(service.IsFormatSupported("test.pdf"));
        Assert.False(service.IsFormatSupported("test.psd"));
        Assert.False(service.IsFormatSupported("test.svg"));
    }

    [Fact]
    public void SupportedFormats_ShouldContainAllExpectedFormats()
    {
        Assert.Contains(".png", FormatConvertService.SupportedFormats);
        Assert.Contains(".jpg", FormatConvertService.SupportedFormats);
        Assert.Contains(".jpeg", FormatConvertService.SupportedFormats);
        Assert.Contains(".bmp", FormatConvertService.SupportedFormats);
        Assert.Contains(".tiff", FormatConvertService.SupportedFormats);
        Assert.Contains(".tif", FormatConvertService.SupportedFormats);
        Assert.Contains(".webp", FormatConvertService.SupportedFormats);
        Assert.Contains(".gif", FormatConvertService.SupportedFormats);
        Assert.Contains(".ico", FormatConvertService.SupportedFormats);
    }

    // ---- 初始状态 ----

    [Fact]
    public void InitialState_ShouldNotBeAvailable()
    {
        var service = new FormatConvertService("python.exe", "router.py");
        Assert.False(service.IsAvailable);
    }

    [Fact]
    public void InitialState_EngineNameShouldBePillow()
    {
        var service = new FormatConvertService();
        Assert.Contains("Pillow", service.EngineName);
    }

    // ---- 输出格式列表 ----

    [Fact]
    public void OutputFormatList_ShouldContainOriginal()
    {
        var original = FormatConvertService.OutputFormatList.FirstOrDefault(f => f.Value == "original");
        Assert.True(original != default);
        Assert.Equal("保持原格式", original.Display);
    }

    [Fact]
    public void OutputFormatList_ShouldContainAllSupportedFormats()
    {
        var values = FormatConvertService.OutputFormatList.Select(f => f.Value).ToHashSet();
        Assert.Contains("png", values);
        Assert.Contains("jpeg", values);
        Assert.Contains("bmp", values);
        Assert.Contains("tiff", values);
        Assert.Contains("webp", values);
        Assert.Contains("gif", values);
        Assert.Contains("ico", values);
    }

    // ---- 锚点列表 ----

    [Fact]
    public void AnchorList_ShouldContainAllAnchors()
    {
        var values = FormatConvertService.AnchorList.Select(a => a.Value).ToHashSet();
        Assert.Contains("center", values);
        Assert.Contains("top_left", values);
        Assert.Contains("top_right", values);
        Assert.Contains("bottom_left", values);
        Assert.Contains("bottom_right", values);
    }

    // ---- Dispose ----

    [Fact]
    public void Dispose_ShouldNotThrow()
    {
        var service = new FormatConvertService("python.exe", "router.py");
        var ex = Record.Exception(() => service.Dispose());
        Assert.Null(ex);
    }
}
