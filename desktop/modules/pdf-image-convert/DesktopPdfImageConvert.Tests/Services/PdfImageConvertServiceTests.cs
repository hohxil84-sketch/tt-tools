using System.Net;
using System.Net.Http;
using System.Text.Json;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;
using TTTools.PdfImageConvert.Models;
using TTTools.PdfImageConvert.Services;
using TTTools.PdfImageConvert.Tests.TestHelpers;

namespace TTTools.PdfImageConvert.Tests.Services;

/// <summary>
/// PdfImageConvertService 单元测试
/// C1: 覆盖权限 fail closed 所有场景。
/// C2: 使用 CloudApiClient(HttpClient, AuthState) + MockHttpMessageHandler 模拟接口。
/// </summary>
public class PdfImageConvertServiceTests
{
    /// <summary>
    /// 构建 PdfImageConvertService 用于测试（不连接真实 Python worker）。
    /// 不调用 StartAsync，因此所有 ConvertAsync 调用都会因服务未启动而失败——
    /// 但权限检查发生在服务可用性检查之前，我们可以测试权限拒绝路径。
    /// </summary>
    private static PdfImageConvertService CreateService(
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
        return new PdfImageConvertService(
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
                Feature = "pdf_image_convert_local_paid",
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
        Assert.Throws<ArgumentNullException>(() => new PdfImageConvertService(
            "python", "router", null!, new AuthState()));
    }

    [Fact]
    public void Constructor_NullAuthState_ShouldThrow()
    {
        var apiClient = new CloudApiClient("http://localhost", new AuthState());
        Assert.Throws<ArgumentNullException>(() => new PdfImageConvertService(
            "python", "router", apiClient, null!));
    }

    [Fact]
    public void Constructor_NullPythonPath_ShouldThrow()
    {
        var apiClient = new CloudApiClient("http://localhost", new AuthState());
        Assert.Throws<ArgumentNullException>(() => new PdfImageConvertService(
            null!, "router", apiClient, new AuthState()));
    }

    [Fact]
    public void Constructor_NullRouterPath_ShouldThrow()
    {
        var apiClient = new CloudApiClient("http://localhost", new AuthState());
        Assert.Throws<ArgumentNullException>(() => new PdfImageConvertService(
            "python", null!, apiClient, new AuthState()));
    }

    // ---- 格式校验 ----

    [Fact]
    public void IsPdfFormatSupported_Pdf_ShouldReturnTrue()
    {
        var service = new PdfImageConvertService();
        Assert.True(service.IsPdfFormatSupported("test.pdf"));
        Assert.True(service.IsPdfFormatSupported("test.PDF"));
    }

    [Fact]
    public void IsPdfFormatSupported_NonPdf_ShouldReturnFalse()
    {
        var service = new PdfImageConvertService();
        Assert.False(service.IsPdfFormatSupported("test.png"));
        Assert.False(service.IsPdfFormatSupported("test.txt"));
    }

    [Fact]
    public void IsImageFormatSupported_KnownFormat_ShouldReturnTrue()
    {
        var service = new PdfImageConvertService();
        Assert.True(service.IsImageFormatSupported("test.png"));
        Assert.True(service.IsImageFormatSupported("test.JPG"));
        Assert.True(service.IsImageFormatSupported("test.webp"));
        Assert.True(service.IsImageFormatSupported("test.TIFF"));
    }

    [Fact]
    public void IsImageFormatSupported_UnknownFormat_ShouldReturnFalse()
    {
        var service = new PdfImageConvertService();
        Assert.False(service.IsImageFormatSupported("test.txt"));
        Assert.False(service.IsImageFormatSupported("test.pdf"));
    }

    [Fact]
    public void IsFormatSupported_ShouldAcceptPdfAndImages()
    {
        var service = new PdfImageConvertService();
        Assert.True(service.IsFormatSupported("test.pdf"));
        Assert.True(service.IsFormatSupported("test.png"));
        Assert.False(service.IsFormatSupported("test.txt"));
    }

    [Fact]
    public void SupportedImageFormats_ShouldContainCommonFormats()
    {
        Assert.Contains(".png", PdfImageConvertService.SupportedImageFormats);
        Assert.Contains(".jpg", PdfImageConvertService.SupportedImageFormats);
        Assert.Contains(".bmp", PdfImageConvertService.SupportedImageFormats);
    }

    // ---- 权限检查（C1: fail closed） ----

    /// <summary>权限拒绝（Allowed=false）：返回 EntitlementAllowed=false，不执行转换</summary>
    [Fact]
    public async Task ConvertAsync_EntitlementDenied_ShouldReturnNotAllowed()
    {
        var service = CreateService(CreateEntitlementResponse(allowed: false));

        var param = new PdfImageConvertParams { Direction = "pdf_to_images", Dpi = 200 };
        // 文件不存在会先报文件不存在错误——但权限检查在文件校验之后
        // 我们需要一个实际存在的文件来测试权限路径
        var tempFile = Path.GetTempFileName();
        try
        {
            // 重命名为 PDF 扩展名以通过格式校验
            var pdfPath = Path.ChangeExtension(tempFile, ".pdf");
            File.Move(tempFile, pdfPath);
            tempFile = pdfPath;

            var result = await service.ConvertAsync(pdfPath, null, param);

            Assert.False(result.EntitlementAllowed);
            Assert.NotNull(result.EntitlementReason);
            Assert.False(result.IsSuccess);
        }
        finally
        {
            if (File.Exists(tempFile)) File.Delete(tempFile);
        }
    }

    /// <summary>权限拒绝（图片转 PDF）：返回 EntitlementAllowed=false</summary>
    [Fact]
    public async Task ConvertAsync_ImagesToPdf_EntitlementDenied_ShouldReturnNotAllowed()
    {
        var service = CreateService(CreateEntitlementResponse(allowed: false));

        var param = new PdfImageConvertParams { Direction = "images_to_pdf" };

        var tempFile = Path.GetTempFileName();
        try
        {
            var imgPath = Path.ChangeExtension(tempFile, ".png");
            File.Move(tempFile, imgPath);
            tempFile = imgPath;

            var result = await service.ConvertAsync(imgPath, null, param,
                inputPaths: new List<string> { imgPath });

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
    public async Task ConvertAsync_EntitlementAllowed_ButServiceNotStarted_ShouldReturnError()
    {
        var service = CreateService(CreateEntitlementResponse(allowed: true));

        var tempFile = Path.GetTempFileName();
        try
        {
            var pdfPath = Path.ChangeExtension(tempFile, ".pdf");
            File.Move(tempFile, pdfPath);
            tempFile = pdfPath;

            var param = new PdfImageConvertParams { Direction = "pdf_to_images", Dpi = 200 };
            var result = await service.ConvertAsync(pdfPath, null, param);

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
    public async Task ConvertAsync_NotLoggedIn_ShouldDenyWithoutNetworkCall()
    {
        var service = CreateService(isLoggedIn: false, entitlementResponse: CreateEntitlementResponse(true));
        // 输入文件不需要存在——未登录检查在文件校验之前

        var param = new PdfImageConvertParams { Direction = "pdf_to_images" };
        var result = await service.ConvertAsync("nonexistent.pdf", null, param);

        Assert.False(result.EntitlementAllowed);
        Assert.Contains("登录", result.EntitlementReason);
        Assert.False(result.IsSuccess);
    }

    /// <summary>文件不存在：报错（权限检查在文件校验之后，但结果正确）</summary>
    [Fact]
    public async Task ConvertAsync_PdfFileNotFound_ShouldReturnError()
    {
        var service = CreateService(CreateEntitlementResponse(allowed: true));

        var param = new PdfImageConvertParams { Direction = "pdf_to_images" };
        var result = await service.ConvertAsync("D:\\nonexistent\\file.pdf", null, param);

        Assert.False(result.IsSuccess);
        Assert.Contains("不存在", result.ErrorMessage);
    }

    /// <summary>不支持的格式：报错</summary>
    [Fact]
    public async Task ConvertAsync_UnsupportedFormat_ShouldReturnError()
    {
        var service = CreateService(CreateEntitlementResponse(allowed: true));

        var tempFile = Path.GetTempFileName();
        try
        {
            var param = new PdfImageConvertParams { Direction = "pdf_to_images" };
            var result = await service.ConvertAsync(tempFile, null, param);

            Assert.False(result.IsSuccess);
            Assert.Contains("不支持", result.ErrorMessage);
        }
        finally
        {
            if (File.Exists(tempFile)) File.Delete(tempFile);
        }
    }

    /// <summary>图片转 PDF 时图片列表为空：报错</summary>
    [Fact]
    public async Task ConvertAsync_ImagesToPdf_EmptyList_ShouldReturnError()
    {
        var service = CreateService(CreateEntitlementResponse(allowed: true));

        var param = new PdfImageConvertParams { Direction = "images_to_pdf" };
        var result = await service.ConvertAsync("empty", null, param,
            inputPaths: new List<string>());

        Assert.False(result.IsSuccess);
        Assert.Contains("图片列表为空", result.ErrorMessage);
    }

    // ---- 401 / null / error 响应拒绝（C1） ----

    /// <summary>HTTP 401：权限拒绝</summary>
    [Fact]
    public async Task ConvertAsync_Http401_ShouldDeny()
    {
        var handler = MockHttpMessageHandler.CreateErrorResponse(HttpStatusCode.Unauthorized);
        var httpClient = new HttpClient(handler) { BaseAddress = new Uri("http://test.local") };
        var authState = new AuthState();
        authState.SetLoggedIn("old_token", "refresh", 0,  // 立即过期，触发 401
            new UserInfo { Id = "u1", Account = "test", DisplayName = "测试", PlanCode = "standard" },
            new DeviceInfo { Id = "d1", Status = "active", IsNew = false });
        var apiClient = new CloudApiClient(httpClient, authState);
        var service = new PdfImageConvertService("python", "router", apiClient, authState);

        var tempFile = Path.GetTempFileName();
        try
        {
            var pdfPath = Path.ChangeExtension(tempFile, ".pdf");
            File.Move(tempFile, pdfPath);
            tempFile = pdfPath;

            var param = new PdfImageConvertParams { Direction = "pdf_to_images" };
            var result = await service.ConvertAsync(pdfPath, null, param);

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

    // ---- PdfImageConvertResult 模型测试 ----

    [Fact]
    public void PdfImageConvertResult_DirectionDisplay_ShouldReturnChinese()
    {
        var result = new PdfImageConvertResult { Direction = "pdf_to_images" };
        Assert.Equal("PDF → 图片", result.DirectionDisplay);

        result.Direction = "images_to_pdf";
        Assert.Equal("图片 → PDF", result.DirectionDisplay);
    }

    [Fact]
    public void PdfImageConvertResult_OutputSizeDisplay_ShouldFormatCorrectly()
    {
        var small = new PdfImageConvertResult { OutputSize = 500 };
        Assert.Equal("500 B", small.OutputSizeDisplay);

        var kb = new PdfImageConvertResult { OutputSize = 2048 };
        Assert.Equal("2.0 KB", kb.OutputSizeDisplay);

        var mb = new PdfImageConvertResult { OutputSize = 2097152 };
        Assert.Equal("2.0 MB", mb.OutputSizeDisplay);
    }

    [Fact]
    public void PdfImageConvertResult_HasWarnings_ShouldBeCorrect()
    {
        var noWarn = new PdfImageConvertResult();
        Assert.False(noWarn.HasWarnings);

        var withWarn = new PdfImageConvertResult { Warnings = new List<string> { "test" } };
        Assert.True(withWarn.HasWarnings);
    }

    [Fact]
    public void PdfImageConvertResult_FromRouterResponse_PdfToImages_ShouldParseCorrectly()
    {
        var json = JsonDocument.Parse(@"{
            ""output_dir"": ""D:\\output"",
            ""direction"": ""pdf_to_images"",
            ""source_format"": ""pdf"",
            ""total_pages"": 5,
            ""output_pages"": 5,
            ""output_format"": ""png"",
            ""output_size"": 123456,
            ""elapsed_ms"": 1234.56,
            ""pages"": [
                {""page_number"": 1, ""width"": 800, ""height"": 600, ""format"": ""png"", ""size_bytes"": 50000},
                {""page_number"": 2, ""width"": 800, ""height"": 600, ""format"": ""png"", ""size_bytes"": 48000}
            ],
            ""warnings"": [""warning1"", ""warning2""]
        }");

        var result = PdfImageConvertResult.FromRouterResponse(json.RootElement, "D:\\input.pdf");

        Assert.Equal("D:\\input.pdf", result.InputPath);
        Assert.Equal("D:\\output", result.OutputPath);
        Assert.Equal("pdf_to_images", result.Direction);
        Assert.Equal("pdf", result.SourceFormat);
        Assert.Equal(5, result.TotalPages);
        Assert.Equal(5, result.OutputPages);
        Assert.Equal(2, result.Pages.Count);
        Assert.Equal(1, result.Pages[0].PageNumber);
        Assert.Equal(800, result.Pages[0].Width);
        Assert.Equal(600, result.Pages[0].Height);
        Assert.Equal(50000, result.Pages[0].SizeBytes);
        Assert.Equal(123456, result.OutputSize);
        Assert.Equal(1234.56, result.ElapsedMs);
        Assert.Equal(2, result.Warnings.Count);
        Assert.True(result.IsSuccess);
    }

    [Fact]
    public void PdfImageConvertResult_FromRouterResponse_ImagesToPdf_ShouldParseCorrectly()
    {
        var json = JsonDocument.Parse(@"{
            ""output_path"": ""D:\\output\\merged.pdf"",
            ""direction"": ""images_to_pdf"",
            ""source_format"": ""images"",
            ""total_pages"": 3,
            ""output_pages"": 3,
            ""output_format"": ""pdf"",
            ""output_size"": 98765,
            ""elapsed_ms"": 567.89,
            ""pages"": [],
            ""warnings"": []
        }");

        var result = PdfImageConvertResult.FromRouterResponse(json.RootElement, "D:\\img1.png");

        Assert.Equal("D:\\output\\merged.pdf", result.OutputPath);
        Assert.Equal("images_to_pdf", result.Direction);
        Assert.Equal(3, result.TotalPages);
        Assert.Equal(567.89, result.ElapsedMs);
    }
}
