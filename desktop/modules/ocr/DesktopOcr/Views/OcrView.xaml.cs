using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using TTTools.OCR.ViewModels;

namespace TTTools.OCR.Views;

/// <summary>
/// OCR 视图代码后置
/// 处理拖拽事件、缩略图点击、服务自动初始化。
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

        // 视图加载时自动初始化 OCR 服务
        Loaded += OnLoaded;
    }

    /// <summary>
    /// 视图加载完成后自动启动 OCR 引擎
    /// </summary>
    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        Loaded -= OnLoaded;
        if (_viewModel != null)
        {
            await System.Windows.Threading.Dispatcher.CurrentDispatcher.InvokeAsync(
                async () => await _viewModel.InitializeAsync());
        }
    }

    private void OnDataContextChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        _viewModel = e.NewValue as OcrViewModel;
    }

    /// <summary>
    /// 缩略图点击：用系统默认图片查看器打开原图
    /// </summary>
    private void OnThumbnailClick(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        if (sender is Border border && border.Tag is string filePath && File.Exists(filePath))
        {
            try
            {
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = filePath,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    $"无法打开图片: {ex.Message}",
                    "打开失败",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning);
            }
        }
    }

    /// <summary>拖拽进入时检查数据格式</summary>
    private void OnDragEnter(object sender, DragEventArgs e)
    {
        e.Effects = e.Data.GetDataPresent(DataFormats.FileDrop) ? DragDropEffects.Copy : DragDropEffects.None;
        e.Handled = true;
    }

    /// <summary>拖拽悬停</summary>
    private void OnDragOver(object sender, DragEventArgs e)
    {
        e.Effects = e.Data.GetDataPresent(DataFormats.FileDrop) ? DragDropEffects.Copy : DragDropEffects.None;
        e.Handled = true;
    }

    /// <summary>放下文件时通知 ViewModel</summary>
    private void OnDrop(object sender, DragEventArgs e)
    {
        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            var filePaths = e.Data.GetData(DataFormats.FileDrop) as string[];
            if (filePaths != null && filePaths.Length > 0)
                _viewModel?.RecognizeDroppedFiles(filePaths);
        }
        e.Handled = true;
    }
}

/// <summary>
/// 置信度到颜色转换器
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

/// <summary>
/// 文件路径到缩略图的转换器（带缓存）
/// </summary>
public class FilePathToThumbnailConverter : IValueConverter
{
    private static readonly Dictionary<string, BitmapImage?> ThumbnailCache = new();

    public object? Convert(object value, Type targetType, object parameter,
        System.Globalization.CultureInfo culture)
    {
        if (value is not string filePath || !File.Exists(filePath))
            return null;

        if (ThumbnailCache.TryGetValue(filePath, out var cached))
            return cached;

        try
        {
            var bitmap = new BitmapImage();
            bitmap.BeginInit();
            bitmap.UriSource = new Uri(filePath);
            bitmap.DecodePixelWidth = 64;
            bitmap.DecodePixelHeight = 64;
            bitmap.CacheOption = BitmapCacheOption.OnLoad;
            bitmap.CreateOptions = BitmapCreateOptions.IgnoreImageCache;
            bitmap.EndInit();
            bitmap.Freeze();

            ThumbnailCache[filePath] = bitmap;
            return bitmap;
        }
        catch
        {
            ThumbnailCache[filePath] = null;
            return null;
        }
    }

    public object ConvertBack(object value, Type targetType, object parameter,
        System.Globalization.CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}
