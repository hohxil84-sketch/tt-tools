using System.Globalization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Input;
using Microsoft.Win32;
using TTTools.FileWorkbench.Services;
using TTTools.FileWorkbench.ViewModels;

namespace TTTools.FileWorkbench.Views;

/// <summary>
/// 文件工作台主视图
/// 负责处理 UI 交互：拖拽导入、文件列表、预览展示、最近文件。
/// </summary>
public partial class WorkbenchView : UserControl
{
    private WorkbenchViewModel? _viewModel;

    /// <summary>
    /// 用于 XAML 绑定的颜色转换器：根据是否支持格式显示不同颜色
    /// </summary>
    public static readonly IValueConverter IsSupportedToColorConverter =
        new SupportedStatusToColorConverter();

    public WorkbenchView()
    {
        InitializeComponent();

        // 数据上下文在 Loaded 时设置，以支持设计时
        DataContextChanged += OnDataContextChanged;
        Loaded += OnLoaded;
    }

    /// <summary>
    /// 数据上下文变更时更新 ViewModel 引用
    /// </summary>
    private void OnDataContextChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        _viewModel = e.NewValue as WorkbenchViewModel;
    }

    /// <summary>
    /// 控件加载完成后初始化预览可见性绑定
    /// </summary>
    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (_viewModel == null) return;

        // 监听预览状态变更以更新预览面板显示
        _viewModel.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName == nameof(WorkbenchViewModel.HasPreview))
                UpdatePreviewVisibility();
            if (args.PropertyName == nameof(WorkbenchViewModel.IsPreviewImage))
                UpdatePreviewVisibility();
        };
    }

    // ==================== 文件拖拽事件处理 ====================

    /// <summary>
    /// 拖入文件列表区域时的处理 —— 高亮拖放区域
    /// </summary>
    private void OnFileListDragEnter(object sender, DragEventArgs e)
    {
        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            e.Effects = DragDropEffects.Copy;
            DragDropZone.Background = new System.Windows.Media.SolidColorBrush(
                System.Windows.Media.Color.FromRgb(0xE8, 0xF0, 0xFE));
            DragDropZone.BorderBrush = new System.Windows.Media.SolidColorBrush(
                System.Windows.Media.Color.FromRgb(0x3B, 0x82, 0xF6));
            DropHint.Text = "📥 松开放置文件";
        }
        else
        {
            e.Effects = DragDropEffects.None;
        }
    }

    /// <summary>
    /// 拖离文件列表区域时恢复默认样式
    /// </summary>
    private void OnFileListDragLeave(object sender, DragEventArgs e)
    {
        ResetDragZoneStyle();
    }

    /// <summary>
    /// 放置文件时导入文件到工作台
    /// </summary>
    private void OnFileListDrop(object sender, DragEventArgs e)
    {
        ResetDragZoneStyle();

        if (!e.Data.GetDataPresent(DataFormats.FileDrop)) return;
        if (_viewModel == null) return;

        var droppedPaths = e.Data.GetData(DataFormats.FileDrop) as string[];
        if (droppedPaths == null || droppedPaths.Length == 0) return;

        _viewModel.ImportDroppedFiles(droppedPaths);
    }

    /// <summary>
    /// 恢复拖拽区域默认样式
    /// </summary>
    private void ResetDragZoneStyle()
    {
        DragDropZone.Background = new System.Windows.Media.SolidColorBrush(
            System.Windows.Media.Color.FromRgb(0xF8, 0xF8, 0xF8));
        DragDropZone.BorderBrush = new System.Windows.Media.SolidColorBrush(
            System.Windows.Media.Color.FromRgb(0xCC, 0xCC, 0xCC));
        DropHint.Text = "📁 拖拽文件到此处开始";
    }

    // ==================== 文件列表交互 ====================

    /// <summary>
    /// 双击文件列表中的文件项 —— 预览该文件
    /// </summary>
    private void OnFileItemDoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (_viewModel == null) return;

        var listBox = sender as ListBox;
        if (listBox?.SelectedItem is FileItemViewModel fileVm)
        {
            _viewModel.PreviewFileCommand.Execute(fileVm);
        }
    }

    /// <summary>
    /// 双击最近文件条目 —— 导入该文件到工作台
    /// </summary>
    private void OnRecentFileDoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (_viewModel == null) return;

        var listBox = sender as ListBox;
        if (listBox?.SelectedItem is RecentFileEntry entry)
        {
            _viewModel.OpenRecentFileCommand.Execute(entry);
        }
    }

    // ==================== 文件导入按钮（点击时打开文件选择对话框） ====================

    /// <summary>
    /// 导入文件按钮的自定义点击处理，打开系统文件选择对话框
    /// 此方法在 XAML 中的按钮 Click 事件中绑定，
    /// 由于 ImportFilesCommand 本身不包含 UI 对话框逻辑，
    /// 由 View 层负责打开对话框并调用 ViewModel.ImportDroppedFiles。
    /// </summary>
    private void OnImportFilesClick(object sender, RoutedEventArgs e)
    {
        if (_viewModel == null) return;

        var dialog = new OpenFileDialog
        {
            Title = "选择要导入的文件",
            Multiselect = true,
            Filter = "支持的图片文件|*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.tiff;*.tif;*.webp;*.ico|" +
                     "PDF 文件|*.pdf|" +
                     "设计文件|*.psd;*.ai;*.eps;*.svg;*.cdr|" +
                     "所有支持的文件|*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.tiff;*.tif;*.webp;*.ico;*.pdf;*.psd;*.ai;*.eps;*.svg;*.cdr|" +
                     "所有文件|*.*"
        };

        if (dialog.ShowDialog() == true)
        {
            _viewModel.ImportDroppedFiles(dialog.FileNames);
        }
    }

    /// <summary>
    /// 更新预览面板的可见性
    /// </summary>
    private void UpdatePreviewVisibility()
    {
        if (_viewModel == null) return;

        var hasPreview = _viewModel.HasPreview;
        var isPreviewImage = _viewModel.IsPreviewImage;

        PreviewContentPanel.Visibility = hasPreview
            ? Visibility.Visible : Visibility.Collapsed;
        PreviewPlaceholder.Visibility = hasPreview
            ? Visibility.Collapsed : Visibility.Visible;

        if (hasPreview)
        {
            PreviewImage.Visibility = isPreviewImage
                ? Visibility.Visible : Visibility.Collapsed;
            NonImagePreviewHint.Visibility = isPreviewImage
                ? Visibility.Collapsed : Visibility.Visible;
        }
    }
}

/// <summary>
/// 文件支持状态到颜色的转换器
/// </summary>
internal class SupportedStatusToColorConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is bool isSupported)
            return isSupported
                ? new System.Windows.Media.SolidColorBrush(
                    System.Windows.Media.Color.FromRgb(0x16, 0xA3, 0x4A)) // 绿色：支持
                : new System.Windows.Media.SolidColorBrush(
                    System.Windows.Media.Color.FromRgb(0xDC, 0x26, 0x26)); // 红色：不支持
        return new System.Windows.Media.SolidColorBrush(
            System.Windows.Media.Color.FromRgb(0x66, 0x66, 0x66));
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotSupportedException();
    }
}
