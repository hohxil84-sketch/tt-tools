using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Text.Json;

namespace TTShared.Settings;

/// <summary>
/// 应用设置管理器
/// 管理用户偏好设置，支持 JSON 文件持久化。
/// 设置存储在用户本地应用数据目录。
/// </summary>
public class AppSettings : INotifyPropertyChanged
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true
    };

    private static readonly Lazy<AppSettings> _instance = new(() => new AppSettings());
    public static AppSettings Instance => _instance.Value;

    private string _serverUrl = "http://192.168.2.101:8000";
    private string _theme = "Light";
    private string _language = "zh-CN";
    private string? _pythonPath;
    private int _maxConcurrentJobs = 3;
    private bool _autoUpdateCheck = true;
    private bool _sendUsageStats = false;

    private readonly string _settingsFilePath;
    private bool _isLoaded;

    /// <summary>云端 API 服务器地址</summary>
    public string ServerUrl
    {
        get => _serverUrl;
        set { _serverUrl = value; OnPropertyChanged(); }
    }

    /// <summary>UI 主题：Light / Dark</summary>
    public string Theme
    {
        get => _theme;
        set { _theme = value; OnPropertyChanged(); }
    }

    /// <summary>界面语言</summary>
    public string Language
    {
        get => _language;
        set { _language = value; OnPropertyChanged(); }
    }

    /// <summary>Python 解释器路径（用于 local worker）</summary>
    public string? PythonPath
    {
        get => _pythonPath;
        set { _pythonPath = value; OnPropertyChanged(); }
    }

    /// <summary>最大并发任务数</summary>
    public int MaxConcurrentJobs
    {
        get => _maxConcurrentJobs;
        set { _maxConcurrentJobs = Math.Clamp(value, 1, 10); OnPropertyChanged(); }
    }

    /// <summary>是否自动检查更新</summary>
    public bool AutoUpdateCheck
    {
        get => _autoUpdateCheck;
        set { _autoUpdateCheck = value; OnPropertyChanged(); }
    }

    /// <summary>是否发送使用统计（匿名）</summary>
    public bool SendUsageStats
    {
        get => _sendUsageStats;
        set { _sendUsageStats = value; OnPropertyChanged(); }
    }

    /// <summary>设置变更事件</summary>
    public event EventHandler<SettingChangedEventArgs>? SettingChanged;

    public event PropertyChangedEventHandler? PropertyChanged;

    public AppSettings() : this(
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "TTTools", "settings", "app-settings.json"))
    { }

    public AppSettings(string settingsFilePath)
    {
        _settingsFilePath = settingsFilePath;
    }

    /// <summary>
    /// 从文件加载设置
    /// </summary>
    public void Load()
    {
        try
        {
            var dir = Path.GetDirectoryName(_settingsFilePath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                Directory.CreateDirectory(dir);

            if (File.Exists(_settingsFilePath))
            {
                var json = File.ReadAllText(_settingsFilePath);
                var loaded = JsonSerializer.Deserialize<SettingsFile>(json, JsonOptions);
                if (loaded != null)
                {
                    _serverUrl = loaded.ServerUrl ?? _serverUrl;
                    _theme = loaded.Theme ?? _theme;
                    _language = loaded.Language ?? _language;
                    _pythonPath = loaded.PythonPath ?? _pythonPath;
                    _maxConcurrentJobs = loaded.MaxConcurrentJobs > 0 ? loaded.MaxConcurrentJobs : _maxConcurrentJobs;
                    _autoUpdateCheck = loaded.AutoUpdateCheck;
                    _sendUsageStats = loaded.SendUsageStats;
                }
            }

            _isLoaded = true;
        }
        catch
        {
            // 加载失败使用默认设置
        }
    }

    /// <summary>
    /// 保存设置到文件
    /// </summary>
    public void Save()
    {
        try
        {
            var dir = Path.GetDirectoryName(_settingsFilePath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                Directory.CreateDirectory(dir);

            var settingsFile = new SettingsFile
            {
                ServerUrl = _serverUrl,
                Theme = _theme,
                Language = _language,
                PythonPath = _pythonPath,
                MaxConcurrentJobs = _maxConcurrentJobs,
                AutoUpdateCheck = _autoUpdateCheck,
                SendUsageStats = _sendUsageStats
            };

            var json = JsonSerializer.Serialize(settingsFile, JsonOptions);
            File.WriteAllText(_settingsFilePath, json);
        }
        catch
        {
            // 保存失败不抛异常
        }
    }

    /// <summary>
    /// 重置为默认设置
    /// </summary>
    public void Reset()
    {
        _serverUrl = "http://192.168.2.101:8000";
        _theme = "Light";
        _language = "zh-CN";
        _pythonPath = null;
        _maxConcurrentJobs = 3;
        _autoUpdateCheck = true;
        _sendUsageStats = false;

        // 通知所有属性变更
        OnPropertyChanged(nameof(ServerUrl));
        OnPropertyChanged(nameof(Theme));
        OnPropertyChanged(nameof(Language));
        OnPropertyChanged(nameof(PythonPath));
        OnPropertyChanged(nameof(MaxConcurrentJobs));
        OnPropertyChanged(nameof(AutoUpdateCheck));
        OnPropertyChanged(nameof(SendUsageStats));

        // 删除设置文件
        try { File.Delete(_settingsFilePath); } catch { }
    }

    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));

        if (_isLoaded)
            SettingChanged?.Invoke(this, new SettingChangedEventArgs(propertyName ?? ""));
    }

    /// <summary>
    /// 设置文件的序列化结构（不暴露给外部）
    /// </summary>
    private class SettingsFile
    {
        public string? ServerUrl { get; set; }
        public string? Theme { get; set; }
        public string? Language { get; set; }
        public string? PythonPath { get; set; }
        public int MaxConcurrentJobs { get; set; } = 3;
        public bool AutoUpdateCheck { get; set; } = true;
        public bool SendUsageStats { get; set; }
    }
}

/// <summary>
/// 设置变更事件参数
/// </summary>
public class SettingChangedEventArgs : EventArgs
{
    public string PropertyName { get; }

    public SettingChangedEventArgs(string propertyName)
    {
        PropertyName = propertyName;
    }
}
