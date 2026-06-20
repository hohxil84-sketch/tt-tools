using TTTools.ExportSettings.Services;
using TTTools.ExportSettings.ViewModels;
using TTShared.FileSystem;

namespace TTTools.ExportSettings.Tests.ViewModels;

/// <summary>
/// ExportViewModel 单元测试
/// </summary>
public class ExportViewModelTests : IDisposable
{
    private readonly string _testDir;
    private readonly ExportViewModel _vm;
    private readonly FileSystemService _fileSystem;
    private readonly ExportService _exportService;

    public ExportViewModelTests()
    {
        _testDir = Path.Combine(Path.GetTempPath(), $"TTTools_VMExport_{Guid.NewGuid():N}");
        Directory.CreateDirectory(_testDir);
        _fileSystem = new FileSystemService(_testDir);
        _exportService = new ExportService(_fileSystem);
        _vm = new ExportViewModel(_exportService, _fileSystem);
    }

    [Fact]
    public void Constructor_InitializesWithDefaults()
    {
        Assert.Empty(_vm.SourceFiles);
        Assert.Equal(0, _vm.Progress);
        Assert.False(_vm.IsExporting);
        Assert.Null(_vm.LastResult);
        Assert.NotNull(_vm.Config);
        Assert.NotNull(_vm.FormatLabels);
        Assert.Equal(4, _vm.FormatLabels.Count);
    }

    [Fact]
    public void AddFilePaths_ValidFiles_AddsToList()
    {
        var file1 = Path.Combine(_testDir, "test1.jpg");
        var file2 = Path.Combine(_testDir, "test2.png");
        File.WriteAllText(file1, "test");
        File.WriteAllText(file2, "test");

        _vm.AddFilePaths(new[] { file1, file2 });

        Assert.Equal(2, _vm.SourceFiles.Count);
        Assert.Contains(file1, _vm.SourceFiles);
        Assert.Contains(file2, _vm.SourceFiles);
    }

    [Fact]
    public void AddFilePaths_DuplicateFiles_SkipsDuplicate()
    {
        var file = Path.Combine(_testDir, "test.jpg");
        File.WriteAllText(file, "test");

        _vm.AddFilePaths(new[] { file });
        _vm.AddFilePaths(new[] { file });

        Assert.Single(_vm.SourceFiles);
    }

    [Fact]
    public void ClearFiles_RemovesAllFiles()
    {
        var file = Path.Combine(_testDir, "test.jpg");
        File.WriteAllText(file, "test");
        _vm.AddFilePaths(new[] { file });

        _vm.ClearFilesCommand.Execute(null);

        Assert.Empty(_vm.SourceFiles);
    }

    [Fact]
    public void RemoveFile_RemovesSpecificFile()
    {
        var file1 = Path.Combine(_testDir, "test1.jpg");
        var file2 = Path.Combine(_testDir, "test2.png");
        File.WriteAllText(file1, "test");
        File.WriteAllText(file2, "test");
        _vm.AddFilePaths(new[] { file1, file2 });

        _vm.RemoveFileCommand.Execute(file1);

        Assert.Single(_vm.SourceFiles);
        Assert.Contains(file2, _vm.SourceFiles);
    }

    [Fact]
    public void SetOutputDirectory_UpdatesConfig()
    {
        _vm.SetOutputDirectory("D:\\output");

        Assert.Equal("D:\\output", _vm.Config.OutputDirectory);
    }

    [Fact]
    public async Task StartExportAsync_NoFiles_ShowsWarning()
    {
        // 直接调用方法（绕过 AsyncRelayCommand 的 async void）
        await InvokeExportAsync();

        Assert.False(_vm.IsExporting);
        Assert.Contains("没有待导出的文件", _vm.ResultSummary);
    }

    [Fact]
    public async Task StartExportAsync_NoOutputDirectory_ShowsError()
    {
        var file = Path.Combine(_testDir, "test.jpg");
        File.WriteAllText(file, "test");
        _vm.AddFilePaths(new[] { file });

        await InvokeExportAsync();

        Assert.Contains("请先选择输出目录", _vm.ResultSummary);
    }

    [Fact]
    public async Task StartExportAsync_ValidConfig_ExportsSuccessfully()
    {
        var file = Path.Combine(_testDir, "test.jpg");
        await File.WriteAllTextAsync(file, "test content");
        _vm.AddFilePaths(new[] { file });
        var outputDir = Path.Combine(_testDir, "output");
        _vm.SetOutputDirectory(outputDir);

        await InvokeExportAsync();

        Assert.False(_vm.IsExporting);
        Assert.NotNull(_vm.LastResult);
        Assert.True(_vm.LastResult!.Success);
        Assert.Contains("导出完成", _vm.ResultSummary);
    }

    [Fact]
    public void SelectedFormatIndex_ChangesConfigFormat()
    {
        _vm.SelectedFormatIndex = 1; // "pdf"

        Assert.Equal("pdf", _vm.Config.Format);
    }

    [Fact]
    public void AddFilePaths_AfterExport_UpdatesProgressText()
    {
        var file = Path.Combine(_testDir, "test.jpg");
        File.WriteAllText(file, "test");

        _vm.AddFilePaths(new[] { file });

        Assert.Contains("已选择 1 个文件", _vm.ProgressText);
    }

    /// <summary>
    /// 辅助方法：通过反射调用私有 StartExportAsync
    /// 由于 AsyncRelayCommand.Execute 是 async void，直接用反射更可靠
    /// </summary>
    private async Task InvokeExportAsync()
    {
        // 通过命令触发（AsyncRelayCommand.Execute 是 async void，
        // 但我们在测试中需要等待完成）
        var tcs = new TaskCompletionSource<bool>();

        // 订阅 IsExporting 变化来检测完成
        var originalVm = _vm;
        originalVm.PropertyChanged += (s, e) =>
        {
            if (e.PropertyName == nameof(ExportViewModel.IsExporting) && !originalVm.IsExporting)
            {
                tcs.TrySetResult(true);
            }
        };

        // 触发命令
        if (_vm.StartExportCommand.CanExecute(null))
            _vm.StartExportCommand.Execute(null);

        // 等待完成（最多 5 秒）
        var completed = await Task.WhenAny(tcs.Task, Task.Delay(5000));
        if (completed != tcs.Task)
            tcs.TrySetResult(false); // timeout, allow test to continue
    }

    public void Dispose()
    {
        try { Directory.Delete(_testDir, recursive: true); } catch { }
    }
}
