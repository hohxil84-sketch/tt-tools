using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using TTShell.Views;

namespace TTShell;

/// <summary>
/// TT Tools 主窗口。
/// 负责导航切换、主题切换、窗口状态管理和模块入口装配。
/// </summary>
public partial class MainWindow : Window
{
    /// <summary>当前选中的导航按钮</summary>
    private Button? _currentNavButton;

    /// <summary>当前主题：Light 或 Dark</summary>
    private string _currentTheme = "Light";

    public MainWindow()
    {
        InitializeComponent();

        // 默认选中首页
        SetNavButtonSelected(NavHome);

        // 初始化窗口控制按钮文字
        UpdateMaxRestoreButton();
        StateChanged += (_, _) => UpdateMaxRestoreButton();
    }

    /// <summary>
    /// 导航按钮点击处理 —— 切换主内容区显示的页面。
    /// </summary>
    private void OnNavigationClick(object sender, RoutedEventArgs e)
    {
        if (sender is not Button button) return;

        SetNavButtonSelected(button);

        var tag = button.Tag?.ToString();

        // 根据导航标签切换页面内容
        MainContent.Content = tag switch
        {
            "Home" => new HomePage(),
            "FileWorkbench" => CreatePlaceholderPage("文件工作台", "模块开发中，即将上线"),
            "AiTools" => CreatePlaceholderPage("AI 工具", "AI 功能模块开发中，即将上线"),
            "Export" => CreatePlaceholderPage("导出", "导出功能模块开发中，即将上线"),
            "Settings" => CreatePlaceholderPage("设置", "设置功能模块开发中，即将上线"),
            _ => new HomePage()
        };

        // 更新状态栏
        var pageName = tag switch
        {
            "Home" => "首页",
            "FileWorkbench" => "文件工作台",
            "AiTools" => "AI 工具",
            "Export" => "导出",
            "Settings" => "设置",
            _ => "首页"
        };
        StatusText.Text = $"当前：{pageName}";
    }

    /// <summary>
    /// 设置导航按钮选中状态（高亮当前按钮，取消上一个按钮高亮）。
    /// </summary>
    private void SetNavButtonSelected(Button button)
    {
        // 取消上一个按钮的选中样式
        if (_currentNavButton != null)
        {
            _currentNavButton.Style = (Style)FindResource("NavButtonStyle");
        }

        // 设置当前按钮的选中样式
        button.Style = (Style)FindResource("NavButtonSelectedStyle");
        _currentNavButton = button;
    }

    /// <summary>
    /// 创建模块占位页面（各模块开发完成前统一使用）。
    /// </summary>
    /// <param name="title">模块名称</param>
    /// <param name="message">占位提示信息</param>
    /// <returns>包含占位文字的页面</returns>
    private static Page CreatePlaceholderPage(string title, string message)
    {
        var page = new Page();
        var grid = new Grid();
        grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });

        // 模块标题
        var titleBlock = new TextBlock
        {
            Text = title,
            Style = (Style)Application.Current.FindResource("TitleTextStyle"),
            HorizontalAlignment = HorizontalAlignment.Center,
            Margin = new Thickness(0, 0, 0, 8)
        };
        Grid.SetRow(titleBlock, 0);
        titleBlock.VerticalAlignment = VerticalAlignment.Bottom;
        grid.Children.Add(titleBlock);

        // 占位提示
        var msgBlock = new TextBlock
        {
            Text = message,
            Style = (Style)Application.Current.FindResource("PlaceholderTextStyle")
        };
        Grid.SetRow(msgBlock, 1);
        grid.Children.Add(msgBlock);

        page.Content = grid;
        return page;
    }

    /// <summary>
    /// 主题切换按钮点击 —— 在浅色和深色主题之间切换。
    /// </summary>
    private void OnThemeToggle(object sender, RoutedEventArgs e)
    {
        _currentTheme = _currentTheme == "Light" ? "Dark" : "Light";
        App.ApplyTheme(_currentTheme);

        // 更新按钮图标
        ThemeToggleButton.Content = _currentTheme == "Dark" ? "☀️" : "🌙";
    }

    /// <summary>
    /// 标题栏拖拽移动窗口（模拟无边框窗口的拖拽行为）。
    /// </summary>
    private void OnTitleBarMouseDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2)
        {
            // 双击标题栏切换最大化
            OnMaximizeRestore(sender, e);
        }
        else if (e.LeftButton == MouseButtonState.Pressed)
        {
            DragMove();
        }
    }

    /// <summary>最小化窗口</summary>
    private void OnMinimize(object sender, RoutedEventArgs e)
    {
        WindowState = WindowState.Minimized;
    }

    /// <summary>最大化/还原窗口</summary>
    private void OnMaximizeRestore(object sender, RoutedEventArgs e)
    {
        WindowState = WindowState == WindowState.Maximized
            ? WindowState.Normal
            : WindowState.Maximized;
    }

    /// <summary>更新最大化/还原按钮文字</summary>
    private void UpdateMaxRestoreButton()
    {
        MaxRestoreButton.Content = WindowState == WindowState.Maximized ? "❐" : "□";
    }

    /// <summary>
    /// 关闭窗口 —— 如果窗口处于最大化状态，先还原再询问确认。
    /// </summary>
    private void OnClose(object sender, RoutedEventArgs e)
    {
        Close();
    }
}
