using System.Windows.Input;
using TTTools.ExportSettings.Models;
using TTTools.ExportSettings.Services;
using TTShared.Settings;
using TTShared.UI;

namespace TTTools.ExportSettings.ViewModels;

/// <summary>
/// 版本更新 ViewModel
/// 管理版本信息展示、更新检查和自动更新设置。
/// </summary>
public class UpdateViewModel : BaseViewModel
{
    private readonly UpdateCheckService _updateService;
    private readonly AppSettings? _settings;

    /// <summary>更新信息</summary>
    private UpdateInfo _updateInfo;
    public UpdateInfo UpdateInfo
    {
        get => _updateInfo;
        set => SetProperty(ref _updateInfo, value);
    }

    /// <summary>是否正在检查更新</summary>
    private bool _isChecking;
    public bool IsChecking
    {
        get => _isChecking;
        set
        {
            if (SetProperty(ref _isChecking, value))
                OnPropertyChanged(nameof(IsNotChecking));
        }
    }

    /// <summary>是否未在检查更新（用于按钮 IsEnabled 绑定）</summary>
    public bool IsNotChecking => !IsChecking;

    /// <summary>状态消息</summary>
    private string _statusMessage = "启动时自动检查更新";
    public string StatusMessage
    {
        get => _statusMessage;
        set => SetProperty(ref _statusMessage, value);
    }

    /// <summary>检查更新命令</summary>
    public ICommand CheckUpdateCommand { get; }

    /// <summary>打开下载页面命令</summary>
    public ICommand OpenDownloadCommand { get; }

    /// <summary>打开发布说明命令</summary>
    public ICommand OpenReleaseNotesCommand { get; }

    public UpdateViewModel(UpdateCheckService? updateService = null, AppSettings? settings = null)
    {
        _updateService = updateService ?? new UpdateCheckService();
        _settings = settings;

        _updateInfo = _updateService.GetCurrentVersionInfo();

        CheckUpdateCommand = new AsyncRelayCommand(CheckUpdateAsync);
        OpenDownloadCommand = new RelayCommand(OpenDownload);
        OpenReleaseNotesCommand = new RelayCommand(OpenReleaseNotes);
    }

    /// <summary>
    /// 默认构造函数（用于设计时和 XAML 实例化）
    /// </summary>
    public UpdateViewModel() : this(null, null) { }

    /// <summary>
    /// 异步检查更新
    /// </summary>
    public async Task CheckUpdateAsync()
    {
        IsChecking = true;
        StatusMessage = "正在检查更新...";

        try
        {
            UpdateInfo = await _updateService.CheckForUpdatesAsync();
            StatusMessage = UpdateInfo.CheckStatusText;
        }
        catch (Exception ex)
        {
            UpdateInfo.CheckFailed = true;
            UpdateInfo.ErrorMessage = ex.Message;
            StatusMessage = $"检查失败：{ex.Message}";
        }
        finally
        {
            IsChecking = false;
        }
    }

    /// <summary>
    /// 打开下载页面
    /// 实际集成时使用 Process.Start 打开浏览器。
    /// </summary>
    private void OpenDownload()
    {
        if (!string.IsNullOrWhiteSpace(UpdateInfo.DownloadUrl))
        {
            // 实际 WPF 中：System.Diagnostics.Process.Start("explorer.exe", UpdateInfo.DownloadUrl);
            StatusMessage = $"打开下载页面：{UpdateInfo.DownloadUrl}";
        }
    }

    /// <summary>
    /// 打开发布说明
    /// 实际集成时使用 Process.Start 打开浏览器。
    /// </summary>
    private void OpenReleaseNotes()
    {
        if (!string.IsNullOrWhiteSpace(UpdateInfo.ReleaseNotesUrl))
        {
            // 实际 WPF 中：System.Diagnostics.Process.Start("explorer.exe", UpdateInfo.ReleaseNotesUrl);
            StatusMessage = $"打开发布说明：{UpdateInfo.ReleaseNotesUrl}";
        }
    }
}
