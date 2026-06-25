using System.Text.Json;
using TTTools.OCR.Models;

namespace TTTools.OCR.Tests.ViewModels;

/// <summary>
/// OcrJobResult 和 OcrTextLine 模型单元测试
/// 覆盖模型属性、FromRouterResponse JSON 反序列化、
/// 低置信度 □ 遮罩、DisplayLines 坐标排序等场景。
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

    /// <summary>OcrTextLine IsLowConfidenceByThreshold 应按给定阈值判断</summary>
    [Fact]
    public void OcrTextLine_IsLowConfidenceByThreshold_ShouldUseGivenThreshold()
    {
        var line = new OcrTextLine { Score = 0.45 };

        // 阈值 0.5：应判定为低置信
        Assert.True(line.IsLowConfidenceByThreshold(0.5));
        // 阈值 0.4：不应判定为低置信
        Assert.False(line.IsLowConfidenceByThreshold(0.4));
        // 阈值 0.0：都不低
        Assert.False(line.IsLowConfidenceByThreshold(0.0));
    }

    /// <summary>OcrJobResult 应有正确的默认值</summary>
    [Fact]
    public void OcrJobResult_DefaultValues_ShouldBeEmpty()
    {
        var result = new OcrJobResult();

        Assert.NotNull(result.TextLines);
        Assert.Empty(result.TextLines);
        Assert.Equal(string.Empty, result.TotalText);
        Assert.Equal(string.Empty, result.FormattedText);
        Assert.Equal(0, result.LineCount);
        Assert.Equal(0.0, result.AvgScore);
        Assert.True(result.IsSuccess);
        Assert.Equal(0, result.HighConfidenceCount);
        Assert.Equal(0, result.LowConfidenceCount);
        Assert.Equal(0.5, result.ConfidenceThreshold); // 默认值
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

    /// <summary>HighConfidenceCount 应正确计数（>= 0.9）</summary>
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
        // 默认阈值 0.5
        Assert.Equal(2, result.LowConfidenceCount);
    }

    /// <summary>LowConfidenceCount 应按当前 ConfidenceThreshold 计算</summary>
    [Fact]
    public void OcrJobResult_LowConfidenceCount_ShouldUseThreshold()
    {
        var result = new OcrJobResult
        {
            TextLines = new List<OcrTextLine>
            {
                new() { Text = "行1", Score = 0.95 },
                new() { Text = "行2", Score = 0.75 },
                new() { Text = "行3", Score = 0.45 },
                new() { Text = "行4", Score = 0.30 },
            }
        };

        // 阈值 0.5：2 行低置信
        result.ConfidenceThreshold = 0.5;
        Assert.Equal(2, result.LowConfidenceCount);

        // 阈值 0.8：3 行低置信
        result.ConfidenceThreshold = 0.8;
        Assert.Equal(3, result.LowConfidenceCount);

        // 阈值 0.0：0 行低置信
        result.ConfidenceThreshold = 0.0;
        Assert.Equal(0, result.LowConfidenceCount);
    }

    /// <summary>低置信度行应替换为等长 □</summary>
    [Fact]
    public void DisplayLines_LowConfidence_ShouldMaskWithAsterisks()
    {
        var result = new OcrJobResult
        {
            ConfidenceThreshold = 0.5,
            ImageWidth = 400,
            TextLines = new List<OcrTextLine>
            {
                new() { Text = "Hello", Score = 0.95, Box = MakeBox(10, 10, 100, 30) },
                new() { Text = "金额", Score = 0.3, Box = MakeBox(10, 50, 80, 70) },
                new() { Text = "ABC123", Score = 0.2, Box = MakeBox(10, 90, 120, 110) },
            }
        };

        var lines = result.DisplayLines;
        Assert.Equal(3, lines.Count);

        // 高置信度：显示原文
        Assert.Equal("Hello", lines[0].DisplayText);
        Assert.False(lines[0].IsMasked);

        // 低置信度"金额"→ "□□"（2 个字符 → 2 个 □）
        Assert.Equal("□□", lines[1].DisplayText);
        Assert.True(lines[1].IsMasked);
        Assert.Equal("金额", lines[1].OriginalText);

        // 低置信度"ABC123"→ "□□□□□□"（6 个字符 → 6 个 □）
        Assert.Equal("□□□□□□", lines[2].DisplayText);
        Assert.True(lines[2].IsMasked);
        Assert.Equal("ABC123", lines[2].OriginalText);
    }

    /// <summary>高于或等于阈值的文字保留原文</summary>
    [Fact]
    public void DisplayLines_AboveThreshold_ShouldKeepOriginal()
    {
        var result = new OcrJobResult
        {
            ConfidenceThreshold = 0.6,
            ImageWidth = 400,
            TextLines = new List<OcrTextLine>
            {
                new() { Text = "测试文字", Score = 0.6, Box = MakeBox(10, 10, 100, 30) },
            }
        };

        var lines = result.DisplayLines;
        Assert.Single(lines);
        Assert.Equal("测试文字", lines[0].DisplayText);
        Assert.False(lines[0].IsMasked);
    }

    /// <summary>DisplayLines 应按坐标从上到下、从左到右排序</summary>
    [Fact]
    public void DisplayLines_ShouldSortByCoordinates()
    {
        var result = new OcrJobResult
        {
            ConfidenceThreshold = 0.5,
            ImageWidth = 400,
            TextLines = new List<OcrTextLine>
            {
                // 故意乱序添加
                new() { Text = "第三行", Score = 0.9, Box = MakeBox(10, 200, 120, 220) },
                new() { Text = "第一行", Score = 0.9, Box = MakeBox(10, 10, 120, 30) },
                new() { Text = "第二行右", Score = 0.9, Box = MakeBox(200, 100, 300, 120) },
                new() { Text = "第二行左", Score = 0.9, Box = MakeBox(10, 100, 100, 120) },
            }
        };

        var lines = result.DisplayLines;
        Assert.Equal(4, lines.Count);
        // 应按 y 坐标排序
        Assert.Equal("第一行", lines[0].DisplayText);
        Assert.Equal("第二行左", lines[1].DisplayText);
        Assert.Equal("第二行右", lines[2].DisplayText);
        Assert.Equal("第三行", lines[3].DisplayText);
    }

    /// <summary>FromRouterResponse 应正确解析 formatted_text</summary>
    [Fact]
    public void FromRouterResponse_ShouldParseFormattedText()
    {
        var json = """
        {
            "line_count": 2,
            "total_text": "Hello\nWorld",
            "formatted_text": "Hello    World",
            "text_lines": [
                {
                    "text": "Hello",
                    "score": 0.95,
                    "box": [[10, 20], [100, 20], [100, 40], [10, 40]]
                },
                {
                    "text": "World",
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
        Assert.Equal("Hello\nWorld", result.TotalText);
        Assert.Equal("Hello    World", result.FormattedText);  // formatted_text 正确解析
        Assert.Equal(2, result.TextLines.Count);
        Assert.Equal(1.5, result.ElapsedTotal);
    }

    /// <summary>FromRouterResponse 应正确解析完整 JSON 响应</summary>
    [Fact]
    public void FromRouterResponse_ShouldParseCompleteJson()
    {
        var json = """
        {
            "line_count": 2,
            "total_text": "测试文字行1测试文字行2",
            "formatted_text": "测试文字行1  测试文字行2",
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
            "formatted_text": "",
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
        Assert.Equal("", result.FormattedText);
        Assert.Empty(result.TextLines);
        Assert.Equal(0.0, result.AvgScore);
        Assert.Equal(0, result.HighConfidenceCount);
        Assert.Equal(0, result.LowConfidenceCount);
    }

    /// <summary>FromRouterResponse 缺少 formatted_text 时应使用空字符串</summary>
    [Fact]
    public void FromRouterResponse_MissingFormattedText_ShouldDefaultToEmpty()
    {
        var json = """
        {
            "line_count": 1,
            "total_text": "test",
            "text_lines": [
                { "text": "test", "score": 0.9, "box": [[0,0],[10,0],[10,10],[0,10]] }
            ],
            "elapsed": { "total": 0.1, "det": 0.05, "rec": 0.05 },
            "engine": { "name": "Test", "version": "1.0" }
        }
        """;

        var doc = JsonDocument.Parse(json);
        var result = OcrJobResult.FromRouterResponse(doc.RootElement);

        Assert.Equal("", result.FormattedText); // 未提供 formatted_text
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

    /// <summary>ConfidenceThreshold 变更应触发 PropertyChanged</summary>
    [Fact]
    public void ConfidenceThreshold_Change_ShouldNotifyPropertyChanged()
    {
        var result = new OcrJobResult();
        var notifiedProps = new List<string>();

        result.PropertyChanged += (sender, args) =>
        {
            if (args.PropertyName != null)
                notifiedProps.Add(args.PropertyName);
        };

        result.ConfidenceThreshold = 0.8;

        Assert.Contains(nameof(OcrJobResult.ConfidenceThreshold), notifiedProps);
        Assert.Contains(nameof(OcrJobResult.LowConfidenceCount), notifiedProps);
        Assert.Contains(nameof(OcrJobResult.DisplayLines), notifiedProps);
    }

    // ---- 辅助方法 ----

    /// <summary>创建模拟坐标框 [左上, 右上, 右下, 左下]</summary>
    private static List<List<double>> MakeBox(double x1, double y1, double x2, double y2)
    {
        // 简化为矩形框：左上 → 右上 → 右下 → 左下
        return new List<List<double>>
        {
            new() { x1, y1 },
            new() { x2, y1 },
            new() { x2, y2 },
            new() { x1, y2 },
        };
    }
}
