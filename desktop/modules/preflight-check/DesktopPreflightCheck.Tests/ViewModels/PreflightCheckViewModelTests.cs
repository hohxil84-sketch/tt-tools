using System.ComponentModel;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTShared.Logging;
using TTTools.PreflightCheck.Models;
using TTTools.PreflightCheck.Services;
using TTTools.PreflightCheck.ViewModels;

namespace TTTools.PreflightCheck.Tests.ViewModels;

/// <summary>
/// PreflightCheckViewModel 单元测试
/// 覆盖初始状态、属性变更通知、命令状态、报告管理等场景。
/// </summary>
public class PreflightCheckViewModelTests
{
    /// <summary>初始状态：服务未就绪、无报告、就绪消息</summary>
    [Fact]
    public void InitialState_ShouldHaveDefaultValues()
    {
        var fs = new FileSystemService();
        var vm = new PreflightCheckViewModel(null, fs);

        Assert.False(vm.IsRunning);
        Assert.False(vm.IsServiceAvailable);
        Assert.False(vm.HasError);
        Assert.False(vm.CanStart);
        Assert.False(vm.CanCancel);
        Assert.Equal(0, vm.ReportCount);
        Assert.Equal(0, vm.PassCount);
        Assert.Equal(0, vm.WarningCount);
        Assert.Equal(0, vm.ErrorCount);
        Assert.Equal(0, vm.ProgressValue);
        Assert.Equal(100, vm.ProgressMax);
        Assert.NotNull(vm.StatusMessage);
        Assert.Contains("引擎未连接", vm.ServiceStatusText);
        Assert.Null(vm.SelectedReport);
        Assert.False(vm.HasSelectedReport);
    }

    /// <summary>默认构造函数应创建有效的 ViewModel 实例</summary>
    [Fact]
    public void DefaultConstructor_ShouldCreateValidInstance()
    {
        var vm = new PreflightCheckViewModel();

        Assert.NotNull(vm);
        Assert.NotNull(vm.SelectFilesCommand);
        Assert.NotNull(vm.StartCheckCommand);
        Assert.NotNull(vm.CancelCommand);
        Assert.NotNull(vm.ClearReportsCommand);
        Assert.NotNull(vm.CopyReportCommand);
        Assert.NotNull(vm.SelectReportCommand);
    }

    /// <summary>选择报告后 HasSelectedReport 应为 true</summary>
    [Fact]
    public void SelectedReport_ShouldUpdateDerivedProperties()
    {
        var fs = new FileSystemService();
        var vm = new PreflightCheckViewModel(null, fs);

        Assert.False(vm.HasSelectedReport);

        var report = new PreflightCheckReport
        {
            FilePath = @"C:\test\poster.jpg",
            FileName = "poster.jpg",
            FileFormat = ".jpg",
            FileSizeBytes = 512000,
            Width = 3000,
            Height = 2400,
            Dpi = 300,
            ColorMode = "CMYK",
            HasTransparency = false,
            OverallRisk = RiskLevel.Pass,
            OverallMessage = "可以提交印刷",
            Checks = new List<PreflightCheckResultItem>
            {
                new() { Item = CheckItemType.FileFormat, RiskLevel = RiskLevel.Pass, Message = "格式支持" },
                new() { Item = CheckItemType.Dimensions, RiskLevel = RiskLevel.Pass, Message = "尺寸满足" },
                new() { Item = CheckItemType.Dpi, RiskLevel = RiskLevel.Pass, Message = "DPI 满足" },
            }
        };

        vm.SelectedReport = report;

        Assert.True(vm.HasSelectedReport);
        Assert.NotNull(vm.SelectedChecks);
        Assert.Equal(3, vm.SelectedChecks!.Count);
        Assert.Contains("错误:0", vm.SelectedReportSummary);
    }

    /// <summary>ClearReports 应重置所有状态</summary>
    [Fact]
    public void ClearReports_ShouldResetAllState()
    {
        var fs = new FileSystemService();
        var vm = new PreflightCheckViewModel(null, fs);

        // 添加模拟报告
        var report = new PreflightCheckReport
        {
            FilePath = "test.png",
            FileName = "test.png",
            OverallRisk = RiskLevel.Pass,
            Checks = new List<PreflightCheckResultItem>
            {
                new() { Item = CheckItemType.FileFormat, RiskLevel = RiskLevel.Pass, Message = "ok" }
            }
        };
        vm.Reports.Add(report);
        vm.SelectedReport = report;

        Assert.Equal(1, vm.ReportCount);

        // 清除
        vm.ClearReportsCommand.Execute(null);

        Assert.Equal(0, vm.ReportCount);
        Assert.Null(vm.SelectedReport);
        Assert.False(vm.HasError);
        Assert.Equal(0, vm.ProgressValue);
        Assert.Contains("已清除", vm.StatusMessage);
    }

    /// <summary>添加不同风险等级的报告时统计应正确</summary>
    [Fact]
    public void Reports_ShouldTrackRiskStatistics()
    {
        var fs = new FileSystemService();
        var vm = new PreflightCheckViewModel(null, fs);

        var passReport = new PreflightCheckReport
        {
            FilePath = "pass.jpg",
            FileName = "pass.jpg",
            OverallRisk = RiskLevel.Pass,
            Checks = new List<PreflightCheckResultItem>()
        };
        var warnReport = new PreflightCheckReport
        {
            FilePath = "warn.jpg",
            FileName = "warn.jpg",
            OverallRisk = RiskLevel.Warning,
            Checks = new List<PreflightCheckResultItem>()
        };
        var errorReport = new PreflightCheckReport
        {
            FilePath = "error.jpg",
            FileName = "error.jpg",
            OverallRisk = RiskLevel.Error,
            Checks = new List<PreflightCheckResultItem>()
        };

        vm.Reports.Add(passReport);
        vm.Reports.Add(warnReport);
        vm.Reports.Add(errorReport);
        vm.Reports.Add(passReport); // 再加一个通过的

        Assert.Equal(4, vm.ReportCount);
        Assert.Equal(2, vm.PassCount);
        Assert.Equal(1, vm.WarningCount);
        Assert.Equal(1, vm.ErrorCount);
    }

    /// <summary>IsRunning 变更时 CanStart 和 CanCancel 应同步更新</summary>
    [Fact]
    public void IsRunning_ShouldUpdateCanStartAndCanCancel()
    {
        var fs = new FileSystemService();
        var vm = new PreflightCheckViewModel(null, fs);

        Assert.False(vm.IsRunning);
        Assert.False(vm.CanStart); // 服务未就绪

        // 模拟服务就绪
        typeof(PreflightCheckViewModel).GetProperty(nameof(PreflightCheckViewModel.IsServiceAvailable))
            ?.SetValue(vm, true);

        Assert.True(vm.CanStart);
        Assert.False(vm.CanCancel);

        // 模拟运行中
        typeof(PreflightCheckViewModel).GetProperty(nameof(PreflightCheckViewModel.IsRunning))
            ?.SetValue(vm, true);

        Assert.False(vm.CanStart);
        Assert.True(vm.CanCancel);
    }

    /// <summary>服务可用时 ServiceStatusText 应显示就绪</summary>
    [Fact]
    public void ServiceStatusText_ShouldReflectAvailability()
    {
        var fs = new FileSystemService();
        var vm = new PreflightCheckViewModel(null, fs);

        Assert.Contains("未连接", vm.ServiceStatusText);

        typeof(PreflightCheckViewModel).GetProperty(nameof(PreflightCheckViewModel.IsServiceAvailable))
            ?.SetValue(vm, true);

        Assert.Contains("就绪", vm.ServiceStatusText);
    }

    /// <summary>ViewModel 不设置 ErrorMessage 时 HasError 应为 false</summary>
    [Fact]
    public void HasError_ShouldBeFalse_WhenNoErrorMessage()
    {
        var fs = new FileSystemService();
        var vm = new PreflightCheckViewModel(null, fs);

        Assert.False(vm.HasError);
        Assert.Null(vm.ErrorMessage);
    }
}
