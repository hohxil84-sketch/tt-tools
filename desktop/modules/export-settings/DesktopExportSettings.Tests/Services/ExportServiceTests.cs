using TTTools.ExportSettings.Models;
using TTTools.ExportSettings.Services;
using TTTools.ExportSettings.Tests.TestHelpers;
using TTShared.FileSystem;

namespace TTTools.ExportSettings.Tests.Services;

/// <summary>
/// ExportService 服务单元测试
/// </summary>
public class ExportServiceTests : IDisposable
{
    private readonly string _testDir;
    private readonly ExportService _service;
    private readonly FileSystemService _fileSystem;

    public ExportServiceTests()
    {
        _testDir = Path.Combine(Path.GetTempPath(), $"TTTools_ExportTest_{Guid.NewGuid():N}");
        Directory.CreateDirectory(_testDir);
        _fileSystem = new FileSystemService(_testDir);
        _service = new ExportService(_fileSystem);
    }

    [Fact]
    public async Task ExportAsync_EmptySourceList_ReturnsSuccess()
    {
        var config = new ExportConfig { OutputDirectory = _testDir };
        var result = await _service.ExportAsync(new List<string>(), config);

        Assert.True(result.Success);
        Assert.Equal(0, result.SuccessCount);
    }

    [Fact]
    public async Task ExportAsync_SingleFile_ExportsSuccessfully()
    {
        // 创建测试源文件
        var sourceFile = Path.Combine(_testDir, "source.txt");
        await File.WriteAllTextAsync(sourceFile, "test content");

        var outputDir = Path.Combine(_testDir, "output");
        var config = new ExportConfig { OutputDirectory = outputDir };

        var result = await _service.ExportAsync(
            new List<string> { sourceFile }, config);

        Assert.True(result.Success);
        Assert.Equal(1, result.SuccessCount);
        Assert.Single(result.OutputPaths);
        Assert.True(File.Exists(result.OutputPaths[0]));
    }

    [Fact]
    public async Task ExportAsync_MultipleFiles_ExportsAll()
    {
        // 创建多个测试源文件
        var sourceFiles = new List<string>();
        for (int i = 0; i < 3; i++)
        {
            var path = Path.Combine(_testDir, $"source_{i}.txt");
            await File.WriteAllTextAsync(path, $"content {i}");
            sourceFiles.Add(path);
        }

        var outputDir = Path.Combine(_testDir, "output");
        var config = new ExportConfig { OutputDirectory = outputDir };

        var result = await _service.ExportAsync(sourceFiles, config);

        Assert.True(result.Success);
        Assert.Equal(3, result.SuccessCount);
        Assert.Equal(3, result.OutputPaths.Count);
        foreach (var outputPath in result.OutputPaths)
            Assert.True(File.Exists(outputPath));
    }

    [Fact]
    public async Task ExportAsync_MissingFile_RecordsError()
    {
        var missingFile = Path.Combine(_testDir, "does_not_exist.txt");
        var outputDir = Path.Combine(_testDir, "output");
        var config = new ExportConfig { OutputDirectory = outputDir };

        var result = await _service.ExportAsync(
            new List<string> { missingFile }, config);

        Assert.False(result.Success);
        Assert.Equal(0, result.SuccessCount);
        Assert.Equal(1, result.FailureCount);
        Assert.Single(result.Errors);
        Assert.Equal(missingFile, result.Errors[0].SourcePath);
    }

    [Fact]
    public async Task ExportAsync_FileNameConflict_GeneratesUniqueName()
    {
        var sourceFile = Path.Combine(_testDir, "file.txt");
        await File.WriteAllTextAsync(sourceFile, "content");

        var outputDir = Path.Combine(_testDir, "output");
        Directory.CreateDirectory(outputDir);

        // 预先创建同名文件
        var existingFile = Path.Combine(outputDir, "file.txt");
        await File.WriteAllTextAsync(existingFile, "existing");

        var config = new ExportConfig { OutputDirectory = outputDir, OverwriteExisting = false };

        var result = await _service.ExportAsync(
            new List<string> { sourceFile }, config);

        Assert.True(result.Success);
        Assert.Equal(1, result.SuccessCount);
        // 应该生成 file_1.txt
        Assert.Contains("_1.txt", result.OutputPaths[0]);
    }

    [Fact]
    public async Task ExportAsync_OverwriteEnabled_OverwritesExistingFile()
    {
        var sourceFile = Path.Combine(_testDir, "file.txt");
        await File.WriteAllTextAsync(sourceFile, "new content");

        var outputDir = Path.Combine(_testDir, "output");
        Directory.CreateDirectory(outputDir);
        var existingFile = Path.Combine(outputDir, "file.txt");
        await File.WriteAllTextAsync(existingFile, "old content");

        var config = new ExportConfig { OutputDirectory = outputDir, OverwriteExisting = true };

        var result = await _service.ExportAsync(
            new List<string> { sourceFile }, config);

        Assert.True(result.Success);
        var content = await File.ReadAllTextAsync(existingFile);
        Assert.Equal("new content", content);
    }

    [Fact]
    public async Task ExportAsync_ProgressCallback_ReportsProgress()
    {
        var sourceFiles = new List<string>();
        for (int i = 0; i < 5; i++)
        {
            var path = Path.Combine(_testDir, $"source_{i}.txt");
            await File.WriteAllTextAsync(path, $"content {i}");
            sourceFiles.Add(path);
        }

        var progress = new SynchronousProgress<(int current, int total)>();

        var outputDir = Path.Combine(_testDir, "output");
        var config = new ExportConfig { OutputDirectory = outputDir };

        await _service.ExportAsync(sourceFiles, config, progress);

        Assert.Equal(5, progress.ReportedValues.Count);
        Assert.Equal((5, 5), progress.ReportedValues[^1]);
    }

    [Fact]
    public async Task ExportAsync_Cancellation_CancelsMidExport()
    {
        var sourceFiles = new List<string>();
        for (int i = 0; i < 10; i++)
        {
            var path = Path.Combine(_testDir, $"source_{i}.txt");
            await File.WriteAllTextAsync(path, $"content {i}");
            sourceFiles.Add(path);
        }

        var outputDir = Path.Combine(_testDir, "output");
        var config = new ExportConfig { OutputDirectory = outputDir };
        var cts = new CancellationTokenSource();

        // 在处理第 3 个文件后取消
        var progress = new SynchronousProgress<(int current, int total)>(p =>
        {
            if (p.current >= 3)
                cts.Cancel();
        });

        await Assert.ThrowsAsync<OperationCanceledException>(() =>
            _service.ExportAsync(sourceFiles, config, progress, cts.Token));
    }

    [Fact]
    public async Task ExportAsync_InvalidOutputDirectory_CreatesDirectoryAndSucceeds()
    {
        var sourceFile = Path.Combine(_testDir, "source.txt");
        await File.WriteAllTextAsync(sourceFile, "test");

        // 使用不存在的嵌套目录
        var outputDir = Path.Combine(_testDir, "deep", "nested", "output");
        var config = new ExportConfig { OutputDirectory = outputDir };

        var result = await _service.ExportAsync(
            new List<string> { sourceFile }, config);

        Assert.True(result.Success);
        Assert.True(Directory.Exists(outputDir));
    }

    public void Dispose()
    {
        try { Directory.Delete(_testDir, recursive: true); } catch { }
    }
}
