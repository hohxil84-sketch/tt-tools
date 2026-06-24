using System.Net.Http;
using System.Text.Json;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;
using TTTools.AiRenderClient.Tests.TestHelpers;
using TTTools.AiRenderClient.ViewModels;

namespace TTTools.AiRenderClient.Tests.ViewModels;

/// <summary>
/// AiRenderViewModel 单元测试
/// 覆盖初始状态、参数管理、命令绑定、属性变更通知、任务创建、状态查询、清除行为和辅助方法。
/// </summary>
public class AiRenderViewModelTests
{
    /// <summary>初始状态：默认参数值</summary>
    [Fact]
    public void InitialState_ShouldHaveDefaultValues()
    {
        var vm = new AiRenderViewModel();

        Assert.Equal("poster_design", vm.SelectedScene);
        Assert.Equal("", vm.Prompt);
        Assert.Equal("", vm.InputFileIdsText);
        Assert.Equal("modern", vm.SelectedStyle);
        Assert.Equal("1024x1024", vm.SelectedSize);
        Assert.False(vm.IsRunning);
        Assert.False(vm.HasError);
        Assert.False(vm.HasTaskResult);
        Assert.False(vm.IsTaskRunning);
        Assert.False(vm.IsTaskCompleted);
        Assert.False(vm.IsTaskFailed);
        Assert.Equal("", vm.CurrentTaskId);
        Assert.Equal("", vm.TaskStatus);
        Assert.Empty(vm.ResultFiles);
        Assert.Empty(vm.HistoryItems);
    }

    /// <summary>所有命令都不为 null</summary>
    [Fact]
    public void AllCommands_ShouldNotBeNull()
    {
        var vm = new AiRenderViewModel();

        Assert.NotNull(vm.CreateTaskCommand);
        Assert.NotNull(vm.RefreshStatusCommand);
        Assert.NotNull(vm.ClearCommand);
        Assert.NotNull(vm.SelectHistoryItemCommand);
        Assert.NotNull(vm.OpenResultFileCommand);
    }

    /// <summary>Prompt 为空时 CanCreateTask 为 false</summary>
    [Fact]
    public void CanCreateTask_WhenPromptEmpty_ShouldBeFalse()
    {
        var vm = new AiRenderViewModel();
        Assert.False(vm.CanCreateTask);
    }

    /// <summary>Prompt 非空且非运行中时 CanCreateTask 为 true</summary>
    [Fact]
    public void CanCreateTask_WhenPromptFilled_ShouldBeTrue()
    {
        var vm = new AiRenderViewModel();
        vm.Prompt = "一张现代风格的海报设计";
        Assert.True(vm.CanCreateTask);
    }

    /// <summary>IsRunning 为 true 时 CanCreateTask 为 false</summary>
    [Fact]
    public void CanCreateTask_WhenRunning_ShouldBeFalse()
    {
        var vm = new AiRenderViewModel();
        vm.Prompt = "一张现代风格的海报设计";
        Assert.True(vm.CanCreateTask);

        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.IsRunning))!
            .SetValue(vm, true);

        Assert.False(vm.CanCreateTask);
    }

    /// <summary>HasError 在 ErrorMessage 不为空时为 true</summary>
    [Fact]
    public void HasError_WhenErrorMessageSet_ShouldBeTrue()
    {
        var vm = new AiRenderViewModel();
        Assert.False(vm.HasError);

        vm.ErrorMessage = "测试错误";
        Assert.True(vm.HasError);

        vm.ErrorMessage = null;
        Assert.False(vm.HasError);
    }

    /// <summary>TaskStatusDisplay 中文显示正确</summary>
    [Fact]
    public void TaskStatusDisplay_ShouldReturnChineseText()
    {
        var vm = new AiRenderViewModel();

        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.TaskStatus))!
            .SetValue(vm, "queued");
        Assert.Equal("排队中...", vm.TaskStatusDisplay);

        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.TaskStatus))!
            .SetValue(vm, "running");
        Assert.Equal("生成中...", vm.TaskStatusDisplay);

        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.TaskStatus))!
            .SetValue(vm, "succeeded");
        Assert.Equal("已完成", vm.TaskStatusDisplay);

        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.TaskStatus))!
            .SetValue(vm, "failed");
        Assert.Equal("失败", vm.TaskStatusDisplay);
    }

    /// <summary>IsTaskRunning 在 queued/running 时为 true，其他为 false</summary>
    [Fact]
    public void IsTaskRunning_ShouldBeCorrectForEachStatus()
    {
        var vm = new AiRenderViewModel();

        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.TaskStatus))!
            .SetValue(vm, "queued");
        Assert.True(vm.IsTaskRunning);

        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.TaskStatus))!
            .SetValue(vm, "running");
        Assert.True(vm.IsTaskRunning);

        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.TaskStatus))!
            .SetValue(vm, "succeeded");
        Assert.False(vm.IsTaskRunning);
        Assert.True(vm.IsTaskCompleted);

        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.TaskStatus))!
            .SetValue(vm, "failed");
        Assert.False(vm.IsTaskRunning);
        Assert.True(vm.IsTaskFailed);
    }

    /// <summary>场景类型列表包含 8 个选项</summary>
    [Fact]
    public void SceneTypeList_ShouldHaveEightItems()
    {
        Assert.Equal(8, AiRenderViewModel.SceneTypeList.Count);
    }

    /// <summary>风格列表包含 8 个选项</summary>
    [Fact]
    public void StyleList_ShouldHaveEightItems()
    {
        Assert.Equal(8, AiRenderViewModel.StyleList.Count);
    }

    /// <summary>尺寸列表包含 6 个选项</summary>
    [Fact]
    public void SizeList_ShouldHaveSixItems()
    {
        Assert.Equal(6, AiRenderViewModel.SizeList.Count);
    }

    /// <summary>PropertyChanged 在 Prompt 变更时触发</summary>
    [Fact]
    public void Prompt_ShouldRaisePropertyChanged()
    {
        var vm = new AiRenderViewModel();
        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName!);

        vm.Prompt = "新提示词";

        Assert.Contains(nameof(AiRenderViewModel.Prompt), changedProps);
    }

    /// <summary>PropertyChanged 在 SelectedScene 变更时触发</summary>
    [Fact]
    public void SelectedScene_ShouldRaisePropertyChanged()
    {
        var vm = new AiRenderViewModel();
        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName!);

        vm.SelectedScene = "interior_design";

        Assert.Contains(nameof(AiRenderViewModel.SelectedScene), changedProps);
    }

    /// <summary>PropertyChanged 在 SelectedStyle 变更时触发</summary>
    [Fact]
    public void SelectedStyle_ShouldRaisePropertyChanged()
    {
        var vm = new AiRenderViewModel();
        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName!);

        vm.SelectedStyle = "chinese";

        Assert.Contains(nameof(AiRenderViewModel.SelectedStyle), changedProps);
    }

    /// <summary>PropertyChanged 在 SelectedSize 变更时触发</summary>
    [Fact]
    public void SelectedSize_ShouldRaisePropertyChanged()
    {
        var vm = new AiRenderViewModel();
        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName!);

        vm.SelectedSize = "1920x1080";

        Assert.Contains(nameof(AiRenderViewModel.SelectedSize), changedProps);
    }

    /// <summary>PropertyChanged 在 InputFileIdsText 变更时触发</summary>
    [Fact]
    public void InputFileIdsText_ShouldRaisePropertyChanged()
    {
        var vm = new AiRenderViewModel();
        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName!);

        vm.InputFileIdsText = "uuid-1, uuid-2";

        Assert.Contains(nameof(AiRenderViewModel.InputFileIdsText), changedProps);
    }

    /// <summary>Clear 命令重置所有状态</summary>
    [Fact]
    public void Clear_ShouldResetAllState()
    {
        var vm = new AiRenderViewModel();
        vm.Prompt = "测试提示词";
        vm.InputFileIdsText = "uuid-1";
        vm.SelectedScene = "interior_design";
        vm.SelectedStyle = "chinese";
        vm.SelectedSize = "1920x1080";
        vm.ErrorMessage = "error";

        // 通过反射设置只读相关属性
        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.CurrentTaskId))!
            .SetValue(vm, "task-123");
        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.TaskStatus))!
            .SetValue(vm, "running");
        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.Provider))!
            .SetValue(vm, "deepseek");
        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.Model))!
            .SetValue(vm, "deepseek-chat");
        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.EstimatedCost))!
            .SetValue(vm, 0.005m);
        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.CreditsCharged))!
            .SetValue(vm, 3);
        typeof(AiRenderViewModel)
            .GetProperty(nameof(AiRenderViewModel.ProviderCallId))!
            .SetValue(vm, "uuid-456");

        // 执行清除
        vm.ClearCommand.Execute(null);

        Assert.Equal("", vm.Prompt);
        Assert.Equal("", vm.InputFileIdsText);
        Assert.Equal("poster_design", vm.SelectedScene);
        Assert.Equal("modern", vm.SelectedStyle);
        Assert.Equal("1024x1024", vm.SelectedSize);

        Assert.Equal("", vm.CurrentTaskId);
        Assert.Equal("", vm.TaskStatus);
        Assert.Equal("", vm.Provider);
        Assert.Equal("", vm.Model);
        Assert.Equal(0m, vm.EstimatedCost);
        Assert.Equal(0, vm.CreditsCharged);
        Assert.Equal("", vm.ProviderCallId);
        Assert.Null(vm.ErrorMessage);
        Assert.Empty(vm.ResultFiles);
        Assert.False(vm.HasError);
        Assert.False(vm.HasTaskResult);
    }

    /// <summary>
    /// 使用 Mock CloudApiClient 测试成功创建任务流程（C2）
    /// 验证 CreateTaskAsync 正确设置所有结果属性。
    /// </summary>
    [Fact]
    public async Task CreateTaskAsync_WithMockApi_ShouldSetTaskProperties()
    {
        // 构造模拟的 API 响应数据（创建任务）
        var createResponseJson = new
        {
            success = true,
            data = new
            {
                task_id = "task-uuid-test-001",
                status = "queued",
                feature = "ai_render_cloud",
                estimated_credits = 5,
            },
            error = (object?)null,
            request_id = "req-server-001"
        };

        var mockHandler = MockHttpMessageHandler.CreateJsonResponse(createResponseJson);
        var httpClient = new HttpClient(mockHandler)
        {
            BaseAddress = new Uri("http://test.local")
        };

        var authState = new AuthState();
        // 使用 SetLoggedIn 设置已登录状态
        authState.SetLoggedIn(
            "fake-token", "fake-refresh-token", 3600,
            new TTShared.Auth.UserInfo { Id = "u1", Account = "test", DisplayName = "测试" },
            new TTShared.Auth.DeviceInfo { Id = "d1", Status = "active" });

        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiRenderViewModel(cloudApiClient, authState);

        // 设置输入参数
        vm.Prompt = "一张现代风格的海报设计，以蓝色为主色调";
        vm.SelectedScene = "poster_design";
        vm.SelectedStyle = "modern";
        vm.SelectedSize = "1024x1024";

        // 执行创建任务
        vm.CreateTaskCommand.Execute(null);

        // 等待异步操作完成
        await Task.Delay(500);

        Assert.Equal("task-uuid-test-001", vm.CurrentTaskId);
        Assert.Equal("queued", vm.TaskStatus);
        Assert.True(vm.HasTaskResult);
        Assert.False(vm.HasError);
        Assert.False(vm.IsRunning);
    }

    /// <summary>
    /// 未登录状态创建任务时显示错误
    /// </summary>
    [Fact]
    public void CreateTaskAsync_WhenNotLoggedIn_ShouldSetError()
    {
        var authState = new AuthState(); // 默认 LoggedOut 状态
        var httpClient = new HttpClient(new MockHttpMessageHandler(_ =>
            new HttpResponseMessage(System.Net.HttpStatusCode.OK)));
        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiRenderViewModel(cloudApiClient, authState);
        vm.Prompt = "测试提示词";

        vm.CreateTaskCommand.Execute(null);

        Assert.True(vm.HasError);
        Assert.Contains("登录", vm.ErrorMessage);
        Assert.False(vm.IsRunning);
    }

    /// <summary>
    /// Prompt 为空时不应发起创建任务
    /// </summary>
    [Fact]
    public void CreateTaskAsync_WhenPromptEmpty_ShouldSetError()
    {
        var authState = new AuthState();
        authState.SetLoggedIn(
            "fake-token", "fake-refresh-token", 3600,
            new TTShared.Auth.UserInfo { Id = "u1", Account = "test", DisplayName = "测试" },
            new TTShared.Auth.DeviceInfo { Id = "d1", Status = "active" });

        var httpClient = new HttpClient(new MockHttpMessageHandler(_ =>
            new HttpResponseMessage(System.Net.HttpStatusCode.OK)));
        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiRenderViewModel(cloudApiClient, authState);
        vm.Prompt = ""; // 空提示词

        vm.CreateTaskCommand.Execute(null);

        Assert.True(vm.HasError);
    }

    /// <summary>
    /// AiRenderHistoryItem 显示属性正确
    /// </summary>
    [Fact]
    public void HistoryItem_DisplayProperties_ShouldBeCorrect()
    {
        var item = new AiRenderHistoryItem
        {
            TaskId = "task-uuid-12345678-1234-1234-1234-123456789abc",
            SceneType = "poster_design",
            Prompt = "这是一段非常长的提示词用于测试截断功能包含大量描述性文字用于测试效果图生成场景内容",
            Status = "succeeded",
            Provider = "deepseek",
            Model = "deepseek-chat",
            EstimatedCredits = 5,
            CreditsCharged = 3,
            CreatedAt = new DateTime(2026, 6, 24, 14, 30, 0),
            RequestId = "req-001"
        };

        Assert.Equal("海报设计", item.SceneTypeDisplay);
        Assert.Equal("14:30:00", item.TimeDisplay);
        Assert.Equal("已完成", item.StatusDisplay);
        Assert.EndsWith("...", item.PromptSummary);
        Assert.True(item.PromptSummary.Length <= 43); // 40 + "..."
        Assert.Equal("-3 额度 / deepseek/deepseek-chat", item.CostSummary);
    }

    /// <summary>
    /// HistoryItem 短提示词不截断
    /// </summary>
    [Fact]
    public void HistoryItem_WhenShortPrompt_ShouldNotTruncate()
    {
        var item = new AiRenderHistoryItem
        {
            Prompt = "短提示词"
        };

        Assert.Equal("短提示词", item.PromptSummary);
    }

    /// <summary>
    /// HistoryItem 状态颜色正确
    /// </summary>
    [Theory]
    [InlineData("queued", "#D69E2E")]
    [InlineData("running", "#3182CE")]
    [InlineData("succeeded", "#38A169")]
    [InlineData("failed", "#E53E3E")]
    [InlineData("unknown", "#718096")]
    public void HistoryItem_StatusColor_ShouldBeCorrect(string status, string expectedColor)
    {
        var item = new AiRenderHistoryItem { Status = status };
        Assert.Equal(expectedColor, item.StatusColor);
    }

    /// <summary>
    /// HistoryItem 未扣费时显示预估
    /// </summary>
    [Fact]
    public void HistoryItem_WhenNoCreditsCharged_ShouldShowEstimated()
    {
        var item = new AiRenderHistoryItem
        {
            EstimatedCredits = 5,
            CreditsCharged = 0
        };

        Assert.Equal("预估 5 额度", item.CostSummary);
    }

    /// <summary>
    /// HistoryCount 跟随 HistoryItems 集合变更
    /// </summary>
    [Fact]
    public void HistoryCount_ShouldReflectCollectionChanges()
    {
        var vm = new AiRenderViewModel();
        Assert.Equal(0, vm.HistoryCount);

        vm.HistoryItems.Add(new AiRenderHistoryItem());
        Assert.Equal(1, vm.HistoryCount);

        vm.HistoryItems.Clear();
        Assert.Equal(0, vm.HistoryCount);
    }

    /// <summary>
    /// SelectHistoryItem 恢复任务属性到当前视图
    /// </summary>
    [Fact]
    public void SelectHistoryItem_ShouldRestoreTaskProperties()
    {
        var vm = new AiRenderViewModel();
        var historyItem = new AiRenderHistoryItem
        {
            TaskId = "task-uuid-restore",
            SceneType = "interior_design",
            Prompt = "室内设计效果图",
            Status = "succeeded",
            Provider = "openai",
            Model = "dall-e-3",
            CreditsCharged = 10
        };

        vm.SelectHistoryItemCommand.Execute(historyItem);

        Assert.Equal("task-uuid-restore", vm.CurrentTaskId);
        Assert.Equal("succeeded", vm.TaskStatus);
        Assert.Equal("openai", vm.Provider);
        Assert.Equal("dall-e-3", vm.Model);
        Assert.Equal(10, vm.CreditsCharged);
        Assert.Equal("室内设计效果图", vm.Prompt);
        Assert.Equal("interior_design", vm.SelectedScene);
    }

    /// <summary>
    /// SelectHistoryItem 传入 null 不应变更当前状态
    /// </summary>
    [Fact]
    public void SelectHistoryItem_WhenNull_ShouldNotChange()
    {
        var vm = new AiRenderViewModel();
        vm.Prompt = "原有提示词";

        vm.SelectHistoryItemCommand.Execute(null);

        Assert.Equal("原有提示词", vm.Prompt);
    }
}
