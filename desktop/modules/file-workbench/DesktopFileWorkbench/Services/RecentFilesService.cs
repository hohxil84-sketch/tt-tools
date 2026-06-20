using System.Text.Json;
using TTTools.FileWorkbench.Models;

namespace TTTools.FileWorkbench.Services;

/// <summary>
/// 最近文件服务
/// 管理用户最近导入/打开的文件记录，支持 JSON 持久化。
/// 最多保留指定数量的最近文件记录。
/// </summary>
public class RecentFilesService
{
    private const int DefaultMaxCount = 50;
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true
    };

    private readonly string _storagePath;
    private readonly int _maxCount;
    private List<RecentFileEntry> _entries;

    /// <summary>最近文件记录列表（按访问时间倒序）</summary>
    public IReadOnlyList<RecentFileEntry> Entries => _entries.AsReadOnly();

    /// <summary>最近文件变更事件</summary>
    public event EventHandler? RecentFilesChanged;

    /// <summary>
    /// 使用默认存储路径初始化最近文件服务
    /// </summary>
    public RecentFilesService() : this(
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "TTTools", "recent-files.json"),
        DefaultMaxCount)
    { }

    /// <summary>
    /// 使用自定义存储路径和最大记录数初始化
    /// </summary>
    public RecentFilesService(string storagePath, int maxCount = DefaultMaxCount)
    {
        _storagePath = storagePath;
        _maxCount = Math.Max(1, maxCount);
        _entries = new List<RecentFileEntry>();
        Load();
    }

    /// <summary>
    /// 记录一个文件到最近文件列表
    /// 如果文件已存在，则更新访问时间并移到列表顶部。
    /// </summary>
    /// <param name="filePath">文件完整路径</param>
    public void RecordFile(string filePath)
    {
        if (string.IsNullOrWhiteSpace(filePath)) return;
        if (!File.Exists(filePath)) return;

        var normalizedPath = Path.GetFullPath(filePath);

        // 移除已存在的同名记录
        _entries.RemoveAll(e =>
            string.Equals(e.FilePath, normalizedPath, StringComparison.OrdinalIgnoreCase));

        // 添加到列表顶部
        _entries.Insert(0, new RecentFileEntry
        {
            FilePath = normalizedPath,
            FileName = Path.GetFileName(normalizedPath),
            Extension = Path.GetExtension(normalizedPath).ToLowerInvariant(),
            LastAccessedAt = DateTime.Now
        });

        // 超出上限时移除最旧的记录
        while (_entries.Count > _maxCount)
            _entries.RemoveAt(_entries.Count - 1);

        // 异步保存到文件（不阻塞调用线程）
        Save();
        RecentFilesChanged?.Invoke(this, EventArgs.Empty);
    }

    /// <summary>
    /// 移除一条最近文件记录
    /// </summary>
    /// <param name="filePath">文件完整路径</param>
    public void RemoveFile(string filePath)
    {
        var removed = _entries.RemoveAll(e =>
            string.Equals(e.FilePath, filePath, StringComparison.OrdinalIgnoreCase));
        if (removed > 0)
        {
            Save();
            RecentFilesChanged?.Invoke(this, EventArgs.Empty);
        }
    }

    /// <summary>
    /// 清空所有最近文件记录
    /// </summary>
    public void Clear()
    {
        _entries.Clear();
        Save();
        RecentFilesChanged?.Invoke(this, EventArgs.Empty);
    }

    /// <summary>
    /// 获取仍然存在于磁盘上的最近文件列表
    /// 自动过滤已删除或移动的文件。
    /// </summary>
    public List<RecentFileEntry> GetExistingFiles()
    {
        return _entries.Where(e => File.Exists(e.FilePath)).ToList();
    }

    /// <summary>
    /// 清理已不存在的文件记录并保存
    /// </summary>
    public void CleanInvalidEntries()
    {
        var removedCount = _entries.RemoveAll(e => !File.Exists(e.FilePath));
        if (removedCount > 0)
        {
            Save();
            RecentFilesChanged?.Invoke(this, EventArgs.Empty);
        }
    }

    /// <summary>
    /// 从 JSON 文件加载最近文件记录
    /// </summary>
    private void Load()
    {
        try
        {
            var dir = Path.GetDirectoryName(_storagePath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                Directory.CreateDirectory(dir);

            if (File.Exists(_storagePath))
            {
                var json = File.ReadAllText(_storagePath);
                _entries = JsonSerializer.Deserialize<List<RecentFileEntry>>(json, JsonOptions)
                           ?? new List<RecentFileEntry>();

                // 清理已不存在的文件记录
                _entries.RemoveAll(e => string.IsNullOrEmpty(e.FilePath));
            }
        }
        catch
        {
            // 加载失败使用空列表
            _entries = new List<RecentFileEntry>();
        }
    }

    /// <summary>
    /// 保存最近文件记录到 JSON 文件
    /// </summary>
    private void Save()
    {
        try
        {
            var dir = Path.GetDirectoryName(_storagePath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                Directory.CreateDirectory(dir);

            var json = JsonSerializer.Serialize(_entries, JsonOptions);
            File.WriteAllText(_storagePath, json);
        }
        catch
        {
            // 保存失败静默处理，不应影响用户操作
        }
    }
}

/// <summary>
/// 最近文件条目
/// 序列化为 JSON 存储，记录文件路径和最后访问时间。
/// </summary>
public class RecentFileEntry
{
    /// <summary>文件完整路径</summary>
    public string FilePath { get; set; } = string.Empty;

    /// <summary>文件名</summary>
    public string FileName { get; set; } = string.Empty;

    /// <summary>文件扩展名（含点号，小写）</summary>
    public string Extension { get; set; } = string.Empty;

    /// <summary>最后访问时间</summary>
    public DateTime LastAccessedAt { get; set; }

    /// <summary>文件当前是否存在于磁盘</summary>
    public bool ExistsOnDisk => File.Exists(FilePath);

    /// <summary>最后访问时间的友好格式</summary>
    public string LastAccessedDisplay => FormatTime(LastAccessedAt);

    private static string FormatTime(DateTime time)
    {
        var localTime = time.ToLocalTime();
        var now = DateTime.Now;
        if (localTime.Date == now.Date)
            return $"今天 {localTime:HH:mm}";
        if (localTime.Date == now.Date.AddDays(-1))
            return $"昨天 {localTime:HH:mm}";
        if (localTime.Year == now.Year)
            return localTime.ToString("MM-dd HH:mm");
        return localTime.ToString("yyyy-MM-dd HH:mm");
    }
}
