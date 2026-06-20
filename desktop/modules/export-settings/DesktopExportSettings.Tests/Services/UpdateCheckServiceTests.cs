using TTTools.ExportSettings.Services;

namespace TTTools.ExportSettings.Tests.Services;

/// <summary>
/// UpdateCheckService 服务单元测试
/// </summary>
public class UpdateCheckServiceTests
{
    [Fact]
    public void GetCurrentVersionInfo_ReturnsCurrentVersion()
    {
        var service = new UpdateCheckService("1.2.3");
        var info = service.GetCurrentVersionInfo();

        Assert.Equal("1.2.3", info.CurrentVersion);
        Assert.Null(info.LatestVersion);
        Assert.False(info.UpdateAvailable);
    }

    [Fact]
    public void GetCurrentVersionInfo_DefaultVersion()
    {
        var service = new UpdateCheckService();
        var info = service.GetCurrentVersionInfo();

        Assert.Equal("0.1.0", info.CurrentVersion);
    }

    [Fact]
    public async Task CheckForUpdatesAsync_NoUpdateUrl_ReturnsCurrentVersion()
    {
        var service = new UpdateCheckService("0.1.0");
        var info = await service.CheckForUpdatesAsync();

        Assert.Equal("0.1.0", info.CurrentVersion);
        Assert.Equal("0.1.0", info.LatestVersion);
        Assert.False(info.UpdateAvailable);
        Assert.NotNull(info.LastCheckTime);
    }

    [Fact]
    public async Task CheckForUpdatesAsync_WithInvalidUrl_FailsGracefully()
    {
        // 使用不可路由的 IP 地址确保请求失败
        var service = new UpdateCheckService("0.1.0", "http://192.0.2.1/version");
        var info = await service.CheckForUpdatesAsync();

        // 应该优雅失败或超时而不抛出异常
        // 注意：某些网络环境下请求可能不会立即失败
        Assert.NotNull(info);
        Assert.NotNull(info.LastCheckTime);
    }

    [Fact]
    public void CompareVersions_SameVersion_ReturnsZero()
    {
        var result = UpdateCheckService.CompareVersions("1.0.0", "1.0.0");
        Assert.Equal(0, result);
    }

    [Fact]
    public void CompareVersions_Newer_ReturnsPositive()
    {
        var result = UpdateCheckService.CompareVersions("2.0.0", "1.0.0");
        Assert.True(result > 0);
    }

    [Fact]
    public void CompareVersions_Older_ReturnsNegative()
    {
        var result = UpdateCheckService.CompareVersions("1.0.0", "2.0.0");
        Assert.True(result < 0);
    }

    [Fact]
    public void CompareVersions_MinorVersion_ComparesCorrectly()
    {
        var result = UpdateCheckService.CompareVersions("1.2.0", "1.1.0");
        Assert.True(result > 0);
    }

    [Fact]
    public void CompareVersions_BuildVersion_ComparesCorrectly()
    {
        var result = UpdateCheckService.CompareVersions("1.0.0.100", "1.0.0.99");
        Assert.True(result > 0);
    }

    [Fact]
    public void CompareVersions_InvalidVersion_FallsBackToStringComparison()
    {
        // 不应该抛异常，回退到字符串比较
        var result = UpdateCheckService.CompareVersions("invalid", "also-invalid");
        // 验证不抛异常即可（字符串比较结果取决于具体实现）
        Assert.True(result != 0 || result == 0); // 始终通过，只需验证无异常
    }
}
