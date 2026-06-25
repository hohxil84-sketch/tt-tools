using System.Net;
using System.Net.Http;
using System.Text.Json;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;
using TTTools.AiImageToolsClient.Tests.TestHelpers;
using TTTools.AiImageToolsClient.ViewModels;

namespace TTTools.AiImageToolsClient.Tests.ViewModels;

/// <summary>
/// AiImageToolsViewModel 单元测试
/// 覆盖用户要求的 6 个核心场景：
/// 1) 未登录不能开始
/// 2) 无权限不能开始
/// 3) 积分不足不能开始
/// 4) 选择文件不会自动处理
/// 5) 点击开始才创建云端任务
/// 6) 任务轮询成功后展示结果
///
/// 同时覆盖：初始状态、命令绑定、属性变更、功能选择、文件管理、历史记录等。
/// </summary>
public class AiImageToolsViewModelTests
{
    // ============================================================
    // 初始状态测试
    // ============================================================

    [Fact]
    public void InitialState_ShouldHaveDefaultValues()
    {
        var vm = new AiImageToolsViewModel();

        Assert.Equal("upscale_image_cloud", vm.SelectedFeature);
        Assert.Equal("", vm.EditPrompt);
        Assert.Equal("svg", vm.VectorOutputFormat);
        Assert.Equal("auto", vm.OcrLanguage);
        Assert.Equal(2, vm.UpscaleFactor);

        Assert.False(vm.IsProcessing);
        Assert.False(vm.HasError);
        Assert.False(vm.HasTaskResult);
        Assert.False(vm.IsTaskRunning);
        Assert.False(vm.IsTaskCompleted);
        Assert.False(vm.IsTaskFailed);
        Assert.False(vm.IsEditFeature);
        Assert.True(vm.IsUpscaleFeature);
        Assert.True(vm.ShowBeforeAfter);

        Assert.Equal("", vm.CurrentTaskId);
        Assert.Equal("", vm.TaskStatus);
        Assert.Equal("", vm.OcrResultText);
        Assert.Empty(vm.PendingFiles);
        Assert.Empty(vm.ResultFiles);
        Assert.Empty(vm.HistoryItems);
    }

    [Fact]
    public void AllCommands_ShouldNotBeNull()
    {
        var vm = new AiImageToolsViewModel();

        Assert.NotNull(vm.AddFilesCommand);
        Assert.NotNull(vm.RemoveFileCommand);
        Assert.NotNull(vm.ClearPendingCommand);
        Assert.NotNull(vm.StartProcessingCommand);
        Assert.NotNull(vm.RefreshStatusCommand);
        Assert.NotNull(vm.ClearCommand);
        Assert.NotNull(vm.SelectHistoryItemCommand);
        Assert.NotNull(vm.OpenResultFileCommand);
        Assert.NotNull(vm.RefreshBalanceCommand);
        Assert.NotNull(vm.DownloadResultFileCommand);
    }

    // ============================================================
    // 功能选择测试
    // ============================================================

    [Fact]
    public void SelectedFeature_ShouldUpdateFeatureFlags()
    {
        var vm = new AiImageToolsViewModel();

        vm.SelectedFeature = "ai_edit_image_cloud";
        Assert.True(vm.IsEditFeature);
        Assert.False(vm.IsUpscaleFeature);
        Assert.False(vm.IsVectorizeFeature);
        Assert.False(vm.IsOcrFeature);
        Assert.False(vm.ShowBeforeAfter);

        vm.SelectedFeature = "vectorize_image_cloud";
        Assert.True(vm.IsVectorizeFeature);
        Assert.False(vm.IsEditFeature);
        Assert.False(vm.IsOcrFeature);

        vm.SelectedFeature = "ocr_cloud";
        Assert.True(vm.IsOcrFeature);
        Assert.False(vm.IsVectorizeFeature);

        vm.SelectedFeature = "remove_bg_cloud";
        Assert.True(vm.IsRemoveBgFeature);
        Assert.True(vm.ShowBeforeAfter); // 高级抠图也显示前后对比
    }

    [Fact]
    public void FeatureList_ShouldHaveFiveItems()
    {
        Assert.Equal(5, AiImageToolsViewModel.FeatureList.Count);
    }

    [Fact]
    public void VectorFormatList_ShouldHaveThreeItems()
    {
        Assert.Equal(3, AiImageToolsViewModel.VectorFormatList.Count);
    }

    [Fact]
    public void OcrLanguageList_ShouldHaveSixItems()
    {
        Assert.Equal(6, AiImageToolsViewModel.OcrLanguageList.Count);
    }

    [Fact]
    public void UpscaleFactorList_ShouldHaveThreeItems()
    {
        Assert.Equal(3, AiImageToolsViewModel.UpscaleFactorList.Count);
    }

    // ============================================================
    // 文件管理测试
    // ============================================================

    [Fact]
    public void PendingFileCount_ShouldReflectCollectionChanges()
    {
        var vm = new AiImageToolsViewModel();
        Assert.Equal(0, vm.PendingFileCount);

        vm.PendingFiles.Add(new PendingFileItem { FilePath = "test.png", FileName = "test.png" });
        Assert.Equal(1, vm.PendingFileCount);

        vm.PendingFiles.Clear();
        Assert.Equal(0, vm.PendingFileCount);
    }

    [Fact]
    public void CanStartProcessing_WhenNoFiles_ShouldBeFalse()
    {
        var vm = new AiImageToolsViewModel();
        Assert.False(vm.CanStartProcessing);
    }

    [Fact]
    public void CanStartProcessing_WhenFilesAdded_ShouldBeTrue()
    {
        var vm = new AiImageToolsViewModel();
        vm.PendingFiles.Add(new PendingFileItem { FilePath = "test.png", FileName = "test.png" });
        Assert.True(vm.CanStartProcessing);
    }

    // ============================================================
    // 场景 1：未登录不能开始
    // ============================================================

    /// <summary>
    /// 未登录状态下点击开始处理，应显示"请先登录"错误，不发起请求。
    /// </summary>
    [Fact]
    public void StartProcessing_WhenNotLoggedIn_ShouldSetErrorAndNotCallApi()
    {
        // Arrange: 未登录的 AuthState
        var authState = new AuthState(); // 默认 LoggedOut
        var httpClient = new HttpClient(new MockHttpMessageHandler(_ =>
            new HttpResponseMessage(HttpStatusCode.OK)));
        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiImageToolsViewModel(cloudApiClient, authState);

        // 添加待处理文件（满足 CanStartProcessing 前提）
        vm.PendingFiles.Add(new PendingFileItem { FilePath = "test.png", FileName = "test.png" });

        // Act: 点击开始处理
        vm.StartProcessingCommand.Execute(null);

        // Assert: 应显示登录错误，不调用 API
        Assert.True(vm.HasError);
        Assert.Contains("登录", vm.ErrorMessage);
        Assert.False(vm.IsProcessing);
        Assert.False(vm.HasTaskResult); // 任务未创建
    }

    // ============================================================
    // 场景 2：无权限不能开始
    // ============================================================

    /// <summary>
    /// 已登录但套餐权限不足时，应显示权限错误，不创建任务。
    /// </summary>
    [Fact]
    public async Task StartProcessing_WhenEntitlementDenied_ShouldSetError()
    {
        // Arrange: 已登录的 AuthState
        var authState = new AuthState();
        authState.SetLoggedIn(
            "token", "refresh", 3600,
            new UserInfo { Id = "u1", Account = "test", DisplayName = "测试" },
            new DeviceInfo { Id = "d1", Status = "active" });

        // Mock: 权限检查返回 denied
        var mockHandler = new MockHttpMessageHandler(request =>
        {
            var url = request.RequestUri?.AbsolutePath ?? "";
            if (url.Contains("/entitlements/check"))
            {
                // 返回权限不足
                var body = new
                {
                    success = true,
                    data = new
                    {
                        allowed = false,
                        feature = "upscale_image_cloud",
                        plan_code = "free",
                        remaining_free_quota = 0,
                        reason = "免费套餐不支持此功能，请升级套餐"
                    },
                    error = (object?)null,
                    request_id = "req-001"
                };
                var json = JsonSerializer.Serialize(body, new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
                });
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(json, Encoding.UTF8, "application/json")
                };
            }
            return new HttpResponseMessage(HttpStatusCode.OK);
        });

        var httpClient = new HttpClient(mockHandler) { BaseAddress = new Uri("http://test.local") };
        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiImageToolsViewModel(cloudApiClient, authState);

        // 添加待处理文件
        vm.PendingFiles.Add(new PendingFileItem { FilePath = "test.png", FileName = "test.png" });

        // Act: 点击开始处理
        vm.StartProcessingCommand.Execute(null);

        // 等待异步完成
        await Task.Delay(500);

        // Assert: 应显示权限不足错误
        Assert.True(vm.HasError);
        Assert.Contains("不支持此功能", vm.ErrorMessage);
        Assert.False(vm.IsProcessing);
        Assert.False(vm.HasTaskResult);
    }

    // ============================================================
    // 场景 3：积分不足不能开始
    // ============================================================

    /// <summary>
    /// 已登录、有权限但积分余额不足时，应显示积分不足错误，不创建任务。
    /// </summary>
    [Fact]
    public async Task StartProcessing_WhenCreditInsufficient_ShouldSetError()
    {
        // Arrange: 已登录的 AuthState
        var authState = new AuthState();
        authState.SetLoggedIn(
            "token", "refresh", 3600,
            new UserInfo { Id = "u1", Account = "test", DisplayName = "测试" },
            new DeviceInfo { Id = "d1", Status = "active" });

        // Mock: 权限通过，余额为 0
        var mockHandler = new MockHttpMessageHandler(request =>
        {
            var url = request.RequestUri?.AbsolutePath ?? "";

            if (url.Contains("/entitlements/check"))
            {
                var body = new
                {
                    success = true,
                    data = new
                    {
                        allowed = true,
                        feature = "upscale_image_cloud",
                        plan_code = "free",
                        remaining_free_quota = (int?)null,
                        reason = (object?)null
                    },
                    error = (object?)null,
                    request_id = "req-001"
                };
                var json = JsonSerializer.Serialize(body, new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
                });
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(json, Encoding.UTF8, "application/json")
                };
            }

            if (url.Contains("/credits/balance"))
            {
                var body = new
                {
                    success = true,
                    data = new
                    {
                        user_id = "u1",
                        plan_code = "free",
                        monthly_grant = 10,
                        balance = 0, // 余额为 0
                        period_start = "2026-06-01T00:00:00Z",
                        period_end = "2026-07-01T00:00:00Z",
                        status = "active",
                        updated_at = "2026-06-26T00:00:00Z"
                    },
                    error = (object?)null,
                    request_id = "req-002"
                };
                var json = JsonSerializer.Serialize(body, new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
                });
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(json, Encoding.UTF8, "application/json")
                };
            }

            return new HttpResponseMessage(HttpStatusCode.OK);
        });

        var httpClient = new HttpClient(mockHandler) { BaseAddress = new Uri("http://test.local") };
        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiImageToolsViewModel(cloudApiClient, authState);

        // 添加待处理文件
        vm.PendingFiles.Add(new PendingFileItem { FilePath = "test.png", FileName = "test.png" });

        // Act: 点击开始处理
        vm.StartProcessingCommand.Execute(null);

        // 等待异步完成
        await Task.Delay(500);

        // Assert: 应显示积分不足错误
        Assert.True(vm.HasError);
        Assert.Contains("余额不足", vm.ErrorMessage);
        Assert.False(vm.IsProcessing);
        Assert.False(vm.HasTaskResult);
    }

    // ============================================================
    // 场景 4：选择文件不会自动处理
    // ============================================================

    /// <summary>
    /// 验证：将文件添加到待处理列表不会自动触发云端请求。
    /// 用户必须手动点击「开始处理」才提交任务。
    /// </summary>
    [Fact]
    public void AddingFiles_ShouldNotAutoProcess()
    {
        var authState = new AuthState();
        authState.SetLoggedIn(
            "token", "refresh", 3600,
            new UserInfo { Id = "u1", Account = "test", DisplayName = "测试" },
            new DeviceInfo { Id = "d1", Status = "active" });

        var httpClient = new HttpClient(new MockHttpMessageHandler(_ =>
            new HttpResponseMessage(HttpStatusCode.OK)));
        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiImageToolsViewModel(cloudApiClient, authState);

        // Act: 添加文件到待处理列表
        vm.PendingFiles.Add(new PendingFileItem { FilePath = "test1.png", FileName = "test1.png" });
        vm.PendingFiles.Add(new PendingFileItem { FilePath = "test2.jpg", FileName = "test2.jpg" });

        // Assert: 任务状态应保持初始状态，不应自动创建任务
        Assert.Equal(2, vm.PendingFileCount);
        Assert.Equal("", vm.CurrentTaskId);     // 没有任务 ID
        Assert.Equal("", vm.TaskStatus);         // 没有任务状态
        Assert.False(vm.HasTaskResult);          // 没有任务结果
        Assert.False(vm.IsProcessing);           // 没有在处理中
        Assert.True(vm.CanStartProcessing);      // 可以开始，但还没开始
    }

    // ============================================================
    // 场景 5：点击开始才创建云端任务
    // ============================================================

    /// <summary>
    /// 验证：只有用户点击「开始处理」后，才会调用云端 API 创建任务。
    /// </summary>
    [Fact]
    public async Task StartProcessing_WhenClicked_ShouldCreateCloudTask()
    {
        // Arrange
        var authState = new AuthState();
        authState.SetLoggedIn(
            "token", "refresh", 3600,
            new UserInfo { Id = "u1", Account = "test", DisplayName = "测试" },
            new DeviceInfo { Id = "d1", Status = "active" });

        // Mock: 权限通过 → 余额充足 → 创建任务成功
        var mockHandler = new MockHttpMessageHandler(request =>
        {
            var url = request.RequestUri?.AbsolutePath ?? "";

            if (url.Contains("/entitlements/check"))
            {
                var body = new
                {
                    success = true,
                    data = new
                    {
                        allowed = true,
                        feature = "upscale_image_cloud",
                        plan_code = "standard",
                        remaining_free_quota = (object?)null,
                        reason = (object?)null
                    },
                    error = (object?)null,
                    request_id = "req-ent-001"
                };
                var json = JsonSerializer.Serialize(body, new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
                });
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(json, Encoding.UTF8, "application/json")
                };
            }

            if (url.Contains("/credits/balance"))
            {
                var body = new
                {
                    success = true,
                    data = new
                    {
                        user_id = "u1",
                        plan_code = "standard",
                        monthly_grant = 100,
                        balance = 50, // 余额充足
                        period_start = "2026-06-01T00:00:00Z",
                        period_end = "2026-07-01T00:00:00Z",
                        status = "active",
                        updated_at = "2026-06-26T00:00:00Z"
                    },
                    error = (object?)null,
                    request_id = "req-bal-001"
                };
                var json = JsonSerializer.Serialize(body, new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
                });
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(json, Encoding.UTF8, "application/json")
                };
            }

            if (url.Contains("/ai/image-tools/tasks") && request.Method == HttpMethod.Post)
            {
                var body = new
                {
                    success = true,
                    data = new
                    {
                        task_id = "task-img-12345678",
                        status = "queued",
                        feature = "upscale_image_cloud",
                        estimated_credits = 5
                    },
                    error = (object?)null,
                    request_id = "req-task-001"
                };
                var json = JsonSerializer.Serialize(body, new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
                });
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(json, Encoding.UTF8, "application/json")
                };
            }

            return new HttpResponseMessage(HttpStatusCode.OK);
        });

        var httpClient = new HttpClient(mockHandler) { BaseAddress = new Uri("http://test.local") };
        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiImageToolsViewModel(cloudApiClient, authState);

        // 添加待处理文件
        vm.PendingFiles.Add(new PendingFileItem { FilePath = "test.png", FileName = "test.png" });

        // 确认初始无任务
        Assert.Equal("", vm.CurrentTaskId);

        // Act: 点击开始处理
        vm.StartProcessingCommand.Execute(null);

        // 等待异步完成
        await Task.Delay(500);

        // Assert: 应成功创建任务
        Assert.False(vm.HasError);
        Assert.Equal("task-img-12345678", vm.CurrentTaskId);
        Assert.Equal("queued", vm.TaskStatus);
        Assert.Equal("upscale_image_cloud", vm.TaskFeature);
        Assert.Equal(5, vm.EstimatedCredits);
        Assert.True(vm.HasTaskResult);
        Assert.False(vm.IsProcessing); // 处理完成
        Assert.Single(vm.HistoryItems); // 历史记录已添加
    }

    // ============================================================
    // 场景 6：任务轮询成功后展示结果
    // ============================================================

    /// <summary>
    /// 验证：轮询任务状态直到成功后，结果文件正确展示。
    /// </summary>
    [Fact]
    public async Task Polling_WhenTaskSucceeds_ShouldDisplayResults()
    {
        // Arrange
        var authState = new AuthState();
        authState.SetLoggedIn(
            "token", "refresh", 3600,
            new UserInfo { Id = "u1", Account = "test", DisplayName = "测试" },
            new DeviceInfo { Id = "d1", Status = "active" });

        // 模拟已完成的任务查询响应（直接构造 JSON 字符串，避免匿名类型 null 赋值限制）
        var completedTaskJson = """
        {
            "success": true,
            "data": {
                "task_id": "task-img-completed",
                "status": "succeeded",
                "feature": "upscale_image_cloud",
                "result_files": [
                    {
                        "file_id": "file-result-001",
                        "url": "https://cdn.example.com/results/001.png",
                        "mime_type": "image/png",
                        "width": 2048,
                        "height": 1536
                    },
                    {
                        "file_id": "file-result-002",
                        "url": "https://cdn.example.com/results/002.png",
                        "mime_type": "image/png",
                        "width": 4096,
                        "height": 3072
                    }
                ],
                "result_json": null,
                "provider": "aws",
                "model": "stable-diffusion-upscale",
                "estimated_cost": 0.015,
                "credits_charged": 5,
                "provider_call_id": "call-uuid-789"
            },
            "error": null,
            "request_id": "req-query-001"
        }
        """;

        var mockHandler = new MockHttpMessageHandler(_ =>
            new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(completedTaskJson, Encoding.UTF8, "application/json")
            });
        var httpClient = new HttpClient(mockHandler) { BaseAddress = new Uri("http://test.local") };
        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiImageToolsViewModel(cloudApiClient, authState);

        // 模拟已有任务（通过反射设置，模拟已经创建了任务的场景）
        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.CurrentTaskId))!
            .SetValue(vm, "task-img-completed");
        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.TaskStatus))!
            .SetValue(vm, "running");
        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.TaskFeature))!
            .SetValue(vm, "upscale_image_cloud");

        // Act: 手动触发状态刷新（模拟轮询）
        vm.RefreshStatusCommand.Execute(null);

        // 等待异步完成
        await Task.Delay(500);

        // Assert: 结果应正确展示
        Assert.Equal("succeeded", vm.TaskStatus);
        Assert.True(vm.IsTaskCompleted);
        Assert.False(vm.IsTaskRunning);
        Assert.False(vm.HasError);
        Assert.Equal(2, vm.ResultFiles.Count);
        Assert.Equal("file-result-001", vm.ResultFiles[0].FileId);
        Assert.Equal("image/png", vm.ResultFiles[0].MimeType);
        Assert.Equal(2048, vm.ResultFiles[0].Width);
        Assert.Equal(1536, vm.ResultFiles[0].Height);
        Assert.Equal("aws", vm.Provider);
        Assert.Equal("stable-diffusion-upscale", vm.Model);
        Assert.Equal(5, vm.CreditsCharged);
    }

    // ============================================================
    // AI 改图参数检查
    // ============================================================

    /// <summary>
    /// AI 改图功能未填写 prompt 时，应显示错误
    /// </summary>
    [Fact]
    public void StartProcessing_WhenEditFeatureWithoutPrompt_ShouldSetError()
    {
        var authState = new AuthState();
        authState.SetLoggedIn(
            "token", "refresh", 3600,
            new UserInfo { Id = "u1", Account = "test", DisplayName = "测试" },
            new DeviceInfo { Id = "d1", Status = "active" });

        var httpClient = new HttpClient(new MockHttpMessageHandler(_ =>
            new HttpResponseMessage(HttpStatusCode.OK)));
        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiImageToolsViewModel(cloudApiClient, authState);

        vm.SelectedFeature = "ai_edit_image_cloud";
        vm.EditPrompt = ""; // 未填写 prompt
        vm.PendingFiles.Add(new PendingFileItem { FilePath = "test.png", FileName = "test.png" });

        vm.StartProcessingCommand.Execute(null);

        Assert.True(vm.HasError);
        Assert.Contains("Prompt", vm.ErrorMessage);
    }

    // ============================================================
    // TaskStatusDisplay 中文显示
    // ============================================================

    [Theory]
    [InlineData("queued", "排队中...")]
    [InlineData("running", "处理中...")]
    [InlineData("succeeded", "已完成")]
    [InlineData("failed", "失败")]
    public void TaskStatusDisplay_ShouldReturnChineseText(string status, string expected)
    {
        var vm = new AiImageToolsViewModel();

        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.TaskStatus))!
            .SetValue(vm, status);

        Assert.Equal(expected, vm.TaskStatusDisplay);
    }

    // ============================================================
    // 历史记录项测试
    // ============================================================

    [Fact]
    public void HistoryItem_DisplayProperties_ShouldBeCorrect()
    {
        var item = new AiImageToolHistoryItem
        {
            TaskId = "task-hist-12345678",
            Feature = "vectorize_image_cloud",
            InputFileNames = new List<string> { "logo.png", "icon.jpg", "banner.png", "extra.png" },
            Status = "succeeded",
            Provider = "aws",
            Model = "vector-model-v2",
            EstimatedCredits = 8,
            CreditsCharged = 5,
            RequestId = "req-hist-001"
        };

        Assert.Equal("📐 转矢量", item.FeatureDisplay);
        Assert.Equal("已完成", item.StatusDisplay);
        Assert.EndsWith("等 4 个文件", item.InputFilesSummary);
        Assert.Equal("-5 额度 / aws/vector-model-v2", item.CostSummary);
    }

    [Fact]
    public void HistoryItem_WhenNoCreditsCharged_ShouldShowEstimated()
    {
        var item = new AiImageToolHistoryItem
        {
            EstimatedCredits = 8,
            CreditsCharged = 0,
            Provider = "aws",
            Model = "model"
        };

        Assert.Equal("预估 8 额度", item.CostSummary);
    }

    [Theory]
    [InlineData("queued", "#D69E2E")]
    [InlineData("running", "#3182CE")]
    [InlineData("succeeded", "#38A169")]
    [InlineData("failed", "#E53E3E")]
    [InlineData("unknown", "#718096")]
    public void HistoryItem_StatusColor_ShouldBeCorrect(string status, string expectedColor)
    {
        var item = new AiImageToolHistoryItem { Status = status };
        Assert.Equal(expectedColor, item.StatusColor);
    }

    [Fact]
    public void HistoryCount_ShouldReflectCollectionChanges()
    {
        var vm = new AiImageToolsViewModel();
        Assert.Equal(0, vm.HistoryCount);

        vm.HistoryItems.Add(new AiImageToolHistoryItem());
        Assert.Equal(1, vm.HistoryCount);

        vm.HistoryItems.Clear();
        Assert.Equal(0, vm.HistoryCount);
    }

    // ============================================================
    // SelectHistoryItem 恢复任务
    // ============================================================

    [Fact]
    public void SelectHistoryItem_ShouldRestoreTaskProperties()
    {
        var vm = new AiImageToolsViewModel();
        var historyItem = new AiImageToolHistoryItem
        {
            TaskId = "task-restore-001",
            Feature = "ocr_cloud",
            Status = "succeeded",
            Provider = "aws",
            Model = "textract",
            CreditsCharged = 3
        };

        vm.SelectHistoryItemCommand.Execute(historyItem);

        Assert.Equal("task-restore-001", vm.CurrentTaskId);
        Assert.Equal("ocr_cloud", vm.SelectedFeature);
        Assert.Equal("succeeded", vm.TaskStatus);
        Assert.Equal("aws", vm.Provider);
        Assert.Equal("textract", vm.Model);
        Assert.Equal(3, vm.CreditsCharged);
    }

    [Fact]
    public void SelectHistoryItem_WhenNull_ShouldNotChange()
    {
        var vm = new AiImageToolsViewModel();
        vm.SelectedFeature = "ocr_cloud";

        vm.SelectHistoryItemCommand.Execute(null);

        Assert.Equal("ocr_cloud", vm.SelectedFeature);
    }

    // ============================================================
    // Clear 重置测试
    // ============================================================

    [Fact]
    public void Clear_ShouldResetAllState()
    {
        var vm = new AiImageToolsViewModel();
        vm.SelectedFeature = "ai_edit_image_cloud";
        vm.EditPrompt = "修改背景";
        vm.VectorOutputFormat = "pdf";
        vm.OcrLanguage = "zh";
        vm.UpscaleFactor = 4;
        vm.ErrorMessage = "error";
        vm.PendingFiles.Add(new PendingFileItem { FilePath = "test.png", FileName = "test.png" });

        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.CurrentTaskId))!
            .SetValue(vm, "task-123");
        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.TaskStatus))!
            .SetValue(vm, "running");
        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.Provider))!
            .SetValue(vm, "aws");
        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.Model))!
            .SetValue(vm, "model");
        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.CreditsCharged))!
            .SetValue(vm, 5);
        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.OcrResultText))!
            .SetValue(vm, "识别结果");

        // Act
        vm.ClearCommand.Execute(null);

        // Assert
        Assert.Equal("upscale_image_cloud", vm.SelectedFeature);
        Assert.Equal("", vm.EditPrompt);
        Assert.Equal("svg", vm.VectorOutputFormat);
        Assert.Equal("auto", vm.OcrLanguage);
        Assert.Equal(2, vm.UpscaleFactor);
        Assert.Equal("", vm.CurrentTaskId);
        Assert.Equal("", vm.TaskStatus);
        Assert.Equal("", vm.Provider);
        Assert.Equal("", vm.Model);
        Assert.Equal("", vm.OcrResultText);
        Assert.Equal(0, vm.CreditsCharged);
        Assert.Null(vm.ErrorMessage);
        Assert.Empty(vm.PendingFiles);
        Assert.Empty(vm.ResultFiles);
    }

    // ============================================================
    // PendingFileItem 展示属性
    // ============================================================

    [Theory]
    [InlineData(500, "500 B")]
    [InlineData(1536, "1.5 KB")]
    [InlineData(1048576, "1.0 MB")]
    [InlineData(3145728, "3.0 MB")]
    public void PendingFileItem_FileSizeDisplay_ShouldBeHumanReadable(long fileSize, string expected)
    {
        var item = new PendingFileItem { FileSize = fileSize };
        Assert.Equal(expected, item.FileSizeDisplay);
    }

    // ============================================================
    // ShowOcrResult 逻辑
    // ============================================================

    [Fact]
    public void ShowOcrResult_WhenOcrTaskSucceeded_ShouldBeTrue()
    {
        var vm = new AiImageToolsViewModel();

        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.TaskStatus))!
            .SetValue(vm, "succeeded");
        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.TaskFeature))!
            .SetValue(vm, "ocr_cloud");
        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.OcrResultText))!
            .SetValue(vm, "识别结果文本\n保留换行");

        Assert.True(vm.ShowOcrResult);
    }

    [Fact]
    public void ShowOcrResult_WhenNotOcr_ShouldBeFalse()
    {
        var vm = new AiImageToolsViewModel();

        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.TaskStatus))!
            .SetValue(vm, "succeeded");
        typeof(AiImageToolsViewModel)
            .GetProperty(nameof(AiImageToolsViewModel.TaskFeature))!
            .SetValue(vm, "upscale_image_cloud");

        Assert.False(vm.ShowOcrResult);
    }

    // ============================================================
    // 服务不可用测试
    // ============================================================

    [Fact]
    public async Task StartProcessing_WhenEntitlementServiceUnavailable_ShouldShowError()
    {
        var authState = new AuthState();
        authState.SetLoggedIn(
            "token", "refresh", 3600,
            new UserInfo { Id = "u1", Account = "test", DisplayName = "测试" },
            new DeviceInfo { Id = "d1", Status = "active" });

        // Mock: 权限检查返回 500
        var mockHandler = MockHttpMessageHandler.CreateErrorResponse(HttpStatusCode.InternalServerError);
        var httpClient = new HttpClient(mockHandler) { BaseAddress = new Uri("http://test.local") };
        var cloudApiClient = new CloudApiClient(httpClient, authState);
        var vm = new AiImageToolsViewModel(cloudApiClient, authState);

        vm.PendingFiles.Add(new PendingFileItem { FilePath = "test.png", FileName = "test.png" });

        vm.StartProcessingCommand.Execute(null);
        await Task.Delay(500);

        Assert.True(vm.HasError);
        Assert.Contains("权限检查失败", vm.ErrorMessage);
        Assert.False(vm.HasTaskResult);
    }
}
