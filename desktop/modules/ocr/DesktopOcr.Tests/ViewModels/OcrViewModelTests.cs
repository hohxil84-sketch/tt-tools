using System.ComponentModel;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTShared.Logging;
using TTTools.OCR.Models;
using TTTools.OCR.Services;
using TTTools.OCR.ViewModels;

namespace TTTools.OCR.Tests.ViewModels;

/// <summary>
/// OcrViewModel 单元测试
/// 覆盖初始状态、待识别列表行为、命令状态、进度更新等场景。
/// </summary>
public class OcrViewModelTests
{
    /// <summary>初始状态：服务未就绪、无结果、无待识别文件</summary>
    [Fact]
    public void InitialState_ShouldHaveDefaultValues()
    {
        var fs = new FileSystemService();
        var vm = new OcrViewModel(null, fs);

        Assert.False(vm.IsRunning);
        Assert.False(vm.IsServiceAvailable);
        Assert.False(vm.HasError);
        Assert.False(vm.CanStart);       // 无服务、无文件
        Assert.False(vm.CanCancel);
        Assert.False(vm.HasPendingFiles);
        Assert.Equal(0, vm.PendingFiles.Count);
        Assert.Equal(0, vm.ResultCount);
        Assert.Equal(0, vm.SuccessCount);
        Assert.Equal(0, vm.FailedCount);
        Assert.Equal(50, vm.TextScorePercent);
        Assert.Equal(0, vm.ProgressValue);
        Assert.Equal(100, vm.ProgressMax);
        Assert.NotNull(vm.StatusMessage);
        Assert.Contains("OCR 引擎未连接", vm.ServiceStatusText);
    }

    /// <summary>TextScorePercent 设置应在 0~100 之间自动限制</summary>
    [Fact]
    public void TextScorePercent_ShouldClampToValidRange()
    {
        var fs = new FileSystemService();
        var vm = new OcrViewModel(null, fs);

        vm.TextScorePercent = 150;
        Assert.Equal(100, vm.TextScorePercent);

        vm.TextScorePercent = -50;
        Assert.Equal(0, vm.TextScorePercent);

        vm.TextScorePercent = 70;
        Assert.Equal(70, vm.TextScorePercent);
    }

    /// <summary>服务可用且有文件且未运行 → CanStart 为 true</summary>
    [Fact]
    public void CanStart_WhenServiceAvailableAndHasPendingFiles_ShouldBeTrue()
    {
        var fs = new FileSystemService();
        var vm = new OcrViewModel(null, fs);

        Assert.False(vm.CanStart);

        // 模拟服务就绪
        typeof(OcrViewModel).GetProperty(nameof(OcrViewModel.IsServiceAvailable))
            ?.SetValue(vm, true);
        Assert.False(vm.CanStart); // 仍无文件

        // 添加待识别文件
        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.True(vm.CanStart);  // 服务可用 + 有文件 → 可开始
    }

    /// <summary>运行中时 CanStart 应为 false</summary>
    [Fact]
    public void CanStart_WhenRunning_ShouldBeFalse()
    {
        var fs = new FileSystemService();
        var vm = new OcrViewModel(null, fs);

        // 设置服务可用 + 有待识别文件
        typeof(OcrViewModel).GetProperty(nameof(OcrViewModel.IsServiceAvailable))
            ?.SetValue(vm, true);
        vm.PendingFiles.Add(@"C:\test\image.png");
        Assert.True(vm.CanStart);

        // 模拟运行中
        typeof(OcrViewModel).GetProperty(nameof(OcrViewModel.IsRunning))
            ?.SetValue(vm, true);
        Assert.False(vm.CanStart);
        Assert.True(vm.CanCancel);
    }

    /// <summary>没有待识别文件时 CanStart 应为 false</summary>
    [Fact]
    public void CanStart_WhenNoPendingFiles_ShouldBeFalse()
    {
        var fs = new FileSystemService();
        var vm = new OcrViewModel(null, fs);

        // 服务可用但无文件
        typeof(OcrViewModel).GetProperty(nameof(OcrViewModel.IsServiceAvailable))
            ?.SetValue(vm, true);
        Assert.False(vm.CanStart);
    }

    /// <summary>添加待识别文件后 HasPendingFiles 应为 true</summary>
    [Fact]
    public void PendingFiles_Add_ShouldUpdateHasPendingFiles()
    {
        var fs = new FileSystemService();
        var vm = new OcrViewModel(null, fs);

        Assert.False(vm.HasPendingFiles);

        vm.PendingFiles.Add(@"C:\test\photo.png");

        Assert.True(vm.HasPendingFiles);
        Assert.Equal(1, vm.PendingFiles.Count);
    }

    /// <summary>选择结果后 HasSelectedResult 应为 true</summary>
    [Fact]
    public void SelectedResult_ShouldUpdateDerivedProperties()
    {
        var fs = new FileSystemService();
        var vm = new OcrViewModel(null, fs);

        Assert.False(vm.HasSelectedResult);

        var result = new OcrJobResult
        {
            IsSuccess = true,
            FilePath = @"C:\test\image.png",
            TotalText = "Hello World",
            FormattedText = "Hello  World",
            LineCount = 1,
            TextLines = new List<OcrTextLine>
            {
                new() { Text = "Hello World", Score = 0.95 }
            },
            ElapsedTotal = 1.5,
            ElapsedDet = 0.3,
            ElapsedRec = 1.0,
            ImageWidth = 800,
            ImageHeight = 600,
            EngineName = "RapidOCR",
            EngineVersion = "1.4.4"
        };

        vm.SelectedResult = result;

        Assert.True(vm.HasSelectedResult);
        Assert.Equal("Hello World", vm.SelectedTotalText);
        Assert.Equal("Hello  World", vm.SelectedFormattedText);
        Assert.Equal(1, vm.SelectedTextLineCount);
    }

    /// <summary>没有 FormattedText 时 SelectedFormattedText 回退到 TotalText</summary>
    [Fact]
    public void SelectedFormattedText_WhenEmpty_ShouldFallbackToTotalText()
    {
        var fs = new FileSystemService();
        var vm = new OcrViewModel(null, fs);

        var result = new OcrJobResult
        {
            IsSuccess = true,
            TotalText = "Fallback Text",
            FormattedText = "",
        };

        vm.SelectedResult = result;

        Assert.Equal("Fallback Text", vm.SelectedFormattedText);
    }

    /// <summary>ClearResults 应清空待识别列表和进度</summary>
    [Fact]
    public void ClearResults_ShouldClearPendingFilesAndProgress()
    {
        var fs = new FileSystemService();
        var vm = new OcrViewModel(null, fs);

        // 添加模拟状态
        var result = new OcrJobResult { IsSuccess = true, FilePath = "test.png" };
        vm.Results.Add(result);
        vm.SelectedResult = result;
        vm.PendingFiles.Add(@"C:\test\new.png");
        vm.ProgressValue = 50;
        vm.ProgressMax = 10;

        // 清除
        vm.ClearResultsCommand.Execute(null);

        Assert.Equal(0, vm.ResultCount);
        Assert.Equal(0, vm.PendingFiles.Count);
        Assert.False(vm.HasPendingFiles);
        Assert.Null(vm.SelectedResult);
        Assert.False(vm.HasError);
        Assert.Equal(0, vm.ProgressValue);
        Assert.Equal(100, vm.ProgressMax);
        Assert.Contains("已清除", vm.StatusMessage);
    }

    /// <summary>添加失败结果时 FailedCount 应递增</summary>
    [Fact]
    public void FailedCount_ShouldTrackFailedResults()
    {
        var fs = new FileSystemService();
        var vm = new OcrViewModel(null, fs);

        var successResult = new OcrJobResult { IsSuccess = true, FilePath = "ok.png" };
        var failedResult = new OcrJobResult { IsSuccess = false, FilePath = "bad.png", ErrorMessage = "error" };

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
        var vm = new OcrViewModel(null, fs);

        Assert.False(vm.IsRunning);
        Assert.False(vm.CanStart); // 服务未就绪

        // 模拟服务就绪 + 有待识别文件
        typeof(OcrViewModel).GetProperty(nameof(OcrViewModel.IsServiceAvailable))
            ?.SetValue(vm, true);
        vm.PendingFiles.Add(@"C:\test\img.png");

        Assert.True(vm.CanStart);
        Assert.False(vm.CanCancel);

        // 模拟运行中
        typeof(OcrViewModel).GetProperty(nameof(OcrViewModel.IsRunning))
            ?.SetValue(vm, true);

        Assert.False(vm.CanStart);
        Assert.True(vm.CanCancel);
    }

    /// <summary>默认构造函数应创建有效的 ViewModel 实例</summary>
    [Fact]
    public void DefaultConstructor_ShouldCreateValidInstance()
    {
        var vm = new OcrViewModel();

        Assert.NotNull(vm);
        Assert.NotNull(vm.SelectFilesCommand);
        Assert.NotNull(vm.StartRecognitionCommand);
        Assert.NotNull(vm.CancelCommand);
        Assert.NotNull(vm.ClearResultsCommand);
        Assert.NotNull(vm.CopyTextCommand);
        Assert.NotNull(vm.SelectResultCommand);
    }

    /// <summary>服务可用时 ServiceStatusText 应显示就绪</summary>
    [Fact]
    public void ServiceStatusText_ShouldReflectAvailability()
    {
        var fs = new FileSystemService();
        var vm = new OcrViewModel(null, fs);

        Assert.Contains("未连接", vm.ServiceStatusText);

        typeof(OcrViewModel).GetProperty(nameof(OcrViewModel.IsServiceAvailable))
            ?.SetValue(vm, true);

        Assert.Contains("就绪", vm.ServiceStatusText);
    }

    /// <summary>TextScorePercent 变更时应更新所有结果的 ConfidenceThreshold</summary>
    [Fact]
    public void TextScorePercent_Change_ShouldUpdateAllResultThresholds()
    {
        var fs = new FileSystemService();
        var vm = new OcrViewModel(null, fs);

        var result1 = new OcrJobResult { IsSuccess = true };
        var result2 = new OcrJobResult { IsSuccess = true };

        vm.Results.Add(result1);
        vm.Results.Add(result2);

        // 默认阈值 0.5
        Assert.Equal(0.5, result1.ConfidenceThreshold);
        Assert.Equal(0.5, result2.ConfidenceThreshold);

        // 修改阈值
        vm.TextScorePercent = 80;

        Assert.Equal(0.8, result1.ConfidenceThreshold);
        Assert.Equal(0.8, result2.ConfidenceThreshold);
    }
}
