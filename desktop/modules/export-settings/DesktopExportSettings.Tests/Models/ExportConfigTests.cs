using TTTools.ExportSettings.Models;

namespace TTTools.ExportSettings.Tests.Models;

/// <summary>
/// ExportConfig 模型单元测试
/// </summary>
public class ExportConfigTests
{
    [Fact]
    public void ExportConfig_DefaultValues_AreCorrect()
    {
        var config = new ExportConfig();

        Assert.Equal("original", config.Format);
        Assert.Empty(config.OutputDirectory);
        Assert.Equal(90, config.JpegQuality);
        Assert.Equal(0, config.Dpi);
        Assert.False(config.OverwriteExisting);
        Assert.True(config.PreserveDirectoryStructure);
        Assert.Null(config.FileNamePrefix);
    }

    [Fact]
    public void SupportedFormats_ContainsExpectedFormats()
    {
        Assert.True(ExportConfig.SupportedFormats.ContainsKey("original"));
        Assert.True(ExportConfig.SupportedFormats.ContainsKey("pdf"));
        Assert.True(ExportConfig.SupportedFormats.ContainsKey("png"));
        Assert.True(ExportConfig.SupportedFormats.ContainsKey("jpeg"));
        Assert.Equal(4, ExportConfig.SupportedFormats.Count);
    }

    [Fact]
    public void ExportConfig_Properties_CanBeSet()
    {
        var config = new ExportConfig
        {
            Format = "png",
            OutputDirectory = "D:\\output",
            JpegQuality = 85,
            Dpi = 300,
            OverwriteExisting = true,
            PreserveDirectoryStructure = false,
            FileNamePrefix = "export_"
        };

        Assert.Equal("png", config.Format);
        Assert.Equal("D:\\output", config.OutputDirectory);
        Assert.Equal(85, config.JpegQuality);
        Assert.Equal(300, config.Dpi);
        Assert.True(config.OverwriteExisting);
        Assert.False(config.PreserveDirectoryStructure);
        Assert.Equal("export_", config.FileNamePrefix);
    }
}
