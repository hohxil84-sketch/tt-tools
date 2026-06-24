using System.ComponentModel;
using System.Net.Http;
using System.Text.Json;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;
using TTTools.AiCopyClient.Tests.TestHelpers;
using TTTools.AiCopyClient.ViewModels;

namespace TTTools.AiCopyClient.Tests.ViewModels;

/// <summary>
/// AiCopyViewModel 单元测试
/// 覆盖初始状态、参数管理、命令绑定、属性变更通知、卖点增删、生成流程和清除行为。
/// </summary>
public class AiCopyViewModelTests
{
    /// <summary>初始状态：默认参数值</summary>
    [Fact]
    public void InitialState_ShouldHaveDefaultValues()
    {
        var vm = new AiCopyViewModel();

        Assert.Equal("poster", vm.SelectedScene);
        Assert.Equal("", vm.ProductName);
        Assert.Equal("", vm.TargetAudience);
        Assert.Equal("direct", vm.SelectedTone);
        Assert.Equal("offline_poster", vm.SelectedPlatform);
        Assert.Equal("", vm.ExtraRequirements);
        Assert.Equal("", vm.NewSellingPoint);
        Assert.False(vm.IsRunning);
        Assert.False(vm.HasError);
        Assert.False(vm.HasResult);
        Assert.False(vm.HasGeneratedText);
        Assert.Empty(vm.SellingPoints);
        Assert.Empty(vm.Variants);
        Assert.Empty(vm.HistoryItems);
    }

    /// <summary>所有命令都不为 null</summary>
    [Fact]
    public void AllCommands_ShouldNotBeNull()
    {
        var vm = new AiCopyViewModel();

        Assert.NotNull(vm.GenerateCommand);
        Assert.NotNull(vm.CancelCommand);
        Assert.NotNull(vm.ClearCommand);
        Assert.NotNull(vm.CopyTextCommand);
        Assert.NotNull(vm.AddSellingPointCommand);
        Assert.NotNull(vm.RemoveSellingPointCommand);
        Assert.NotNull(vm.SelectHistoryItemCommand);
        Assert.NotNull(vm.SelectVariantCommand);
    }

    /// <summary>ProductName 为空时 CanGenerate 为 false</summary>
    [Fact]
    public void CanGenerate_WhenProductNameEmpty_ShouldBeFalse()
    {
        var vm = new AiCopyViewModel();
        Assert.False(vm.CanGenerate);
    }

    /// <summary>ProductName 非空且非运行中时 CanGenerate 为 true</summary>
    [Fact]
    public void CanGenerate_WhenProductNameFilled_ShouldBeTrue()
    {
        var vm = new AiCopyViewModel();
        vm.ProductName = "测试产品";
        Assert.True(vm.CanGenerate);
    }

    /// <summary>IsRunning 为 true 时 CanGenerate 为 false</summary>
    [Fact]
    public void CanGenerate_WhenRunning_ShouldBeFalse()
    {
        var vm = new AiCopyViewModel();
        vm.ProductName = "测试产品";
        Assert.True(vm.CanGenerate);

        typeof(AiCopyViewModel)
            .GetProperty(nameof(AiCopyViewModel.IsRunning))!
            .SetValue(vm, true);

        Assert.False(vm.CanGenerate);
    }

    /// <summary>HasError 在 ErrorMessage 不为空时为 true</summary>
    [Fact]
    public void HasError_WhenErrorMessageSet_ShouldBeTrue()
    {
        var vm = new AiCopyViewModel();
        Assert.False(vm.HasError);

        vm.ErrorMessage = "测试错误";
        Assert.True(vm.HasError);

        vm.ErrorMessage = null;
        Assert.False(vm.HasError);
    }

    /// <summary>HasGeneratedText 在 GeneratedText 不为空时为 true</summary>
    [Fact]
    public void HasGeneratedText_WhenGeneratedTextSet_ShouldBeTrue()
    {
        var vm = new AiCopyViewModel();
        Assert.False(vm.HasGeneratedText);

        vm.GeneratedText = "这是生成的文案";
        Assert.True(vm.HasGeneratedText);

        vm.GeneratedText = "";
        Assert.False(vm.HasGeneratedText);
    }

    /// <summary>HasResult 跟随 GeneratedText</summary>
    [Fact]
    public void HasResult_ShouldFollow_GeneratedText()
    {
        var vm = new AiCopyViewModel();
        Assert.False(vm.HasResult);

        vm.GeneratedText = "文案";
        Assert.True(vm.HasResult);
    }

    /// <summary>添加卖点：输入有效文本后执行命令</summary>
    [Fact]
    public void AddSellingPoint_WhenValidText_ShouldAddToList()
    {
        var vm = new AiCopyViewModel();
        vm.NewSellingPoint = "当天取件";

        vm.AddSellingPointCommand.Execute(null);

        Assert.Single(vm.SellingPoints);
        Assert.Equal("当天取件", vm.SellingPoints[0]);
        Assert.Equal("", vm.NewSellingPoint);
        Assert.True(vm.HasSellingPoints);
    }

    /// <summary>添加卖点：重复文本不应重复添加</summary>
    [Fact]
    public void AddSellingPoint_WhenDuplicate_ShouldNotAdd()
    {
        var vm = new AiCopyViewModel();
        vm.NewSellingPoint = "高清印刷";
        vm.AddSellingPointCommand.Execute(null);

        vm.NewSellingPoint = "高清印刷";
        vm.AddSellingPointCommand.Execute(null);

        Assert.Single(vm.SellingPoints);
    }

    /// <summary>添加卖点：空白文本不应添加</summary>
    [Fact]
    public void AddSellingPoint_WhenWhitespace_ShouldNotAdd()
    {
        var vm = new AiCopyViewModel();
        vm.NewSellingPoint = "   ";
        vm.AddSellingPointCommand.Execute(null);

        Assert.Empty(vm.SellingPoints);
    }

    /// <summary>移除卖点：从列表删除指定卖点</summary>
    [Fact]
    public void RemoveSellingPoint_ShouldRemoveFromList()
    {
        var vm = new AiCopyViewModel();
        vm.SellingPoints.Add("卖点A");
        vm.SellingPoints.Add("卖点B");

        vm.RemoveSellingPointCommand.Execute("卖点A");

        Assert.Single(vm.SellingPoints);
        Assert.Equal("卖点B", vm.SellingPoints[0]);
    }

    /// <summary>CanAddSellingPoint 跟随 NewSellingPoint 的值</summary>
    [Fact]
    public void CanAddSellingPoint_WhenNewSellingPointHasText_ShouldBeTrue()
    {
        var vm = new AiCopyViewModel();
        Assert.False(vm.CanAddSellingPoint);

        vm.NewSellingPoint = "新卖点";
        Assert.True(vm.CanAddSellingPoint);
    }

    /// <summary>SelectVariant 命令更新 SelectedVariant</summary>
    [Fact]
    public void SelectVariant_ShouldUpdateSelectedVariant()
    {
        var vm = new AiCopyViewModel();
        vm.SelectVariantCommand.Execute("变体文案");

        Assert.Equal("变体文案", vm.SelectedVariant);
    }

    /// <summary>SelectVariant 传入 null 不更新</summary>
    [Fact]
    public void SelectVariant_WhenNull_ShouldNotChange()
    {
        var vm = new AiCopyViewModel();
        vm.SelectedVariant = "已有选中";
        vm.SelectVariantCommand.Execute(null);

        Assert.Equal("已有选中", vm.SelectedVariant);
    }

    /// <summary>场景列表包含 8 个选项</summary>
    [Fact]
    public void SceneList_ShouldHaveEightItems()
    {
        Assert.Equal(8, AiCopyViewModel.SceneList.Count);
    }

    /// <summary>语气列表包含 6 个选项</summary>
    [Fact]
    public void ToneList_ShouldHaveSixItems()
    {
        Assert.Equal(6, AiCopyViewModel.ToneList.Count);
    }

    /// <summary>平台列表包含 8 个选项</summary>
    [Fact]
    public void PlatformList_ShouldHaveEightItems()
    {
        Assert.Equal(8, AiCopyViewModel.PlatformList.Count);
    }

    /// <summary>PropertyChanged 在 SelectedScene 变更时触发</summary>
    [Fact]
    public void SelectedScene_ShouldRaisePropertyChanged()
    {
        var vm = new AiCopyViewModel();
        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName!);

        vm.SelectedScene = "social_media";

        Assert.Contains(nameof(AiCopyViewModel.SelectedScene), changedProps);
    }

    /// <summary>PropertyChanged 在 ProductName 变更时触发</summary>
    [Fact]
    public void ProductName_ShouldRaisePropertyChanged()
    {
        var vm = new AiCopyViewModel();
        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName!);

        vm.ProductName = "新产品";

        Assert.Contains(nameof(AiCopyViewModel.ProductName), changedProps);
    }

    /// <summary>Clear 命令重置所有状态</summary>
    [Fact]
    public void Clear_ShouldResetAllState()
    {
        var vm = new AiCopyViewModel();
        vm.ProductName = "测试产品";
        vm.TargetAudience = "年轻人";
        vm.ExtraRequirements = "突出活动";
        vm.NewSellingPoint = "test";
        vm.SellingPoints.Add("卖点1");
        vm.SelectedScene = "social_media";
        vm.SelectedTone = "friendly";
        vm.SelectedPlatform = "weibo";

        vm.GeneratedText = "生成文案";
        vm.Variants.Add("变体1");
        vm.SelectedVariant = "变体1";
        vm.Provider = "deepseek";
        vm.Model = "deepseek-chat";
        vm.EstimatedCost = 0.002m;
        vm.CreditsCharged = 2;
        vm.ProviderCallId = "uuid-123";
        vm.ErrorMessage = "error";

        // 执行清除
        vm.ClearCommand.Execute(null);

        Assert.Equal("", vm.ProductName);
        Assert.Equal("", vm.TargetAudience);
        Assert.Equal("", vm.ExtraRequirements);
        Assert.Equal("", vm.NewSellingPoint);
        Assert.Empty(vm.SellingPoints);
        Assert.Equal("poster", vm.SelectedScene);
        Assert.Equal("direct", vm.SelectedTone);
        Assert.Equal("offline_poster", vm.SelectedPlatform);

        Assert.Equal("", vm.GeneratedText);
        Assert.Empty(vm.Variants);
        Assert.Equal("", vm.SelectedVariant);
        Assert.Equal("", vm.Provider);
        Assert.Equal("", vm.Model);
        Assert.Equal(0m, vm.EstimatedCost);
        Assert.Equal(0, vm.CreditsCharged);
        Assert.Equal("", vm.ProviderCallId);
        Assert.Null(vm.ErrorMessage);
        Assert.False(vm.HasError);
    }

    /// <summary>
    /// 使用 Mock CloudApiClient 测试成功生成流程（C2）
    /// 验证 GenerateAsync 正确设置所有结果属性。
    /// </summary>
    [Fact]
    public async Task GenerateAsync_WithMockApi_ShouldSetResultProperties()
    {
        // 构造模拟的 API 响应数据
        var responseJson = new
        {
            success = true,
            data = new
            {
                feature = "ai_copy_cloud",
                text = "开业大促，高清快印，当天取件！",
                variants = new[] { "开业印刷不用等，高清宣传单当天取。" },
                provider = "deepseek",
                model = "deepseek-chat",
                estimated_cost = 0.002,
                credits_charged = 1,
                provider_call_id = "uuid-test-12345",
            },
            error = (object?)null,
            request_id = "req-server-001"
        };

        var mockHandler = MockHttpMessageHandler.CreateJsonResponse(responseJson);
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
        var vm = new AiCopyViewModel(cloudApiClient, authState);

        // 设置输入参数
        vm.ProductName = "测试快印";
        vm.SelectedScene = "poster";
        vm.SelectedTone = "direct";
        vm.SellingPoints.Add("当天取件");
        vm.SellingPoints.Add("高清印刷");

        // 执行生成（异步命令）
        vm.GenerateCommand.Execute(null);

        // 等待异步生成完成
        await Task.Delay(500);

        Assert.Equal("开业大促，高清快印，当天取件！", vm.GeneratedText);
        Assert.Equal("deepseek", vm.Provider);
        Assert.Equal("deepseek-chat", vm.Model);
        Assert.Equal(0.002m, vm.EstimatedCost);
        Assert.Equal(1, vm.CreditsCharged);
        Assert.Equal("uuid-test-12345", vm.ProviderCallId);
        Assert.Single(vm.Variants);
        Assert.True(vm.HasResult);
        Assert.False(vm.HasError);
        Assert.False(vm.IsRunning);
    }

    /// <summary>
    /// 未登录状态生成时显示错误
    /// </summary>
    [Fact]
    public void GenerateAsync_WhenNotLoggedIn_ShouldSetError()
    {
        var authState = new AuthState(); // 默认 LoggedOut 状态
        // 提供一个有效的 CloudApiClient，避免 null 检查先触发
        var httpClient = new HttpClient(new MockHttpMessageHandler(_ =>
            new HttpResponseMessage(System.Net.HttpStatusCode.OK)));
        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiCopyViewModel(cloudApiClient, authState);
        vm.ProductName = "测试产品";

        vm.GenerateCommand.Execute(null);

        Assert.True(vm.HasError);
        Assert.Contains("登录", vm.ErrorMessage);
        Assert.False(vm.IsRunning);
    }

    /// <summary>
    /// ProductName 为空时不应发起生成
    /// </summary>
    [Fact]
    public void GenerateAsync_WhenProductNameEmpty_ShouldSetError()
    {
        var authState = new AuthState();
        // 使用 SetLoggedIn 设置已登录状态
        authState.SetLoggedIn(
            "fake-token", "fake-refresh-token", 3600,
            new TTShared.Auth.UserInfo { Id = "u1", Account = "test", DisplayName = "测试" },
            new TTShared.Auth.DeviceInfo { Id = "d1", Status = "active" });

        var httpClient = new HttpClient(new MockHttpMessageHandler(_ =>
            new HttpResponseMessage(System.Net.HttpStatusCode.OK)));
        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiCopyViewModel(cloudApiClient, authState);
        vm.ProductName = ""; // 空产品名
        vm.GenerateCommand.Execute(null);

        Assert.True(vm.HasError);
    }

    /// <summary>
    /// AiCopyHistoryItem 显示属性正确
    /// </summary>
    [Fact]
    public void HistoryItem_DisplayProperties_ShouldBeCorrect()
    {
        var item = new AiCopyHistoryItem
        {
            Scene = "poster",
            ProductName = "快印宣传单",
            GeneratedText = "这是一段比较长的文案内容用于测试截断功能，快印店开业大促高清印刷当天取件免费设计质量保证价格实惠欢迎光临",
            Provider = "deepseek",
            Model = "deepseek-chat",
            CreditsCharged = 3,
            CreatedAt = new DateTime(2026, 6, 24, 14, 30, 0),
            RequestId = "req-001"
        };

        Assert.Equal("海报 / 宣传单", item.SceneDisplay);
        Assert.Equal("14:30:00", item.TimeDisplay);
        Assert.EndsWith("...", item.TextSummary);
        Assert.True(item.TextSummary.Length <= 53); // 50 + "..."
        Assert.Equal("-3 额度 / deepseek/deepseek-chat", item.CostSummary);
    }

    /// <summary>
    /// HistoryItem 短文案不截断
    /// </summary>
    [Fact]
    public void HistoryItem_WhenShortText_ShouldNotTruncate()
    {
        var item = new AiCopyHistoryItem
        {
            GeneratedText = "短文案"
        };

        Assert.Equal("短文案", item.TextSummary);
    }

    /// <summary>
    /// HistoryCount 跟随 HistoryItems 集合变更
    /// </summary>
    [Fact]
    public void HistoryCount_ShouldReflectCollectionChanges()
    {
        var vm = new AiCopyViewModel();
        Assert.Equal(0, vm.HistoryCount);

        vm.HistoryItems.Add(new AiCopyHistoryItem());
        Assert.Equal(1, vm.HistoryCount);

        vm.HistoryItems.Clear();
        Assert.Equal(0, vm.HistoryCount);
    }

    /// <summary>
    /// HasSellingPoints 跟随 SellingPoints 集合变更
    /// </summary>
    [Fact]
    public void HasSellingPoints_ShouldReflectCollectionChanges()
    {
        var vm = new AiCopyViewModel();
        Assert.False(vm.HasSellingPoints);

        vm.SellingPoints.Add("卖点1");
        Assert.True(vm.HasSellingPoints);

        vm.SellingPoints.Clear();
        Assert.False(vm.HasSellingPoints);
    }
}
