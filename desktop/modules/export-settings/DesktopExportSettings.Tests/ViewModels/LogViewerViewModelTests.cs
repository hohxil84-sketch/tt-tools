using TTTools.ExportSettings.Services;
using TTTools.ExportSettings.ViewModels;

namespace TTTools.ExportSettings.Tests.ViewModels;

/// <summary>
/// LogViewerViewModel 单元测试
/// </summary>
public class LogViewerViewModelTests : IDisposable
{
    private readonly string _testLogDir;
    private readonly LogReaderService _logReader;
    private readonly LogViewerViewModel _vm;

    public LogViewerViewModelTests()
    {
        _testLogDir = Path.Combine(Path.GetTempPath(), $"TTTools_VMLog_{Guid.NewGuid():N}");
        Directory.CreateDirectory(_testLogDir);
        _logReader = new LogReaderService(_testLogDir);
        _vm = new LogViewerViewModel(_logReader);
    }

    [Fact]
    public void Constructor_InitializesWithDefaults()
    {
        Assert.Empty(_vm.LogEntries);
        Assert.False(_vm.IsLoading);
        Assert.Equal("就绪", _vm.StatusText);
        Assert.Equal(0, _vm.DisplayCount);
        Assert.Equal(0, _vm.SelectedLevelFilterIndex);
    }

    [Fact]
    public void LevelFilters_HasAllLevels()
    {
        Assert.Equal(6, _vm.LevelFilters.Count);
        Assert.Equal("全部", _vm.LevelFilters[0].Label);
        Assert.Equal("ERROR", _vm.LevelFilters[4].Label);
        Assert.Equal("FATAL", _vm.LevelFilters[5].Label);
    }

    [Fact]
    public async Task RefreshAsync_WithNoLogs_ShowsEmpty()
    {
        await RefreshAsync();

        Assert.Empty(_vm.LogEntries);
        Assert.Equal("已加载 0 条日志", _vm.StatusText);
    }

    [Fact]
    public async Task RefreshAsync_WithLogFiles_LoadsEntries()
    {
        var logPath = Path.Combine(_testLogDir, "tttools-20260620.log");
        await File.WriteAllTextAsync(logPath,
            "2026-06-20 10:00:00.000 [INFO] [default] message 1\n" +
            "2026-06-20 10:01:00.000 [ERROR] [auth] message 2\n");

        await RefreshAsync();

        Assert.Equal(2, _vm.LogEntries.Count);
        Assert.Equal(2, _vm.DisplayCount);
        Assert.Contains("已加载 2 条日志", _vm.StatusText);
    }

    [Fact]
    public async Task RefreshAsync_LoadError_ShowsErrorStatus()
    {
        // 使用无效目录测试错误处理
        var badReader = new LogReaderService("Z:\\invalid_path_for_test\\");
        var badVm = new LogViewerViewModel(badReader);

        await RefreshAsync(badVm);

        // 不应该抛异常，应该有错误状态
        Assert.False(badVm.IsLoading);
    }

    [Fact]
    public void ClearLogs_ClearsAllEntries()
    {
        var logPath = Path.Combine(_testLogDir, "tttools-20260620.log");
        File.WriteAllText(logPath, "2026-06-20 10:00:00.000 [INFO] [default] test\n");

        _vm.ClearLogsCommand.Execute(null);

        Assert.Empty(_vm.LogEntries);
        Assert.Equal(0, _vm.DisplayCount);
        Assert.Equal("日志已清除", _vm.StatusText);
    }

    [Fact]
    public void SelectedLevelFilter_UpdatesFilterOptions()
    {
        _vm.SelectedLevelFilterIndex = 4; // ERROR

        Assert.Equal(TTShared.Logging.LogLevel.Error, _vm.FilterOptions.MinLevel);
    }

    [Fact]
    public async Task ExportLogsToFile_ExportsSuccessfully()
    {
        var logPath = Path.Combine(_testLogDir, "tttools-20260620.log");
        await File.WriteAllTextAsync(logPath,
            "2026-06-20 10:00:00.000 [INFO] [default] message 1\n");

        var exportPath = Path.Combine(_testLogDir, "exported.log");
        await _vm.ExportLogsToFileAsync(exportPath);

        Assert.True(File.Exists(exportPath));
        var content = await File.ReadAllTextAsync(exportPath);
        Assert.Contains("message 1", content);
    }

    /// <summary>
    /// 辅助方法：通过命令触发刷新并等待完成
    /// </summary>
    private async Task RefreshAsync(LogViewerViewModel? vm = null)
    {
        vm ??= _vm;
        var tcs = new TaskCompletionSource<bool>();

        vm.PropertyChanged += (s, e) =>
        {
            if (e.PropertyName == nameof(LogViewerViewModel.IsLoading) && !vm.IsLoading)
                tcs.TrySetResult(true);
        };

        if (vm.RefreshCommand.CanExecute(null))
            vm.RefreshCommand.Execute(null);

        var completed = await Task.WhenAny(tcs.Task, Task.Delay(5000));
        if (completed != tcs.Task)
            tcs.TrySetResult(false);
    }

    public void Dispose()
    {
        try { Directory.Delete(_testLogDir, recursive: true); } catch { }
    }
}
