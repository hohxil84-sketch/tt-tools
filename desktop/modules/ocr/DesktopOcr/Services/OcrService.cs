using System.Collections.Concurrent;
using System.Diagnostics;
using System.Text.Json;
using TTShared.LocalRuntime;
using TTShared.Logging;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTTools.OCR.Models;

namespace TTTools.OCR.Services;

/// <summary>
/// OCR 服务
/// 封装与 local-worker OCR 引擎的通信，提供单张识别、批量识别、健康检查能力。
/// 通过 LocalRuntimeClient 启动 Python worker 进程，使用 stdin/stdout JSON 协议通信。
/// </summary>
public class OcrService : IDisposable
{
    private readonly LocalRuntimeClient? _runtimeClient;
    private readonly JobManager? _jobManager;
    private readonly AppLogger? _logger;
    private readonly string _pythonPath = "";
    private readonly string _routerScriptPath = "";
    private bool _isAvailable;
    private string? _availabilityError;

    /// <summary>OCR 服务是否可用</summary>
    public bool IsAvailable => _isAvailable;

    /// <summary>OCR 引擎名称</summary>
    public string EngineName { get; private set; } = "RapidOCR";

    /// <summary>支持的图片格式列表</summary>
    public List<string> SupportedFormats { get; private set; } = new()
    {
        ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"
    };

    /// <summary>服务不可用时的错误信息</summary>
    public string? AvailabilityError => _availabilityError;

    /// <summary>
    /// 构造函数
    /// </summary>
    /// <param name="pythonPath">Python 解释器路径</param>
    /// <param name="routerScriptPath">OCR router 脚本路径</param>
    /// <param name="jobManager">任务管理器（可选）</param>
    /// <param name="logger">日志记录器（可选）</param>
    public OcrService(string pythonPath, string routerScriptPath,
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
    public OcrService() { }

    /// <summary>
    /// 启动 OCR worker 进程并检查可用性
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
                _availabilityError = "OCR worker 进程启动失败";
                return false;
            }

            // 健康检查
            var pingResult = await _runtimeClient.SendAsync<object, JsonElement>(
                "ping", new { }, ct);

            _isAvailable = true;
            _availabilityError = null;
            _logger?.Info("OCR 服务就绪", "desktop-ocr");
            return true;
        }
        catch (Exception ex)
        {
            _isAvailable = false;
            _availabilityError = $"OCR 服务启动失败: {ex.Message}";
            _logger?.Error($"OCR 服务启动失败: {ex.Message}", ex, "desktop-ocr");
            return false;
        }
    }

    /// <summary>
    /// 对单张图片执行 OCR 识别
    /// </summary>
    /// <param name="filePath">图片文件路径</param>
    /// <param name="textScore">置信度阈值 (0.0 ~ 1.0)</param>
    /// <param name="useDml">是否使用 GPU 加速</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>OCR 识别结果</returns>
    public async Task<OcrJobResult> RecognizeAsync(
        string filePath,
        double textScore = 0.5,
        bool useDml = false,
        CancellationToken ct = default)
    {
        if (!_isAvailable || _runtimeClient == null)
            throw new InvalidOperationException(
                _availabilityError ?? "OCR 服务不可用，请先调用 StartAsync");

        if (!File.Exists(filePath))
            throw new FileNotFoundException($"图片文件不存在: {filePath}");

        // 校验文件格式
        var ext = FileSystemService.GetExtension(filePath);
        if (!SupportedFormats.Contains(ext))
            throw new ArgumentException(
                $"不支持的图片格式: {ext}，支持: {string.Join(", ", SupportedFormats)}");

        _logger?.Info($"开始 OCR 识别: {Path.GetFileName(filePath)}", "desktop-ocr");

        // 发送识别请求
        var requestData = new
        {
            file_path = filePath,
            text_score = textScore,
            use_dml = useDml
        };

        JsonElement? response = await _runtimeClient.SendAsync<object, JsonElement>(
            "recognize", requestData, ct);

        if (response is null)
            throw new InvalidOperationException("OCR worker 返回空响应");

        var resp = response.Value;

        // 解析响应
        if (resp.TryGetProperty("success", out var success) && !success.GetBoolean())
        {
            var error = resp.TryGetProperty("error", out var err)
                ? err.GetString() ?? "未知错误" : "未知错误";
            return new OcrJobResult
            {
                IsSuccess = false,
                ErrorMessage = error,
                FilePath = filePath
            };
        }

        // 解析识别数据
        var result = OcrJobResult.FromRouterResponse(
            resp.TryGetProperty("data", out var data) ? data : resp,
            filePath);
        result.IsSuccess = true;

        _logger?.Info(
            $"OCR 识别完成: {Path.GetFileName(filePath)}, {result.LineCount} 行, " +
            $"耗时 {result.ElapsedTotal:F2}s",
            "desktop-ocr");

        return result;
    }

    /// <summary>
    /// 批量识别多张图片
    /// </summary>
    /// <param name="filePaths">图片文件路径列表</param>
    /// <param name="textScore">置信度阈值</param>
    /// <param name="useDml">是否使用 GPU 加速</param>
    /// <param name="progressCallback">进度回调 (当前索引, 总数)</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>OCR 识别结果列表</returns>
    public async Task<List<OcrJobResult>> RecognizeBatchAsync(
        List<string> filePaths,
        double textScore = 0.5,
        bool useDml = false,
        Action<int, int>? progressCallback = null,
        CancellationToken ct = default)
    {
        if (!_isAvailable || _runtimeClient == null)
            throw new InvalidOperationException(
                _availabilityError ?? "OCR 服务不可用");

        // 逐张识别（批量接口可能因内存等原因不稳定，逐张调用更可靠）
        var results = new List<OcrJobResult>();
        var total = filePaths.Count;

        for (var i = 0; i < total; i++)
        {
            ct.ThrowIfCancellationRequested();

            var filePath = filePaths[i];
            try
            {
                var result = await RecognizeAsync(filePath, textScore, useDml, ct);
                results.Add(result);
            }
            catch (Exception ex)
            {
                // 单张失败不影响后续识别
                results.Add(new OcrJobResult
                {
                    IsSuccess = false,
                    ErrorMessage = ex.Message,
                    FilePath = filePath
                });
                _logger?.Error(
                    $"批量 OCR 第 {i + 1}/{total} 张失败: {ex.Message}", ex, "desktop-ocr");
            }

            progressCallback?.Invoke(i + 1, total);
        }

        return results;
    }

    /// <summary>
    /// 带任务跟踪的异步 OCR 识别
    /// 创建 JobRecord 并在开始、进度、完成时更新状态。
    /// </summary>
    /// <param name="filePaths">图片文件路径列表</param>
    /// <param name="textScore">置信度阈值</param>
    /// <param name="useDml">是否使用 GPU 加速</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>创建的任务 ID</returns>
    public async Task<string> RecognizeWithJobTrackingAsync(
        List<string> filePaths,
        double textScore = 0.5,
        bool useDml = false,
        CancellationToken ct = default)
    {
        if (_jobManager == null)
            throw new InvalidOperationException("未配置 JobManager");

        // 创建任务记录
        var job = _jobManager.CreateJob(
            $"OCR 识别 - {filePaths.Count} 张图片",
            "ocr_local",
            filePaths);

        try
        {
            // 更新为运行中
            _jobManager.UpdateJobStatus(job.Id, JobStatus.Running);
            _jobManager.UpdateJobProgress(job.Id, 0);

            var results = await RecognizeBatchAsync(
                filePaths, textScore, useDml,
                (current, total) =>
                {
                    var progress = (int)((double)current / total * 100);
                    _jobManager.UpdateJobProgress(job.Id, progress);
                },
                ct);

            // 检查结果
            var successCount = results.Count(r => r.IsSuccess);
            var failCount = results.Count - successCount;

            job.OutputFiles = results
                .Where(r => r.IsSuccess)
                .Select(r => r.FilePath!)
                .ToList();

            if (failCount > 0)
            {
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Failed,
                    $"完成 {successCount}/{results.Count} 张，{failCount} 张失败");
            }
            else
            {
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Succeeded,
                    $"成功识别 {successCount} 张图片");
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
    /// 判断文件格式是否支持 OCR
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
        _availabilityError = $"OCR worker 进程已退出，退出码: {exitCode}";
        _logger?.Warning($"OCR worker 进程退出 (exitCode={exitCode})", "desktop-ocr");
    }

    public void Dispose()
    {
        if (_runtimeClient != null)
            _runtimeClient.ProcessExited -= OnProcessExited;
        _runtimeClient?.Dispose();
        GC.SuppressFinalize(this);
    }
}
