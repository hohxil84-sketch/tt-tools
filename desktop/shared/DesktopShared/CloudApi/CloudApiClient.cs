using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using TTShared.Auth;
using TTShared.CloudApi.Dtos;

namespace TTShared.CloudApi;

/// <summary>
/// 云端 API 客户端
/// 封装所有云端 HTTP 调用，自动附加 Bearer 鉴权头。
/// DTO 字段严格对应 shared-contract/openapi/*.yaml 定义。
/// </summary>
public class CloudApiClient : IDisposable
{
    private readonly HttpClient _httpClient;
    private readonly AuthState _authState;
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    public event EventHandler<string>? TokenRefreshFailed;

    /// <summary>
    /// 初始化云端 API 客户端
    /// </summary>
    /// <param name="baseUrl">云端 API 基础 URL，如 https://api.example.com</param>
    /// <param name="authState">认证状态实例</param>
    public CloudApiClient(string baseUrl, AuthState authState)
    {
        _authState = authState;
        _httpClient = new HttpClient
        {
            BaseAddress = new Uri(baseUrl.TrimEnd('/')),
            Timeout = TimeSpan.FromSeconds(30)
        };
        _httpClient.DefaultRequestHeaders.Accept.Add(
            new MediaTypeWithQualityHeaderValue("application/json"));
    }

    /// <summary>
    /// 初始化云端 API 客户端（可注入自定义 HttpClient，方便测试 mock）
    /// </summary>
    public CloudApiClient(HttpClient httpClient, AuthState authState)
    {
        _httpClient = httpClient;
        _authState = authState;
    }

    // ==================== Auth / Device ====================

    /// <summary>登录</summary>
    public async Task<ApiResponse<LoginData>?> LoginAsync(string account, string password,
        string deviceFingerprint, string? deviceName = null, string? clientVersion = null,
        CancellationToken ct = default)
    {
        // 桌面端不保存明文密码，构造请求后立即释放
        var request = new LoginRequest
        {
            Account = account,
            Password = password,
            DeviceFingerprint = deviceFingerprint,
            DeviceName = deviceName ?? Environment.MachineName,
            ClientVersion = clientVersion ?? "0.1.0"
        };

        return await PostAsync<LoginRequest, LoginData>("/api/v1/auth/login", request, ct);
    }

    /// <summary>刷新访问令牌</summary>
    public async Task<ApiResponse<RefreshData>?> RefreshTokenAsync(string refreshToken,
        CancellationToken ct = default)
    {
        var request = new RefreshRequest { RefreshToken = refreshToken };
        return await PostAsync<RefreshRequest, RefreshData>("/api/v1/auth/refresh", request, ct);
    }

    /// <summary>退出登录</summary>
    public async Task<ApiResponse<Dictionary<string, bool>>?> LogoutAsync(string refreshToken,
        CancellationToken ct = default)
    {
        var request = new LogoutRequest { RefreshToken = refreshToken };
        return await PostAsync<LogoutRequest, Dictionary<string, bool>>(
            "/api/v1/auth/logout", request, ct);
    }

    /// <summary>获取当前设备状态</summary>
    public async Task<ApiResponse<CurrentDeviceDto>?> GetCurrentDeviceAsync(
        CancellationToken ct = default)
    {
        return await GetAsync<CurrentDeviceDto>("/api/v1/devices/current", ct);
    }

    /// <summary>绑定当前设备</summary>
    public async Task<ApiResponse<DeviceDto>?> BindDeviceAsync(string deviceFingerprint,
        string? deviceName = null, string? clientVersion = null,
        CancellationToken ct = default)
    {
        var request = new BindDeviceRequest
        {
            DeviceFingerprint = deviceFingerprint,
            DeviceName = deviceName ?? Environment.MachineName,
            ClientVersion = clientVersion ?? "0.1.0"
        };
        return await PostAsync<BindDeviceRequest, DeviceDto>("/api/v1/devices/bind", request, ct);
    }

    // ==================== Credits / Billing ====================

    /// <summary>查询 AI 额度余额</summary>
    public async Task<ApiResponse<CreditBalanceDto>?> GetCreditBalanceAsync(
        CancellationToken ct = default)
    {
        return await GetAsync<CreditBalanceDto>("/api/v1/credits/balance", ct);
    }

    /// <summary>查询额度流水</summary>
    public async Task<ApiResponse<PaginatedData<CreditLedgerItemDto>>?> GetCreditLedgerAsync(
        int limit = 50, int offset = 0, string? changeType = null,
        CancellationToken ct = default)
    {
        var query = $"/api/v1/credits/ledger?limit={limit}&offset={offset}";
        if (!string.IsNullOrEmpty(changeType))
            query += $"&change_type={Uri.EscapeDataString(changeType)}";
        return await GetAsync<PaginatedData<CreditLedgerItemDto>>(query, ct);
    }

    /// <summary>检查套餐权限（本地付费功能调用前）</summary>
    public async Task<ApiResponse<EntitlementCheckData>?> CheckEntitlementAsync(
        string feature, string operation = "single", string? clientRequestId = null,
        CancellationToken ct = default)
    {
        // 桌面端生成请求追踪 ID（不决定套餐权限和扣费）
        var request = new EntitlementCheckRequest
        {
            Feature = feature,
            Operation = operation,
            ClientRequestId = clientRequestId ?? GenerateClientRequestId()
        };
        return await PostAsync<EntitlementCheckRequest, EntitlementCheckData>(
            "/api/v1/entitlements/check", request, ct);
    }

    // ==================== AI Copy ====================

    /// <summary>生成广告文案</summary>
    public async Task<ApiResponse<AiCopyGenerateData>?> GenerateAiCopyAsync(
        AiCopyGenerateRequest request, CancellationToken ct = default)
    {
        // 确保 client_request_id 存在
        request.ClientRequestId = string.IsNullOrEmpty(request.ClientRequestId)
            ? GenerateClientRequestId()
            : request.ClientRequestId;
        return await PostAsync<AiCopyGenerateRequest, AiCopyGenerateData>(
            "/api/v1/ai/copy/generate", request, ct);
    }

    /// <summary>预估文案生成扣点和耗时</summary>
    public async Task<ApiResponse<AiCopyEstimateResponse>?> EstimateAiCopyAsync(
        AiCopyEstimateRequest request, CancellationToken ct = default)
    {
        request.ClientRequestId = string.IsNullOrEmpty(request.ClientRequestId)
            ? GenerateClientRequestId()
            : request.ClientRequestId;
        return await PostAsync<AiCopyEstimateRequest, AiCopyEstimateResponse>(
            "/api/v1/ai/copy/estimate", request, ct);
    }

    // ==================== AI Render ====================

    /// <summary>创建效果图生成任务</summary>
    public async Task<ApiResponse<CreatedTaskData>?> CreateAiRenderTaskAsync(
        CreateAiRenderTaskRequest request, CancellationToken ct = default)
    {
        request.ClientRequestId = string.IsNullOrEmpty(request.ClientRequestId)
            ? GenerateClientRequestId()
            : request.ClientRequestId;
        return await PostAsync<CreateAiRenderTaskRequest, CreatedTaskData>(
            "/api/v1/ai/render/tasks", request, ct);
    }

    /// <summary>查询效果图生成任务</summary>
    public async Task<ApiResponse<AiRenderTaskData>?> GetAiRenderTaskAsync(
        string taskId, CancellationToken ct = default)
    {
        return await GetAsync<AiRenderTaskData>(
            $"/api/v1/ai/render/tasks/{Uri.EscapeDataString(taskId)}", ct);
    }

    // ==================== AI Image Tools ====================

    /// <summary>创建高级图片 AI 任务</summary>
    public async Task<ApiResponse<CreatedTaskData>?> CreateAiImageToolTaskAsync(
        CreateAiImageToolTaskRequest request, CancellationToken ct = default)
    {
        request.ClientRequestId = string.IsNullOrEmpty(request.ClientRequestId)
            ? GenerateClientRequestId()
            : request.ClientRequestId;
        return await PostAsync<CreateAiImageToolTaskRequest, CreatedTaskData>(
            "/api/v1/ai/image-tools/tasks", request, ct);
    }

    /// <summary>查询高级图片 AI 任务</summary>
    public async Task<ApiResponse<AiImageToolTaskData>?> GetAiImageToolTaskAsync(
        string taskId, CancellationToken ct = default)
    {
        return await GetAsync<AiImageToolTaskData>(
            $"/api/v1/ai/image-tools/tasks/{Uri.EscapeDataString(taskId)}", ct);
    }

    // ==================== Provider Log ====================

    /// <summary>查询 Provider 调用日志</summary>
    public async Task<ApiResponse<PaginatedData<ProviderCallLogItemDto>>?> GetProviderCallLogsAsync(
        int limit = 50, int offset = 0, string? feature = null,
        string? status = null, string? provider = null, CancellationToken ct = default)
    {
        var query = $"/api/v1/provider-call-logs?limit={limit}&offset={offset}";
        if (!string.IsNullOrEmpty(feature))
            query += $"&feature={Uri.EscapeDataString(feature)}";
        if (!string.IsNullOrEmpty(status))
            query += $"&status={Uri.EscapeDataString(status)}";
        if (!string.IsNullOrEmpty(provider))
            query += $"&provider={Uri.EscapeDataString(provider)}";
        return await GetAsync<PaginatedData<ProviderCallLogItemDto>>(query, ct);
    }

    // ==================== 内部 HTTP 方法 ====================

    /// <summary>
    /// 发送 GET 请求，自动附加 Bearer 令牌和自动刷新
    /// </summary>
    private async Task<ApiResponse<T>?> GetAsync<T>(string path, CancellationToken ct)
    {
        return await SendAsync<T>(() =>
            new HttpRequestMessage(HttpMethod.Get, path), ct);
    }

    /// <summary>
    /// 发送 POST 请求，自动附加 Bearer 令牌和自动刷新
    /// </summary>
    private async Task<ApiResponse<T>?> PostAsync<TReq, T>(string path, TReq body,
        CancellationToken ct)
    {
        return await SendAsync<T>(() =>
        {
            var msg = new HttpRequestMessage(HttpMethod.Post, path);
            msg.Content = new StringContent(
                JsonSerializer.Serialize(body, JsonOptions),
                Encoding.UTF8, "application/json");
            return msg;
        }, ct);
    }

    /// <summary>
    /// 统一发送请求，处理鉴权、自动刷新和错误
    /// </summary>
    private async Task<ApiResponse<T>?> SendAsync<T>(
        Func<HttpRequestMessage> requestFactory, CancellationToken ct)
    {
        // 尝试刷新过期令牌
        if (_authState.IsLoggedIn && _authState.IsTokenExpiringSoon())
        {
            await TryRefreshTokenAsync(ct);
        }

        var request = requestFactory();
        AttachAuthHeader(request);

        try
        {
            var response = await _httpClient.SendAsync(request, ct);

            // 如果 401 且已登录，尝试刷新令牌后重试一次
            if (response.StatusCode == System.Net.HttpStatusCode.Unauthorized &&
                _authState.IsLoggedIn && !string.IsNullOrEmpty(_authState.RefreshTokenValue))
            {
                var refreshed = await TryRefreshTokenAsync(ct);
                if (refreshed)
                {
                    // 使用新令牌重试
                    request.Dispose();
                    request = requestFactory();
                    AttachAuthHeader(request);
                    response.Dispose();
                    response = await _httpClient.SendAsync(request, ct);
                }
            }

            var responseBody = await response.Content.ReadAsStringAsync(ct);
            if (!string.IsNullOrWhiteSpace(responseBody))
            {
                try
                {
                    var apiResponse = JsonSerializer.Deserialize<ApiResponse<T>>(responseBody, JsonOptions);
                    if (apiResponse != null)
                        return apiResponse;
                }
                catch (JsonException)
                {
                    // 非统一 JSON 错误体会落到下面的 http_error，避免登录页丢失结果。
                }
            }

            if (!response.IsSuccessStatusCode)
            {
                return new ApiResponse<T>
                {
                    Success = false,
                    Data = default,
                    Error = new ApiError
                    {
                        Code = "http_error",
                        Message = $"HTTP {(int)response.StatusCode} {response.ReasonPhrase}"
                    },
                    RequestId = string.Empty
                };
            }

            return null;
        }
        catch (HttpRequestException ex)
        {
            // 网络错误时返回包含错误信息的模拟响应
            return new ApiResponse<T>
            {
                Success = false,
                Data = default,
                Error = new ApiError
                {
                    Code = "network_error",
                    Message = ex.Message
                },
                RequestId = string.Empty
            };
        }
    }

    /// <summary>
    /// 为请求附加 Bearer 鉴权头
    /// </summary>
    private void AttachAuthHeader(HttpRequestMessage request)
    {
        if (_authState.IsLoggedIn && !string.IsNullOrEmpty(_authState.AccessToken))
        {
            request.Headers.Authorization = new AuthenticationHeaderValue(
                "Bearer", _authState.AccessToken);
        }
    }

    /// <summary>
    /// 尝试刷新令牌，成功返回 true
    /// </summary>
    private async Task<bool> TryRefreshTokenAsync(CancellationToken ct)
    {
        if (string.IsNullOrEmpty(_authState.RefreshTokenValue)) return false;

        _authState.SetRefreshing();
        var result = await RefreshTokenAsync(_authState.RefreshTokenValue, ct);

        if (result?.IsSuccess == true && result.Data != null)
        {
            _authState.UpdateTokens(
                result.Data.AccessToken,
                result.Data.RefreshToken,
                result.Data.ExpiresIn);
            return true;
        }

        // 刷新失败，触发登出
        TokenRefreshFailed?.Invoke(this, result?.Error?.Message ?? "令牌刷新失败");
        _authState.Logout();
        return false;
    }

    /// <summary>
    /// 生成客户端请求追踪 ID
    /// </summary>
    private static string GenerateClientRequestId()
        => $"req_{Guid.NewGuid():N}";

    public void Dispose()
    {
        _httpClient?.Dispose();
        GC.SuppressFinalize(this);
    }
}
