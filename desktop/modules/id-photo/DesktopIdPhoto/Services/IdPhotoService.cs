using System.Text.Json;
using TTShared.LocalRuntime;
using TTShared.Logging;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTShared.Settings;
using TTTools.IdPhoto.Models;

namespace TTTools.IdPhoto.Services;

/// <summary>
/// 证件照换底色服务
/// 封装与 local-worker id-photo 引擎的通信，提供换底色处理、规格查询、底色查询能力。
/// 通过 LocalRuntimeClient 启动 Python worker 进程，使用 stdin/stdout JSON 协议通信。
/// 证件照换底色是本地免费功能，不需要云端权限检查。
/// </summary>
public class IdPhotoService : IDisposable
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
    public string EngineName { get; private set; } = "OpenCV ID Photo Processor";

    /// <summary>支持的图片格式列表</summary>
    public List<string> SupportedFormats { get; private set; } = new()
    {
        ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"
    };

    /// <summary>服务不可用时的错误信息</summary>
    public string? AvailabilityError => _availabilityError;

    /// <summary>缓存的证件照规格列表</summary>
    private List<PhotoSpecItem>? _cachedSpecs;

    /// <summary>缓存的背景色列表</summary>
    private List<BackgroundColorItem>? _cachedColors;

    /// <summary>
    /// 构造函数
    /// </summary>
    /// <param name="pythonPath">Python 解释器路径</param>
    /// <param name="routerScriptPath">id_photo_router 脚本路径</param>
    /// <param name="jobManager">任务管理器（可选）</param>
    /// <param name="logger">日志记录器（可选）</param>
    public IdPhotoService(string pythonPath, string routerScriptPath,
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
    /// 默认构造函数（自动检测 Python 路径和路由脚本）
    /// </summary>
    public IdPhotoService()
    {
        _pythonPath = AppSettings.Instance.PythonPath
            ?? @"D:\localPath\venvs\local-worker-shared\Scripts\python.exe";
        _routerScriptPath = Path.Combine(
            Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location)!,
            "id_photo_router.py");
    }

    /// <summary>
    /// 启动证件照 worker 进程并检查可用性，同时预加载规格和底色列表
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
                _availabilityError = "证件照 worker 进程启动失败";
                return false;
            }

            // 健康检查
            var pingResult = await _runtimeClient.SendAsync<object, JsonElement>(
                "ping", new { }, ct);

            // 预加载规格和底色列表
            await LoadSpecsAndColorsAsync(ct);

            _isAvailable = true;
            _availabilityError = null;
            _logger?.Info("证件照服务就绪", "desktop-id-photo");
            return true;
        }
        catch (Exception ex)
        {
            _isAvailable = false;
            _availabilityError = $"证件照服务启动失败: {ex.Message}";
            _logger?.Error($"证件照服务启动失败: {ex.Message}", ex, "desktop-id-photo");
            return false;
        }
    }

    /// <summary>
    /// 预加载规格和底色列表（启动时调用一次）
    /// </summary>
    private async Task LoadSpecsAndColorsAsync(CancellationToken ct)
    {
        try
        {
            // 加载规格
            JsonElement? specsResp = await _runtimeClient!.SendAsync<object, JsonElement>(
                "list_specs", new { dpi = 300 }, ct);
            if (specsResp.HasValue && specsResp.Value.TryGetProperty("specs", out var specsArr))
            {
                _cachedSpecs = specsArr.EnumerateArray()
                    .Select(PhotoSpecItem.FromJsonElement)
                    .ToList();
            }

            // 加载底色
            JsonElement? colorsResp = await _runtimeClient.SendAsync<object, JsonElement>(
                "list_background_colors", new { }, ct);
            if (colorsResp.HasValue && colorsResp.Value.TryGetProperty("colors", out var colorsArr))
            {
                _cachedColors = new List<BackgroundColorItem>();
                foreach (var colorElem in colorsArr.EnumerateArray())
                {
                    var key = colorElem.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "";
                    _cachedColors.Add(BackgroundColorItem.FromJsonElement(colorElem, key));
                }
            }
        }
        catch (Exception ex)
        {
            _logger?.Warning($"预加载规格/底色失败: {ex.Message}", "desktop-id-photo");
            // 预加载失败不是致命错误，继续
        }
    }

    /// <summary>
    /// 获取可用的证件照规格列表
    /// </summary>
    public async Task<List<PhotoSpecItem>> GetSpecsAsync(bool useCache = true, CancellationToken ct = default)
    {
        if (useCache && _cachedSpecs != null)
            return _cachedSpecs;

        if (!_isAvailable || _runtimeClient == null)
            throw new InvalidOperationException(_availabilityError ?? "证件照服务不可用");

        JsonElement? response = await _runtimeClient.SendAsync<object, JsonElement>(
            "list_specs", new { dpi = 300 }, ct);

        if (response is null)
            throw new InvalidOperationException("Worker 返回空响应");

        var resp = response.Value;
        if (resp.TryGetProperty("specs", out var specsArr))
        {
            _cachedSpecs = specsArr.EnumerateArray()
                .Select(PhotoSpecItem.FromJsonElement)
                .ToList();
            return _cachedSpecs;
        }

        return new List<PhotoSpecItem>();
    }

    /// <summary>
    /// 获取可用的背景色列表
    /// </summary>
    public async Task<List<BackgroundColorItem>> GetBackgroundColorsAsync(
        bool useCache = true, CancellationToken ct = default)
    {
        if (useCache && _cachedColors != null)
            return _cachedColors;

        if (!_isAvailable || _runtimeClient == null)
            throw new InvalidOperationException(_availabilityError ?? "证件照服务不可用");

        JsonElement? response = await _runtimeClient.SendAsync<object, JsonElement>(
            "list_background_colors", new { }, ct);

        if (response is null)
            throw new InvalidOperationException("Worker 返回空响应");

        var resp = response.Value;
        if (resp.TryGetProperty("colors", out var colorsArr))
        {
            _cachedColors = new List<BackgroundColorItem>();
            foreach (var colorElem in colorsArr.EnumerateArray())
            {
                var key = colorElem.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "";
                _cachedColors.Add(BackgroundColorItem.FromJsonElement(colorElem, key));
            }
            return _cachedColors;
        }

        return new List<BackgroundColorItem>();
    }

    /// <summary>
    /// 对单张图片执行证件照换底色处理
    /// </summary>
    /// <param name="inputPath">输入图片文件路径</param>
    /// <param name="outputPath">输出图片文件路径（可选，不传时自动生成）</param>
    /// <param name="background">目标底色名称，如 "white"、"red"、"blue"</param>
    /// <param name="specName">目标规格名称，如 "1寸"、"2寸"</param>
    /// <param name="dpi">目标 DPI，默认 300</param>
    /// <param name="autoDetectBackground">是否自动检测原图背景色</param>
    /// <param name="edgeFeather">是否边缘羽化</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>处理结果</returns>
    public async Task<IdPhotoResult> ProcessAsync(
        string inputPath,
        string? outputPath = null,
        string background = "white",
        string specName = "1寸",
        int dpi = 300,
        bool autoDetectBackground = true,
        bool edgeFeather = true,
        CancellationToken ct = default)
    {
        if (!_isAvailable || _runtimeClient == null)
            throw new InvalidOperationException(
                _availabilityError ?? "证件照服务不可用，请先调用 StartAsync");

        if (!File.Exists(inputPath))
            throw new FileNotFoundException($"图片文件不存在: {inputPath}");

        // 校验文件格式
        var ext = FileSystemService.GetExtension(inputPath);
        if (!SupportedFormats.Contains(ext))
            throw new ArgumentException(
                $"不支持的图片格式: {ext}，支持: {string.Join(", ", SupportedFormats)}");

        _logger?.Info($"开始证件照换底色: {Path.GetFileName(inputPath)}, " +
                      $"底色={background}, 规格={specName}", "desktop-id-photo");

        // 发送处理请求
        var requestData = new
        {
            input_path = inputPath,
            output_path = outputPath ?? "",
            background,
            spec_name = specName,
            dpi,
            auto_detect_background = autoDetectBackground,
            edge_feather = edgeFeather,
        };

        JsonElement? response = await _runtimeClient.SendAsync<object, JsonElement>(
            "process_id_photo", requestData, ct);

        if (response is null)
            throw new InvalidOperationException("证件照 worker 返回空响应");

        var resp = response.Value;

        // 解析响应
        if (resp.TryGetProperty("success", out var success) && !success.GetBoolean())
        {
            var error = resp.TryGetProperty("error", out var err)
                ? err.GetString() ?? "未知错误" : "未知错误";
            return new IdPhotoResult
            {
                IsSuccess = false,
                ErrorMessage = error,
                InputPath = inputPath
            };
        }

        // 解析处理数据
        var result = IdPhotoResult.FromRouterResponse(
            resp.TryGetProperty("data", out var data) ? data : resp);
        result.IsSuccess = true;
        result.InputPath = inputPath;

        _logger?.Info(
            $"证件照处理完成: {Path.GetFileName(inputPath)}, " +
            $"规格={specName}, 底色={background}, 尺寸={result.SizeSummary}",
            "desktop-id-photo");

        return result;
    }

    /// <summary>
    /// 带任务跟踪的异步证件照处理
    /// 创建 JobRecord 并在开始、进度、完成时更新状态。
    /// </summary>
    /// <param name="inputPath">输入图片文件路径</param>
    /// <param name="outputPath">输出图片文件路径（可选）</param>
    /// <param name="background">目标底色名称</param>
    /// <param name="specName">目标规格名称</param>
    /// <param name="dpi">目标 DPI</param>
    /// <param name="autoDetectBackground">是否自动检测背景</param>
    /// <param name="edgeFeather">是否边缘羽化</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>创建的任务 ID</returns>
    public async Task<string> ProcessWithJobTrackingAsync(
        string inputPath,
        string? outputPath = null,
        string background = "white",
        string specName = "1寸",
        int dpi = 300,
        bool autoDetectBackground = true,
        bool edgeFeather = true,
        CancellationToken ct = default)
    {
        if (_jobManager == null)
            throw new InvalidOperationException("未配置 JobManager");

        // 创建任务记录
        var job = _jobManager.CreateJob(
            $"证件照换底色 - {Path.GetFileName(inputPath)}",
            "id_photo_local",
            new List<string> { inputPath });

        try
        {
            // 更新为运行中
            _jobManager.UpdateJobStatus(job.Id, JobStatus.Running);
            _jobManager.UpdateJobProgress(job.Id, 0);

            var result = await ProcessAsync(
                inputPath, outputPath, background, specName, dpi,
                autoDetectBackground, edgeFeather, ct);

            _jobManager.UpdateJobProgress(job.Id, 50);

            if (!result.IsSuccess)
            {
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Failed,
                    result.ErrorMessage ?? "处理失败");
            }
            else
            {
                job.OutputFiles = new List<string> { result.OutputPath };
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Succeeded,
                    $"底色={background}, 规格={specName}, 尺寸={result.SizeSummary}");
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
    /// 判断文件格式是否支持证件照处理
    /// </summary>
    public bool IsFormatSupported(string filePath)
    {
        var ext = FileSystemService.GetExtension(filePath);
        return SupportedFormats.Contains(ext);
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
        _availabilityError = $"证件照 worker 进程已退出，退出码: {exitCode}";
        _logger?.Warning($"证件照 worker 进程退出 (exitCode={exitCode})", "desktop-id-photo");
    }

    public void Dispose()
    {
        if (_runtimeClient != null)
            _runtimeClient.ProcessExited -= OnProcessExited;
        _runtimeClient?.Dispose();
        GC.SuppressFinalize(this);
    }
}
