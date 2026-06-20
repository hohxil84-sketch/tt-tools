using TTTools.ExportSettings.Models;

namespace TTTools.ExportSettings.Tests.Models;

/// <summary>
/// ExportResult 模型单元测试
/// </summary>
public class ExportResultTests
{
    [Fact]
    public void AllSuccess_CreatesResultWithAllSuccess()
    {
        var paths = new List<string> { "D:\\out\\file1.png", "D:\\out\\file2.png" };

        var result = ExportResult.AllSuccess(paths, 1500);

        Assert.True(result.Success);
        Assert.Equal(2, result.SuccessCount);
        Assert.Equal(0, result.FailureCount);
        Assert.Equal(2, result.OutputPaths.Count);
        Assert.Empty(result.Errors);
        Assert.Equal(1500, result.ElapsedMs);
    }

    [Fact]
    public void WithFailures_CreatesResultWithPartialSuccess()
    {
        var paths = new List<string> { "D:\\out\\file1.png" };
        var errors = new List<ExportError>
        {
            new ExportError { SourcePath = "D:\\in\\bad.jpg", Message = "文件不存在" }
        };

        var result = ExportResult.WithFailures(1, paths, errors, 800);

        Assert.False(result.Success);
        Assert.Equal(1, result.SuccessCount);
        Assert.Equal(1, result.FailureCount);
        Assert.Single(result.OutputPaths);
        Assert.Single(result.Errors);
        Assert.Equal(800, result.ElapsedMs);
    }

    [Fact]
    public void WithFailures_NoErrors_IsSuccess()
    {
        var paths = new List<string> { "D:\\out\\file1.png" };
        var errors = new List<ExportError>();

        var result = ExportResult.WithFailures(1, paths, errors, 500);

        Assert.True(result.Success);
        Assert.Equal(1, result.SuccessCount);
        Assert.Equal(0, result.FailureCount);
    }

    [Fact]
    public void ExportError_Properties_CanBeSet()
    {
        var error = new ExportError
        {
            SourcePath = "D:\\in\\test.jpg",
            Message = "导出失败：磁盘空间不足",
            ExceptionType = "IOException"
        };

        Assert.Equal("D:\\in\\test.jpg", error.SourcePath);
        Assert.Equal("导出失败：磁盘空间不足", error.Message);
        Assert.Equal("IOException", error.ExceptionType);
    }
}
