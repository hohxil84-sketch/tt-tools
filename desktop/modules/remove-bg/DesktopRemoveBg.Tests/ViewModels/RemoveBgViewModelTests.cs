using System.ComponentModel;
using TTShared.FileSystem;
using TTTools.RemoveBg.Models;
using TTTools.RemoveBg.ViewModels;

namespace TTTools.RemoveBg.Tests.ViewModels;

/// <summary>
/// RemoveBgViewModel 单元测试
/// 测试 ViewModel 的初始状态、属性变更通知、命令可执行性等不依赖 Python worker 的逻辑。
/// </summary>
public class RemoveBgViewModelTests
{
    [Fact]
    public void Constructor_Default_ShouldSetInitialState()
    {
        var vm = new RemoveBgViewModel();

        Assert.False(vm.IsServiceAvailable);
        Assert.False(vm.IsRunning);
        Assert.False(vm.HasError);
        Assert.False(vm.HasSelectedResult);
        Assert.Null(vm.SelectedResult);
        Assert.NotNull(vm.StatusMessage);
        Assert.Equal("请选择文件", vm.StatusMessage);
    }

    [Fact]
    public void Constructor_Default_ShouldSetDefaultParameters()
    {
        var vm = new RemoveBgViewModel();

        // 默认参数
        Assert.Equal("u2net", vm.SelectedModelName);
        Assert.False(vm.AlphaMatting);
        Assert.True(vm.OutputRgba);
        Assert.False(vm.SynthesizeBackground);
        Assert.Equal(255, vm.BgRed);
        Assert.Equal(255, vm.BgGreen);
        Assert.Equal(255, vm.BgBlue);
    }

    [Fact]
    public void Constructor_Default_ShouldCreateCommands()
    {
        var vm = new RemoveBgViewModel();

        Assert.NotNull(vm.SelectFilesCommand);
        Assert.NotNull(vm.StartProcessingCommand);
        Assert.NotNull(vm.CancelCommand);
        Assert.NotNull(vm.ClearResultsCommand);
        Assert.NotNull(vm.OpenOutputFileCommand);
        Assert.NotNull(vm.SelectResultCommand);
        Assert.NotNull(vm.SetWhiteBackgroundCommand);
        Assert.NotNull(vm.SetRedBackgroundCommand);
        Assert.NotNull(vm.SetBlueBackgroundCommand);
    }

    [Fact]
    public void Constructor_Default_CanStartShouldBeFalse()
    {
        var vm = new RemoveBgViewModel();
        Assert.False(vm.CanStart);
        Assert.False(vm.CanCancel);
    }

    [Fact]
    public void IsServiceAvailable_SetTrue_ShouldUpdateCanStart()
    {
        var vm = new RemoveBgViewModel();
        vm.IsServiceAvailable = true;
        // CanStart 还依赖 PendingFiles，此时无待处理文件 → false
        Assert.False(vm.CanStart);
        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.True(vm.CanStart);
        // ServiceStatusText 属性仍然保留供内部使用
        Assert.Equal("抠图引擎就绪", vm.ServiceStatusText);
    }

    [Fact]
    public void IsRunning_ShouldAffectCanStartAndCanCancel()
    {
        var vm = new RemoveBgViewModel();
        vm.IsServiceAvailable = true;
        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.True(vm.CanStart);

        vm.IsRunning = true;
        Assert.False(vm.CanStart);
        Assert.True(vm.CanCancel);

        vm.IsRunning = false;
        Assert.True(vm.CanStart);
        Assert.False(vm.CanCancel);
    }

    [Fact]
    public void ErrorMessage_ShouldUpdateHasError()
    {
        var vm = new RemoveBgViewModel();
        Assert.False(vm.HasError);

        vm.ErrorMessage = "测试错误";
        Assert.True(vm.HasError);

        vm.ErrorMessage = null;
        Assert.False(vm.HasError);
    }

    [Fact]
    public void SelectedResult_ShouldUpdateHasSelectedResult()
    {
        var vm = new RemoveBgViewModel();
        Assert.False(vm.HasSelectedResult);

        vm.SelectedResult = new RemoveBgResult
        {
            InputPath = "test.png",
            OutputPath = "test_remove_bg.png",
            Model = "u2net",
            IsSuccess = true
        };
        Assert.True(vm.HasSelectedResult);
    }

    [Fact]
    public void SelectedResult_Null_ShouldSetHasSelectedResultToFalse()
    {
        var vm = new RemoveBgViewModel();
        vm.SelectedResult = new RemoveBgResult { InputPath = "test.png" };
        Assert.True(vm.HasSelectedResult);

        vm.SelectedResult = null;
        Assert.False(vm.HasSelectedResult);
    }

    [Fact]
    public void BackgroundColor_ShouldUpdateIndividualChannels()
    {
        var vm = new RemoveBgViewModel();

        // 通过属性设置
        vm.BgRed = 128;
        vm.BgGreen = 64;
        vm.BgBlue = 32;

        Assert.Equal(128, vm.BgRed);
        Assert.Equal(64, vm.BgGreen);
        Assert.Equal(32, vm.BgBlue);
    }

    [Fact]
    public void BackgroundColor_Clamp_ShouldRestrictToValidRange()
    {
        var vm = new RemoveBgViewModel();

        vm.BgRed = 300;
        vm.BgGreen = -50;
        vm.BgBlue = 1000;

        Assert.Equal(255, vm.BgRed);
        Assert.Equal(0, vm.BgGreen);
        Assert.Equal(255, vm.BgBlue);
    }

    [Fact]
    public void SynthesizeBackground_SetTrue_ShouldShowColorPicker()
    {
        var vm = new RemoveBgViewModel();
        Assert.False(vm.ShowBackgroundColorPicker);

        vm.SynthesizeBackground = true;
        Assert.True(vm.ShowBackgroundColorPicker);
    }

    [Fact]
    public void OutputRgba_SetFalse_ShouldNotHideColorPicker()
    {
        var vm = new RemoveBgViewModel();
        vm.SynthesizeBackground = true;
        Assert.True(vm.ShowBackgroundColorPicker);

        vm.OutputRgba = false;
        // ShowBackgroundColorPicker 取决于 SynthesizeBackground，不取决于 OutputRgba
        Assert.True(vm.ShowBackgroundColorPicker);
    }

    [Fact]
    public void SetWhiteBackgroundCommand_ShouldSetWhiteColor()
    {
        var vm = new RemoveBgViewModel();
        vm.SetWhiteBackgroundCommand.Execute(null);

        Assert.Equal(255, vm.BgRed);
        Assert.Equal(255, vm.BgGreen);
        Assert.Equal(255, vm.BgBlue);
        Assert.True(vm.SynthesizeBackground);
    }

    [Fact]
    public void SetRedBackgroundCommand_ShouldSetRedColor()
    {
        var vm = new RemoveBgViewModel();
        vm.SetRedBackgroundCommand.Execute(null);

        Assert.Equal(255, vm.BgRed);
        Assert.Equal(0, vm.BgGreen);
        Assert.Equal(0, vm.BgBlue);
        Assert.True(vm.SynthesizeBackground);
    }

    [Fact]
    public void SetBlueBackgroundCommand_ShouldSetBlueColor()
    {
        var vm = new RemoveBgViewModel();
        vm.SetBlueBackgroundCommand.Execute(null);

        Assert.Equal(0, vm.BgRed);
        Assert.Equal(0, vm.BgGreen);
        Assert.Equal(255, vm.BgBlue);
        Assert.True(vm.SynthesizeBackground);
    }

    [Fact]
    public void Results_Add_ShouldUpdateCounts()
    {
        var vm = new RemoveBgViewModel();

        Assert.Equal(0, vm.ResultCount);
        Assert.Equal(0, vm.SuccessCount);
        Assert.Equal(0, vm.FailedCount);

        vm.Results.Add(new RemoveBgResult
        {
            InputPath = "test.png",
            IsSuccess = true
        });

        Assert.Equal(1, vm.ResultCount);
        Assert.Equal(1, vm.SuccessCount);
        Assert.Equal(0, vm.FailedCount);
    }

    [Fact]
    public void Results_AddFailed_ShouldUpdateFailedCount()
    {
        var vm = new RemoveBgViewModel();

        vm.Results.Add(new RemoveBgResult
        {
            InputPath = "bad.png",
            IsSuccess = false,
            ErrorMessage = "处理失败"
        });

        Assert.Equal(1, vm.ResultCount);
        Assert.Equal(0, vm.SuccessCount);
        Assert.Equal(1, vm.FailedCount);
    }

    [Fact]
    public void ClearResults_ShouldResetAll()
    {
        var vm = new RemoveBgViewModel();
        vm.Results.Add(new RemoveBgResult { InputPath = "test.png", IsSuccess = true });
        vm.SelectedResult = vm.Results[0];
        vm.ErrorMessage = "some error";

        vm.ClearResultsCommand.Execute(null);

        Assert.Equal(0, vm.ResultCount);
        Assert.Empty(vm.PendingFiles);
        Assert.Null(vm.SelectedResult);
        Assert.False(vm.HasError);
        Assert.Equal("请选择文件", vm.StatusMessage);
    }

    [Fact]
    public void ProgressValue_ShouldSetAndGet()
    {
        var vm = new RemoveBgViewModel();
        vm.ProgressValue = 50;
        Assert.Equal(50, vm.ProgressValue);

        vm.ProgressValue = 100;
        Assert.Equal(100, vm.ProgressValue);

        vm.ProgressValue = 0;
        Assert.Equal(0, vm.ProgressValue);
    }

    [Fact]
    public void AvailableModels_ShouldBeEmptyByDefault()
    {
        var vm = new RemoveBgViewModel();
        Assert.Empty(vm.AvailableModels);
    }

    [Fact]
    public void StatusMessage_ShouldUpdate()
    {
        var vm = new RemoveBgViewModel();
        vm.StatusMessage = "正在处理...";
        Assert.Equal("正在处理...", vm.StatusMessage);
    }

    // ---- 交互逻辑测试：选择不自动处理，开始才触发 ----

    /// <summary>ProcessDroppedFiles 只加入待处理列表，不自动触发处理</summary>
    [Fact]
    public void ProcessDroppedFiles_ShouldOnlyAddToPending_NotTriggerProcessing()
    {
        var vm = new RemoveBgViewModel();
        Assert.False(vm.IsRunning);
        Assert.Equal(0, vm.PendingFiles.Count);
        // 验证 HasPendingFiles 随 PendingFiles 变化
        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.True(vm.HasPendingFiles);
        Assert.Equal(1, vm.PendingFiles.Count);
        Assert.False(vm.IsRunning); // 仍在等待，未自动处理
    }

    /// <summary>无待处理文件时 CanStart 为 false</summary>
    [Fact]
    public void CanStart_ShouldBeFalse_WhenNoPendingFiles()
    {
        var vm = new RemoveBgViewModel();
        vm.IsServiceAvailable = true;
        Assert.False(vm.CanStart);
    }

    /// <summary>有待处理文件且服务可用时 CanStart 为 true</summary>
    [Fact]
    public void CanStart_ShouldBeTrue_WhenHasPendingFilesAndServiceAvailable()
    {
        var vm = new RemoveBgViewModel();
        vm.IsServiceAvailable = true;
        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.True(vm.CanStart);
    }

    /// <summary>服务不可用时 CanStart 为 false（即使有文件）</summary>
    [Fact]
    public void CanStart_ShouldBeFalse_WhenServiceUnavailable()
    {
        var vm = new RemoveBgViewModel();
        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.False(vm.CanStart); // 服务不可用
    }

    /// <summary>取消后 StatusMessage 应反映已取消</summary>
    [Fact]
    public void Cancel_ShouldUpdateStatus()
    {
        var vm = new RemoveBgViewModel();
        typeof(RemoveBgViewModel)
            .GetProperty(nameof(RemoveBgViewModel.IsRunning))!
            .SetValue(vm, true);

        vm.CancelCommand.Execute(null);

        Assert.Contains("取消", vm.StatusMessage);
    }

    /// <summary>PendingFiles 变更时 HasPendingFiles 应同步更新</summary>
    [Fact]
    public void PendingFiles_Add_ShouldUpdateHasPendingFiles()
    {
        var vm = new RemoveBgViewModel();
        Assert.False(vm.HasPendingFiles);
        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.True(vm.HasPendingFiles);
        Assert.Single(vm.PendingFiles);
    }
}
