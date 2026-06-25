using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using TTShared.CloudApi.Dtos;
using TTTools.AiImageToolsClient.ViewModels;

namespace TTTools.AiImageToolsClient.Views;

/// <summary>
/// 云端 AI 图片工具视图
/// 左右布局：左侧为待处理文件列表，右侧为任务状态和结果展示。
/// DataContext 绑定到 AiImageToolsViewModel。
/// </summary>
public partial class AiImageToolsView : UserControl
{
    private AiImageToolsViewModel? _viewModel;

    public AiImageToolsView()
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
        _viewModel = e.NewValue as AiImageToolsViewModel;
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
    /// 从待处理列表中移除指定文件
    /// </summary>
    private void OnRemoveFileClick(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is PendingFileItem item)
        {
            _viewModel?.RemoveFileCommand.Execute(item);
        }
    }

    /// <summary>
    /// 点击结果文件项，在浏览器中打开文件 URL
    /// </summary>
    private void OnResultFileClick(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is ResultFileDto file)
        {
            _viewModel?.OpenResultFileCommand.Execute(file);
        }
    }

    /// <summary>
    /// 点击下载按钮，下载结果文件到本地
    /// </summary>
    private void OnDownloadClick(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is ResultFileDto file)
        {
            _viewModel?.DownloadResultFileCommand.Execute(file);
        }
    }

    /// <summary>
    /// 点击历史记录项，恢复对应任务状态到当前视图
    /// </summary>
    private void OnHistoryItemClick(object sender, MouseButtonEventArgs e)
    {
        if (sender is Border border && border.DataContext is AiImageToolHistoryItem item)
        {
            _viewModel?.SelectHistoryItemCommand.Execute(item);
        }
    }
}
