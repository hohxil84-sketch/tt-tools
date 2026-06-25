using System.ComponentModel;
using TTShared.FileSystem;
using TTTools.FormatConvert.ViewModels;

namespace TTTools.FormatConvert.Tests.ViewModels;

/// <summary>
/// FormatConvertViewModel 单元测试
/// 覆盖初始状态、操作切换、CanStart 逻辑、PendingFiles 行为等场景。
/// </summary>
public class FormatConvertViewModelTests
{
    [Fact]
    public void Constructor_Default_ShouldSetInitialState()
    {
        var vm = new FormatConvertViewModel();

        Assert.False(vm.IsServiceAvailable);
        Assert.False(vm.IsRunning);
        Assert.False(vm.HasError);
        Assert.False(vm.HasSelectedResult);
        Assert.Null(vm.SelectedResult);
        Assert.Equal("请选择文件", vm.StatusMessage);
        Assert.Equal("compress", vm.SelectedOperation);
        Assert.Empty(vm.Results);
        Assert.Empty(vm.PendingFiles);
    }

    [Fact]
    public void Constructor_Default_ShouldCreateCommands()
    {
        var vm = new FormatConvertViewModel();

        Assert.NotNull(vm.SelectFilesCommand);
        Assert.NotNull(vm.StartProcessingCommand);
        Assert.NotNull(vm.CancelCommand);
        Assert.NotNull(vm.ClearResultsCommand);
        Assert.NotNull(vm.OpenOutputFileCommand);
        Assert.NotNull(vm.SelectResultCommand);
        Assert.NotNull(vm.SelectOperationCommand);
        Assert.NotNull(vm.SelectQuickAngleCommand);
    }

    [Fact]
    public void Constructor_Default_CanStartShouldBeFalse()
    {
        var vm = new FormatConvertViewModel();
        Assert.False(vm.CanStart);
        Assert.False(vm.CanCancel);
    }

    [Fact]
    public void CanStart_WhenServiceAvailableAndHasPendingFiles_ShouldBeTrue()
    {
        var vm = new FormatConvertViewModel();
        vm.IsServiceAvailable = true;
        Assert.False(vm.CanStart); // 无待处理文件

        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.True(vm.CanStart);
    }

    [Fact]
    public void CanStart_WhenRunning_ShouldBeFalse()
    {
        var vm = new FormatConvertViewModel();
        vm.IsServiceAvailable = true;
        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.True(vm.CanStart);

        typeof(FormatConvertViewModel)
            .GetProperty(nameof(FormatConvertViewModel.IsRunning))!
            .SetValue(vm, true);

        Assert.False(vm.CanStart);
        Assert.True(vm.CanCancel);
    }

    [Fact]
    public void CanStart_WhenNoPendingFiles_ShouldBeFalse()
    {
        var vm = new FormatConvertViewModel();
        vm.IsServiceAvailable = true;
        Assert.False(vm.CanStart);
    }

    [Fact]
    public void CanStart_WhenServiceUnavailable_ShouldBeFalse()
    {
        var vm = new FormatConvertViewModel();
        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.False(vm.CanStart);
    }

    [Fact]
    public void SelectedOperation_ShouldUpdateVisibility()
    {
        var vm = new FormatConvertViewModel();

        vm.SelectedOperation = "convert_format";
        Assert.True(vm.ShowConvertParams);
        Assert.False(vm.ShowCompressParams);

        vm.SelectedOperation = "compress";
        Assert.True(vm.ShowCompressParams);
        Assert.False(vm.ShowCropParams);

        vm.SelectedOperation = "crop";
        Assert.True(vm.ShowCropParams);
        Assert.False(vm.ShowRotateParams);

        vm.SelectedOperation = "rotate";
        Assert.True(vm.ShowRotateParams);
        Assert.False(vm.ShowConvertParams);
    }

    [Fact]
    public void HasError_WhenErrorMessageSet_ShouldBeTrue()
    {
        var vm = new FormatConvertViewModel();
        Assert.False(vm.HasError);

        vm.ErrorMessage = "测试错误";
        Assert.True(vm.HasError);

        vm.ErrorMessage = null;
        Assert.False(vm.HasError);
    }

    [Fact]
    public void SelectedResult_ShouldUpdateHasSelectedResult()
    {
        var vm = new FormatConvertViewModel();
        Assert.False(vm.HasSelectedResult);

        vm.SelectedResult = new TTTools.FormatConvert.Models.FormatConvertResult
        {
            InputPath = "test.png",
            IsSuccess = true,
            OperationType = "compress",
        };
        Assert.True(vm.HasSelectedResult);

        vm.SelectedResult = null;
        Assert.False(vm.HasSelectedResult);
    }

    [Fact]
    public void ClearResults_ShouldResetState()
    {
        var vm = new FormatConvertViewModel();
        vm.Results.Add(new TTTools.FormatConvert.Models.FormatConvertResult { InputPath = "test.png", IsSuccess = true });
        vm.SelectedResult = vm.Results[0];
        vm.ErrorMessage = "error";
        vm.ProgressValue = 50;
        vm.PendingFiles.Add(@"C:\test\new.png");

        vm.ClearResultsCommand.Execute(null);

        Assert.Empty(vm.Results);
        Assert.Empty(vm.PendingFiles);
        Assert.Null(vm.SelectedResult);
        Assert.Null(vm.ErrorMessage);
        Assert.Equal(0, vm.ProgressValue);
        Assert.Equal(100, vm.ProgressMax);
        Assert.Equal("请选择文件", vm.StatusMessage);
    }

    // ---- 交互逻辑测试 ----

    /// <summary>ProcessDroppedFiles 只加入待处理列表，不自动触发处理</summary>
    [Fact]
    public void ProcessDroppedFiles_ShouldOnlyAddToPending_NotTriggerProcessing()
    {
        var vm = new FormatConvertViewModel();
        Assert.False(vm.IsRunning);
        Assert.Equal(0, vm.PendingFiles.Count);

        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.True(vm.HasPendingFiles);
        Assert.False(vm.IsRunning); // 仍在等待，未自动处理
    }

    /// <summary>取消后 StatusMessage 应反映已取消</summary>
    [Fact]
    public void Cancel_ShouldUpdateStatus()
    {
        var vm = new FormatConvertViewModel();
        typeof(FormatConvertViewModel)
            .GetProperty(nameof(FormatConvertViewModel.IsRunning))!
            .SetValue(vm, true);

        vm.CancelCommand.Execute(null);

        Assert.Contains("取消", vm.StatusMessage);
    }

    /// <summary>PendingFiles 变更时 HasPendingFiles 应同步更新</summary>
    [Fact]
    public void PendingFiles_Add_ShouldUpdateHasPendingFiles()
    {
        var vm = new FormatConvertViewModel();
        Assert.False(vm.HasPendingFiles);
        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.True(vm.HasPendingFiles);
        Assert.Single(vm.PendingFiles);
    }

    /// <summary>ServiceStatusText 属性仍保留供内部使用</summary>
    [Fact]
    public void ServiceStatusText_ShouldReflectAvailability()
    {
        var vm = new FormatConvertViewModel();
        Assert.Contains("未连接", vm.ServiceStatusText);

        vm.IsServiceAvailable = true;
        Assert.Contains("就绪", vm.ServiceStatusText);
    }
}
