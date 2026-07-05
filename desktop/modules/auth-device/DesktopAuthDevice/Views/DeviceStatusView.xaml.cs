using System.Windows;
using System.Windows.Controls;
using TTTools.AuthDevice.ViewModels;

namespace TTTools.AuthDevice.Views;

/// <summary>
/// DeviceStatusView.xaml 的代码后置。
/// 处理设备 ID 复制按钮点击事件。
/// </summary>
public partial class DeviceStatusView : UserControl
{
    public DeviceStatusView()
    {
        InitializeComponent();
    }

    /// <summary>
    /// 复制完整设备 ID 到剪贴板。
    /// 点击后按钮短暂显示"已复制"反馈。
    /// </summary>
    private void OnCopyDeviceIdClick(object sender, RoutedEventArgs e)
    {
        if (DataContext is DeviceStatusViewModel vm && !string.IsNullOrEmpty(vm.DeviceId))
        {
            Clipboard.SetText(vm.DeviceId);

            // 复制成功后按钮短暂反馈"已复制"
            if (sender is Button btn)
            {
                var original = btn.Content;
                btn.Content = "已复制 ✓";
                // 1.5 秒后恢复原文
                _ = System.Threading.Tasks.Task.Delay(1500).ContinueWith(_ =>
                {
                    Dispatcher.Invoke(() => btn.Content = original);
                });
            }
        }
    }
}
