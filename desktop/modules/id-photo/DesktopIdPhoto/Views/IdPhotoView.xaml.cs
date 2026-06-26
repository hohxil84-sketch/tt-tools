using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using System.Globalization;
using TTTools.IdPhoto.Models;
using TTTools.IdPhoto.ViewModels;

namespace TTTools.IdPhoto.Views;

/// <summary>
/// 证件照换底色视图代码后置
/// 处理拖拽事件，将文件拖入操作转发给 ViewModel。
/// </summary>
public partial class IdPhotoView : UserControl
{
    private IdPhotoViewModel? _viewModel;

    public IdPhotoView()
    {
        InitializeComponent();

        // 注册拖拽支持
        AllowDrop = true;
        DragEnter += OnDragEnter;
        DragOver += OnDragOver;
        Drop += OnDrop;

        // 数据上下文变更时更新 ViewModel 引用
        DataContextChanged += OnDataContextChanged;

        // 视图加载完成后异步初始化证件照服务
        Loaded += OnLoaded;
    }

    /// <summary>
    /// 视图加载完成后调用 ViewModel 初始化，启动 worker 并加载规格/底色列表
    /// </summary>
    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        Loaded -= OnLoaded; // 只执行一次
        if (_viewModel != null)
        {
            await _viewModel.InitializeAsync();
        }
    }

    private void OnDataContextChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        _viewModel = e.NewValue as IdPhotoViewModel;
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
                _viewModel?.ProcessDroppedFile(filePaths);
            }
        }
        e.Handled = true;
    }
}

/// <summary>
/// BackgroundColorItem 到 SolidColorBrush 转换器
/// 将背景色数据模型转为 WPF 画刷用于 UI 色块展示。
/// </summary>
public class ColorItemToBrushConverter : IValueConverter
{
    /// <summary>单例</summary>
    public static readonly ColorItemToBrushConverter Instance = new();

    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is BackgroundColorItem colorItem)
        {
            return new SolidColorBrush(colorItem.ToMediaColor());
        }
        return new SolidColorBrush(Colors.Gray);
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// 底色选中状态比较转换器
/// 用于比较当前迭代的底色 Key 与 ViewModel 中选中的底色 Key 是否一致，
/// 从而决定色块是否高亮显示。
/// </summary>
public class SelectedColorEqualityConverter : IMultiValueConverter
{
    public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
    {
        if (values.Length < 2) return false;
        var currentKey = values[0] as string;
        var selectedKey = values[1] as string;

        if (string.IsNullOrEmpty(currentKey) || string.IsNullOrEmpty(selectedKey))
            return false;

        return currentKey == selectedKey;
    }

    public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}
