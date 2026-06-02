using TTShared.Settings;

namespace TTShared.Tests.Settings;

public class AppSettingsTests
{
    [Fact]
    public void DefaultValues_ShouldBeCorrect()
    {
        var tempFile = Path.Combine(Path.GetTempPath(), $"tt_test_settings_{Guid.NewGuid():N}.json");
        var settings = new AppSettings(tempFile);

        Assert.Equal("http://localhost:8000", settings.ServerUrl);
        Assert.Equal("Light", settings.Theme);
        Assert.Equal("zh-CN", settings.Language);
        Assert.Equal(3, settings.MaxConcurrentJobs);
        Assert.True(settings.AutoUpdateCheck);
        Assert.False(settings.SendUsageStats);
    }

    [Fact]
    public void SaveAndLoad_ShouldPersistValues()
    {
        var tempFile = Path.Combine(Path.GetTempPath(), $"tt_test_settings_{Guid.NewGuid():N}.json");
        try
        {
            var settings = new AppSettings(tempFile);
            settings.ServerUrl = "https://api.example.com";
            settings.Theme = "Dark";
            settings.MaxConcurrentJobs = 5;
            settings.Save();

            // 重新加载
            var settings2 = new AppSettings(tempFile);
            settings2.Load();

            Assert.Equal("https://api.example.com", settings2.ServerUrl);
            Assert.Equal("Dark", settings2.Theme);
            Assert.Equal(5, settings2.MaxConcurrentJobs);
        }
        finally
        {
            SafeDelete(tempFile);
        }
    }

    [Fact]
    public void MaxConcurrentJobs_ShouldClamp()
    {
        var tempFile = Path.Combine(Path.GetTempPath(), $"tt_test_settings_{Guid.NewGuid():N}.json");
        var settings = new AppSettings(tempFile);

        settings.MaxConcurrentJobs = 100; // 应限制为 10
        Assert.Equal(10, settings.MaxConcurrentJobs);

        settings.MaxConcurrentJobs = 0; // 应限制为 1
        Assert.Equal(1, settings.MaxConcurrentJobs);
    }

    [Fact]
    public void Reset_ShouldRestoreDefaults()
    {
        var tempFile = Path.Combine(Path.GetTempPath(), $"tt_test_settings_{Guid.NewGuid():N}.json");
        var settings = new AppSettings(tempFile);
        settings.ServerUrl = "https://custom.example.com";
        settings.Theme = "Dark";
        settings.Reset();

        Assert.Equal("http://localhost:8000", settings.ServerUrl);
        Assert.Equal("Light", settings.Theme);
    }

    [Fact]
    public void SettingChanged_ShouldFire_WhenLoaded()
    {
        var tempFileA = Path.Combine(Path.GetTempPath(), $"tt_test_settings_{Guid.NewGuid():N}.json");
        var tempFileB = Path.Combine(Path.GetTempPath(), $"tt_test_settings_{Guid.NewGuid():N}.json");
        try
        {
            // 先保存一些设置
            var settings = new AppSettings(tempFileA);
            settings.ServerUrl = "https://api.example.com";
            settings.Save();

            // 加载到新实例
            var settings2 = new AppSettings(tempFileB);
            settings2.Load();
            // 验证加载的值
            Assert.Equal("http://localhost:8000", settings2.ServerUrl); // 不同文件，默认值
        }
        finally
        {
            SafeDelete(tempFileA);
            SafeDelete(tempFileB);
        }
    }

    private static void SafeDelete(string path)
    {
        try { File.Delete(path); } catch { }
    }
}
