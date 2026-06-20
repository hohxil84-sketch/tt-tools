using TTTools.ExportSettings.Models;

namespace TTTools.ExportSettings.Tests.Models;

/// <summary>
/// UpdateInfo 模型单元测试
/// </summary>
public class UpdateInfoTests
{
    [Fact]
    public void UpdateInfo_DefaultValues_AreCorrect()
    {
        var info = new UpdateInfo();

        Assert.Equal("0.1.0", info.CurrentVersion);
        Assert.Null(info.LatestVersion);
        Assert.False(info.UpdateAvailable);
        Assert.Null(info.ReleaseNotesUrl);
        Assert.Null(info.DownloadUrl);
        Assert.Null(info.LastCheckTime);
        Assert.False(info.CheckFailed);
        Assert.Null(info.ErrorMessage);
    }

    [Fact]
    public void CheckStatusText_NotChecked_ReturnsCorrectMessage()
    {
        var info = new UpdateInfo();
        Assert.Equal("尚未检查", info.CheckStatusText);
    }

    [Fact]
    public void CheckStatusText_UpdateAvailable_ReturnsCorrectMessage()
    {
        var info = new UpdateInfo
        {
            LatestVersion = "0.2.0",
            UpdateAvailable = true,
            LastCheckTime = DateTime.Now
        };
        Assert.Equal("有新版本可用：0.2.0", info.CheckStatusText);
    }

    [Fact]
    public void CheckStatusText_UpToDate_ReturnsCorrectMessage()
    {
        var info = new UpdateInfo
        {
            LatestVersion = "0.1.0",
            UpdateAvailable = false,
            LastCheckTime = DateTime.Now
        };
        Assert.Equal("已是最新版本", info.CheckStatusText);
    }

    [Fact]
    public void CheckStatusText_CheckFailed_ReturnsCorrectMessage()
    {
        var info = new UpdateInfo
        {
            CheckFailed = true,
            ErrorMessage = "网络错误"
        };
        Assert.Equal("检查失败", info.CheckStatusText);
    }

    [Fact]
    public void LastCheckTimeFormatted_NotChecked_ReturnsDash()
    {
        var info = new UpdateInfo();
        Assert.Equal("--", info.LastCheckTimeFormatted);
    }

    [Fact]
    public void LastCheckTimeFormatted_AfterCheck_ReturnsFormattedTime()
    {
        var checkTime = new DateTime(2026, 6, 20, 14, 30, 45);
        var info = new UpdateInfo { LastCheckTime = checkTime };
        Assert.Equal("2026-06-20 14:30:45", info.LastCheckTimeFormatted);
    }
}
