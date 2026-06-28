using System.Text.Json;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTShared.LocalRuntime;
using TTShared.Logging;
using TTShared.Settings;
using TTTools.ResizeImage.Models;

namespace TTTools.ResizeImage.Services;

/// <summary>
/// 图片改尺寸服务
/// 封装套餐权限校验（CloudApiClient）+ 本地 Python worker 通信（LocalRuntimeClient）。
/// 本地付费功能：每次 resize 前必须通过 /api/v1/entitlements/check 检查权限。
/// 权限 fail closed：未登录、网络错误、接口异常、allowed=false 均拒绝执行。
/// </summary>
public class ResizeImageService : IDisposable
{
    private readonly LocalRuntimeClient? _runtimeClient;
    private readonly CloudApiClient _cloudApiClient;
    private readonly AuthState _authState;
    private readonly JobManager? _jobManager;
    private readonly AppLogger? _logger;
    private readonly string _pythonPath;
    private readonly string _routerScriptPath;
    private bool _isAvailable;
    private string? _availabilityError;

    /// <summary>关联的认证状态（供 ViewModel 读取登录态）</summary>
    public AuthState AuthState => _authState;

    /// <summary>服务是否可用（worker 已启动且健康检查通过）</summary>
    public bool IsAvailable => _isAvailable;

    /// <summary>引擎名称</summary>
    public string EngineName { get; private set; } = "Pillow (纯本地图像处理)";

    /// <summary>支持的输入图片格式</summary>
    public static readonly HashSet<string> SupportedFormats = new(StringComparer.OrdinalIgnoreCase)
    {
        ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"
    };

    /// <summary>服务不可用时的错误信息</summary>
    public string? AvailabilityError => _availabilityError;

    /// <summary>缓存的预设列表</summary>
    private List<PresetInfo>? _cachedPresets;

    /// <summary>
    /// 初始化图片改尺寸服务。
    /// </summary>
    /// <param name="pythonPath">Python 解释器路径</param>
    /// <param name="routerScriptPath">resize_image_router.py 脚本路径</param>
    /// <param name="cloudApiClient">云端 API 客户端（C1: 必须非 null）</param>
    /// <param name="authState">认证状态（C1: 必须非 null）</param>
    /// <param name="jobManager">任务管理器（可选）</param>
    /// <param name="logger">日志记录器（可选）</param>
    /// <exception cref="ArgumentNullException">cloudApiClient 或 authState 为 null</exception>
    public ResizeImageService(
        string pythonPath,
        string routerScriptPath,
        CloudApiClient cloudApiClient,
        AuthState authState,
        JobManager? jobManager = null,
        AppLogger? logger = null)
    {
        _pythonPath = pythonPath ?? throw new ArgumentNullException(nameof(pythonPath));
        _routerScriptPath = routerScriptPath ?? throw new ArgumentNullException(nameof(routerScriptPath));
        // C1: cloudApiClient 和 authState 必须非 null（fail closed 的基础）
        _cloudApiClient = cloudApiClient ?? throw new ArgumentNullException(nameof(cloudApiClient));
        _authState = authState ?? throw new ArgumentNullException(nameof(authState));
        _jobManager = jobManager;
        _logger = logger;

        _runtimeClient = new LocalRuntimeClient(pythonPath, routerScriptPath);
        _runtimeClient.ProcessExited += OnProcessExited;
    }

    /// <summary>
    /// 默认构造函数（壳层无 DI 时使用，自动解析 Python 路径和 router 脚本路径）
    /// </summary>
    public ResizeImageService()
    {
        _authState = AuthState.Shared;
        _cloudApiClient = new CloudApiClient(AppSettings.Instance.ServerUrl, _authState);
        // resize-image 模块专用 venv
        _pythonPath = @"D:\localPath\venvs\local-worker-resize-image\Scripts\python.exe";
        // router 脚本与 DLL 在同一输出目录（csproj 配置了 CopyToOutputDirectory）
        _routerScriptPath = Path.Combine(
            Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location)!,
            "resize_image_router.py");

        _runtimeClient = new LocalRuntimeClient(_pythonPath, _routerScriptPath);
        _runtimeClient.ProcessExited += OnProcessExited;
    }

    /// <summary>
    /// 启动 Python worker 进程并进行健康检查，同时预加载预设列表。
    /// </summary>
    public async Task<bool> StartAsync(CancellationToken ct = default)
    {
        if (_runtimeClient == null) return false;

        try
        {
            var started = await _runtimeClient.StartAsync(ct);
            if (!started)
            {
                _isAvailable = false;
                _availabilityError = "改尺寸 worker 进程启动失败";
                return false;
            }

            // 健康检查
            JsonElement? pingResult = await _runtimeClient.SendAsync<object, JsonElement>(
                "ping", new { }, ct);

            if (pingResult is not null)
            {
                var ping = pingResult.Value;
                // 从 ping 响应中提取引擎信息
                if (ping.TryGetProperty("engine", out var engine))
                    EngineName = engine.GetString() ?? EngineName;
            }

            // 预加载预设列表
            await LoadPresetsAsync(ct);

            _isAvailable = true;
            _availabilityError = null;
            _logger?.Info("图片改尺寸服务就绪", "desktop-resize-image");
            return true;
        }
        catch (Exception ex)
        {
            _isAvailable = false;
            _availabilityError = $"改尺寸服务启动失败: {ex.Message}";
            _logger?.Error($"改尺寸服务启动失败: {ex.Message}", ex, "desktop-resize-image");
            return false;
        }
    }

    /// <summary>
    /// 预加载预设尺寸列表（启动时调用一次，无权限要求）。
    /// </summary>
    private async Task LoadPresetsAsync(CancellationToken ct)
    {
        try
        {
            JsonElement? resp = await _runtimeClient!.SendAsync<object, JsonElement>(
                "list_presets", new { }, ct);
            if (resp is not null)
            {
                var r = resp.Value;
                if (r.TryGetProperty("presets", out var arr))
                {
                    _cachedPresets = arr.EnumerateArray()
                        .Select(e => PresetInfo.FromJsonElement(e))
                        .ToList();
                }
            }
        }
        catch (Exception ex)
        {
            _logger?.Warning($"预加载预设列表失败: {ex.Message}", "desktop-resize-image");
            // 预加载失败不是致命错误，后续按需获取
        }
    }

    /// <summary>
    /// 获取所有可用预设尺寸。
    /// </summary>
    /// <param name="useCache">是否使用缓存（默认 true）</param>
    public async Task<List<PresetInfo>> GetPresetsAsync(
        bool useCache = true, CancellationToken ct = default)
    {
        if (useCache && _cachedPresets != null)
            return _cachedPresets;

        if (!_isAvailable || _runtimeClient == null)
            throw new InvalidOperationException(_availabilityError ?? "改尺寸服务不可用");

        JsonElement? resp = await _runtimeClient.SendAsync<object, JsonElement>(
            "list_presets", new { }, ct);

        if (resp is null)
            throw new InvalidOperationException("Worker 返回空响应");

        var r = resp.Value;
        if (r.TryGetProperty("presets", out var arr))
        {
            _cachedPresets = arr.EnumerateArray()
                .Select(e => PresetInfo.FromJsonElement(e))
                .ToList();
            return _cachedPresets;
        }

        return new List<PresetInfo>();
    }

    /// <summary>
    /// 对单张图片执行改尺寸处理（含套餐权限校验）。
    /// C1: 每次调用都检查权限，权限不通过时拒绝执行，不创建输出文件。
    /// </summary>
    /// <param name="inputPath">输入图片文件路径</param>
    /// <param name="outputPath">输出文件路径（可选，为空时由 worker 自动生成）</param>
    /// <param name="params">改尺寸参数</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>处理结果（含权限信息）</returns>
    public async Task<ResizeImageResult> ResizeAsync(
        string inputPath,
        string? outputPath,
        ResizeImageParams param,
        CancellationToken ct = default)
    {
        // ---- 1. 校验登录状态（C1: 未登录直接拒绝，不调网络） ----
        if (!_authState.IsLoggedIn)
        {
            _logger?.Warning("未登录，拒绝改尺寸请求", "desktop-resize-image");
            return new ResizeImageResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = false,
                EntitlementReason = "请先登录后再使用图片改尺寸功能",
                ErrorMessage = "未登录",
            };
        }

        // ---- 2. 校验输入文件 ----
        if (!File.Exists(inputPath))
        {
            return new ResizeImageResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                ErrorMessage = $"图片文件不存在: {inputPath}",
            };
        }

        var ext = FileSystemService.GetExtension(inputPath);
        if (!SupportedFormats.Contains(ext))
        {
            return new ResizeImageResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                ErrorMessage = $"不支持的图片格式: {ext}，支持: {string.Join(", ", SupportedFormats)}",
            };
        }

        // ---- 3. 套餐权限检查（C1: fail closed） ----
        // 每次 resize 前都调用，不缓存权限结果
        _logger?.Info($"开始权限检查: {Path.GetFileName(inputPath)}", "desktop-resize-image");

        ApiResponse<EntitlementCheckData>? entitlementResp;
        try
        {
            entitlementResp = await _cloudApiClient.CheckEntitlementAsync(
                "resize_image_local_paid", "single",
                clientRequestId: $"resize_{Guid.NewGuid():N}",
                ct: ct);
        }
        catch (Exception ex)
        {
            // 网络异常视为无权限（C1: fail closed）
            _logger?.Error($"权限检查网络异常: {ex.Message}", ex, "desktop-resize-image");
            return new ResizeImageResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = false,
                EntitlementReason = "无法连接云端权限服务，请检查网络连接",
                ErrorMessage = $"权限检查失败: {ex.Message}",
            };
        }

        // ---- 4. 权限判断（fail closed: 只有明确 success + allowed 才放行） ----
        if (entitlementResp == null)
        {
            _logger?.Warning("权限检查返回 null，拒绝执行", "desktop-resize-image");
            return new ResizeImageResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = false,
                EntitlementReason = "无法连接云端权限服务",
                ErrorMessage = "权限服务返回空响应",
            };
        }

        if (!entitlementResp.IsSuccess || entitlementResp.Data == null)
        {
            var reason = entitlementResp.Error?.Message ?? "权限服务返回异常";
            _logger?.Warning($"权限检查失败: {reason}", "desktop-resize-image");
            return new ResizeImageResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = false,
                EntitlementReason = reason,
                ErrorMessage = $"权限检查失败: {reason}",
            };
        }

        if (!entitlementResp.Data.Allowed)
        {
            _logger?.Info(
                $"权限拒绝: feature=resize_image_local_paid, " +
                $"reason={entitlementResp.Data.Reason}, " +
                $"plan={entitlementResp.Data.PlanId}",
                "desktop-resize-image");
            return new ResizeImageResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = false,
                EntitlementReason = entitlementResp.Data.Reason ?? "当前套餐不支持此功能",
                PlanCode = entitlementResp.Data.PlanId,
                RemainingFreeQuota = entitlementResp.Data.RemainingFreeQuota,
                ErrorMessage = "套餐权限不足",
            };
        }

        // ---- 5. 权限通过，执行 resize ----
        if (!_isAvailable || _runtimeClient == null)
        {
            return new ResizeImageResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = true,
                PlanCode = entitlementResp.Data.PlanId,
                ErrorMessage = _availabilityError ?? "改尺寸服务不可用，请先调用 StartAsync",
            };
        }

        _logger?.Info(
            $"权限通过，开始改尺寸: {Path.GetFileName(inputPath)}, " +
            $"mode={param.Mode}, preset={param.Preset ?? "自定义"}",
            "desktop-resize-image");

        // 构建发送给 Python worker 的请求数据
        var requestData = BuildRequestData(inputPath, outputPath, param);

        JsonElement? workerResp;
        try
        {
            workerResp = await _runtimeClient.SendAsync<object, JsonElement>(
                "resize", requestData, ct);
        }
        catch (Exception ex)
        {
            _logger?.Error($"Worker 通信异常: {ex.Message}", ex, "desktop-resize-image");
            return new ResizeImageResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = true,
                PlanCode = entitlementResp.Data.PlanId,
                ErrorMessage = $"改尺寸处理失败: {ex.Message}",
            };
        }

        if (workerResp is null)
        {
            return new ResizeImageResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = true,
                PlanCode = entitlementResp.Data.PlanId,
                ErrorMessage = "改尺寸 worker 返回空响应",
            };
        }

        var resp = workerResp.Value;

        // 检查 worker 是否返回了错误
        if (resp.TryGetProperty("success", out var successProp) && !successProp.GetBoolean())
        {
            var error = resp.TryGetProperty("error", out var err)
                ? err.GetString() ?? "未知错误" : "未知错误";
            return new ResizeImageResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = true,
                PlanCode = entitlementResp.Data.PlanId,
                ErrorMessage = error,
            };
        }

        // ---- 6. 构建成功结果 ----
        var data = resp.TryGetProperty("data", out var d) ? d : resp;
        var result = ResizeImageResult.FromRouterResponse(data, inputPath);
        result.IsSuccess = true;
        result.EntitlementAllowed = true;
        result.PlanCode = entitlementResp.Data.PlanId;
        result.RemainingFreeQuota = entitlementResp.Data.RemainingFreeQuota;

        _logger?.Info(
            $"改尺寸完成: {Path.GetFileName(inputPath)}, " +
            $"尺寸={result.SizeSummary}, " +
            $"格式={result.OutputFormatSummary}, " +
            $"耗时={result.ElapsedMs:F1}ms",
            "desktop-resize-image");

        return result;
    }

    /// <summary>
    /// 带任务跟踪的改尺寸处理（C1: 权限拒绝时 Job 标记为 Failed）。
    /// </summary>
    public async Task<string> ProcessWithJobTrackingAsync(
        string inputPath,
        string? outputPath,
        ResizeImageParams param,
        CancellationToken ct = default)
    {
        if (_jobManager == null)
            throw new InvalidOperationException("未配置 JobManager");

        // 创建任务记录
        var job = _jobManager.CreateJob(
            $"图片改尺寸 - {Path.GetFileName(inputPath)}",
            "resize_image_local_paid",
            new List<string> { inputPath });

        try
        {
            _jobManager.UpdateJobStatus(job.Id, JobStatus.Running);
            _jobManager.UpdateJobProgress(job.Id, 0);

            var result = await ResizeAsync(inputPath, outputPath, param, ct);

            _jobManager.UpdateJobProgress(job.Id, 50);

            if (!result.IsSuccess)
            {
                // C1: 权限拒绝或处理失败均标记为 Failed
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Failed,
                    result.EntitlementAllowed
                        ? (result.ErrorMessage ?? "改尺寸处理失败")
                        : $"权限拒绝: {result.EntitlementReason}");
            }
            else
            {
                job.OutputFiles = new List<string> { result.OutputPath };
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Succeeded,
                    $"尺寸={result.SizeSummary}, 格式={result.OutputFormatSummary}");
            }

            _jobManager.UpdateJobProgress(job.Id, 100);
        }
        catch (OperationCanceledException)
        {
            _jobManager.UpdateJobStatus(job.Id, JobStatus.Cancelled, "任务已取消");
            throw;
        }
        catch (Exception ex)
        {
            _jobManager.UpdateJobStatus(job.Id, JobStatus.Failed, ex.Message);
            throw;
        }

        return job.Id;
    }

    /// <summary>
    /// 判断文件格式是否支持改尺寸处理。
    /// </summary>
    public bool IsFormatSupported(string filePath)
    {
        var ext = FileSystemService.GetExtension(filePath);
        return SupportedFormats.Contains(ext);
    }

    /// <summary>
    /// 健康检查。
    /// </summary>
    public async Task<bool> PingAsync(CancellationToken ct = default)
    {
        if (_runtimeClient == null || !_runtimeClient.IsRunning) return false;
        try
        {
            return await _runtimeClient.PingAsync(ct);
        }
        catch
        {
            _isAvailable = false;
            return false;
        }
    }

    /// <summary>
    /// 停止 Python worker 进程。
    /// </summary>
    public void Stop()
    {
        _runtimeClient?.Stop();
        _isAvailable = false;
    }

    // ===== 内部方法 =====

    /// <summary>
    /// 将 ResizeImageParams 构建为发送给 Python worker 的字典。
    /// </summary>
    private static Dictionary<string, object?> BuildRequestData(
        string inputPath, string? outputPath, ResizeImageParams param)
    {
        var data = new Dictionary<string, object?>
        {
            ["input_path"] = inputPath,
            ["mode"] = param.Mode,
            ["resample"] = param.Resample,
            ["output_format"] = param.OutputFormat,
            ["keep_aspect"] = param.KeepAspect,
            ["jpeg_quality"] = param.JpegQuality,
            ["png_compress_level"] = param.PngCompressLevel,
            ["webp_quality"] = param.WebpQuality,
        };

        // 可选字段按模式添加
        if (param.Width.HasValue)
            data["width"] = param.Width.Value;
        if (param.Height.HasValue)
            data["height"] = param.Height.Value;
        if (param.ScalePercent != 100.0)
            data["scale_percent"] = param.ScalePercent;
        if (param.ShortSide.HasValue)
            data["short_side"] = param.ShortSide.Value;
        if (param.LongSide.HasValue)
            data["long_side"] = param.LongSide.Value;
        if (param.TargetDpi.HasValue)
            data["target_dpi"] = param.TargetDpi.Value;

        // 输出路径（C4: Python bridge 会校验外部传入路径）
        if (!string.IsNullOrEmpty(outputPath))
            data["output_path"] = outputPath;

        // DPI
        if (param.Dpi != null && param.Dpi.Count == 2)
            data["dpi"] = param.Dpi;

        // Preset（优先级高于 mode + 尺寸参数）
        if (!string.IsNullOrEmpty(param.Preset))
            data["preset"] = param.Preset;

        return data;
    }

    /// <summary>
    /// Worker 进程退出回调。
    /// </summary>
    private void OnProcessExited(object? sender, int exitCode)
    {
        _isAvailable = false;
        _availabilityError = $"改尺寸 worker 进程已退出，退出码: {exitCode}";
        _logger?.Warning($"改尺寸 worker 进程退出 (exitCode={exitCode})", "desktop-resize-image");
    }

    public void Dispose()
    {
        if (_runtimeClient != null)
            _runtimeClient.ProcessExited -= OnProcessExited;
        _runtimeClient?.Dispose();
        GC.SuppressFinalize(this);
    }
}
