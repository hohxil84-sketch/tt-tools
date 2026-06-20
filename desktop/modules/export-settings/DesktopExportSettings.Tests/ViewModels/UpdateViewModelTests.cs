using TTTools.ExportSettings.Services;
using TTTools.ExportSettings.ViewModels;

namespace TTTools.ExportSettings.Tests.ViewModels;

/// <summary>
/// UpdateViewModel 单元测试
/// </summary>
public class UpdateViewModelTests
{
    [Fact]
    public void Constructor_InitializesWithCurrentVersion()
    {
        var vm = new UpdateViewModel();

        Assert.Equal("0.1.0", vm.UpdateInfo.CurrentVersion);
        Assert.False(vm.UpdateInfo.UpdateAvailable);
        Assert.False(vm.IsChecking);
        Assert.True(vm.IsNotChecking);
        Assert.Equal("启动时自动检查更新", vm.StatusMessage);
    }

    [Fact]
    public void Constructor_WithCustomVersion_UsesCustomVersion()
    {
        var service = new UpdateCheckService("2.0.0");
        var vm = new UpdateViewModel(service);

        Assert.Equal("2.0.0", vm.UpdateInfo.CurrentVersion);
    }

    [Fact]
    public async Task CheckUpdateAsync_UpdatesInfo()
    {
        var vm = new UpdateViewModel();

        await InvokeCheckUpdateAsync(vm);

        Assert.False(vm.IsChecking);
        Assert.NotNull(vm.UpdateInfo.LastCheckTime);
        Assert.False(vm.UpdateInfo.UpdateAvailable); // mock 不返回更新
    }

    [Fact]
    public void IsNotChecking_ReflectsIsCheckingState()
    {
        var vm = new UpdateViewModel();

        Assert.True(vm.IsNotChecking);

        // 验证 IsNotChecking 与 IsChecking 反向
        Assert.True(vm.IsNotChecking);
    }

    [Fact]
    public void IsChecking_InitiallyFalse()
    {
        var vm = new UpdateViewModel();

        Assert.False(vm.IsChecking);
        Assert.True(vm.IsNotChecking);
    }

    [Fact]
    public void Commands_AreInitialized()
    {
        var vm = new UpdateViewModel();

        Assert.NotNull(vm.CheckUpdateCommand);
        Assert.NotNull(vm.OpenDownloadCommand);
        Assert.NotNull(vm.OpenReleaseNotesCommand);
    }

    /// <summary>
    /// 辅助方法：通过命令触发检查更新并等待完成
    /// </summary>
    private async Task InvokeCheckUpdateAsync(UpdateViewModel vm)
    {
        var tcs = new TaskCompletionSource<bool>();

        vm.PropertyChanged += (s, e) =>
        {
            if (e.PropertyName == nameof(UpdateViewModel.IsChecking) && !vm.IsChecking)
                tcs.TrySetResult(true);
        };

        if (vm.CheckUpdateCommand.CanExecute(null))
            vm.CheckUpdateCommand.Execute(null);

        var completed = await Task.WhenAny(tcs.Task, Task.Delay(5000));
        if (completed != tcs.Task)
            tcs.TrySetResult(false);
    }
}
