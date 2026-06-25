using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.FileSystem;
using TTShared.Settings;
using TTShell.Views;
using TTTools.FileWorkbench.Views;
using TTTools.OCR.Views;
using TTTools.PreflightCheck.Views;
using TTTools.AiCopyClient.Views;
using TTTools.AiRenderClient.Views;
using TTTools.ResizeImage.Views;
using TTTools.FormatConvert.Views;
using TTTools.PdfImageConvert.Views;
using TTTools.IdPhoto.Views;
using TTTools.RemoveBg.Views;
using TTTools.AuthDevice.Views;
using TTTools.AuthDevice.ViewModels;
using TTTools.ExportSettings.Views;

namespace TTShell;

/// <summary>
/// TT Tools 主窗口。
/// 负责导航切换、主题切换、窗口状态管理和模块入口装配。
/// 全部模块使用 ViewModel 默认构造函数，后续统一 DI 机制就位后替换为带参构造函数。
/// </summary>
public partial class MainWindow : Window
{
    private Button? _currentNavButton;
    private string _currentTheme = "Light";

    /// <summary>共享的认证状态，所有模块通过此实例感知登录/登出</summary>
    private readonly AuthState _authState = AuthState.Shared;
    /// <summary>共享的云端 API 客户端</summary>
    private readonly CloudApiClient _apiClient;

    public MainWindow()
    {
        InitializeComponent();

        // 使用共享 AuthState 初始化 API 客户端（后续各模块共用）
        _apiClient = new CloudApiClient(AppSettings.Instance.ServerUrl, _authState);

        // 订阅认证状态变化，更新状态栏用户名
        _authState.LoggedIn += OnUserLoggedIn;
        _authState.LoggedOut += OnUserLoggedOut;

        SetNavButtonSelected(NavHome);
    }

    /// <summary>登录成功后自动跳转到首页并更新状态栏和右上角用户按钮</summary>
    private void OnUserLoggedIn(object? sender, EventArgs e)
    {
        Dispatcher.Invoke(() =>
        {
            StatusText.Text = $"当前：首页 | 用户：{_authState.User.DisplayName ?? _authState.User.Account}";
            UserEntryButton.Content = $"👤 {_authState.User.DisplayName ?? _authState.User.Account}";
            // 登录成功后自动跳转到首页
            MainContent.Content = new HomePage();
            SetNavButtonSelected(NavHome);
        });
    }

    /// <summary>登出后清除状态栏用户信息和右上角用户按钮</summary>
    private void OnUserLoggedOut(object? sender, EventArgs e)
    {
        Dispatcher.Invoke(() =>
        {
            StatusText.Text = "就绪（未登录）";
            UserEntryButton.Content = "👤 登录";
        });
    }

    /// <summary>
    /// 右上角用户按钮点击处理。
    /// 未登录时跳转登录页，已登录时跳转设备状态页。
    /// </summary>
    private void OnUserEntryClick(object sender, RoutedEventArgs e)
    {
        if (_authState.IsLoggedIn)
        {
            // 已登录 -> 显示设备绑定状态（含退出登录按钮）
            MainContent.Content = new DeviceStatusView { DataContext = new DeviceStatusViewModel(_authState, _apiClient) };
            StatusText.Text = "当前：设备状态";
            _currentNavButton = null; // 取消侧边栏高亮
        }
        else
        {
            // 未登录 -> 跳转登录页
            MainContent.Content = new LoginView { DataContext = new LoginViewModel(_authState, _apiClient) };
            StatusText.Text = "当前：登录管理";
            _currentNavButton = null;
        }
    }

    /// <summary>
    /// 导航按钮点击处理 —— 切换主内容区显示的页面。
    /// </summary>
    private void OnNavigationClick(object sender, RoutedEventArgs e)
    {
        if (sender is not Button button) return;
        SetNavButtonSelected(button);

        var tag = button.Tag?.ToString();
        MainContent.Content = tag switch
        {
            "Home"            => new HomePage(),

            // 文件 / 印前
            "FileWorkbench"   => new WorkbenchView { DataContext = new TTTools.FileWorkbench.ViewModels.WorkbenchViewModel() },
            "Ocr"             => new OcrView { DataContext = new TTTools.OCR.ViewModels.OcrViewModel() },
            "Preflight"       => new PreflightCheckView { DataContext = new TTTools.PreflightCheck.ViewModels.PreflightCheckViewModel() },

            // AI 工具
            "AiCopy"          => new AiCopyView { DataContext = new TTTools.AiCopyClient.ViewModels.AiCopyViewModel(_apiClient, _authState) },
            "AiRender"        => new AiRenderView { DataContext = new TTTools.AiRenderClient.ViewModels.AiRenderViewModel(_apiClient, _authState) },

            // 图片处理
            "ResizeImage"     => new ResizeImageView { DataContext = new TTTools.ResizeImage.ViewModels.ResizeImageViewModel(new TTTools.ResizeImage.Services.ResizeImageService(), _authState, new FileSystemService()) },
            "FormatConvert"   => new FormatConvertView { DataContext = new TTTools.FormatConvert.ViewModels.FormatConvertViewModel() },
            "PdfImageConvert" => new PdfImageConvertView { DataContext = new TTTools.PdfImageConvert.ViewModels.PdfImageConvertViewModel(new TTTools.PdfImageConvert.Services.PdfImageConvertService(), _authState, new FileSystemService()) },
            "IdPhoto"         => new IdPhotoView { DataContext = new TTTools.IdPhoto.ViewModels.IdPhotoViewModel() },
            "RemoveBg"        => new RemoveBgView { DataContext = new TTTools.RemoveBg.ViewModels.RemoveBgViewModel() },

            // 系统
            "Login"           => new LoginView { DataContext = new LoginViewModel(_authState, _apiClient) },

            // 导出 / 设置
            "Export"          => new ExportView(),
            "LogViewer"       => new LogViewerView { DataContext = new TTTools.ExportSettings.ViewModels.LogViewerViewModel() },
            "Settings"        => new SettingsView { DataContext = new TTTools.ExportSettings.ViewModels.SettingsViewModel() },

            _                 => new HomePage()
        };

        StatusText.Text = $"当前：{GetPageName(tag)}";
    }

    /// <summary>
    /// 根据导航标签返回中文页面名。
    /// </summary>
    private static string GetPageName(string? tag) => tag switch
    {
        "Home"            => "首页",
        "FileWorkbench"   => "文件工作台",
        "Ocr"             => "OCR 文字识别",
        "Preflight"       => "印前检查",
        "AiCopy"          => "AI 文案生成",
        "AiRender"        => "效果图生成",
        "ResizeImage"     => "图片改尺寸",
        "FormatConvert"   => "格式转换",
        "PdfImageConvert" => "PDF/图片互转",
        "IdPhoto"         => "证件照换底色",
        "RemoveBg"        => "智能抠图",
        "Login"           => "登录管理",
        "Export"          => "导出",
        "LogViewer"       => "日志查看",
        "Settings"        => "设置",
        _                 => "首页"
    };

    private void SetNavButtonSelected(Button button)
    {
        if (_currentNavButton != null)
            _currentNavButton.Style = (Style)FindResource("NavButtonStyle");
        button.Style = (Style)FindResource("NavButtonSelectedStyle");
        _currentNavButton = button;
    }

    private void OnThemeToggle(object sender, RoutedEventArgs e)
    {
        _currentTheme = _currentTheme == "Light" ? "Dark" : "Light";
        App.ApplyTheme(_currentTheme);
        ThemeToggleButton.Content = _currentTheme == "Dark" ? "☀️" : "🌙";
    }

    private void OnTitleBarMouseDown(object sender, MouseButtonEventArgs e)
    {
        if (e.LeftButton == MouseButtonState.Pressed)
            DragMove();
    }
}
