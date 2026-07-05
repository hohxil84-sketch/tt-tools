using System.Windows;
using System.Windows.Controls;

namespace TTShell.Views;

/// <summary>
/// 首页 Dashboard —— 欢迎区 + 快捷入口 + 最近任务 + 算力 + 引擎状态。
/// 快捷入口卡片点击后通过 MainWindow 导航到对应模块。
/// </summary>
public partial class HomePage : UserControl
{
    public HomePage()
    {
        InitializeComponent();
    }

    /// <summary>
    /// 通过查找父窗口中的侧边栏按钮触发导航（复用 MainWindow.OnNavigationClick 中的 View/ViewModel 创建逻辑）。
    /// </summary>
    private void NavigateViaMainWindow(string buttonName)
    {
        if (Window.GetWindow(this) is MainWindow mainWindow)
        {
            if (mainWindow.FindName(buttonName) is Button navButton)
            {
                navButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            }
        }
    }

    private void OnQuickActionOcr(object sender, RoutedEventArgs e)
        => NavigateViaMainWindow("NavOcr");

    private void OnQuickActionResize(object sender, RoutedEventArgs e)
        => NavigateViaMainWindow("NavResizeImage");

    private void OnQuickActionIdPhoto(object sender, RoutedEventArgs e)
        => NavigateViaMainWindow("NavIdPhoto");

    private void OnQuickActionRemoveBg(object sender, RoutedEventArgs e)
        => NavigateViaMainWindow("NavRemoveBg");
}
