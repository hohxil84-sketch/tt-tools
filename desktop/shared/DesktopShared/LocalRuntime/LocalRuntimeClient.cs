using System.Diagnostics;
using System.Text;
using System.Text.Json;

namespace TTShared.LocalRuntime;

/// <summary>
/// 本地 Python worker 进程客户端
/// 通过 JSON 协议与本地 Python worker 进程通信（stdin/stdout）。
/// 负责进程生命周期管理和请求/响应编解码。
/// </summary>
public class LocalRuntimeClient : IDisposable
{
    private Process? _process;
    private readonly string _pythonPath;
    private readonly string _workerScriptPath;
    private readonly TimeSpan _startTimeout = TimeSpan.FromSeconds(30);
    private readonly List<string> _stderrLines = new();  // 收集 stderr 用于诊断
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    /// <summary>worker 进程是否正在运行</summary>
    public bool IsRunning => _process != null && !_process.HasExited;

    /// <summary>最近收集的 stderr 输出（用于诊断）</summary>
    public string LastStderr => string.Join("\n", _stderrLines.TakeLast(20));

    /// <summary>进程退出事件</summary>
    public event EventHandler<int>? ProcessExited;

    /// <summary>
    /// 初始化本地 runtime 客户端
    /// </summary>
    /// <param name="pythonPath">Python 解释器路径</param>
    /// <param name="workerScriptPath">本地 worker 入口脚本路径</param>
    public LocalRuntimeClient(string pythonPath, string workerScriptPath)
    {
        _pythonPath = pythonPath;
        _workerScriptPath = workerScriptPath;
    }

    /// <summary>
    /// 启动本地 Python worker 进程
    /// </summary>
    public async Task<bool> StartAsync(CancellationToken ct = default)
    {
        if (IsRunning) return true;

        if (!File.Exists(_pythonPath))
            throw new FileNotFoundException($"Python 解释器未找到：{_pythonPath}");

        if (!File.Exists(_workerScriptPath))
            throw new FileNotFoundException($"Worker 脚本未找到：{_workerScriptPath}");

        _process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = _pythonPath,
                Arguments = $"\"{_workerScriptPath}\"",
                UseShellExecute = false,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardInputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8,
            },
            EnableRaisingEvents = true
        };

        // 设置环境变量：确保 Python 子进程使用 UTF-8 编码，禁用输出缓冲
        _process.StartInfo.Environment["PYTHONIOENCODING"] = "utf-8";
        _process.StartInfo.Environment["PYTHONUNBUFFERED"] = "1";

        _process.Exited += OnProcessExited;
        _stderrLines.Clear();
        // 收集 stderr 用于诊断
        _process.ErrorDataReceived += (_, args) =>
        {
            if (!string.IsNullOrEmpty(args.Data))
                _stderrLines.Add(args.Data);
        };

        try
        {
            _process.Start();
            _process.BeginErrorReadLine(); // 避免 stderr 缓冲区满导致阻塞

            // 等待进程启动就绪（给 Python 导入模块留足时间）
            await Task.Delay(2000, ct);
            return !_process.HasExited;
        }
        catch (Exception)
        {
            _process.Dispose();
            _process = null;
            throw;
        }
    }

    /// <summary>
    /// 向 worker 发送请求并等待响应
    /// </summary>
    /// <typeparam name="TRequest">请求数据类型</typeparam>
    /// <typeparam name="TResponse">响应数据类型</typeparam>
    /// <param name="action">操作名称</param>
    /// <param name="requestData">请求数据</param>
    /// <returns>响应数据</returns>
    public async Task<TResponse?> SendAsync<TRequest, TResponse>(
        string action, TRequest requestData, CancellationToken ct = default)
    {
        if (!IsRunning)
            throw new InvalidOperationException("本地 worker 进程未启动");

        var requestObj = new
        {
            action,
            data = requestData,
            request_id = $"local_{Guid.NewGuid():N}"
        };

        var requestJson = JsonSerializer.Serialize(requestObj, JsonOptions);
        var requestLine = requestJson + "\n";

        // 通过 stdin 发送请求
        await _process!.StandardInput.WriteAsync(requestLine);
        await _process.StandardInput.FlushAsync(ct);

        // 通过 stdout 读取响应（单行 JSON），使用 300 秒超时
        // 首次运行 rembg 需下载 ONNX 模型（u2net 约 179MB），慢速网络可能需要数分钟
        using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeoutCts.CancelAfter(TimeSpan.FromSeconds(300));

        string? responseJson;
        try
        {
            // 跳过日志等非 JSON 行，直到找到以 { 开头的 JSON 响应
            do
            {
                responseJson = await _process.StandardOutput.ReadLineAsync(timeoutCts.Token);
            }
            while (responseJson != null && !responseJson.TrimStart().StartsWith('{'));

            if (responseJson != null && responseJson.TrimStart().StartsWith('{'))
            {
                // 跳过闭合大括号后的尾部内容（如共享库的 flush() 操作可能产生的空行）
            }
        }
        catch (OperationCanceledException)
        {
            var stderrInfo = _stderrLines.Count > 0
                ? $"\n[stderr 最近输出]: {string.Join(" | ", _stderrLines.TakeLast(5))}"
                : "";
            throw new TimeoutException($"本地 worker 操作超时：{action}{stderrInfo}");
        }

        if (string.IsNullOrEmpty(responseJson))
        {
            var stderrInfo = _stderrLines.Count > 0
                ? $"\n[stderr 输出]: {string.Join(" | ", _stderrLines.TakeLast(10))}"
                : "\n[stderr 无输出，进程可能已崩溃]";
            throw new InvalidOperationException($"本地 worker 返回空响应（进程可能已退出）{stderrInfo}");
        }

        return JsonSerializer.Deserialize<TResponse>(responseJson, JsonOptions);
    }

    /// <summary>
    /// 健康检查：向 worker 发送 ping 命令
    /// </summary>
    public async Task<bool> PingAsync(CancellationToken ct = default)
    {
        if (!IsRunning) return false;

        try
        {
            await SendAsync<object, object>("ping", new { }, ct);
            return true;
        }
        catch
        {
            return false;
        }
    }

    /// <summary>
    /// 停止本地 worker 进程
    /// </summary>
    public void Stop()
    {
        if (_process == null) return;

        try
        {
            if (!_process.HasExited)
            {
                // 发送优雅退出命令
                _process.StandardInput.WriteLine("{\"action\":\"shutdown\"}\n");
                _process.StandardInput.Flush();

                // 等待 5 秒，未退出则强制结束
                if (!_process.WaitForExit(5000))
                {
                    _process.Kill(entireProcessTree: true);
                }
            }
        }
        catch
        {
            // 进程可能已经退出
        }
        finally
        {
            _process.Dispose();
            _process = null;
        }
    }

    private void OnProcessExited(object? sender, EventArgs e)
    {
        var exitCode = _process?.ExitCode ?? -1;
        ProcessExited?.Invoke(this, exitCode);
    }

    public void Dispose()
    {
        Stop();
        GC.SuppressFinalize(this);
    }
}
