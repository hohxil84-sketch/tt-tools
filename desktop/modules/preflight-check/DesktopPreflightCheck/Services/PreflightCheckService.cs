using System.Diagnostics;
using System.Text.Json;
using TTShared.LocalRuntime;
using TTShared.Logging;
using TTShared.FileSystem;
using TTShared.JobSystem;
using TTTools.PreflightCheck.Models;

namespace TTTools.PreflightCheck.Services;

/// <summary>
/// 印前检查服务
/// 封装与 local-worker PreflightChecker 的通信，提供单文件检查、
/// 批量检查和健康检查能力。
/// 通过 LocalRuntimeClient 启动 Python worker 进程，使用 stdin/stdout JSON 协议通信。
/// 印前检查是本地免费功能，不需要云端权限检查。
/// </summary>
public class PreflightCheckService : IDisposable
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

    /// <summary>检查器名称</summary>
    public string CheckerName { get; private set; } = "PreflightChecker";

    /// <summary>支持的图片格式列表</summary>
    public List<string> SupportedFormats { get; private set; } = new()
    {
        ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"
    };

    /// <summary>服务不可用时的错误信息</summary>
    public string? AvailabilityError => _availabilityError;

    /// <summary>
    /// 构造函数
    /// </summary>
    /// <param name="pythonPath">Python 解释器路径</param>
    /// <param name="routerScriptPath">印前检查 router 脚本路径</param>
    /// <param name="jobManager">任务管理器（可选）</param>
    /// <param name="logger">日志记录器（可选）</param>
    public PreflightCheckService(string pythonPath, string routerScriptPath,
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
    public PreflightCheckService() { }

    /// <summary>
    /// 启动印前检查 worker 进程并检查可用性
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
                _availabilityError = "印前检查 worker 进程启动失败";
                return false;
            }

            // 健康检查
            await _runtimeClient.SendAsync<object, JsonElement>(
                "ping", new { }, ct);

            _isAvailable = true;
            _availabilityError = null;
            _logger?.Info("印前检查服务就绪", "desktop-preflight-check");
            return true;
        }
        catch (Exception ex)
        {
            _isAvailable = false;
            _availabilityError = $"印前检查服务启动失败: {ex.Message}";
            _logger?.Error($"印前检查服务启动失败: {ex.Message}", ex, "desktop-preflight-check");
            return false;
        }
    }

    /// <summary>
    /// 对单个文件执行印前检查
    /// </summary>
    /// <param name="filePath">图像文件路径</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>印前检查报告</returns>
    public async Task<PreflightCheckReport> CheckAsync(
        string filePath, CancellationToken ct = default)
    {
        if (!_isAvailable || _runtimeClient == null)
            throw new InvalidOperationException(
                _availabilityError ?? "印前检查服务不可用，请先调用 StartAsync");

        if (!File.Exists(filePath))
            throw new FileNotFoundException($"文件不存在: {filePath}");

        // 校验文件格式
        var ext = FileSystemService.GetExtension(filePath);
        if (!SupportedFormats.Contains(ext))
            throw new ArgumentException(
                $"不支持的图片格式: {ext}，支持: {string.Join(", ", SupportedFormats)}");

        _logger?.Info($"开始印前检查: {Path.GetFileName(filePath)}", "desktop-preflight-check");

        // 发送检查请求
        var requestData = new { file_path = filePath };

        JsonElement? response = await _runtimeClient.SendAsync<object, JsonElement>(
            "check", requestData, ct);

        if (response is null)
            throw new InvalidOperationException("印前检查 worker 返回空响应");

        var resp = response.Value;

        // 检查响应是否成功
        if (resp.TryGetProperty("success", out var success) && !success.GetBoolean())
        {
            var error = resp.TryGetProperty("error", out var err)
                ? err.GetString() ?? "未知错误" : "未知错误";
            return PreflightCheckReport.CreateFailedReport(filePath, error);
        }

        // 解析检查报告数据
        var data = resp.TryGetProperty("data", out var d) ? d : resp;
        var report = PreflightCheckReport.FromRouterResponse(data);

        _logger?.Info(
            $"印前检查完成: {Path.GetFileName(filePath)}, 总体: {report.OverallRiskLabel}, " +
            $"错误:{report.ErrorCount} 警告:{report.WarningCount} 通过:{report.PassCount}",
            "desktop-preflight-check");

        return report;
    }

    /// <summary>
    /// 批量检查多个文件
    /// </summary>
    /// <param name="filePaths">图像文件路径列表</param>
    /// <param name="progressCallback">进度回调 (当前索引, 总数)</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>印前检查报告列表</returns>
    public async Task<List<PreflightCheckReport>> CheckBatchAsync(
        List<string> filePaths,
        Action<int, int>? progressCallback = null,
        CancellationToken ct = default)
    {
        if (!_isAvailable || _runtimeClient == null)
            throw new InvalidOperationException(
                _availabilityError ?? "印前检查服务不可用");

        // 逐文件检查（保证每张图片独立处理，单张失败不影响后续）
        var reports = new List<PreflightCheckReport>();
        var total = filePaths.Count;

        for (var i = 0; i < total; i++)
        {
            ct.ThrowIfCancellationRequested();

            var filePath = filePaths[i];
            try
            {
                var report = await CheckAsync(filePath, ct);
                reports.Add(report);
            }
            catch (Exception ex)
            {
                // 单张失败不影响后续检查
                reports.Add(PreflightCheckReport.CreateFailedReport(
                    filePath, $"检查失败: {ex.Message}"));
                _logger?.Error(
                    $"批量印前检查第 {i + 1}/{total} 个文件失败: {ex.Message}",
                    ex, "desktop-preflight-check");
            }

            progressCallback?.Invoke(i + 1, total);
        }

        return reports;
    }

    /// <summary>
    /// 带任务跟踪的异步印前检查
    /// 创建 JobRecord 并在开始、进度、完成时更新状态。
    /// </summary>
    /// <param name="filePaths">图像文件路径列表</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>创建的任务 ID</returns>
    public async Task<string> CheckWithJobTrackingAsync(
        List<string> filePaths, CancellationToken ct = default)
    {
        if (_jobManager == null)
            throw new InvalidOperationException("未配置 JobManager");

        // 创建任务记录
        var job = _jobManager.CreateJob(
            $"印前检查 - {filePaths.Count} 个文件",
            "preflight_check_local",
            filePaths);

        try
        {
            // 更新为运行中
            _jobManager.UpdateJobStatus(job.Id, JobStatus.Running);
            _jobManager.UpdateJobProgress(job.Id, 0);

            var reports = await CheckBatchAsync(
                filePaths,
                (current, total) =>
                {
                    var progress = (int)((double)current / total * 100);
                    _jobManager.UpdateJobProgress(job.Id, progress);
                },
                ct);

            // 统计结果
            var errorCount = reports.Count(r => r.OverallRisk == RiskLevel.Error);
            var warningCount = reports.Count(r => r.OverallRisk == RiskLevel.Warning);
            var passCount = reports.Count(r => r.OverallRisk == RiskLevel.Pass);

            if (errorCount > 0)
            {
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Failed,
                    $"{errorCount} 个文件存在严重风险，{warningCount} 个文件需要复核，{passCount} 个文件通过");
            }
            else if (warningCount > 0)
            {
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Succeeded,
                    $"{passCount} 个文件通过，{warningCount} 个文件存在注意事项");
            }
            else
            {
                _jobManager.UpdateJobStatus(job.Id, JobStatus.Succeeded,
                    $"全部 {passCount} 个文件通过印前检查");
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
    /// 判断文件格式是否支持印前检查
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
        _availabilityError = $"印前检查 worker 进程已退出，退出码: {exitCode}";
        _logger?.Warning($"印前检查 worker 进程退出 (exitCode={exitCode})", "desktop-preflight-check");
    }

    public void Dispose()
    {
        if (_runtimeClient != null)
            _runtimeClient.ProcessExited -= OnProcessExited;
        _runtimeClient?.Dispose();
        GC.SuppressFinalize(this);
    }
}
