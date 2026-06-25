using TTShared.FileSystem;
using TTShared.JobSystem;
using TTShared.Logging;
using TTTools.IdPhoto.Models;
using TTTools.IdPhoto.Services;
using TTTools.IdPhoto.ViewModels;

namespace TTTools.IdPhoto.Tests.ViewModels;

/// <summary>
/// IdPhotoViewModel 单元测试
/// 覆盖初始状态、属性变更通知、命令状态、结果管理等场景。
/// </summary>
public class IdPhotoViewModelTests
{
    /// <summary>初始状态：服务未就绪、无结果、就绪消息</summary>
    [Fact]
    public void InitialState_ShouldHaveDefaultValues()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        Assert.False(vm.IsRunning);
        Assert.False(vm.IsServiceAvailable);
        Assert.False(vm.HasError);
        Assert.False(vm.CanStart);
        Assert.True(vm.CanCancel == false);
        Assert.False(vm.HasInputFile);
        Assert.False(vm.HasSelectedSpec);
        Assert.False(vm.HasSelectedBackground);
        Assert.False(vm.HasSelectedResult);
        Assert.Equal(0, vm.ResultCount);
        Assert.Equal(0, vm.SuccessCount);
        Assert.Equal(0, vm.FailedCount);
        Assert.Equal(300, vm.Dpi);
        Assert.True(vm.AutoDetectBackground);
        Assert.True(vm.EdgeFeather);
        Assert.Equal(0, vm.ProgressValue);
        Assert.Equal(100, vm.ProgressMax);
        Assert.Contains("引擎未连接", vm.ServiceStatusText);
    }

    /// <summary>Dpi 设置应在 72~600 之间自动限制</summary>
    [Fact]
    public void Dpi_ShouldClampToValidRange()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        vm.Dpi = 1000;
        Assert.Equal(600, vm.Dpi);

        vm.Dpi = 10;
        Assert.Equal(72, vm.Dpi);

        vm.Dpi = 300;
        Assert.Equal(300, vm.Dpi);
    }

    /// <summary>设置 CurrentInputPath 后 HasInputFile 应为 true</summary>
    [Fact]
    public void CurrentInputPath_ShouldUpdateHasInputFile()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        Assert.False(vm.HasInputFile);
        Assert.Equal("未选择文件", vm.InputFileName);

        vm.CurrentInputPath = @"C:\test\photo.jpg";

        Assert.True(vm.HasInputFile);
        Assert.Equal("photo.jpg", vm.InputFileName);
    }

    /// <summary>选择规格后 HasSelectedSpec 应为 true</summary>
    [Fact]
    public void SelectedSpec_ShouldUpdateHasSelectedSpec()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        Assert.False(vm.HasSelectedSpec);
        Assert.Contains("请选择规格", vm.SelectedSpecText);

        vm.SelectedSpec = new PhotoSpecItem
        {
            Name = "1寸",
            WidthMm = 25,
            HeightMm = 35,
            WidthPx = 295,
            HeightPx = 413,
            Dpi = 300
        };

        Assert.True(vm.HasSelectedSpec);
        Assert.Contains("1寸", vm.SelectedSpecText);
    }

    /// <summary>选择底色后 HasSelectedBackground 应为 true</summary>
    [Fact]
    public void SelectedBackgroundColor_ShouldUpdateHasSelectedBackground()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        Assert.False(vm.HasSelectedBackground);

        vm.SelectedBackgroundColor = new BackgroundColorItem
        {
            Name = "红色",
            Key = "red",
            R = 219,
            G = 0,
            B = 0,
            Hex = "#DB0000"
        };

        Assert.True(vm.HasSelectedBackground);
        Assert.Contains("红色", vm.SelectedBackgroundText);
        Assert.NotNull(vm.BackgroundColorPreview);
    }

    /// <summary>选择结果后 HasSelectedResult 应为 true</summary>
    [Fact]
    public void SelectedResult_ShouldUpdateDerivedProperties()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        Assert.False(vm.HasSelectedResult);

        var json = """
        {
            "output_path": "C:\\temp\\photo_id_photo.jpg",
            "input_path": "C:\\temp\\photo.jpg",
            "width_px": 295,
            "height_px": 413,
            "spec": {
                "name": "1寸",
                "width_mm": 25,
                "height_mm": 35,
                "width_px": 295,
                "height_px": 413,
                "dpi": 300
            },
            "background_color": {
                "name": "红色",
                "r": 219,
                "g": 0,
                "b": 0,
                "hex": "#DB0000",
                "bgr": [0, 0, 219]
            },
            "metadata": {
                "mask_method": "color_distance"
            }
        }
        """;

        var element = System.Text.Json.JsonDocument.Parse(json).RootElement;
        var result = IdPhotoResult.FromRouterResponse(element);

        vm.SelectedResult = result;

        Assert.True(vm.HasSelectedResult);
        Assert.Equal("photo.jpg", vm.SelectedInputFileName);
        Assert.Equal("295 × 413 px", vm.SelectedSizeSummary);
        Assert.Contains("1寸", vm.SelectedSpecSummary);
        Assert.Contains("红色", vm.SelectedBackgroundSummary);
        Assert.Equal("颜色距离法", vm.SelectedMaskMethod);
    }

    /// <summary>ClearResults 应重置所有状态</summary>
    [Fact]
    public void ClearResults_ShouldResetAllState()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        // 添加模拟结果
        var json = """
        {
            "output_path": "C:\\temp\\photo_id_photo.jpg",
            "input_path": "C:\\temp\\photo.jpg",
            "width_px": 295,
            "height_px": 413,
            "spec": {
                "name": "1寸",
                "width_mm": 25,
                "height_mm": 35,
                "width_px": 295,
                "height_px": 413,
                "dpi": 300
            },
            "background_color": {
                "name": "红色",
                "r": 219,
                "g": 0,
                "b": 0,
                "hex": "#DB0000",
                "bgr": [0, 0, 219]
            }
        }
        """;

        var element = System.Text.Json.JsonDocument.Parse(json).RootElement;
        var result = IdPhotoResult.FromRouterResponse(element);
        vm.Results.Add(result);
        vm.SelectedResult = result;

        // 清除
        vm.ClearResultsCommand.Execute(null);

        Assert.Equal(0, vm.ResultCount);
        Assert.Null(vm.SelectedResult);
        Assert.False(vm.HasError);
        Assert.Equal(0, vm.ProgressValue);
        Assert.Equal("请选择文件", vm.StatusMessage);
    }

    /// <summary>添加失败结果时 FailedCount 应递增</summary>
    [Fact]
    public void FailedCount_ShouldTrackFailedResults()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        var successResult = new IdPhotoResult
        {
            IsSuccess = true,
            InputPath = "ok.jpg",
            OutputPath = "ok_out.jpg"
        };
        var failedResult = new IdPhotoResult
        {
            IsSuccess = false,
            InputPath = "bad.jpg",
            ErrorMessage = "处理失败"
        };

        vm.Results.Add(successResult);
        vm.Results.Add(failedResult);

        Assert.Equal(2, vm.ResultCount);
        Assert.Equal(1, vm.SuccessCount);
        Assert.Equal(1, vm.FailedCount);
    }

    /// <summary>IsRunning 变更时 CanStart 和 CanCancel 应同步更新</summary>
    [Fact]
    public void IsRunning_ShouldUpdateCanStartAndCanCancel()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        Assert.False(vm.IsRunning);
        Assert.False(vm.CanStart); // 服务未就绪，没有输入文件

        // 模拟服务就绪且有输入文件
        typeof(IdPhotoViewModel).GetProperty(nameof(IdPhotoViewModel.IsServiceAvailable))
            ?.SetValue(vm, true);
        vm.CurrentInputPath = @"C:\test\photo.jpg";

        Assert.True(vm.CanStart);
        Assert.False(vm.CanCancel);

        // 模拟运行中
        typeof(IdPhotoViewModel).GetProperty(nameof(IdPhotoViewModel.IsRunning))
            ?.SetValue(vm, true);

        Assert.False(vm.CanStart);
        Assert.True(vm.CanCancel);
    }

    /// <summary>默认构造函数应创建有效的 ViewModel 实例</summary>
    [Fact]
    public void DefaultConstructor_ShouldCreateValidInstance()
    {
        var vm = new IdPhotoViewModel();

        Assert.NotNull(vm);
        Assert.NotNull(vm.SelectFileCommand);
        Assert.NotNull(vm.StartProcessCommand);
        Assert.NotNull(vm.CancelCommand);
        Assert.NotNull(vm.ExportResultCommand);
        Assert.NotNull(vm.ClearResultsCommand);
        Assert.NotNull(vm.SelectResultCommand);
        Assert.NotNull(vm.SelectBackgroundColorCommand);
    }

    /// <summary>服务可用时 ServiceStatusText 应显示就绪</summary>
    [Fact]
    public void ServiceStatusText_ShouldReflectAvailability()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        Assert.Contains("未连接", vm.ServiceStatusText);

        typeof(IdPhotoViewModel).GetProperty(nameof(IdPhotoViewModel.IsServiceAvailable))
            ?.SetValue(vm, true);

        Assert.Contains("就绪", vm.ServiceStatusText);
    }

    /// <summary>AutoDetectBackground 和 EdgeFeather 默认值应为 true</summary>
    [Fact]
    public void ProcessingOptions_ShouldDefaultToTrue()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        Assert.True(vm.AutoDetectBackground);
        Assert.True(vm.EdgeFeather);

        vm.AutoDetectBackground = false;
        vm.EdgeFeather = false;

        Assert.False(vm.AutoDetectBackground);
        Assert.False(vm.EdgeFeather);
    }

    /// <summary>PhotoSpecItem 显示属性应正确</summary>
    [Fact]
    public void PhotoSpecItem_DisplayText_ShouldBeCorrect()
    {
        var spec = new PhotoSpecItem
        {
            Name = "2寸",
            WidthMm = 35,
            HeightMm = 49,
            WidthPx = 413,
            HeightPx = 579,
            Dpi = 300
        };

        Assert.Equal("2寸 (35×49mm, 413×579px)", spec.DisplayText);
        Assert.Equal("35 × 49 mm", spec.SizeMmText);
        Assert.Equal("413 × 579 px", spec.SizePxText);
    }

    /// <summary>BackgroundColorItem 显示属性应正确</summary>
    [Fact]
    public void BackgroundColorItem_DisplayText_ShouldBeCorrect()
    {
        var color = new BackgroundColorItem
        {
            Name = "蓝色",
            Key = "blue",
            R = 67,
            G = 142,
            B = 219,
            Hex = "#438EDB"
        };

        Assert.Equal("蓝色 (#438EDB)", color.DisplayText);

        var mediaColor = color.ToMediaColor();
        Assert.Equal(67, mediaColor.R);
        Assert.Equal(142, mediaColor.G);
        Assert.Equal(219, mediaColor.B);

        var brush = color.ToBrush();
        Assert.NotNull(brush);
        Assert.Equal(mediaColor, brush.Color);
    }

    // ---- 交互逻辑测试 ----

    /// <summary>ProcessDroppedFile 只设置 CurrentInputPath，不自动触发处理</summary>
    [Fact]
    public void ProcessDroppedFile_ShouldOnlySetInputPath_NotTriggerProcessing()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        Assert.False(vm.IsRunning);
        Assert.False(vm.HasInputFile);

        // 设置输入路径（模拟选择/拖拽后的状态），不触发处理
        vm.CurrentInputPath = @"C:\test\photo.jpg";
        Assert.True(vm.HasInputFile);
        Assert.False(vm.IsRunning); // 未自动处理
    }

    /// <summary>取消后 StatusMessage 应反映已取消</summary>
    [Fact]
    public void Cancel_ShouldUpdateStatus()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        typeof(IdPhotoViewModel).GetProperty(nameof(IdPhotoViewModel.IsRunning))
            ?.SetValue(vm, true);

        vm.CancelCommand.Execute(null);

        Assert.Contains("取消", vm.StatusMessage);
    }

    /// <summary>无输入文件时 CanStart 为 false</summary>
    [Fact]
    public void CanStart_ShouldBeFalse_WhenNoInputFile()
    {
        var fs = new FileSystemService();
        var vm = new IdPhotoViewModel(null, fs);

        typeof(IdPhotoViewModel).GetProperty(nameof(IdPhotoViewModel.IsServiceAvailable))
            ?.SetValue(vm, true);
        Assert.False(vm.CanStart); // 无输入文件
    }
}
