using System.Text.Json;
using TTShared.LocalRuntime;
using TTShared.Logging;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTTools.RemoveBg.Models;

namespace TTTools.RemoveBg.Services;

/// <summary>
/// 智能抠图服务
/// 封装与 local-worker remove-bg 引擎的通信，提供背景去除、模型查询、缓存管理能力。
/// 通过 LocalRuntimeClient 启动 Python worker 进程，使用 stdin/stdout JSON 协议通信。
/// 智能抠图是本地免费功能，不需要云端权限检查。
/// </summary>
public class RemoveBgService : IDisposable
{
    private readonly LocalRuntimeClient? _runtimeClient;
    private readonly JobManager? _jobManager;
    private readonly AppLogger? _logger;
    private readonly string _pythonPath = "";
    private readonly string _routerScriptPath = "";
    private bool _isAvailable;
    private string? _availabilityError;

    /// <summary>服务是否可用</summary>
    public bool IsAvailable => _isAvailable;

    /// <summary>引擎名称</summary>
    public string EngineName { get; private set; } = "rembg (ONNX Runtime + u2net)";

    /// <summary>默认模型名称</summary>
    public string DefaultModel { get; private set; } = "u2net";

    /// <summary>支持的图片格式列表</summary>
    public List<string> SupportedFormats { get; private set; } = new()
    {
        ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"
    };

    /// <summary>服务不可用时的错误信息</summary>
    public string? AvailabilityError => _availabilityError;

    /// <summary>缓存的模型列表</summary>
    private List<RemoveBgModelInfo>? _cachedModels;

    /// <summary>
    /// 构造函数
    /// </summary>
    /// <param name="pythonPath">Python 解释器路径</param>
    /// <param name="routerScriptPath">remove_bg_router 脚本路径</param>
    /// <param name="jobManager">任务管理器（可选）</param>
    /// <param name="logger">日志记录器（可选）</param>
    public RemoveBgService(string pythonPath, string routerScriptPath,
        JobManager? jobManager = null, AppLogger? logger = null)
    {
        _pythonPath = pythonPath ?? throw new ArgumentNullException(nameof(pythonPath));
        _routerScriptPath = routerScriptPath ?? throw new ArgumentNullException(nameof(routerScriptPath));
        _jobManager = jobManager;
        _logger = logger;

        _runtimeClient = new LocalRuntimeClient(pythonPath, routerScriptPath);
        _runtimeClient.ProcessExited += OnProcessExited;
    }

    /// <summary>
    /// 默认构造函数（不使用 LocalRuntimeClient，仅用于测试或设计时）
    /// </summary>
    public RemoveBgService() { }

    /// <summary>
    /// 启动抠图 worker 进程并检查可用性，同时预加载模型列表
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
                _availabilityError = "抠图 worker 进程启动失败";
                return false;
            }

            // 健康检查
            JsonElement? pingResult = await _runtimeClient.SendAsync<object, JsonElement>(
                "ping", new { }, ct);

            if (pingResult is not null)
            {
                var ping = pingResult.Value;
                if (ping.TryGetProperty("default_model", out var dm))
                    DefaultModel = dm.GetString() ?? "u2net";
            }

            // 预加载模型列表
            await LoadModelsAsync(ct);

            _isAvailable = true;
            _availabilityError = null;
            _logger?.Info("智能抠图服务就绪", "desktop-remove-bg");
            return true;
        }
        catch (Exception ex)
        {
            _isAvailable = false;
            _availabilityError = $"抠图服务启动失败: {ex.Message}";
            _logger?.Error($"抠图服务启动失败: {ex.Message}", ex, "desktop-remove-bg");
            return false;
        }
    }

    /// <summary>
    /// 预加载模型列表（启动时调用一次）
    /// </summary>
    private async Task LoadModelsAsync(CancellationToken ct)
    {
        try
        {
            JsonElement? modelsResp = await _runtimeClient!.SendAsync<object, JsonElement>(
                "list_models", new { }, ct);
            if (modelsResp.HasValue)
            {
                var resp = modelsResp.Value;
                var defaultModel = resp.TryGetProperty("default_model", out var dm) ? dm.GetString() ?? "" : "";
                if (resp.TryGetProperty("models", out var modelsArr))
                {
                    _cachedModels = modelsArr.EnumerateArray()
                        .Select(e => RemoveBgModelInfo.FromJsonElement(e, defaultModel))
                        .ToList();
                }
            }
        }
        catch (Exception ex)
        {
            _logger?.Warning($"预加载模型列表失败: {ex.Message}", "desktop-remove-bg");
            // 预加载失败不是致命错误，继续
        }
    }

    /// <summary>
    /// 获取支持的扣图模型列表
    /// </summary>
    public async Task<List<RemoveBgModelInfo>> GetModelsAsync(
        bool useCache = true, CancellationToken ct = default)
    {
        if (useCache && _cachedModels != null)
            return _cachedModels;

        if (!_isAvailable || _runtimeClient == null)
            throw new InvalidOperationException(_availabilityError ?? "抠图服务不可用");

        JsonElement? response = await _runtimeClient.SendAsync<object, JsonElement>(
            "list_models", new { }, ct);

        if (response is null)
            throw new InvalidOperationException("Worker 返回空响应");

        var resp = response.Value;
        var defaultModel = resp.TryGetProperty("default_model", out var dm) ? dm.GetString() ?? "" : "";
        if (resp.TryGetProperty("models", out var modelsArr))
        {
            _cachedModels = modelsArr.EnumerateArray()
                .Select(e => RemoveBgModelInfo.FromJsonElement(e, defaultModel))
                .ToList();
            return _cachedModels;
        }

        return new List<RemoveBgModelInfo>();
    }

    /// <summary>
    /// 对单张图片执行智能抠图处理
    /// </summary>
    /// <param name="inputPath">输入图片文件路径</param>
    /// <param name="outputPath">输出图片文件路径（可选，不传时自动生成）</param>
    /// <param name="modelName">模型名称，默认 "u2net"</param>
    /// <param name="alphaMatting">是否启用 Alpha Matting 精细化边缘</param>
    /// <param name="outputRgba">是否输出 RGBA 透明 PNG</param>
    /// <param name="compositeColor">合成背景色 RGB（可选，如 [255,255,255] 白色）</param>
    /// <param name="onlyMask">是否只返回 Alpha 遮罩</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>处理结果</returns>
    public async Task<RemoveBgResult> ProcessAsync(
        string inputPath,
        string? outputPath = null,
        string modelName = "u2net",
        bool alphaMatting = false,
        bool outputRgba = true,
        List<int>? compositeColor = null,
        bool onlyMask = false,
        CancellationToken ct = default)
    {
        if (!_isAvailable || _runtimeClient == null)
            throw new InvalidOperationException(
                _availabilityError ?? "抠图服务不可用，请先调用 StartAsync");

        if (!File.Exists(inputPath))
            throw new FileNotFoundException($"图片文件不存在: {inputPath}");

        // 校验文件格式
        var ext = FileSystemService.GetExtension(inputPath);
        if (!SupportedFormats.Contains(ext))
            throw new ArgumentException(
                $"不支持的图片格式: {ext}，支持: {string.Join(", ", SupportedFormats)}");

        _logger?.Info($"开始智能抠图: {Path.GetFileName(inputPath)}, " +
                      $"模型={modelName}, alpha_matting={alphaMatting}", "desktop-remove-bg");

        // 发送处理请求
        var requestData = new Dictionary<string, object?>
        {
            ["input_path"] = inputPath,
            ["output_path"] = outputPath ?? "",
            ["model_name"] = modelName,
            ["alpha_matting"] = alphaMatting,
            ["output_rgba"] = outputRgba,
            ["only_mask"] = onlyMask,
        };

        if (compositeColor != null && compositeColor.Count == 3)
            requestData["composite_color"] = compositeColor;

        JsonElement? response = await _runtimeClient.SendAsync<object, JsonElement>(
            "remove_background", requestData, ct);

        if (response is null)
            throw new InvalidOperationException("抠图 worker 返回空响应");

        var resp = response.Value;

        // 解析响应
        if (resp.TryGetProperty("success", out var success) && !success.GetBoolean())
        {
            var error = resp.TryGetProperty("error", out var err)
                ? err.GetString() ?? "未知错误" : "未知错误";
            return new RemoveBgResult
            {
                IsSuccess = false,
                ErrorMessage = error,
                InputPath = inputPath
            };
        }

        // 解析处理数据
        var result = RemoveBgResult.FromRouterResponse(
            resp.TryGetProperty("data", out var data) ? data : resp,
            inputPath);
        result.IsSuccess = true;

        _logger?.Info(
            $"抠图完成: {Path.GetFileName(inputPath)}, " +
            $"模型={modelName}, 尺寸={result.SizeSummary}",
            "desktop-remove-bg");

        return result;
    }

    /// <summary>
    /// 带任务跟踪的异步抠图处理
    /// 创建 JobRecord 并在开始、进度、完成时更新状态。
    /// </summary>
    /// <param name="inputPath">输入图片文件路径</param>
    /// <param name="outputPath">输出图片文件路径（可选）</param>
    /// <param name="modelName">模型名称</param>
    /// <param name="alphaMatting">是否启用 Alpha Matting</param>
    /// <param name="outputRgba">是否输出 RGBA</param>
    /// <param name="compositeColor">合成背景色（可选）</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>创建的任务 ID</returns>
    public async Task<string> ProcessWithJobTrackingAsync(
        string inputPath,
        string? outputPath = null,
        string modelName = "u2net",
        bool alphaMatting = false,
        bool outputRgba = true,
        List<int>? compositeColor = null,
        CancellationToken ct = default)
    {
        if (_jobManager == null)
            throw new InvalidOperationException("未配置 JobManager");

        // 创建任务记录
        var job = _jobManager.CreateJob(
            $"智能抠图 - {Path.GetFileName(inputPath)}",
            "remove_bg_local",
            new List<string> { inputPath });

        try
        {
            // 更新为运行中
            _jobManager.UpdateJobStatus(job.Id, JobStatus.Running);
            _jobManager.UpdateJobProgress(job.Id, 0);

            var result = await ProcessAsync(
                inputPath, outputPath, modelName, alphaMatting,
                outputRgba, compositeColor, onlyMask: false, ct);

            _jobManager.UpdateJobProgress(job.Id, 50);

            if (!result.IsSuccess)
            {
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Failed,
                    result.ErrorMessage ?? "抠图处理失败");
            }
            else
            {
                job.OutputFiles = new List<string> { result.OutputPath };
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Succeeded,
                    $"模型={modelName}, AlphaMatting={alphaMatting}, 尺寸={result.SizeSummary}");
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
    /// 判断文件格式是否支持抠图处理
    /// </summary>
    public bool IsFormatSupported(string filePath)
    {
        var ext = FileSystemService.GetExtension(filePath);
        return SupportedFormats.Contains(ext);
    }

    /// <summary>
    /// 清除模型缓存（释放内存）
    /// </summary>
    /// <param name="modelName">指定模型名称（可选，不传则清除全部）</param>
    public async Task ClearModelCacheAsync(string? modelName = null, CancellationToken ct = default)
    {
        if (!_isAvailable || _runtimeClient == null)
            return;

        var requestData = new Dictionary<string, object?>();
        if (modelName != null)
            requestData["model_name"] = modelName;

        await _runtimeClient.SendAsync<object, object>(
            "clear_cache", requestData, ct);

        // 同时清除本地缓存的模型列表
        if (modelName == null)
            _cachedModels = null;

        _logger?.Info(
            modelName != null
                ? $"已清除模型缓存: {modelName}"
                : "已清除全部模型缓存",
            "desktop-remove-bg");
    }

    /// <summary>
    /// 健康检查
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

    private void OnProcessExited(object? sender, int exitCode)
    {
        _isAvailable = false;
        _availabilityError = $"抠图 worker 进程已退出，退出码: {exitCode}";
        _logger?.Warning($"抠图 worker 进程退出 (exitCode={exitCode})", "desktop-remove-bg");
    }

    public void Dispose()
    {
        if (_runtimeClient != null)
            _runtimeClient.ProcessExited -= OnProcessExited;
        _runtimeClient?.Dispose();
        GC.SuppressFinalize(this);
    }
}
