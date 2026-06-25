using System.ComponentModel;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.FileSystem;
using TTShared.UI;
using TTTools.ResizeImage.Models;
using TTTools.ResizeImage.Services;
using TTTools.ResizeImage.ViewModels;

namespace TTTools.ResizeImage.Tests.ViewModels;

/// <summary>
/// ResizeImageViewModel 单元测试
/// 覆盖初始状态、模式切换可见性、预设选择、命令和状态管理。
/// </summary>
public class ResizeImageViewModelTests
{
    /// <summary>初始状态：默认参数值</summary>
    [Fact]
    public void InitialState_ShouldHaveDefaultValues()
    {
        var vm = new ResizeImageViewModel();

        Assert.Equal("fit", vm.SelectedMode);
        Assert.Equal("", vm.SelectedPreset);
        Assert.Equal(800, vm.Width);
        Assert.Equal(600, vm.Height);
        Assert.Equal(50.0, vm.ScalePercent);
        Assert.Equal("lanczos", vm.SelectedResample);
        Assert.True(vm.KeepAspect);
        Assert.Equal("original", vm.SelectedOutputFormat);
        Assert.False(vm.IsRunning);
        Assert.False(vm.IsServiceAvailable);
        Assert.False(vm.HasError);
        Assert.Empty(vm.Results);
        Assert.Null(vm.SelectedResult);
    }

    /// <summary>FIT 模式显示宽高输入</summary>
    [Fact]
    public void Mode_WhenFit_ShowWidthHeightShouldBeTrue()
    {
        var vm = new ResizeImageViewModel();
        vm.SelectedMode = "fit";
        Assert.True(vm.ShowWidthHeight);
        Assert.False(vm.ShowScalePercent);
        Assert.False(vm.ShowShortSide);
        Assert.False(vm.ShowLongSide);
    }

    /// <summary>SCALE 模式显示百分比</summary>
    [Fact]
    public void Mode_WhenScale_ShowScalePercentShouldBeTrue()
    {
        var vm = new ResizeImageViewModel();
        vm.SelectedMode = "scale";
        Assert.True(vm.ShowScalePercent);
        Assert.False(vm.ShowWidthHeight);
    }

    /// <summary>SHORT_SIDE 模式显示短边约束</summary>
    [Fact]
    public void Mode_WhenShortSide_ShowShortSideShouldBeTrue()
    {
        var vm = new ResizeImageViewModel();
        vm.SelectedMode = "short_side";
        Assert.True(vm.ShowShortSide);
    }

    /// <summary>LONG_SIDE 模式显示长边约束</summary>
    [Fact]
    public void Mode_WhenLongSide_ShowLongSideShouldBeTrue()
    {
        var vm = new ResizeImageViewModel();
        vm.SelectedMode = "long_side";
        Assert.True(vm.ShowLongSide);
    }

    /// <summary>EXACT 模式显示保持宽高比选项</summary>
    [Fact]
    public void Mode_WhenExact_ShowKeepAspectShouldBeTrue()
    {
        var vm = new ResizeImageViewModel();
        vm.SelectedMode = "exact";
        Assert.True(vm.ShowKeepAspect);
        Assert.True(vm.ShowWidthHeight);
    }

    /// <summary>CUSTOM_DPI 模式显示目标 DPI</summary>
    [Fact]
    public void Mode_WhenCustomDpi_ShowTargetDpiShouldBeTrue()
    {
        var vm = new ResizeImageViewModel();
        vm.SelectedMode = "custom_dpi";
        Assert.True(vm.ShowTargetDpi);
    }

    /// <summary>JPEG 输出格式时显示质量控件</summary>
    [Fact]
    public void OutputFormat_WhenJpeg_ShowJpegQualityShouldBeTrue()
    {
        var vm = new ResizeImageViewModel();
        vm.SelectedOutputFormat = "jpeg";
        Assert.True(vm.ShowJpegQuality);
        Assert.False(vm.ShowPngCompress);
    }

    /// <summary>PNG 输出格式时显示压缩控件</summary>
    [Fact]
    public void OutputFormat_WhenPng_ShowPngCompressShouldBeTrue()
    {
        var vm = new ResizeImageViewModel();
        vm.SelectedOutputFormat = "png";
        Assert.True(vm.ShowPngCompress);
    }

    /// <summary>WEBP 输出格式时显示质量控件</summary>
    [Fact]
    public void OutputFormat_WhenWebp_ShowWebpQualityShouldBeTrue()
    {
        var vm = new ResizeImageViewModel();
        vm.SelectedOutputFormat = "webp";
        Assert.True(vm.ShowWebpQuality);
    }

    /// <summary>选择预设后自动填入宽高并切换到 FIT 模式</summary>
    [Fact]
    public void SelectedPreset_WhenSet_ShouldUpdateWidthAndHeight()
    {
        var vm = new ResizeImageViewModel();
        vm.AvailablePresets.Add(new PresetInfo
        {
            Name = "id_1inch",
            Width = 295,
            Height = 413,
            Description = "一寸证件照"
        });

        vm.SelectedPreset = "id_1inch";

        Assert.Equal("fit", vm.SelectedMode);
        Assert.Equal(295, vm.Width);
        Assert.Equal(413, vm.Height);
    }

    /// <summary>所有命令都不为 null</summary>
    [Fact]
    public void AllCommands_ShouldNotBeNull()
    {
        var vm = new ResizeImageViewModel();

        Assert.NotNull(vm.SelectFilesCommand);
        Assert.NotNull(vm.StartProcessingCommand);
        Assert.NotNull(vm.CancelCommand);
        Assert.NotNull(vm.ClearResultsCommand);
        Assert.NotNull(vm.OpenOutputFileCommand);
        Assert.NotNull(vm.SelectResultCommand);
        Assert.NotNull(vm.SelectPresetCommand);
    }

    /// <summary>IsRunning 为 true 时 CanStart 为 false</summary>
    [Fact]
    public void CanStart_WhenRunning_ShouldBeFalse()
    {
        var vm = new ResizeImageViewModel();
        vm.IsServiceAvailable = true;
        Assert.True(vm.CanStart);

        // 通过反射设置 IsRunning
        typeof(ResizeImageViewModel)
            .GetProperty(nameof(ResizeImageViewModel.IsRunning))!
            .SetValue(vm, true);

        Assert.False(vm.CanStart);
    }

    /// <summary>IsServiceAvailable 为 false 时 CanStart 为 false</summary>
    [Fact]
    public void CanStart_WhenServiceUnavailable_ShouldBeFalse()
    {
        var vm = new ResizeImageViewModel();
        Assert.False(vm.CanStart);
    }

    /// <summary>HasError 在 ErrorMessage 不为空时为 true</summary>
    [Fact]
    public void HasError_WhenErrorMessageSet_ShouldBeTrue()
    {
        var vm = new ResizeImageViewModel();
        Assert.False(vm.HasError);

        vm.ErrorMessage = "测试错误";
        Assert.True(vm.HasError);

        vm.ErrorMessage = null;
        Assert.False(vm.HasError);
    }

    /// <summary>HasSelectedResult 在选择结果时为 true</summary>
    [Fact]
    public void HasSelectedResult_WhenResultSelected_ShouldBeTrue()
    {
        var vm = new ResizeImageViewModel();
        Assert.False(vm.HasSelectedResult);

        vm.SelectedResult = new ResizeImageResult();
        Assert.True(vm.HasSelectedResult);

        vm.SelectedResult = null;
        Assert.False(vm.HasSelectedResult);
    }

    /// <summary>增加值边界检查：Width 不能为负数</summary>
    [Fact]
    public void Width_WhenSetToZero_ShouldBeClampedToOne()
    {
        var vm = new ResizeImageViewModel();
        vm.Width = 0;
        Assert.Equal(1, vm.Width);
    }

    /// <summary>JPEG 质量边界：Clamp 到 1-100</summary>
    [Fact]
    public void JpegQuality_WhenOutOfRange_ShouldBeClamped()
    {
        var vm = new ResizeImageViewModel();
        vm.JpegQuality = 0;
        Assert.Equal(1, vm.JpegQuality);
        vm.JpegQuality = 200;
        Assert.Equal(100, vm.JpegQuality);
    }

    /// <summary>PropertyChanged 在 SelectedMode 变更时触发</summary>
    [Fact]
    public void SelectedMode_ShouldRaisePropertyChanged()
    {
        var vm = new ResizeImageViewModel();
        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName!);

        vm.SelectedMode = "exact";

        Assert.Contains(nameof(ResizeImageViewModel.SelectedMode), changedProps);
        Assert.Contains(nameof(ResizeImageViewModel.ShowKeepAspect), changedProps);
    }

    /// <summary>BuildParamsFromUI 默认生成正确的参数</summary>
    [Fact]
    public void BuildParamsFromUI_WithDefaults_ShouldReturnValidParams()
    {
        var vm = new ResizeImageViewModel();
        var param = vm.BuildParamsFromUI();

        Assert.Equal("fit", param.Mode);
        Assert.Equal(800, param.Width);
        Assert.Equal(600, param.Height);
        Assert.Equal("lanczos", param.Resample);
        Assert.True(param.KeepAspect);
        Assert.Equal("original", param.OutputFormat);
    }

    /// <summary>BuildParamsFromUI 在 SCALE 模式下只设置百分比</summary>
    [Fact]
    public void BuildParamsFromUI_WhenScale_ShouldSetScalePercent()
    {
        var vm = new ResizeImageViewModel();
        vm.SelectedMode = "scale";
        vm.ScalePercent = 75;
        var param = vm.BuildParamsFromUI();

        Assert.Equal("scale", param.Mode);
        Assert.Equal(75.0, param.ScalePercent);
        Assert.Null(param.Width);
    }

    /// <summary>ClearResults 清除所有状态</summary>
    [Fact]
    public void ClearResults_ShouldResetState()
    {
        var vm = new ResizeImageViewModel();
        vm.Results.Add(new ResizeImageResult());
        vm.SelectedResult = vm.Results[0];
        vm.ErrorMessage = "error";
        vm.ProgressValue = 50;

        vm.ClearResultsCommand.Execute(null);

        Assert.Empty(vm.Results);
        Assert.Null(vm.SelectedResult);
        Assert.Null(vm.ErrorMessage);
        Assert.Equal(0, vm.ProgressValue);
    }

    /// <summary>模式列表包含 7 个选项</summary>
    [Fact]
    public void ModeList_ShouldHaveSevenItems()
    {
        var vm = new ResizeImageViewModel();
        Assert.Equal(7, vm.ModeList.Count);
    }

    /// <summary>重采样列表包含 6 个选项</summary>
    [Fact]
    public void ResampleList_ShouldHaveSixItems()
    {
        var vm = new ResizeImageViewModel();
        Assert.Equal(6, vm.ResampleList.Count);
    }

    /// <summary>格式列表包含 6 个选项</summary>
    [Fact]
    public void FormatList_ShouldHaveSixItems()
    {
        var vm = new ResizeImageViewModel();
        Assert.Equal(6, vm.FormatList.Count);
    }
}
