using TTTools.ExportSettings.Models;

namespace TTTools.ExportSettings.Services;

/// <summary>
/// 版本更新检查服务
/// 当前阶段提供基础版本信息展示和手动检查框架。
/// 后续阶段可接入云端版本检查 API 实现自动更新通知。
/// </summary>
public class UpdateCheckService
{
    private readonly string _currentVersion;
    private readonly string? _updateCheckUrl;

    /// <summary>
    /// 创建版本更新检查服务
    /// </summary>
    /// <param name="currentVersion">当前应用版本</param>
    /// <param name="updateCheckUrl">版本检查 API 地址（可选）</param>
    public UpdateCheckService(string currentVersion = "0.1.0", string? updateCheckUrl = null)
    {
        _currentVersion = currentVersion;
        _updateCheckUrl = updateCheckUrl;
    }

    /// <summary>
    /// 获取当前版本信息
    /// </summary>
    public UpdateInfo GetCurrentVersionInfo()
    {
        return new UpdateInfo
        {
            CurrentVersion = _currentVersion,
            LatestVersion = null,
            UpdateAvailable = false
        };
    }

    /// <summary>
    /// 检查更新
    /// 当前阶段返回当前版本信息（后续阶段可接入云端 API）。
    /// </summary>
    public async Task<UpdateInfo> CheckForUpdatesAsync()
    {
        var info = new UpdateInfo
        {
            CurrentVersion = _currentVersion,
            LastCheckTime = DateTime.Now
        };

        // 如果没有配置更新检查 URL，仅返回版本信息
        if (string.IsNullOrWhiteSpace(_updateCheckUrl))
        {
            info.LatestVersion = _currentVersion;
            info.UpdateAvailable = false;
            return info;
        }

        // 后续阶段：调用云端 API 检查更新
        try
        {
            using var httpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
            var response = await httpClient.GetAsync(_updateCheckUrl);

            if (response.IsSuccessStatusCode)
            {
                var json = await response.Content.ReadAsStringAsync();
                // 后续阶段：解析远端版本信息并比较
                // var remoteInfo = JsonSerializer.Deserialize<VersionResponse>(json);
                info.LatestVersion = _currentVersion;
                info.UpdateAvailable = false;
            }
        }
        catch
        {
            info.CheckFailed = true;
            info.ErrorMessage = "无法连接到更新服务器";
        }

        return info;
    }

    /// <summary>
    /// 比较两个版本号
    /// </summary>
    /// <param name="version1">版本1</param>
    /// <param name="version2">版本2</param>
    /// <returns>版本1 > 版本2 返回正数，相等返回 0，小于返回负数</returns>
    public static int CompareVersions(string version1, string version2)
    {
        try
        {
            var v1 = new Version(version1);
            var v2 = new Version(version2);
            return v1.CompareTo(v2);
        }
        catch
        {
            // 版本号格式不正确时回退为字符串比较
            return string.Compare(version1, version2, StringComparison.OrdinalIgnoreCase);
        }
    }
}
