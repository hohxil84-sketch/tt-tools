namespace TTTools.ExportSettings.Models;

/// <summary>
/// 版本更新信息模型
/// </summary>
public class UpdateInfo
{
    /// <summary>当前版本</summary>
    public string CurrentVersion { get; set; } = "0.1.0";

    /// <summary>最新版本（null 表示尚未检查）</summary>
    public string? LatestVersion { get; set; }

    /// <summary>是否有可用更新</summary>
    public bool UpdateAvailable { get; set; }

    /// <summary>更新发布说明 URL</summary>
    public string? ReleaseNotesUrl { get; set; }

    /// <summary>更新下载 URL</summary>
    public string? DownloadUrl { get; set; }

    /// <summary>最近检查时间</summary>
    public DateTime? LastCheckTime { get; set; }

    /// <summary>检查是否失败</summary>
    public bool CheckFailed { get; set; }

    /// <summary>失败原因</summary>
    public string? ErrorMessage { get; set; }

    /// <summary>检查状态文字</summary>
    public string CheckStatusText
    {
        get
        {
            if (CheckFailed)
                return "检查失败";
            if (!LastCheckTime.HasValue)
                return "尚未检查";
            if (UpdateAvailable)
                return $"有新版本可用：{LatestVersion}";
            return "已是最新版本";
        }
    }

    /// <summary>最近检查时间的格式化文本</summary>
    public string LastCheckTimeFormatted
        => LastCheckTime?.ToString("yyyy-MM-dd HH:mm:ss") ?? "--";
}
