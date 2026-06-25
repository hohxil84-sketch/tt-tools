using System.ComponentModel;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.FileSystem;
using TTTools.PdfImageConvert.Models;
using TTTools.PdfImageConvert.ViewModels;

namespace TTTools.PdfImageConvert.Tests.ViewModels;

/// <summary>
/// PdfImageConvertViewModel 单元测试
/// 覆盖初始状态、方向切换、CanStart 逻辑、PendingFiles 行为等场景。
/// </summary>
public class PdfImageConvertViewModelTests
{
    [Fact]
    public void Constructor_Default_ShouldSetInitialState()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);

        Assert.False(vm.IsServiceAvailable);
        Assert.False(vm.IsRunning);
        Assert.False(vm.HasError);
        Assert.False(vm.HasSelectedResult);
        Assert.Null(vm.SelectedResult);
        Assert.Equal("请选择文件", vm.StatusMessage);
        Assert.Equal("pdf_to_images", vm.SelectedDirection);
        Assert.Equal("png", vm.SelectedOutputFormat);
        Assert.Equal(200, vm.Dpi);
        Assert.Empty(vm.Results);
        Assert.Empty(vm.PendingFiles);
    }

    [Fact]
    public void Constructor_Default_ShouldCreateCommands()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);

        Assert.NotNull(vm.SelectFilesCommand);
        Assert.NotNull(vm.StartProcessingCommand);
        Assert.NotNull(vm.CancelCommand);
        Assert.NotNull(vm.ClearResultsCommand);
        Assert.NotNull(vm.OpenOutputFileCommand);
        Assert.NotNull(vm.SelectResultCommand);
    }

    [Fact]
    public void Constructor_Default_CanStartShouldBeFalse()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        Assert.False(vm.CanStart);
        Assert.False(vm.CanCancel);
    }

    [Fact]
    public void CanStart_WhenServiceAvailableAndHasPendingFiles_ShouldBeTrue()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        vm.IsServiceAvailable = true;
        Assert.False(vm.CanStart); // 无待处理文件

        vm.PendingFiles.Add(@"C:\test\document.pdf");
        Assert.True(vm.CanStart);
    }

    [Fact]
    public void CanStart_WhenRunning_ShouldBeFalse()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        vm.IsServiceAvailable = true;
        vm.PendingFiles.Add(@"C:\test\document.pdf");
        Assert.True(vm.CanStart);

        typeof(PdfImageConvertViewModel)
            .GetProperty(nameof(PdfImageConvertViewModel.IsRunning))!
            .SetValue(vm, true);

        Assert.False(vm.CanStart);
        Assert.True(vm.CanCancel);
    }

    [Fact]
    public void CanStart_WhenNoPendingFiles_ShouldBeFalse()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        vm.IsServiceAvailable = true;
        Assert.False(vm.CanStart);
    }

    [Fact]
    public void CanStart_WhenServiceUnavailable_ShouldBeFalse()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        vm.PendingFiles.Add(@"C:\test\document.pdf");
        Assert.False(vm.CanStart);
    }

    [Fact]
    public void SelectedDirection_ShouldUpdateIsPdfToImages()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);

        Assert.True(vm.IsPdfToImages); // default

        vm.SelectedDirection = "images_to_pdf";
        Assert.False(vm.IsPdfToImages);

        vm.SelectedDirection = "pdf_to_images";
        Assert.True(vm.IsPdfToImages);
    }

    [Fact]
    public void Dpi_ShouldClampToValidRange()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);

        vm.Dpi = 1000;
        Assert.Equal(600, vm.Dpi);

        vm.Dpi = 10;
        Assert.Equal(72, vm.Dpi);

        vm.Dpi = 300;
        Assert.Equal(300, vm.Dpi);
    }

    [Fact]
    public void HasError_WhenErrorMessageSet_ShouldBeTrue()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        Assert.False(vm.HasError);

        vm.ErrorMessage = "测试错误";
        Assert.True(vm.HasError);

        vm.ErrorMessage = null;
        Assert.False(vm.HasError);
    }

    [Fact]
    public void SelectedResult_ShouldUpdateHasSelectedResult()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        Assert.False(vm.HasSelectedResult);

        vm.SelectedResult = new PdfImageConvertResult
        {
            InputPath = "test.pdf",
            IsSuccess = true,
        };
        Assert.True(vm.HasSelectedResult);

        vm.SelectedResult = null;
        Assert.False(vm.HasSelectedResult);
    }

    [Fact]
    public void ClearResults_ShouldResetState()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        vm.Results.Add(new PdfImageConvertResult { InputPath = "test.pdf", IsSuccess = true });
        vm.SelectedResult = vm.Results[0];
        vm.ErrorMessage = "error";
        vm.ProgressValue = 50;
        vm.PendingFiles.Add(@"C:\test\new.pdf");

        vm.ClearResultsCommand.Execute(null);

        Assert.Empty(vm.Results);
        Assert.Empty(vm.PendingFiles);
        Assert.Null(vm.SelectedResult);
        Assert.Null(vm.ErrorMessage);
        Assert.Equal(0, vm.ProgressValue);
        Assert.Equal(100, vm.ProgressMax);
        Assert.Equal("请选择文件", vm.StatusMessage);
    }

    [Fact]
    public void BuildParamsFromUI_WithDefaults_ShouldReturnValidParams()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        var param = vm.BuildParamsFromUI();

        Assert.Equal("pdf_to_images", param.Direction);
        Assert.Equal("png", param.OutputFormat);
        Assert.Equal(200, param.Dpi);
        Assert.Equal(92, param.JpegQuality);
    }

    // ---- 交互逻辑测试 ----

    /// <summary>ProcessDroppedFiles 只加入待处理列表，不自动触发处理</summary>
    [Fact]
    public void ProcessDroppedFiles_ShouldOnlyAddToPending_NotTriggerProcessing()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        Assert.False(vm.IsRunning);
        Assert.Equal(0, vm.PendingFiles.Count);

        vm.PendingFiles.Add(@"C:\test\document.pdf");
        Assert.True(vm.HasPendingFiles);
        Assert.False(vm.IsRunning); // 仍在等待
    }

    /// <summary>取消后 StatusMessage 应反映已取消</summary>
    [Fact]
    public void Cancel_ShouldUpdateStatus()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        typeof(PdfImageConvertViewModel)
            .GetProperty(nameof(PdfImageConvertViewModel.IsRunning))!
            .SetValue(vm, true);

        vm.CancelCommand.Execute(null);

        Assert.Contains("取消", vm.StatusMessage);
    }

    /// <summary>PendingFiles 变更时 HasPendingFiles 应同步更新</summary>
    [Fact]
    public void PendingFiles_Add_ShouldUpdateHasPendingFiles()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        Assert.False(vm.HasPendingFiles);
        vm.PendingFiles.Add(@"C:\test\document.pdf");
        Assert.True(vm.HasPendingFiles);
        Assert.Single(vm.PendingFiles);
    }

    /// <summary>ServiceStatusText 属性仍保留供内部使用</summary>
    [Fact]
    public void ServiceStatusText_ShouldReflectAvailability()
    {
        var fs = new FileSystemService();
        var vm = new PdfImageConvertViewModel(null, null, fs);
        Assert.Contains("未连接", vm.ServiceStatusText);

        vm.IsServiceAvailable = true;
        Assert.Contains("就绪", vm.ServiceStatusText);
    }
}
