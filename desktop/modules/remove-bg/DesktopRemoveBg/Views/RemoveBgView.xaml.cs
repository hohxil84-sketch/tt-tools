using System.Windows;
using System.Windows.Controls;
using TTTools.RemoveBg.ViewModels;

namespace TTTools.RemoveBg.Views;

/// <summary>
/// 智能抠图视图代码后置
/// 处理拖拽事件，将文件拖入操作转发给 ViewModel。
/// </summary>
public partial class RemoveBgView : UserControl
{
    private RemoveBgViewModel? _viewModel;

    public RemoveBgView()
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
        _viewModel = e.NewValue as RemoveBgViewModel;
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
                _viewModel?.ProcessDroppedFiles(filePaths);
            }
        }
        e.Handled = true;
    }
}
