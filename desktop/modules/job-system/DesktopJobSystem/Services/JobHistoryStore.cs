using System.Collections.Concurrent;
using System.Text.Json;
using TTShared.JobSystem;

namespace TTTools.JobSystem.Services;

/// <summary>
/// 基于 JSON 文件的任务历史持久化存储
/// 将已完成的任务记录序列化到本地 JSON 文件，
/// 支持应用重启后恢复任务历史。
/// </summary>
public class JobHistoryStore : IJobHistoryStore, IDisposable
{
    private const int DefaultMaxHistorySize = 1000;
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true
    };

    /// <summary>
    /// 用于 JSON 序列化的任务记录 DTO
    /// 仅持久化展示所需字段，不含 INotifyPropertyChanged 订阅等运行时状态。
    /// </summary>
    private class JobRecordDto
    {
        public string Id { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public string Feature { get; set; } = string.Empty;
        public string Status { get; set; } = string.Empty;
        public int Progress { get; set; }
        public List<string> InputFiles { get; set; } = new();
        public List<string> OutputFiles { get; set; } = new();
        public string? ErrorMessage { get; set; }
        public string? ResultMessage { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime? CompletedAt { get; set; }

        public static JobRecordDto FromJobRecord(JobRecord job) => new()
        {
            Id = job.Id,
            Name = job.Name,
            Feature = job.Feature,
            Status = job.Status.ToString(),
            Progress = job.Progress,
            InputFiles = job.InputFiles,
            OutputFiles = job.OutputFiles,
            ErrorMessage = job.ErrorMessage,
            ResultMessage = job.ResultMessage,
            CreatedAt = job.CreatedAt,
            CompletedAt = job.CompletedAt
        };

        public JobRecord ToJobRecord()
        {
            var job = new JobRecord
            {
                Id = Id,
                Name = Name,
                Feature = Feature,
                Progress = Progress,
                InputFiles = InputFiles ?? new List<string>(),
                OutputFiles = OutputFiles ?? new List<string>(),
                ErrorMessage = ErrorMessage,
                ResultMessage = ResultMessage,
                CreatedAt = CreatedAt,
                CompletedAt = CompletedAt
            };

            // 恢复状态枚举
            if (Enum.TryParse<JobStatus>(Status, out var parsedStatus))
                job.Status = parsedStatus;

            return job;
        }
    }

    private readonly string _storagePath;
    private readonly int _maxHistorySize;
    private readonly ConcurrentDictionary<string, JobRecord> _history = new();
    private readonly SemaphoreSlim _saveLock = new(1, 1);

    /// <summary>当前历史记录数量</summary>
    public int Count => _history.Count;

    /// <summary>
    /// 使用默认存储路径初始化历史存储
    /// 默认路径：%LocalAppData%/TTTools/job-history.json
    /// </summary>
    public JobHistoryStore() : this(
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "TTTools", "job-history.json"),
        DefaultMaxHistorySize)
    { }

    /// <summary>
    /// 使用自定义存储路径和最大记录数初始化
    /// </summary>
    /// <param name="storagePath">JSON 文件存储路径</param>
    /// <param name="maxHistorySize">最大历史记录数量</param>
    public JobHistoryStore(string storagePath, int maxHistorySize = DefaultMaxHistorySize)
    {
        _storagePath = storagePath ?? throw new ArgumentNullException(nameof(storagePath));
        _maxHistorySize = Math.Max(1, maxHistorySize);
    }

    /// <summary>
    /// 保存一条已完成的任务记录
    /// 仅保存已完成（成功/失败/取消）的任务，忽略活动任务。
    /// </summary>
    public async Task SaveAsync(JobRecord job)
    {
        if (job == null) throw new ArgumentNullException(nameof(job));
        if (!job.IsCompleted) return; // 只保存已完成的任务

        _history[job.Id] = job;

        // 超出上限时移除最旧的记录
        while (_history.Count > _maxHistorySize)
        {
            var oldest = _history.Values
                .OrderBy(j => j.CompletedAt ?? j.CreatedAt)
                .FirstOrDefault();
            if (oldest != null)
                _history.TryRemove(oldest.Id, out _);
        }

        await PersistToFileAsync();
    }

    /// <summary>
    /// 加载所有历史任务记录
    /// </summary>
    public async Task<List<JobRecord>> LoadAsync()
    {
        // 如果内存中已有数据，直接返回
        if (!_history.IsEmpty)
            return _history.Values
                .OrderByDescending(j => j.CompletedAt ?? j.CreatedAt)
                .ToList();

        // 从文件加载
        var loaded = await LoadFromFileAsync();
        foreach (var job in loaded)
            _history[job.Id] = job;

        return _history.Values
            .OrderByDescending(j => j.CompletedAt ?? j.CreatedAt)
            .ToList();
    }

    /// <summary>
    /// 清除所有历史记录
    /// </summary>
    public async Task ClearAsync()
    {
        _history.Clear();
        await PersistToFileAsync();
    }

    /// <summary>
    /// 将历史记录持久化到 JSON 文件
    /// </summary>
    private async Task PersistToFileAsync()
    {
        await _saveLock.WaitAsync();
        try
        {
            var dir = Path.GetDirectoryName(_storagePath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                Directory.CreateDirectory(dir);

            var dtos = _history.Values.Select(JobRecordDto.FromJobRecord).ToList();
            var json = JsonSerializer.Serialize(dtos, JsonOptions);
            await File.WriteAllTextAsync(_storagePath, json);
        }
        catch
        {
            // 保存失败静默处理，不应影响用户操作
        }
        finally
        {
            _saveLock.Release();
        }
    }

    /// <summary>
    /// 从 JSON 文件加载历史记录
    /// </summary>
    private async Task<List<JobRecord>> LoadFromFileAsync()
    {
        try
        {
            if (!File.Exists(_storagePath))
                return new List<JobRecord>();

            var json = await File.ReadAllTextAsync(_storagePath);
            var dtos = JsonSerializer.Deserialize<List<JobRecordDto>>(json, JsonOptions);
            return dtos?.Select(d => d.ToJobRecord()).ToList() ?? new List<JobRecord>();
        }
        catch
        {
            // 加载失败返回空列表
            return new List<JobRecord>();
        }
    }

    public void Dispose()
    {
        _saveLock.Dispose();
    }
}
