using System.Text.Json;
using TTTools.PreflightCheck.Models;

namespace TTTools.PreflightCheck.Tests.Models;

/// <summary>
/// PreflightCheckModels 单元测试
/// 覆盖报告模型创建、解析、静态工厂方法等场景。
/// </summary>
public class PreflightCheckModelsTests
{
    /// <summary>FromRouterResponse 应正确解析完整检查报告</summary>
    [Fact]
    public void FromRouterResponse_ShouldParseCompleteReport()
    {
        // 构造模拟的 Python worker 返回的 JSON
        var json = """
        {
            "file_path": "C:\\test\\image.png",
            "file_name": "image.png",
            "file_format": ".png",
            "file_size_bytes": 204800,
            "width": 1920,
            "height": 1080,
            "dpi": 300.0,
            "dpi_h": 300.0,
            "dpi_v": 300.0,
            "color_mode": "RGB",
            "has_transparency": false,
            "overall_risk": "warning",
            "has_errors": false,
            "has_warnings": true,
            "overall_message": "通过基本检查，但有 1 项注意事项",
            "checks": [
                {
                    "item": "file_format",
                    "risk_level": "pass",
                    "message": "文件格式 .png 受支持",
                    "details": {"format": ".png"}
                },
                {
                    "item": "dimensions",
                    "risk_level": "pass",
                    "message": "图像尺寸 1920×1080 满足最低要求",
                    "details": {"width": 1920, "height": 1080}
                },
                {
                    "item": "dpi",
                    "risk_level": "pass",
                    "message": "DPI 300 满足印刷要求",
                    "details": {"dpi": 300}
                },
                {
                    "item": "color_mode",
                    "risk_level": "warning",
                    "message": "颜色模式为 RGB，印刷时可能存在色差",
                    "details": {"color_mode": "RGB", "suggestion": "转换为 CMYK"}
                },
                {
                    "item": "transparency",
                    "risk_level": "pass",
                    "message": "图像无透明通道",
                    "details": {}
                },
                {
                    "item": "low_resolution",
                    "risk_level": "pass",
                    "message": "未检测到明显低清风险",
                    "details": {}
                },
                {
                    "item": "file_size",
                    "risk_level": "pass",
                    "message": "文件大小 200.0 KB，正常",
                    "details": {"file_size_bytes": 204800}
                }
            ]
        }
        """;

        using var doc = JsonDocument.Parse(json);
        var report = PreflightCheckReport.FromRouterResponse(doc.RootElement);

        // 基本属性
        Assert.Equal("image.png", report.FileName);
        Assert.Equal(".png", report.FileFormat);
        Assert.Equal(204800, report.FileSizeBytes);
        Assert.Equal(1920, report.Width);
        Assert.Equal(1080, report.Height);
        Assert.Equal(300.0, report.Dpi);
        Assert.Equal("RGB", report.ColorMode);
        Assert.False(report.HasTransparency);

        // 总体评估
        Assert.Equal(RiskLevel.Warning, report.OverallRisk);
        Assert.False(report.HasErrors);
        Assert.True(report.HasWarnings);

        // 检查项
        Assert.Equal(7, report.TotalCheckCount);
        Assert.Equal(6, report.PassCount);
        Assert.Equal(1, report.WarningCount);
        Assert.Equal(0, report.ErrorCount);

        // 第一个检查项
        var firstCheck = report.Checks[0];
        Assert.Equal(CheckItemType.FileFormat, firstCheck.Item);
        Assert.Equal(RiskLevel.Pass, firstCheck.RiskLevel);
        Assert.Equal("文件格式", firstCheck.ItemDisplayName);
        Assert.True(firstCheck.IsPass);
        Assert.False(firstCheck.IsWarning);
        Assert.False(firstCheck.IsError);
    }

    /// <summary>CreateFailedReport 应创建错误报告</summary>
    [Fact]
    public void CreateFailedReport_ShouldCreateErrorReport()
    {
        var report = PreflightCheckReport.CreateFailedReport(
            @"C:\test\bad.ico", "不支持的文件格式: .ico");

        Assert.Equal("bad.ico", report.FileName);
        Assert.Equal(RiskLevel.Error, report.OverallRisk);
        Assert.True(report.HasErrors);
        Assert.Single(report.Checks);
        Assert.Equal(CheckItemType.FileFormat, report.Checks[0].Item);
        Assert.Equal(RiskLevel.Error, report.Checks[0].RiskLevel);
    }

    /// <summary>所有检查项的 ItemDisplayName 均应返回中文名</summary>
    [Fact]
    public void CheckResultItem_AllDisplayNames_ShouldBeChinese()
    {
        var names = new Dictionary<CheckItemType, PreflightCheckResultItem>
        {
            [CheckItemType.FileFormat] = new() { Item = CheckItemType.FileFormat, RiskLevel = RiskLevel.Pass, Message = "" },
            [CheckItemType.Dimensions] = new() { Item = CheckItemType.Dimensions, RiskLevel = RiskLevel.Pass, Message = "" },
            [CheckItemType.Dpi] = new() { Item = CheckItemType.Dpi, RiskLevel = RiskLevel.Pass, Message = "" },
            [CheckItemType.ColorMode] = new() { Item = CheckItemType.ColorMode, RiskLevel = RiskLevel.Pass, Message = "" },
            [CheckItemType.Transparency] = new() { Item = CheckItemType.Transparency, RiskLevel = RiskLevel.Pass, Message = "" },
            [CheckItemType.LowResolution] = new() { Item = CheckItemType.LowResolution, RiskLevel = RiskLevel.Pass, Message = "" },
            [CheckItemType.FileSize] = new() { Item = CheckItemType.FileSize, RiskLevel = RiskLevel.Pass, Message = "" },
        };

        Assert.Equal("文件格式", names[CheckItemType.FileFormat].ItemDisplayName);
        Assert.Equal("图片尺寸", names[CheckItemType.Dimensions].ItemDisplayName);
        Assert.Equal("DPI 分辨率", names[CheckItemType.Dpi].ItemDisplayName);
        Assert.Equal("颜色模式", names[CheckItemType.ColorMode].ItemDisplayName);
        Assert.Equal("透明通道", names[CheckItemType.Transparency].ItemDisplayName);
        Assert.Equal("低清风险", names[CheckItemType.LowResolution].ItemDisplayName);
        Assert.Equal("文件大小", names[CheckItemType.FileSize].ItemDisplayName);
    }

    /// <summary>风险等级显示文本应正确</summary>
    [Fact]
    public void RiskLevelDisplay_ShouldShowCorrectText()
    {
        var passItem = new PreflightCheckResultItem { Item = CheckItemType.FileFormat, RiskLevel = RiskLevel.Pass, Message = "" };
        var warnItem = new PreflightCheckResultItem { Item = CheckItemType.FileFormat, RiskLevel = RiskLevel.Warning, Message = "" };
        var errorItem = new PreflightCheckResultItem { Item = CheckItemType.FileFormat, RiskLevel = RiskLevel.Error, Message = "" };

        Assert.Equal("通过", passItem.RiskLevelDisplay);
        Assert.Equal("警告", warnItem.RiskLevelDisplay);
        Assert.Equal("错误", errorItem.RiskLevelDisplay);
    }

    /// <summary>Report 展示属性应正确计算</summary>
    [Fact]
    public void Report_DisplayProperties_ShouldBeCorrect()
    {
        var report = new PreflightCheckReport
        {
            FilePath = @"C:\test\poster.jpg",
            FileName = "poster.jpg",
            FileFormat = ".jpg",
            FileSizeBytes = 2048000,
            Width = 3000,
            Height = 2000,
            Dpi = 300,
            ColorMode = "CMYK",
            HasTransparency = false,
            OverallRisk = RiskLevel.Pass,
            OverallMessage = "所有检查项均已通过，可以提交印刷。",
        };

        Assert.Equal(2000.0, report.FileSizeKB);
        Assert.Contains("MB", report.FileSizeDisplay);
        Assert.Equal("3000×2000", report.ImageSizeDisplay);
        Assert.Equal("300", report.DpiDisplay);
        Assert.Equal("CMYK", report.ColorModeDisplay);
        Assert.Contains("可以印刷", report.OverallRiskDisplay);
        Assert.Equal("通过", report.OverallRiskLabel);
    }
}
