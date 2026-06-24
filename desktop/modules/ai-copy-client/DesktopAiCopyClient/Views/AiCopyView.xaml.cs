using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using TTTools.AiCopyClient.ViewModels;

namespace TTTools.AiCopyClient.Views;

/// <summary>
/// 云端文案生成视图
/// 左右布局：左侧为参数输入表单，右侧为生成结果和历史记录。
/// DataContext 绑定到 AiCopyViewModel。
/// </summary>
public partial class AiCopyView : UserControl
{
    private AiCopyViewModel? _viewModel;

    public AiCopyView()
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
        _viewModel = e.NewValue as AiCopyViewModel;
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
    /// 点击变体文案，选中并更新 SelectedVariant
    /// </summary>
    private void OnVariantClick(object sender, MouseButtonEventArgs e)
    {
        if (sender is Border border && border.DataContext is string variantText)
        {
            _viewModel?.SelectVariantCommand.Execute(variantText);
        }
    }

    /// <summary>
    /// 点击历史记录项，恢复对应结果
    /// </summary>
    private void OnHistoryItemClick(object sender, MouseButtonEventArgs e)
    {
        if (sender is Border border && border.DataContext is AiCopyHistoryItem item)
        {
            _viewModel?.SelectHistoryItemCommand.Execute(item);
        }
    }
}
