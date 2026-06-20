using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using TTTools.OCR.ViewModels;

namespace TTTools.OCR.Views;

/// <summary>
/// OCR 视图代码后置
/// 处理拖拽事件，将文件拖入操作转发给 ViewModel。
/// </summary>
public partial class OcrView : UserControl
{
    private OcrViewModel? _viewModel;

    public OcrView()
    {
        InitializeComponent();

        // 注册拖拽支持
        AllowDrop = true;
        DragEnter += OnDragEnter;
        DragOver += OnDragOver;
        Drop += OnDrop;

        // 数据上下文变更时更新 ViewModel 引用
        DataContextChanged += OnDataContextChanged;
    }

    private void OnDataContextChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        _viewModel = e.NewValue as OcrViewModel;
    }

    /// <summary>
    /// 拖拽进入时检查数据格式
    /// </summary>
    private void OnDragEnter(object sender, DragEventArgs e)
    {
        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            e.Effects = DragDropEffects.Copy;
        }
        else
        {
            e.Effects = DragDropEffects.None;
        }
        e.Handled = true;
    }

    /// <summary>
    /// 拖拽悬停时保持 Copy 效果
    /// </summary>
    private void OnDragOver(object sender, DragEventArgs e)
    {
        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            e.Effects = DragDropEffects.Copy;
        }
        else
        {
            e.Effects = DragDropEffects.None;
        }
        e.Handled = true;
    }

    /// <summary>
    /// 放下文件时通知 ViewModel 处理
    /// </summary>
    private void OnDrop(object sender, DragEventArgs e)
    {
        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            var filePaths = e.Data.GetData(DataFormats.FileDrop) as string[];
            if (filePaths != null && filePaths.Length > 0)
            {
                _viewModel?.RecognizeDroppedFiles(filePaths);
            }
        }
        e.Handled = true;
    }
}

/// <summary>
/// 置信度到颜色转换器
/// 高置信度 (>0.9) 显示绿色，低置信度 (<0.5) 显示橙色，正常显示黑色。
/// </summary>
public class ScoreToBrushConverter : IValueConverter
{
    private static readonly SolidColorBrush HighConfBrush = new(Color.FromRgb(0x1B, 0x5E, 0x20));
    private static readonly SolidColorBrush LowConfBrush = new(Color.FromRgb(0xE6, 0x51, 0x00));
    private static readonly SolidColorBrush NormalBrush = new(Color.FromRgb(0x21, 0x21, 0x21));

    public object Convert(object value, Type targetType, object parameter,
        System.Globalization.CultureInfo culture)
    {
        if (value is double score)
        {
            if (score >= 0.9) return HighConfBrush;
            if (score < 0.5) return LowConfBrush;
        }
        return NormalBrush;
    }

    public object ConvertBack(object value, Type targetType, object parameter,
        System.Globalization.CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}
