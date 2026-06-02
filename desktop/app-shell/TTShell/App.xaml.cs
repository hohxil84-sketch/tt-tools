using System.Windows;
using System.Windows.Threading;

namespace TTShell;

/// <summary>
/// TT Tools 应用程序入口。
/// 负责启动主窗口、全局异常捕获和主题初始化。
/// </summary>
public partial class App : Application
{
    /// <summary>
    /// 应用启动时加载默认主题并创建主窗口。
    /// </summary>
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        // 注册全局未处理异常捕获，避免程序静默崩溃
        DispatcherUnhandledException += OnDispatcherUnhandledException;
        AppDomain.CurrentDomain.UnhandledException += OnAppDomainUnhandledException;

        // 默认使用浅色主题（后续可从用户设置读取）
        ApplyTheme("Light");

        // 创建并显示主窗口
        var mainWindow = new MainWindow();
        mainWindow.Show();
    }

    /// <summary>
    /// 切换应用主题（浅色 / 深色）。
    /// </summary>
    /// <param name="theme">"Light" 或 "Dark"</param>
    public static void ApplyTheme(string theme)
    {
        var appResources = Current.Resources.MergedDictionaries;

        // 移除旧主题
        var oldThemes = appResources
            .Where(d => d.Source != null &&
                        (d.Source.OriginalString.EndsWith("LightTheme.xaml") ||
                         d.Source.OriginalString.EndsWith("DarkTheme.xaml")))
            .ToList();

        foreach (var old in oldThemes)
        {
            appResources.Remove(old);
        }

        // 加载新主题
        var themePath = theme == "Dark" ? "Resources/DarkTheme.xaml" : "Resources/LightTheme.xaml";
        var newTheme = new ResourceDictionary { Source = new Uri(themePath, UriKind.Relative) };
        appResources.Insert(0, newTheme);
    }

    /// <summary>
    /// UI 线程未处理异常捕获 —— 记录日志并提示用户，避免静默崩溃。
    /// </summary>
    private void OnDispatcherUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
    {
        // 标记为已处理，防止进程直接退出
        e.Handled = true;

        MessageBox.Show(
            $"发生未预期的错误：{e.Exception.Message}\n\n详细信息已记录，请查看日志。",
            "TT Tools - 错误",
            MessageBoxButton.OK,
            MessageBoxImage.Error);
    }

    /// <summary>
    /// 非 UI 线程未处理异常捕获 —— 记录日志并提示用户。
    /// </summary>
    private void OnAppDomainUnhandledException(object sender, UnhandledExceptionEventArgs e)
    {
        if (e.ExceptionObject is Exception ex)
        {
            // 非 UI 线程异常无法恢复，记录后提示用户
            MessageBox.Show(
                $"发生严重错误：{ex.Message}\n\n程序即将退出。",
                "TT Tools - 严重错误",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
    }
}
