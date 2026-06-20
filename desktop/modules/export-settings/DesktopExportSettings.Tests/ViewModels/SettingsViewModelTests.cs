using TTTools.ExportSettings.ViewModels;
using TTShared.Settings;

namespace TTTools.ExportSettings.Tests.ViewModels;

/// <summary>
/// SettingsViewModel 单元测试
/// </summary>
public class SettingsViewModelTests : IDisposable
{
    private readonly string _testSettingsPath;
    private readonly AppSettings _settings;
    private readonly SettingsViewModel _vm;

    public SettingsViewModelTests()
    {
        _testSettingsPath = Path.Combine(Path.GetTempPath(),
            $"TTTools_SettingsTest_{Guid.NewGuid():N}", "app-settings.json");
        _settings = new AppSettings(_testSettingsPath);
        _settings.Load();
        _vm = new SettingsViewModel(_settings);
    }

    [Fact]
    public void Constructor_LoadsDefaultValues()
    {
        Assert.Equal("http://localhost:8000", _vm.ServerUrl);
        Assert.Equal("Light", _vm.Theme);
        Assert.Equal("zh-CN", _vm.Language);
        Assert.Null(_vm.PythonPath);
        Assert.Equal(3, _vm.MaxConcurrentJobs);
        Assert.True(_vm.AutoUpdateCheck);
        Assert.False(_vm.SendUsageStats);
        Assert.False(_vm.IsDirty);
    }

    [Fact]
    public void ModifyProperty_MarksIsDirty()
    {
        _vm.ServerUrl = "http://example.com:8000";

        Assert.True(_vm.IsDirty);
        Assert.Equal("http://example.com:8000", _vm.ServerUrl);
    }

    [Fact]
    public void Save_SavesSettingsAndClearsDirty()
    {
        _vm.ServerUrl = "http://example.com:8000";
        _vm.Theme = "Dark";
        Assert.True(_vm.IsDirty);

        _vm.SaveCommand.Execute(null);

        Assert.False(_vm.IsDirty);
        Assert.Equal("设置已保存", _vm.StatusMessage);

        // 验证设置已持久化
        var reloadedSettings = new AppSettings(_testSettingsPath);
        reloadedSettings.Load();
        Assert.Equal("http://example.com:8000", reloadedSettings.ServerUrl);
        Assert.Equal("Dark", reloadedSettings.Theme);
    }

    [Fact]
    public void Reset_ResetsAllValuesToDefault()
    {
        _vm.ServerUrl = "http://example.com:8000";
        _vm.Theme = "Dark";
        _vm.Language = "en-US";
        _vm.PythonPath = "D:\\python\\python.exe";
        _vm.MaxConcurrentJobs = 5;
        _vm.AutoUpdateCheck = false;
        _vm.SendUsageStats = true;

        _vm.ResetCommand.Execute(null);

        Assert.Equal("http://localhost:8000", _vm.ServerUrl);
        Assert.Equal("Light", _vm.Theme);
        Assert.Equal("zh-CN", _vm.Language);
        Assert.Null(_vm.PythonPath);
        Assert.Equal(3, _vm.MaxConcurrentJobs);
        Assert.True(_vm.AutoUpdateCheck);
        Assert.False(_vm.SendUsageStats);
        Assert.False(_vm.IsDirty);
        Assert.Equal("设置已重置为默认值", _vm.StatusMessage);
    }

    [Fact]
    public void ThemeOptions_ContainsLightAndDark()
    {
        Assert.Equal(2, _vm.ThemeOptions.Count);
        Assert.Contains("Light", _vm.ThemeOptions);
        Assert.Contains("Dark", _vm.ThemeOptions);
    }

    [Fact]
    public void LanguageOptions_ContainsZhCNAndEnUS()
    {
        Assert.Equal(2, _vm.LanguageOptions.Count);
        Assert.Contains("zh-CN", _vm.LanguageOptions);
        Assert.Contains("en-US", _vm.LanguageOptions);
    }

    [Fact]
    public void SetPythonPath_UpdatesPathAndMarksDirty()
    {
        _vm.SetPythonPath("D:\\python\\python.exe");

        Assert.Equal("D:\\python\\python.exe", _vm.PythonPath);
        Assert.True(_vm.IsDirty);
    }

    [Fact]
    public void MaxConcurrentJobs_Clamped_ByAppSettings()
    {
        // AppSettings 自动 clamp 1-10
        _vm.MaxConcurrentJobs = 0;  // 会被 clamp 到 1

        Assert.Equal(1, _settings.MaxConcurrentJobs);
    }

    public void Dispose()
    {
        try
        {
            var dir = Path.GetDirectoryName(_testSettingsPath);
            if (dir != null && Directory.Exists(dir))
                Directory.Delete(dir, recursive: true);
        }
        catch { }
    }
}
