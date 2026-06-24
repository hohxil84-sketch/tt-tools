using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
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
