using System.Text.Json;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTShared.LocalRuntime;
using TTShared.Logging;
using TTTools.PdfImageConvert.Models;

namespace TTTools.PdfImageConvert.Services;

/// <summary>
/// PDF/图片互转服务
/// 封装套餐权限校验（CloudApiClient）+ 本地 Python worker 通信（LocalRuntimeClient）。
/// 本地付费功能：每次 convert 前必须通过 /api/v1/entitlements/check 检查权限。
/// 权限 fail closed：未登录、网络错误、接口异常、allowed=false 均拒绝执行。
/// </summary>
public class PdfImageConvertService : IDisposable
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

    /// <summary>服务是否可用（worker 已启动且健康检查通过）</summary>
    public bool IsAvailable => _isAvailable;

    /// <summary>引擎名称</summary>
    public string EngineName { get; private set; } = "PyMuPDF + Pillow (纯本地 PDF/图片互转)";

    /// <summary>支持输入的 PDF 后缀</summary>
    public static readonly string SupportedPdfSuffix = ".pdf";

    /// <summary>支持输入的图片格式后缀</summary>
    public static readonly HashSet<string> SupportedImageFormats = new(StringComparer.OrdinalIgnoreCase)
    {
        ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"
    };

    /// <summary>服务不可用时的错误信息</summary>
    public string? AvailabilityError => _availabilityError;

    /// <summary>
    /// 初始化 PDF/图片互转服务。
    /// </summary>
    /// <param name="pythonPath">Python 解释器路径</param>
    /// <param name="routerScriptPath">pdf_image_convert_router.py 脚本路径</param>
    /// <param name="cloudApiClient">云端 API 客户端（C1: 必须非 null）</param>
    /// <param name="authState">认证状态（C1: 必须非 null）</param>
    /// <param name="jobManager">任务管理器（可选）</param>
    /// <param name="logger">日志记录器（可选）</param>
    /// <exception cref="ArgumentNullException">cloudApiClient 或 authState 为 null</exception>
    public PdfImageConvertService(
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
    /// 默认构造函数（仅用于设计时或格式校验测试，不使用 LocalRuntimeClient）。
    /// </summary>
    public PdfImageConvertService()
    {
        _authState = new AuthState();
        _cloudApiClient = new CloudApiClient("http://localhost:8000", _authState);
        _pythonPath = string.Empty;
        _routerScriptPath = string.Empty;
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
                _availabilityError = "PDF/图片互转 worker 进程启动失败";
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
            _logger?.Info("PDF/图片互转服务就绪", "desktop-pdf-image-convert");
            return true;
        }
        catch (Exception ex)
        {
            _isAvailable = false;
            _availabilityError = $"PDF/图片互转服务启动失败: {ex.Message}";
            _logger?.Error($"PDF/图片互转服务启动失败: {ex.Message}", ex, "desktop-pdf-image-convert");
            return false;
        }
    }

    /// <summary>
    /// 执行 PDF/图片互转处理（含套餐权限校验）。
    /// C1: 每次调用都检查权限，权限不通过时拒绝执行，不创建输出文件。
    /// </summary>
    /// <param name="inputPath">输入文件路径（PDF→图片时为 PDF 路径，图片→PDF 时为首张图片路径）</param>
    /// <param name="outputPath">输出路径（可选），PDF→图片时为输出目录，图片→PDF 时为输出文件路径</param>
    /// <param name="param">转换参数</param>
    /// <param name="inputPaths">图片转 PDF 时的全部图片路径列表（PDF→图片时为 null）</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>处理结果（含权限信息）</returns>
    public async Task<PdfImageConvertResult> ConvertAsync(
        string inputPath,
        string? outputPath,
        PdfImageConvertParams param,
        List<string>? inputPaths = null,
        CancellationToken ct = default)
    {
        // ---- 1. 校验登录状态（C1: 未登录直接拒绝，不调网络） ----
        if (!_authState.IsLoggedIn)
        {
            _logger?.Warning("未登录，拒绝 PDF/图片互转请求", "desktop-pdf-image-convert");
            return new PdfImageConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = false,
                EntitlementReason = "请先登录后再使用 PDF/图片互转功能",
                ErrorMessage = "未登录",
            };
        }

        // ---- 2. 校验输入文件 ----
        var isPdfToImages = param.Direction == "pdf_to_images";

        if (isPdfToImages)
        {
            // PDF 转图片：校验单个 PDF 文件
            if (!File.Exists(inputPath))
            {
                return new PdfImageConvertResult
                {
                    IsSuccess = false,
                    InputPath = inputPath,
                    ErrorMessage = $"PDF 文件不存在: {inputPath}",
                };
            }
            if (!IsPdfFormatSupported(inputPath))
            {
                return new PdfImageConvertResult
                {
                    IsSuccess = false,
                    InputPath = inputPath,
                    ErrorMessage = $"不支持的 PDF 文件格式，仅支持 .pdf 后缀",
                };
            }
        }
        else
        {
            // 图片转 PDF：校验所有图片文件
            var paths = inputPaths ?? (File.Exists(inputPath) ? new List<string> { inputPath } : null);
            if (paths == null || paths.Count == 0)
            {
                return new PdfImageConvertResult
                {
                    IsSuccess = false,
                    InputPath = inputPath,
                    ErrorMessage = "图片列表为空",
                };
            }
            foreach (var path in paths)
            {
                if (!File.Exists(path))
                {
                    return new PdfImageConvertResult
                    {
                        IsSuccess = false,
                        InputPath = path,
                        ErrorMessage = $"图片文件不存在: {path}",
                    };
                }
                if (!IsImageFormatSupported(path))
                {
                    var ext = FileSystemService.GetExtension(path);
                    return new PdfImageConvertResult
                    {
                        IsSuccess = false,
                        InputPath = path,
                        ErrorMessage = $"不支持的图片格式: {ext}，支持: {string.Join(", ", SupportedImageFormats)}",
                    };
                }
            }
        }

        // ---- 3. 套餐权限检查（C1: fail closed） ----
        // 每次 convert 前都调用，不缓存权限结果
        _logger?.Info($"开始权限检查: {Path.GetFileName(inputPath)}", "desktop-pdf-image-convert");

        ApiResponse<EntitlementCheckData>? entitlementResp;
        try
        {
            entitlementResp = await _cloudApiClient.CheckEntitlementAsync(
                "pdf_image_convert_local_paid", "single",
                clientRequestId: $"pdf_convert_{Guid.NewGuid():N}",
                ct: ct);
        }
        catch (Exception ex)
        {
            // 网络异常视为无权限（C1: fail closed）
            _logger?.Error($"权限检查网络异常: {ex.Message}", ex, "desktop-pdf-image-convert");
            return new PdfImageConvertResult
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
            _logger?.Warning("权限检查返回 null，拒绝执行", "desktop-pdf-image-convert");
            return new PdfImageConvertResult
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
            _logger?.Warning($"权限检查失败: {reason}", "desktop-pdf-image-convert");
            return new PdfImageConvertResult
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
                $"权限拒绝: feature=pdf_image_convert_local_paid, " +
                $"reason={entitlementResp.Data.Reason}, " +
                $"plan={entitlementResp.Data.PlanCode}",
                "desktop-pdf-image-convert");
            return new PdfImageConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = false,
                EntitlementReason = entitlementResp.Data.Reason ?? "当前套餐不支持此功能",
                PlanCode = entitlementResp.Data.PlanCode,
                RemainingFreeQuota = entitlementResp.Data.RemainingFreeQuota,
                ErrorMessage = "套餐权限不足",
            };
        }

        // ---- 5. 权限通过，执行转换 ----
        if (!_isAvailable || _runtimeClient == null)
        {
            return new PdfImageConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = true,
                PlanCode = entitlementResp.Data.PlanCode,
                ErrorMessage = _availabilityError ?? "PDF/图片互转服务不可用，请先调用 StartAsync",
            };
        }

        _logger?.Info(
            $"权限通过，开始转换: {Path.GetFileName(inputPath)}, " +
            $"direction={param.Direction}",
            "desktop-pdf-image-convert");

        // 构建发送给 Python worker 的请求数据
        var action = isPdfToImages ? "pdf_to_images" : "images_to_pdf";
        var requestData = BuildRequestData(inputPath, outputPath, param, inputPaths);

        JsonElement? workerResp;
        try
        {
            workerResp = await _runtimeClient.SendAsync<object, JsonElement>(
                action, requestData, ct);
        }
        catch (Exception ex)
        {
            _logger?.Error($"Worker 通信异常: {ex.Message}", ex, "desktop-pdf-image-convert");
            return new PdfImageConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = true,
                PlanCode = entitlementResp.Data.PlanCode,
                ErrorMessage = $"转换处理失败: {ex.Message}",
            };
        }

        if (workerResp is null)
        {
            return new PdfImageConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = true,
                PlanCode = entitlementResp.Data.PlanCode,
                ErrorMessage = "PDF/图片互转 worker 返回空响应",
            };
        }

        var resp = workerResp.Value;

        // 检查 worker 是否返回了错误
        if (resp.TryGetProperty("success", out var successProp) && !successProp.GetBoolean())
        {
            var error = resp.TryGetProperty("error", out var err)
                ? err.GetString() ?? "未知错误" : "未知错误";
            return new PdfImageConvertResult
            {
                IsSuccess = false,
                InputPath = inputPath,
                EntitlementAllowed = true,
                PlanCode = entitlementResp.Data.PlanCode,
                ErrorMessage = error,
            };
        }

        // ---- 6. 构建成功结果 ----
        var data = resp.TryGetProperty("data", out var d) ? d : resp;
        var result = PdfImageConvertResult.FromRouterResponse(data, inputPath);
        result.IsSuccess = true;
        result.EntitlementAllowed = true;
        result.PlanCode = entitlementResp.Data.PlanCode;
        result.RemainingFreeQuota = entitlementResp.Data.RemainingFreeQuota;

        _logger?.Info(
            $"转换完成: {Path.GetFileName(inputPath)}, " +
            $"方向={result.DirectionDisplay}, " +
            $"输出={result.OutputSizeDisplay}, " +
            $"耗时={result.ElapsedMsDisplay}",
            "desktop-pdf-image-convert");

        return result;
    }

    /// <summary>
    /// 带任务跟踪的转换处理（C1: 权限拒绝时 Job 标记为 Failed）。
    /// </summary>
    public async Task<string> ProcessWithJobTrackingAsync(
        string inputPath,
        string? outputPath,
        PdfImageConvertParams param,
        List<string>? inputPaths = null,
        CancellationToken ct = default)
    {
        if (_jobManager == null)
            throw new InvalidOperationException("未配置 JobManager");

        // 创建任务记录
        var job = _jobManager.CreateJob(
            $"PDF/图片互转 - {Path.GetFileName(inputPath)}",
            "pdf_image_convert_local_paid",
            inputPaths ?? new List<string> { inputPath });

        try
        {
            _jobManager.UpdateJobStatus(job.Id, JobStatus.Running);
            _jobManager.UpdateJobProgress(job.Id, 0);

            var result = await ConvertAsync(inputPath, outputPath, param, inputPaths, ct);

            _jobManager.UpdateJobProgress(job.Id, 50);

            if (!result.IsSuccess)
            {
                // C1: 权限拒绝或处理失败均标记为 Failed
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Failed,
                    result.EntitlementAllowed
                        ? (result.ErrorMessage ?? "转换处理失败")
                        : $"权限拒绝: {result.EntitlementReason}");
            }
            else
            {
                job.OutputFiles = new List<string> { result.OutputPath };
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Succeeded,
                    $"方向={result.DirectionDisplay}, 输出={result.OutputSizeDisplay}");
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
    /// 判断文件是否为支持的 PDF 格式。
    /// </summary>
    public bool IsPdfFormatSupported(string filePath)
    {
        var ext = FileSystemService.GetExtension(filePath);
        return string.Equals(ext, SupportedPdfSuffix, StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// 判断文件是否为支持的图片格式。
    /// </summary>
    public bool IsImageFormatSupported(string filePath)
    {
        var ext = FileSystemService.GetExtension(filePath);
        return SupportedImageFormats.Contains(ext);
    }

    /// <summary>
    /// 判断文件是否支持（PDF 或图片）。
    /// </summary>
    public bool IsFormatSupported(string filePath)
    {
        return IsPdfFormatSupported(filePath) || IsImageFormatSupported(filePath);
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
    /// 将 PdfImageConvertParams 构建为发送给 Python worker 的字典。
    /// PDF→图片和图片→PDF 的请求结构不同：
    ///   - pdf_to_images: input_path + dpi + output_format 等
    ///   - images_to_pdf: input_paths（多张图片路径列表）+ output_path
    /// </summary>
    private static Dictionary<string, object?> BuildRequestData(
        string inputPath, string? outputPath, PdfImageConvertParams param,
        List<string>? inputPaths)
    {
        var data = new Dictionary<string, object?>();

        if (param.Direction == "pdf_to_images")
        {
            // PDF 转图片：单个 PDF 文件路径
            data["input_path"] = inputPath;
            data["dpi"] = param.Dpi;
            data["output_format"] = param.OutputFormat;
            data["jpeg_quality"] = param.JpegQuality;

            // 输出目录（PDF→图片时 output_path 为目录）
            if (!string.IsNullOrEmpty(outputPath))
                data["output_dir"] = outputPath;

            // 页码范围
            if (param.PageRange != null && param.PageRange.Count == 2)
                data["page_range"] = param.PageRange;

            // 页面限制
            if (param.PageLimit.HasValue)
                data["page_limit"] = param.PageLimit.Value;
        }
        else
        {
            // 图片转 PDF：多张图片路径列表
            var paths = inputPaths ?? (new List<string> { inputPath });
            data["input_paths"] = paths;

            // 输出 PDF 文件路径
            if (!string.IsNullOrEmpty(outputPath))
                data["output_path"] = outputPath;
        }

        return data;
    }

    /// <summary>
    /// Worker 进程退出回调。
    /// </summary>
    private void OnProcessExited(object? sender, int exitCode)
    {
        _isAvailable = false;
        _availabilityError = $"PDF/图片互转 worker 进程已退出，退出码: {exitCode}";
        _logger?.Warning($"PDF/图片互转 worker 进程退出 (exitCode={exitCode})", "desktop-pdf-image-convert");
    }

    public void Dispose()
    {
        if (_runtimeClient != null)
            _runtimeClient.ProcessExited -= OnProcessExited;
        _runtimeClient?.Dispose();
        GC.SuppressFinalize(this);
    }
}
