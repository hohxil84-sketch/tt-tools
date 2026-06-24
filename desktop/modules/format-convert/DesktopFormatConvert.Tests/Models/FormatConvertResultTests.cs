using System.Text.Json;
using TTTools.FormatConvert.Models;

namespace TTTools.FormatConvert.Tests.Models;

/// <summary>
/// FormatConvertResult 模型单元测试
/// 测试从 Python worker JSON 反序列化和 UI 辅助属性。
/// </summary>
public class FormatConvertResultTests
{
    /// <summary>构建标准成功的测试 JSON data</summary>
    private static JsonElement CreateSuccessData(
        int sourceW = 1920, int sourceH = 1080,
        int outputW = 800, int outputH = 600,
        string format = "jpeg", long outputSize = 102400,
        double compressionRatio = 0.5, double elapsed = 123.45,
        string outputPath = "D:/test/output.jpg")
    {
        // 使用 JSON 安全路径（反斜杠在 JSON 中需转义，直接用正斜杠）
        var escapedPath = outputPath.Replace("\\", "/");
        var json = $$"""
        {
            "output_path": "{{escapedPath}}",
            "source_width": {{sourceW}},
            "source_height": {{sourceH}},
            "output_width": {{outputW}},
            "output_height": {{outputH}},
            "output_format": "{{format}}",
            "output_size": {{outputSize}},
            "compression_ratio": {{(compressionRatio.ToString("F4", System.Globalization.CultureInfo.InvariantCulture))}},
            "elapsed_ms": {{(elapsed.ToString("F2", System.Globalization.CultureInfo.InvariantCulture))}},
            "warnings": ["测试警告1", "测试警告2"]
        }
        """;
        return JsonDocument.Parse(json).RootElement;
    }

    [Fact]
    public void FromRouterResponse_WithValidData_ShouldMapAllFields()
    {
        var data = CreateSuccessData();
        var result = FormatConvertResult.FromRouterResponse(data, "D:\\test\\input.png", "compress");

        Assert.True(result.IsSuccess);
        Assert.Contains("test", result.InputPath);
        Assert.Contains("output.jpg", result.OutputPath);
        Assert.Equal(1920, result.SourceWidth);
        Assert.Equal(1080, result.SourceHeight);
        Assert.Equal(800, result.OutputWidth);
        Assert.Equal(600, result.OutputHeight);
        Assert.Equal("jpeg", result.OutputFormat);
        Assert.Equal(102400, result.OutputSize);
        Assert.Equal(0.5, result.CompressionRatio);
        Assert.Equal(123.45, result.ElapsedMs);
        Assert.Equal("compress", result.OperationType);
        Assert.Equal(2, result.Warnings.Count);
        Assert.True(result.HasWarnings);
    }

    [Fact]
    public void FromRouterResponse_WithNullOutputPath_ShouldReturnEmpty()
    {
        var json = """
        {
            "output_path": null,
            "source_width": 100,
            "source_height": 50,
            "output_width": 100,
            "output_height": 50,
            "output_format": "png",
            "output_size": 0,
            "compression_ratio": 1.0,
            "elapsed_ms": 0
        }
        """;
        var data = JsonDocument.Parse(json).RootElement;
        var result = FormatConvertResult.FromRouterResponse(data, "input.png", "convert_format");

        Assert.Equal("", result.OutputPath);
        Assert.True(result.IsSuccess);
    }

    [Fact]
    public void InputFileName_WithPath_ShouldReturnFileName()
    {
        var data = CreateSuccessData();
        var result = FormatConvertResult.FromRouterResponse(data, "D:\\photos\\vacation.png", "crop");

        Assert.Equal("vacation.png", result.InputFileName);
    }

    [Fact]
    public void OutputFileName_WithPath_ShouldReturnFileName()
    {
        var data = CreateSuccessData(outputPath: "D:\\output\\vacation_cropped.png");
        var result = FormatConvertResult.FromRouterResponse(data, "input.png", "crop");

        Assert.Equal("vacation_cropped.png", result.OutputFileName);
    }

    [Fact]
    public void SourceSizeSummary_ShouldReturnFormattedString()
    {
        var data = CreateSuccessData(sourceW: 800, sourceH: 600);
        var result = FormatConvertResult.FromRouterResponse(data, "input.png", "rotate");

        Assert.Equal("800 x 600 px", result.SourceSizeSummary);
    }

    [Fact]
    public void SourceSizeSummary_ZeroDimensions_ShouldReturnUnknown()
    {
        var data = CreateSuccessData(sourceW: 0, sourceH: 0);
        var result = FormatConvertResult.FromRouterResponse(data, "input.png", "rotate");

        Assert.Equal("未知", result.SourceSizeSummary);
    }

    [Fact]
    public void SizeSummary_ShouldShowTransition()
    {
        var data = CreateSuccessData(sourceW: 1920, sourceH: 1080, outputW: 800, outputH: 600);
        var result = FormatConvertResult.FromRouterResponse(data, "input.png", "crop");

        Assert.Contains("1920 x 1080 px", result.SizeSummary);
        Assert.Contains("800 x 600 px", result.SizeSummary);
    }

    [Fact]
    public void OutputFormatSummary_ShouldFormatKB()
    {
        var data = CreateSuccessData(format: "jpeg", outputSize: 204800);
        var result = FormatConvertResult.FromRouterResponse(data, "input.png", "convert_format");

        Assert.Contains("JPEG", result.OutputFormatSummary.ToUpperInvariant());
        Assert.Contains("200.0 KB", result.OutputFormatSummary);
    }

    [Fact]
    public void CompressionRatioDisplay_LessThan1_ShouldShowCompression()
    {
        var data = CreateSuccessData(compressionRatio: 0.452);
        var result = FormatConvertResult.FromRouterResponse(data, "input.png", "compress");

        Assert.Contains("45.2%", result.CompressionRatioDisplay);
    }

    [Fact]
    public void CompressionRatioDisplay_EqualTo1_ShouldShowUncompressed()
    {
        var data = CreateSuccessData(compressionRatio: 1.0);
        var result = FormatConvertResult.FromRouterResponse(data, "input.png", "convert_format");

        Assert.Contains("未压缩", result.CompressionRatioDisplay);
    }

    [Fact]
    public void HasError_WhenFailedWithMessage_ShouldReturnTrue()
    {
        var result = new FormatConvertResult
        {
            IsSuccess = false,
            ErrorMessage = "处理失败",
        };

        Assert.True(result.HasError);
    }

    [Fact]
    public void HasError_WhenSuccess_ShouldReturnFalse()
    {
        var result = new FormatConvertResult { IsSuccess = true };

        Assert.False(result.HasError);
    }

    [Fact]
    public void HasWarnings_WithWarnings_ShouldReturnTrue()
    {
        var data = CreateSuccessData();
        var result = FormatConvertResult.FromRouterResponse(data, "input.png", "compress");

        Assert.True(result.HasWarnings);
    }

    [Fact]
    public void HasWarnings_WithoutWarnings_ShouldReturnFalse()
    {
        var json = """
        {
            "output_path": "out.png",
            "source_width": 100, "source_height": 100,
            "output_width": 100, "output_height": 100,
            "output_format": "png", "output_size": 1000,
            "compression_ratio": 1.0, "elapsed_ms": 5.0
        }
        """;
        var data = JsonDocument.Parse(json).RootElement;
        var result = FormatConvertResult.FromRouterResponse(data, "in.png", "rotate");

        Assert.False(result.HasWarnings);
    }

    [Fact]
    public void ElapsedDisplay_ShouldFormatMilliseconds()
    {
        var data = CreateSuccessData(elapsed: 1234.56);
        var result = FormatConvertResult.FromRouterResponse(data, "input.png", "rotate");

        Assert.Contains("1234.6 ms", result.ElapsedDisplay);
    }
}
