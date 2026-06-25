using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using TTTools.ResizeImage.ViewModels;

namespace TTTools.ResizeImage.Views;

/// <summary>
/// 图片改尺寸视图
/// 支持文件拖拽导入，DataContext 绑定到 ResizeImageViewModel。
/// Loaded 事件自动触发 ViewModel 初始化（启动 Python worker）。
/// </summary>
public partial class ResizeImageView : UserControl
{
    private ResizeImageViewModel? _viewModel;

    public ResizeImageView()
    {
        InitializeComponent();

        // 启用拖拽支持
        AllowDrop = true;

        // 通过 DataContextChanged 获取 ViewModel 引用
        DataContextChanged += OnDataContextChanged;

        // 视图加载完成后自动初始化 ViewModel（启动 worker + 加载预设）
        Loaded += OnViewLoaded;
    }

    /// <summary>
    /// DataContext 变更时更新 ViewModel 引用。
    /// </summary>
    private void OnDataContextChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        _viewModel = e.NewValue as ResizeImageViewModel;
    }

    /// <summary>
    /// 视图加载完成后初始化 ViewModel。
    /// 异步启动 Python worker 并进行健康检查。
    /// </summary>
    private async void OnViewLoaded(object sender, RoutedEventArgs e)
    {
        if (_viewModel != null)
            await _viewModel.InitializeAsync();
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
