using System.Text.Json;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTShared.LocalRuntime;
using TTShared.Logging;
using TTShared.Settings;
using TTTools.FormatConvert.Models;

namespace TTTools.FormatConvert.Services;

/// <summary>
/// 图片格式转换服务
/// 封装本地 Python worker 通信（LocalRuntimeClient），提供格式转换、压缩、裁剪、旋转功能。
/// 本地免费功能：无需套餐权限校验，不消耗云端 AI 额度，直接调用本地 worker。
/// </summary>
public class FormatConvertService : IDisposable
{
    private readonly LocalRuntimeClient? _runtimeClient;
    private readonly JobManager? _jobManager;
    private readonly AppLogger? _logger;
    private readonly string _pythonPath;
    private readonly string _routerScriptPath;
    private bool _isAvailable;
    private string? _availabilityError;

    /// <summary>服务是否可用（worker 已启动且健康检查通过）</summary>
    public bool IsAvailable => _isAvailable;

    /// <summary>引擎名称</summary>
    public string EngineName { get; private set; } = "Pillow (纯本地图像处理)";

    /// <summary>支持的输入图片格式</summary>
    public static readonly HashSet<string> SupportedFormats = new(StringComparer.OrdinalIgnoreCase)
    {
        ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif", ".ico"
    };

    /// <summary>可用的输出格式列表（中文描述）</summary>
    public static readonly List<(string Value, string Display)> OutputFormatList = new()
    {
        ("original", "保持原格式"),
        ("png", "PNG - 无损，支持透明"),
        ("jpeg", "JPEG - 有损，文件小"),
        ("bmp", "BMP - 无压缩，Windows 标准"),
        ("tiff", "TIFF - 印刷标准，LZW 压缩"),
        ("webp", "WEBP - Web 优化格式"),
        ("gif", "GIF - 动图/调色板"),
        ("ico", "ICO - 图标格式"),
    };

    /// <summary>可用的裁剪锚点列表</summary>
    public static readonly List<(string Value, string Display)> AnchorList = new()
    {
        ("center", "居中裁剪"),
        ("top_left", "左上角对齐"),
        ("top_right", "右上角对齐"),
        ("bottom_left", "左下角对齐"),
        ("bottom_right", "右下角对齐"),
    };

    /// <summary>可用的直角旋转角度</summary>
    public static readonly List<(double Value, string Display)> QuickRotateList = new()
    {
        (90, "顺时针 90°"),
        (180, "顺时针 180°"),
        (270, "顺时针 270°"),
    };

    /// <summary>服务不可用时的错误信息</summary>
    public string? AvailabilityError => _availabilityError;

    /// <summary>
    /// 初始化格式转换服务。
    /// </summary>
    /// <param name="pythonPath">Python 解释器路径</param>
    /// <param name="routerScriptPath">format_convert_router.py 脚本路径</param>
    /// <param name="jobManager">任务管理器（可选）</param>
    /// <param name="logger">日志记录器（可选）</param>
    public FormatConvertService(
        string pythonPath,
        string routerScriptPath,
        JobManager? jobManager = null,
        AppLogger? logger = null)
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
    public FormatConvertService()
    {
        _pythonPath = AppSettings.Instance.PythonPath
            ?? @"D:\localPath\venvs\local-worker-shared\Scripts\python.exe";
        _routerScriptPath = Path.Combine(
            Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location)!,
            "format_convert_router.py");
    }

    /// <summary>
    /// 启动 Python worker 进程并进行健康检查。
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
                _availabilityError = "格式转换 worker 进程启动失败";
                return false;
            }

            // 健康检查
            JsonElement? pingResult = await _runtimeClient.SendAsync<object, JsonElement>(
                "ping", new { }, ct);

            if (pingResult is not null)
            {
                var ping = pingResult.Value;
                if (ping.TryGetProperty("engine", out var engine))
                    EngineName = engine.GetString() ?? EngineName;
            }

            _isAvailable = true;
            _availabilityError = null;
            _logger?.Info("图片格式转换服务就绪", "desktop-format-convert");
            return true;
        }
        catch (Exception ex)
        {
            _isAvailable = false;
            _availabilityError = $"格式转换服务启动失败: {ex.Message}";
            _logger?.Error($"格式转换服务启动失败: {ex.Message}", ex, "desktop-format-convert");
            return false;
        }
    }

    // ===== 格式转换 =====

    /// <summary>
    /// 执行图片格式转换。
    /// </summary>
    /// <param name="inputPath">输入图片文件路径</param>
    /// <param name="outputPath">输出文件路径（可选，为空时由 worker 自动生成）</param>
    /// <param name="param">格式转换参数</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>处理结果</returns>
    public async Task<FormatConvertResult> ConvertFormatAsync(
        string inputPath,
        string? outputPath,
        FormatConvertParams param,
        CancellationToken ct = default)
    {
        // 校验输入文件
        var validationError = ValidateInputFile(inputPath);
        if (validationError != null)
            return validationError;

        // 校验服务可用
        if (!_isAvailable || _runtimeClient == null)
        {
            return new FormatConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                OperationType = "convert_format",
                ErrorMessage = _availabilityError ?? "格式转换服务不可用，请先调用 StartAsync",
            };
        }

        var requestData = new Dictionary<string, object?>
        {
            ["input_path"] = inputPath,
            ["target_format"] = param.TargetFormat,
            ["quality"] = param.Quality,
            ["png_compress"] = param.PngCompress,
            ["webp_quality"] = param.WebpQuality,
            ["preserve_alpha"] = param.PreserveAlpha,
        };

        if (!string.IsNullOrEmpty(outputPath))
            requestData["output_path"] = outputPath;

        return await ExecuteOperationAsync("convert_format", inputPath, requestData, ct);
    }

    // ===== 压缩 =====

    /// <summary>
    /// 执行图片压缩。
    /// </summary>
    public async Task<FormatConvertResult> CompressAsync(
        string inputPath,
        string? outputPath,
        CompressParams param,
        CancellationToken ct = default)
    {
        var validationError = ValidateInputFile(inputPath);
        if (validationError != null)
            return validationError;

        if (!_isAvailable || _runtimeClient == null)
        {
            return new FormatConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                OperationType = "compress",
                ErrorMessage = _availabilityError ?? "格式转换服务不可用，请先调用 StartAsync",
            };
        }

        var requestData = new Dictionary<string, object?>
        {
            ["input_path"] = inputPath,
            ["quality"] = param.Quality,
            ["target_format"] = param.TargetFormat,
            ["png_compress"] = param.PngCompress,
        };

        if (param.MaxSizeBytes.HasValue)
            requestData["max_size_bytes"] = param.MaxSizeBytes.Value;

        if (!string.IsNullOrEmpty(outputPath))
            requestData["output_path"] = outputPath;

        return await ExecuteOperationAsync("compress", inputPath, requestData, ct);
    }

    // ===== 裁剪 =====

    /// <summary>
    /// 执行图片裁剪（支持坐标模式和锚点模式）。
    /// </summary>
    public async Task<FormatConvertResult> CropAsync(
        string inputPath,
        string? outputPath,
        CropParams param,
        CancellationToken ct = default)
    {
        var validationError = ValidateInputFile(inputPath);
        if (validationError != null)
            return validationError;

        if (!_isAvailable || _runtimeClient == null)
        {
            return new FormatConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                OperationType = "crop",
                ErrorMessage = _availabilityError ?? "格式转换服务不可用，请先调用 StartAsync",
            };
        }

        var requestData = new Dictionary<string, object?>
        {
            ["input_path"] = inputPath,
            ["width"] = param.Width,
            ["height"] = param.Height,
        };

        // 锚点模式：传递 anchor
        if (!string.IsNullOrEmpty(param.Anchor))
        {
            requestData["anchor"] = param.Anchor;
        }
        else
        {
            // 坐标模式：传递 left/top
            requestData["left"] = param.Left;
            requestData["top"] = param.Top;
        }

        if (!string.IsNullOrEmpty(outputPath))
            requestData["output_path"] = outputPath;

        return await ExecuteOperationAsync("crop", inputPath, requestData, ct);
    }

    // ===== 旋转 =====

    /// <summary>
    /// 执行图片旋转。
    /// </summary>
    public async Task<FormatConvertResult> RotateAsync(
        string inputPath,
        string? outputPath,
        RotateParams param,
        CancellationToken ct = default)
    {
        var validationError = ValidateInputFile(inputPath);
        if (validationError != null)
            return validationError;

        if (!_isAvailable || _runtimeClient == null)
        {
            return new FormatConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                OperationType = "rotate",
                ErrorMessage = _availabilityError ?? "格式转换服务不可用，请先调用 StartAsync",
            };
        }

        var requestData = new Dictionary<string, object?>
        {
            ["input_path"] = inputPath,
            ["angle"] = param.Angle,
            ["expand"] = param.Expand,
            ["fillcolor_r"] = param.FillColorR,
            ["fillcolor_g"] = param.FillColorG,
            ["fillcolor_b"] = param.FillColorB,
        };

        if (!string.IsNullOrEmpty(outputPath))
            requestData["output_path"] = outputPath;

        return await ExecuteOperationAsync("rotate", inputPath, requestData, ct);
    }

    // ===== 带任务跟踪的处理 =====

    /// <summary>
    /// 带任务跟踪的格式转换/压缩/裁剪/旋转处理。
    /// </summary>
    public async Task<string> ProcessWithJobTrackingAsync(
        string inputPath,
        string? outputPath,
        string operationType,
        object param,
        CancellationToken ct = default)
    {
        if (_jobManager == null)
            throw new InvalidOperationException("未配置 JobManager");

        var operationNames = new Dictionary<string, string>
        {
            ["convert_format"] = "格式转换",
            ["compress"] = "压缩",
            ["crop"] = "裁剪",
            ["rotate"] = "旋转",
        };

        var opDisplayName = operationNames.GetValueOrDefault(operationType, operationType);

        var job = _jobManager.CreateJob(
            $"图片{opDisplayName} - {Path.GetFileName(inputPath)}",
            "format_convert_local",
            new List<string> { inputPath });

        try
        {
            _jobManager.UpdateJobStatus(job.Id, JobStatus.Running);
            _jobManager.UpdateJobProgress(job.Id, 0);

            FormatConvertResult result = operationType switch
            {
                "convert_format" => await ConvertFormatAsync(inputPath, outputPath, (FormatConvertParams)param, ct),
                "compress" => await CompressAsync(inputPath, outputPath, (CompressParams)param, ct),
                "crop" => await CropAsync(inputPath, outputPath, (CropParams)param, ct),
                "rotate" => await RotateAsync(inputPath, outputPath, (RotateParams)param, ct),
                _ => throw new ArgumentException($"不支持的操作类型: {operationType}"),
            };

            _jobManager.UpdateJobProgress(job.Id, 50);

            if (!result.IsSuccess)
            {
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Failed,
                    result.ErrorMessage ?? $"{opDisplayName}处理失败");
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
    /// 判断文件格式是否支持处理。
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
    /// 执行一次操作（发送请求给 Python worker 并解析响应）。
    /// </summary>
    /// <param name="action">操作名称（convert_format / compress / crop / rotate）</param>
    /// <param name="inputPath">输入文件路径</param>
    /// <param name="requestData">发送给 worker 的请求数据</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>处理结果</returns>
    private async Task<FormatConvertResult> ExecuteOperationAsync(
        string action,
        string inputPath,
        Dictionary<string, object?> requestData,
        CancellationToken ct)
    {
        var operationNames = new Dictionary<string, string>
        {
            ["convert_format"] = "格式转换",
            ["compress"] = "压缩",
            ["crop"] = "裁剪",
            ["rotate"] = "旋转",
        };
        var opDisplayName = operationNames.GetValueOrDefault(action, action);

        _logger?.Info(
            $"开始{opDisplayName}: {Path.GetFileName(inputPath)}",
            "desktop-format-convert");

        JsonElement? workerResp;
        try
        {
            workerResp = await _runtimeClient!.SendAsync<object, JsonElement>(
                action, requestData, ct);
        }
        catch (Exception ex)
        {
            _logger?.Error($"Worker 通信异常: {ex.Message}", ex, "desktop-format-convert");
            return new FormatConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                OperationType = action,
                ErrorMessage = $"{opDisplayName}失败: {ex.Message}",
            };
        }

        if (workerResp is null)
        {
            return new FormatConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                OperationType = action,
                ErrorMessage = "Worker 返回空响应",
            };
        }

        var resp = workerResp.Value;

        // 检查 worker 是否返回了错误
        if (resp.TryGetProperty("success", out var successProp) && !successProp.GetBoolean())
        {
            var error = resp.TryGetProperty("error", out var err)
                ? err.GetString() ?? "未知错误" : "未知错误";
            return new FormatConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                OperationType = action,
                ErrorMessage = error,
            };
        }

        // 构建成功结果
        var data = resp.TryGetProperty("data", out var d) ? d : resp;
        var result = FormatConvertResult.FromRouterResponse(data, inputPath, action);
        result.IsSuccess = true;

        _logger?.Info(
            $"{opDisplayName}完成: {Path.GetFileName(inputPath)}, " +
            $"尺寸={result.SizeSummary}, " +
            $"格式={result.OutputFormatSummary}, " +
            $"耗时={result.ElapsedDisplay}",
            "desktop-format-convert");

        return result;
    }

    /// <summary>
    /// 校验输入文件是否存在以及格式是否支持。
    /// 返回 null 表示通过，返回 FormatConvertResult 表示失败。
    /// </summary>
    private static FormatConvertResult? ValidateInputFile(string inputPath)
    {
        var operationType = "validate";

        if (!File.Exists(inputPath))
        {
            return new FormatConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                OperationType = operationType,
                ErrorMessage = $"图片文件不存在: {inputPath}",
            };
        }

        var ext = FileSystemService.GetExtension(inputPath);
        if (!SupportedFormats.Contains(ext))
        {
            return new FormatConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                OperationType = operationType,
                ErrorMessage = $"不支持的图片格式: {ext}，支持: {string.Join(", ", SupportedFormats)}",
            };
        }

        return null;
    }

    /// <summary>
    /// Worker 进程退出回调。
    /// </summary>
    private void OnProcessExited(object? sender, int exitCode)
    {
        _isAvailable = false;
        _availabilityError = $"格式转换 worker 进程已退出，退出码: {exitCode}";
        _logger?.Warning($"格式转换 worker 进程退出 (exitCode={exitCode})", "desktop-format-convert");
    }

    public void Dispose()
    {
        if (_runtimeClient != null)
            _runtimeClient.ProcessExited -= OnProcessExited;
        _runtimeClient?.Dispose();
        GC.SuppressFinalize(this);
    }
}
