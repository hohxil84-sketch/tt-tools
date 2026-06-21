using System.Text.Json;
using TTTools.ResizeImage.Models;

namespace TTTools.ResizeImage.Tests.Models;

/// <summary>
/// ResizeImageResult 模型单元测试
/// 覆盖默认值、显示属性和 FromRouterResponse 反序列化。
/// </summary>
public class ResizeImageResultTests
{
    /// <summary>默认结果 success 为 true（初始值）</summary>
    [Fact]
    public void Default_ShouldHaveExpectedDefaultValues()
    {
        var result = new ResizeImageResult();

        Assert.True(result.IsSuccess);
        Assert.Empty(result.InputPath);
        Assert.Empty(result.OutputPath);
        Assert.Equal(0, result.SourceWidth);
        Assert.Equal(0, result.SourceHeight);
        Assert.Equal(0, result.OutputWidth);
        Assert.Equal(0, result.OutputHeight);
        Assert.Empty(result.Warnings);
        Assert.True(result.HasPermission);
    }

    /// <summary>SourceSizeSummary 未知时显示"未知"</summary>
    [Fact]
    public void SourceSizeSummary_WhenUnknown_ShouldReturnUnknown()
    {
        var result = new ResizeImageResult();
        Assert.Equal("未知", result.SourceSizeSummary);
    }

    /// <summary>尺寸摘要格式正确</summary>
    [Fact]
    public void SourceSizeSummary_WithData_ShouldReturnFormattedString()
    {
        var result = new ResizeImageResult { SourceWidth = 1920, SourceHeight = 1080 };
        Assert.Equal("1920 x 1080 px", result.SourceSizeSummary);
    }

    /// <summary>ScaleRatio 为 1 时显示"原始"</summary>
    [Fact]
    public void ScaleRatioDisplay_WhenRatioIsOne_ShouldShowOriginal()
    {
        var result = new ResizeImageResult { ScaleRatio = 1.0 };
        Assert.Equal("1:1 (原始)", result.ScaleRatioDisplay);
    }

    /// <summary>ScaleRatio 小于 1 时显示"缩小"</summary>
    [Fact]
    public void ScaleRatioDisplay_WhenZoomOut_ShouldShowShrink()
    {
        var result = new ResizeImageResult { ScaleRatio = 0.5 };
        Assert.Contains("缩小", result.ScaleRatioDisplay);
    }

    /// <summary>ScaleRatio 大于 1 时显示"放大"</summary>
    [Fact]
    public void ScaleRatioDisplay_WhenZoomIn_ShouldShowEnlarge()
    {
        var result = new ResizeImageResult { ScaleRatio = 2.0 };
        Assert.Contains("放大", result.ScaleRatioDisplay);
    }

    /// <summary>OutputFormatSummary 格式正确</summary>
    [Fact]
    public void OutputFormatSummary_ShouldIncludeFormatAndSize()
    {
        var result = new ResizeImageResult { OutputFormat = "png", OutputSize = 12345 };
        Assert.Contains("PNG", result.OutputFormatSummary);
        Assert.Contains("12.1", result.OutputFormatSummary);
    }

    /// <summary>DpiSummary 无 DPI 时显示"保持原图"</summary>
    [Fact]
    public void DpiSummary_WhenNull_ShouldReturnPreserve()
    {
        var result = new ResizeImageResult();
        Assert.Equal("保持原图", result.DpiSummary);
    }

    /// <summary>DpiSummary 有 DPI 时显示"300 x 300"</summary>
    [Fact]
    public void DpiSummary_WithData_ShouldReturnFormattedString()
    {
        var result = new ResizeImageResult { DpiX = 300, DpiY = 300 };
        Assert.Equal("300 x 300", result.DpiSummary);
    }

    /// <summary>HasWarnings 在有警告时为 true</summary>
    [Fact]
    public void HasWarnings_WithWarnings_ShouldBeTrue()
    {
        var result = new ResizeImageResult { Warnings = new List<string> { "测试警告" } };
        Assert.True(result.HasWarnings);
    }

    /// <summary>HasWarnings 无警告时为 false</summary>
    [Fact]
    public void HasWarnings_WithoutWarnings_ShouldBeFalse()
    {
        var result = new ResizeImageResult();
        Assert.False(result.HasWarnings);
    }

    /// <summary>HasPermission 依赖于 EntitlementAllowed</summary>
    [Fact]
    public void HasPermission_WhenNotAllowed_ShouldBeFalse()
    {
        var result = new ResizeImageResult { EntitlementAllowed = false };
        Assert.False(result.HasPermission);
    }

    /// <summary>FromRouterResponse 正确解析 JSON</summary>
    [Fact]
    public void FromRouterResponse_ShouldParseCorrectly()
    {
        var jsonStr = @"{
            ""output_path"": ""D:/output/test_resized.png"",
            ""source_width"": 1920,
            ""source_height"": 1080,
            ""output_width"": 800,
            ""output_height"": 450,
            ""mode"": ""fit"",
            ""scale_ratio"": 0.416667,
            ""output_format"": ""png"",
            ""output_size"": 123456,
            ""dpi"": [300.0, 300.0],
            ""warnings"": [""非等比缩放警告""],
            ""elapsed_ms"": 45.50,
            ""preset"": ""id_1inch""
        }";

        var doc = JsonDocument.Parse(jsonStr);
        var result = ResizeImageResult.FromRouterResponse(doc.RootElement, "D:/input/test.png");

        Assert.True(result.IsSuccess);
        Assert.Equal("D:/input/test.png", result.InputPath);
        Assert.Equal("D:/output/test_resized.png", result.OutputPath);
        Assert.Equal(1920, result.SourceWidth);
        Assert.Equal(1080, result.SourceHeight);
        Assert.Equal(800, result.OutputWidth);
        Assert.Equal(450, result.OutputHeight);
        Assert.Equal("fit", result.Mode);
        Assert.Equal(0.416667, result.ScaleRatio, precision: 5);
        Assert.Equal("png", result.OutputFormat);
        Assert.Equal(123456, result.OutputSize);
        Assert.Equal(300.0, result.DpiX);
        Assert.Equal(300.0, result.DpiY);
        Assert.Single(result.Warnings);
        Assert.Equal(45.50, result.ElapsedMs);
        Assert.Equal("id_1inch", result.Preset);
    }

    /// <summary>FromRouterResponse 处理空警告</summary>
    [Fact]
    public void FromRouterResponse_NoWarnings_ShouldHaveEmptyList()
    {
        var jsonStr = @"{""output_path"": ""out.png"", ""source_width"": 100, ""source_height"": 100, ""output_width"": 100, ""output_height"": 100, ""mode"": ""fit"", ""scale_ratio"": 1.0, ""output_format"": ""png"", ""output_size"": 1000, ""elapsed_ms"": 10}";
        var doc = JsonDocument.Parse(jsonStr);
        var result = ResizeImageResult.FromRouterResponse(doc.RootElement, "in.png");

        Assert.Empty(result.Warnings);
    }
}
