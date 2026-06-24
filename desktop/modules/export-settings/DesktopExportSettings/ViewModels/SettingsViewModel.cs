using System.Collections.ObjectModel;
using System.Windows.Input;
using TTShared.Settings;
using TTShared.UI;

namespace TTTools.ExportSettings.ViewModels;

/// <summary>
/// 设置页面 ViewModel
/// 包装 AppSettings.Instance 的属性用于 UI 绑定，
/// 提供保存、重置等命令。
/// </summary>
public class SettingsViewModel : BaseViewModel
{
    private readonly AppSettings _settings;

    /// <summary>服务器地址</summary>
    public string ServerUrl
    {
        get => _settings.ServerUrl;
        set
        {
            if (_settings.ServerUrl != value)
            {
                _settings.ServerUrl = value;
                OnPropertyChanged();
                MarkDirty();
            }
        }
    }

    /// <summary>UI 主题</summary>
    public string Theme
    {
        get => _settings.Theme;
        set
        {
            if (_settings.Theme != value)
            {
                _settings.Theme = value;
                OnPropertyChanged();
                MarkDirty();
            }
        }
    }

    /// <summary>界面语言</summary>
    public string Language
    {
        get => _settings.Language;
        set
        {
            if (_settings.Language != value)
            {
                _settings.Language = value;
                OnPropertyChanged();
                MarkDirty();
            }
        }
    }

    /// <summary>Python 解释器路径</summary>
    public string? PythonPath
    {
        get => _settings.PythonPath;
        set
        {
            if (_settings.PythonPath != value)
            {
                _settings.PythonPath = value;
                OnPropertyChanged();
                MarkDirty();
            }
        }
    }

    /// <summary>最大并发任务数</summary>
    public int MaxConcurrentJobs
    {
        get => _settings.MaxConcurrentJobs;
        set
        {
            if (_settings.MaxConcurrentJobs != value)
            {
                _settings.MaxConcurrentJobs = value;
                OnPropertyChanged();
                MarkDirty();
            }
        }
    }

    /// <summary>是否自动检查更新</summary>
    public bool AutoUpdateCheck
    {
        get => _settings.AutoUpdateCheck;
        set
        {
            if (_settings.AutoUpdateCheck != value)
            {
                _settings.AutoUpdateCheck = value;
                OnPropertyChanged();
                MarkDirty();
            }
        }
    }

    /// <summary>是否发送使用统计</summary>
    public bool SendUsageStats
    {
        get => _settings.SendUsageStats;
        set
        {
            if (_settings.SendUsageStats != value)
            {
                _settings.SendUsageStats = value;
                OnPropertyChanged();
                MarkDirty();
            }
        }
    }

    /// <summary>是否有未保存的更改</summary>
    private bool _isDirty;
    public bool IsDirty
    {
        get => _isDirty;
        set => SetProperty(ref _isDirty, value);
    }

    /// <summary>保存状态提示</summary>
    private string _statusMessage = string.Empty;
    public string StatusMessage
    {
        get => _statusMessage;
        set => SetProperty(ref _statusMessage, value);
    }

    /// <summary>主题选项</summary>
    public ObservableCollection<string> ThemeOptions { get; } = new()
    {
        "Light", "Dark"
    };

    /// <summary>语言选项</summary>
    public ObservableCollection<string> LanguageOptions { get; } = new()
    {
        "zh-CN", "en-US"
    };

    /// <summary>保存设置命令</summary>
    public ICommand SaveCommand { get; }

    /// <summary>重置为默认设置命令</summary>
    public ICommand ResetCommand { get; }

    /// <summary>选择 Python 路径命令</summary>
    public ICommand BrowsePythonPathCommand { get; }

    public SettingsViewModel(AppSettings? settings = null)
    {
        _settings = settings ?? AppSettings.Instance;

        SaveCommand = new RelayCommand(Save);
        ResetCommand = new RelayCommand(Reset);
        BrowsePythonPathCommand = new RelayCommand(BrowsePythonPath);
    }

    /// <summary>
    /// 默认构造函数（用于设计时和 XAML 实例化）
    /// </summary>
    public SettingsViewModel() : this(null) { }

    /// <summary>
    /// 保存设置到文件
    /// </summary>
    public void Save()
    {
        try
        {
            _settings.Save();
            IsDirty = false;
            StatusMessage = "设置已保存";
        }
        catch (Exception ex)
        {
            StatusMessage = $"保存失败：{ex.Message}";
        }
    }

    /// <summary>
    /// 重置为默认设置
    /// </summary>
    public void Reset()
    {
        _settings.Reset();

        // 通知所有属性变更
        OnPropertyChanged(nameof(ServerUrl));
        OnPropertyChanged(nameof(Theme));
        OnPropertyChanged(nameof(Language));
        OnPropertyChanged(nameof(PythonPath));
        OnPropertyChanged(nameof(MaxConcurrentJobs));
        OnPropertyChanged(nameof(AutoUpdateCheck));
        OnPropertyChanged(nameof(SendUsageStats));

        IsDirty = false;
        StatusMessage = "设置已重置为默认值";
    }

    /// <summary>
    /// 浏览选择 Python 解释器路径
    /// 实际集成时使用 OpenFileDialog。
    /// </summary>
    public void BrowsePythonPath()
    {
        // 实际 WPF 中使用 OpenFileDialog 选择 python.exe
        // 此处提供方法供 View 层调用
    }

    /// <summary>
    /// 设置 Python 路径（供 View 层调用）
    /// </summary>
    public void SetPythonPath(string path)
    {
        if (!string.IsNullOrWhiteSpace(path))
        {
            PythonPath = path;
        }
    }

    /// <summary>
    /// 标记有未保存更改
    /// </summary>
    private void MarkDirty()
    {
        IsDirty = true;
        StatusMessage = string.Empty;
    }
}
