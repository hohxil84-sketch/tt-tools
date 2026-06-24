using System.Globalization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Input;
using System.Windows.Media;
using TTTools.PdfImageConvert.ViewModels;

namespace TTTools.PdfImageConvert.Views;

/// <summary>
/// PDF/图片互转视图
/// 支持文件拖拽导入，DataContext 绑定到 PdfImageConvertViewModel。
/// </summary>
public partial class PdfImageConvertView : UserControl
{
    private PdfImageConvertViewModel? _viewModel;

    public PdfImageConvertView()
    {
        InitializeComponent();

        // 启用拖拽支持
        AllowDrop = true;

        // 通过 DataContextChanged 获取 ViewModel 引用
        DataContextChanged += OnDataContextChanged;
    }

    /// <summary>
    /// DataContext 变更时更新 ViewModel 引用。
    /// </summary>
    private void OnDataContextChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        _viewModel = e.NewValue as PdfImageConvertViewModel;
    }

    /// <summary>
    /// 拖拽进入窗口，检查是否为文件。
    /// </summary>
    protected override void OnDragEnter(DragEventArgs e)
    {
        base.OnDragEnter(e);

        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            e.Effects = DragDropEffects.Copy;
            e.Handled = true;
        }
        else
        {
            e.Effects = DragDropEffects.None;
        }
    }

    /// <summary>
    /// 拖拽悬停在窗口上。
    /// </summary>
    protected override void OnDragOver(DragEventArgs e)
    {
        base.OnDragOver(e);

        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            e.Effects = DragDropEffects.Copy;
            e.Handled = true;
        }
        else
        {
            e.Effects = DragDropEffects.None;
        }
    }

    /// <summary>
    /// 文件拖放完成，将文件路径传递给 ViewModel 处理。
    /// </summary>
    protected override void OnDrop(DragEventArgs e)
    {
        base.OnDrop(e);

        if (e.Data.GetDataPresent(DataFormats.FileDrop) &&
            e.Data.GetData(DataFormats.FileDrop) is string[] files &&
            files.Length > 0)
        {
            _viewModel?.ProcessDroppedFiles(files);
            e.Handled = true;
        }
    }
}

/// <summary>
/// 布尔到颜色转换器（服务可用=绿色，不可用=红色）
/// </summary>
public class BoolToColorConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is bool b && b
            ? new SolidColorBrush(Color.FromRgb(0x16, 0xA3, 0x4A))
            : new SolidColorBrush(Color.FromRgb(0xDC, 0x26, 0x26));
    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

/// <summary>
/// 布尔到成功/失败文字转换器
/// </summary>
public class BoolToSuccessTextConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is bool b && b ? "成功" : "失败";
    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

/// <summary>
/// 布尔到成功/失败颜色转换器
/// </summary>
public class BoolToSuccessColorConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is bool b && b
            ? new SolidColorBrush(Color.FromRgb(0x16, 0xA3, 0x4A))
            : new SolidColorBrush(Color.FromRgb(0xDC, 0x26, 0x26));
    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
