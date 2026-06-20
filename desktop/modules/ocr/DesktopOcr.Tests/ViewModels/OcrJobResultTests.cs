using System.Text.Json;
using TTTools.OCR.Models;

namespace TTTools.OCR.Tests.ViewModels;

/// <summary>
/// OcrJobResult 和 OcrTextLine 模型单元测试
/// 覆盖模型属性、FromRouterResponse JSON 反序列化等场景。
/// </summary>
public class OcrJobResultTests
{
    /// <summary>OcrTextLine 应有正确的默认值</summary>
    [Fact]
    public void OcrTextLine_DefaultValues_ShouldBeEmpty()
    {
        var line = new OcrTextLine();

        Assert.Equal(string.Empty, line.Text);
        Assert.Equal(0.0, line.Score);
        Assert.NotNull(line.Box);
        Assert.Empty(line.Box);
    }

    /// <summary>OcrTextLine ScorePercent 应返回格式化的百分比</summary>
    [Fact]
    public void OcrTextLine_ScorePercent_ShouldFormatCorrectly()
    {
        var line = new OcrTextLine { Score = 0.95 };
        Assert.Equal("95.0%", line.ScorePercent);

        line.Score = 0.873;
        Assert.Equal("87.3%", line.ScorePercent);

        line.Score = 0.0;
        Assert.Equal("0.0%", line.ScorePercent);
    }

    /// <summary>OcrTextLine IsHighConfidence 应在 Score >= 0.9 时为 true</summary>
    [Fact]
    public void OcrTextLine_IsHighConfidence_ShouldBeBasedOnScore()
    {
        Assert.True(new OcrTextLine { Score = 0.95 }.IsHighConfidence);
        Assert.True(new OcrTextLine { Score = 0.90 }.IsHighConfidence);
        Assert.False(new OcrTextLine { Score = 0.89 }.IsHighConfidence);
        Assert.False(new OcrTextLine { Score = 0.5 }.IsHighConfidence);
    }

    /// <summary>OcrTextLine IsLowConfidence 应在 Score < 0.5 时为 true</summary>
    [Fact]
    public void OcrTextLine_IsLowConfidence_ShouldBeBasedOnScore()
    {
        Assert.True(new OcrTextLine { Score = 0.3 }.IsLowConfidence);
        Assert.True(new OcrTextLine { Score = 0.0 }.IsLowConfidence);
        Assert.False(new OcrTextLine { Score = 0.5 }.IsLowConfidence);
        Assert.False(new OcrTextLine { Score = 0.8 }.IsLowConfidence);
    }

    /// <summary>OcrJobResult 应有正确的默认值</summary>
    [Fact]
    public void OcrJobResult_DefaultValues_ShouldBeEmpty()
    {
        var result = new OcrJobResult();

        Assert.NotNull(result.TextLines);
        Assert.Empty(result.TextLines);
        Assert.Equal(string.Empty, result.TotalText);
        Assert.Equal(0, result.LineCount);
        Assert.Equal(0.0, result.AvgScore);
        Assert.True(result.IsSuccess);
        Assert.Equal(0, result.HighConfidenceCount);
        Assert.Equal(0, result.LowConfidenceCount);
    }

    /// <summary>OcrJobResult IsSuccess=false 应有错误消息</summary>
    [Fact]
    public void OcrJobResult_WhenFailed_ShouldHaveErrorMessage()
    {
        var result = new OcrJobResult
        {
            IsSuccess = false,
            ErrorMessage = "文件不存在"
        };

        Assert.False(result.IsSuccess);
        Assert.Equal("文件不存在", result.ErrorMessage);
    }

    /// <summary>ElapsedSummary 应正确格式化耗时信息</summary>
    [Fact]
    public void OcrJobResult_ElapsedSummary_ShouldFormatCorrectly()
    {
        var result = new OcrJobResult
        {
            ElapsedTotal = 2.345,
            ElapsedDet = 0.567,
            ElapsedRec = 1.234
        };

        var summary = result.ElapsedSummary;

        Assert.Contains("2.35", summary);   // 总耗时
        Assert.Contains("0.567", summary);  // 检测耗时
        Assert.Contains("1.234", summary);  // 识别耗时
    }

    /// <summary>HighConfidenceCount 和 LowConfidenceCount 应正确计数</summary>
    [Fact]
    public void OcrJobResult_ConfidenceCounts_ShouldBeCorrect()
    {
        var result = new OcrJobResult
        {
            TextLines = new List<OcrTextLine>
            {
                new() { Text = "高置信度行1", Score = 0.95 },
                new() { Text = "高置信度行2", Score = 0.92 },
                new() { Text = "正常行", Score = 0.75 },
                new() { Text = "低置信度行1", Score = 0.35 },
                new() { Text = "低置信度行2", Score = 0.20 },
            }
        };

        Assert.Equal(2, result.HighConfidenceCount);
        Assert.Equal(2, result.LowConfidenceCount);
    }

    /// <summary>FromRouterResponse 应正确解析完整 JSON 响应</summary>
    [Fact]
    public void FromRouterResponse_ShouldParseCompleteJson()
    {
        var json = """
        {
            "line_count": 2,
            "total_text": "测试文字行1测试文字行2",
            "text_lines": [
                {
                    "text": "测试文字行1",
                    "score": 0.95,
                    "box": [[10, 20], [100, 20], [100, 40], [10, 40]]
                },
                {
                    "text": "测试文字行2",
                    "score": 0.82,
                    "box": [[10, 60], [200, 60], [200, 80], [10, 80]]
                }
            ],
            "elapsed": {
                "total": 1.5,
                "det": 0.3,
                "rec": 1.0,
                "cls": 0.2
            },
            "engine": {
                "name": "RapidOCR",
                "version": "1.4.4"
            },
            "image": {
                "width": 800,
                "height": 600
            }
        }
        """;

        var doc = JsonDocument.Parse(json);
        var result = OcrJobResult.FromRouterResponse(doc.RootElement, @"C:\test.png");

        Assert.Equal(@"C:\test.png", result.FilePath);
        Assert.Equal(2, result.LineCount);
        Assert.Equal("测试文字行1测试文字行2", result.TotalText);
        Assert.Equal(2, result.TextLines.Count);
        Assert.Equal("测试文字行1", result.TextLines[0].Text);
        Assert.Equal(0.95, result.TextLines[0].Score);
        Assert.Equal(4, result.TextLines[0].Box.Count);
        Assert.Equal(2, result.TextLines[0].Box[0].Count);
        Assert.Equal(1.5, result.ElapsedTotal);
        Assert.Equal(0.3, result.ElapsedDet);
        Assert.Equal(1.0, result.ElapsedRec);
        Assert.Equal(0.2, result.ElapsedCls);
        Assert.Equal("RapidOCR", result.EngineName);
        Assert.Equal("1.4.4", result.EngineVersion);
        Assert.Equal(800, result.ImageWidth);
        Assert.Equal(600, result.ImageHeight);

        // 验证派生属性
        Assert.Equal(0.885, result.AvgScore, 3); // (0.95 + 0.82) / 2
        Assert.Equal(1, result.HighConfidenceCount);   // 0.95
        Assert.Equal(0, result.LowConfidenceCount);
    }

    /// <summary>FromRouterResponse 无文字行时应正确解析</summary>
    [Fact]
    public void FromRouterResponse_EmptyTextLines_ShouldHandleGracefully()
    {
        var json = """
        {
            "line_count": 0,
            "total_text": "",
            "text_lines": [],
            "elapsed": {
                "total": 0.5,
                "det": 0.3,
                "rec": 0.2
            },
            "engine": {
                "name": "RapidOCR",
                "version": "1.4.4"
            }
        }
        """;

        var doc = JsonDocument.Parse(json);
        var result = OcrJobResult.FromRouterResponse(doc.RootElement);

        Assert.Equal(0, result.LineCount);
        Assert.Equal("", result.TotalText);
        Assert.Empty(result.TextLines);
        Assert.Equal(0.0, result.AvgScore);
        Assert.Equal(0, result.HighConfidenceCount);
        Assert.Equal(0, result.LowConfidenceCount);
    }

    /// <summary>FromRouterResponse 缺少耗时字段时应使用默认值</summary>
    [Fact]
    public void FromRouterResponse_MissingElapsed_ShouldUseDefaults()
    {
        var json = """
        {
            "line_count": 0,
            "total_text": "",
            "text_lines": [],
            "engine": { "name": "Test", "version": "1.0" }
        }
        """;

        var doc = JsonDocument.Parse(json);
        var result = OcrJobResult.FromRouterResponse(doc.RootElement);

        Assert.Equal(0.0, result.ElapsedTotal);
        Assert.Equal(0.0, result.ElapsedDet);
        Assert.Equal(0.0, result.ElapsedRec);
    }

    /// <summary>ImageSizeSummary 应正确格式化图片尺寸</summary>
    [Fact]
    public void ImageSizeSummary_ShouldFormatCorrectly()
    {
        var resultWithSize = new OcrJobResult { ImageWidth = 1920, ImageHeight = 1080 };
        Assert.Equal("1920×1080", resultWithSize.ImageSizeSummary);

        var resultWithoutSize = new OcrJobResult();
        Assert.Equal("未知", resultWithoutSize.ImageSizeSummary);
    }
}
