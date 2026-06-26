using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using TTShared.CloudApi.Dtos;
using TTTools.AiRenderClient.ViewModels;

namespace TTTools.AiRenderClient.Views;

/// <summary>
/// 云端效果图生成视图
/// 左右布局：左侧为参数输入表单，右侧为任务状态和结果展示。
/// DataContext 绑定到 AiRenderViewModel。
/// </summary>
public partial class AiRenderView : UserControl
{
    private AiRenderViewModel? _viewModel;

    public AiRenderView()
    {
        InitializeComponent();

        // 通过 DataContextChanged 获取 ViewModel 引用
        DataContextChanged += OnDataContextChanged;
    }

    /// <summary>
    /// DataContext 变更时更新 ViewModel 引用
    /// </summary>
    private void OnDataContextChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        _viewModel = e.NewValue as AiRenderViewModel;
    }

    /// <summary>
    /// 关闭错误消息提示条
    /// </summary>
    private void OnDismissError(object sender, RoutedEventArgs e)
    {
        if (_viewModel != null)
            _viewModel.ErrorMessage = null;
    }

    /// <summary>
    /// 点击结果文件项，在浏览器中打开文件 URL
    /// </summary>
    private void OnResultFileClick(object sender, MouseButtonEventArgs e)
    {
        if (sender is Border border && border.DataContext is ResultFileDto file)
        {
            _viewModel?.OpenResultFileCommand.Execute(file);
        }
    }

    /// <summary>
    /// 点击历史记录项，恢复对应任务状态到当前视图
    /// </summary>
    private void OnHistoryItemClick(object sender, MouseButtonEventArgs e)
    {
        if (sender is Border border && border.DataContext is AiRenderHistoryItem item)
        {
            _viewModel?.SelectHistoryItemCommand.Execute(item);
        }
    }

    /// <summary>
    /// 点击预览弹窗背景 → 关闭预览
    /// </summary>
    private void OnPreviewBackgroundClick(object sender, MouseButtonEventArgs e)
    {
        _viewModel?.ClosePreviewCommand.Execute(null);
    }

    /// <summary>
    /// 点击预览大图本身 → 关闭预览（阻止事件冒泡已由背景处理）
    /// </summary>
    private void OnPreviewImageClick(object sender, MouseButtonEventArgs e)
    {
        _viewModel?.ClosePreviewCommand.Execute(null);
        e.Handled = true;  // 阻止事件冒泡到背景，避免重复触发
    }
}
