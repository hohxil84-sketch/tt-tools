using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using TTTools.PreflightCheck.Models;
using TTTools.PreflightCheck.ViewModels;

namespace TTTools.PreflightCheck.Views;

/// <summary>
/// 印前检查视图代码后置
/// 处理拖拽事件，将图像文件拖入操作转发给 ViewModel。
/// </summary>
public partial class PreflightCheckView : UserControl
{
    private PreflightCheckViewModel? _viewModel;

    public PreflightCheckView()
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
        _viewModel = e.NewValue as PreflightCheckViewModel;
    }

    /// <summary>
    /// 拖拽进入时检查数据格式（仅接受文件拖放）
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
                _viewModel?.CheckDroppedFiles(filePaths);
            }
        }
        e.Handled = true;
    }
}

#region 值转换器

/// <summary>
/// 风险等级到图标转换器
/// Pass → ✅, Warning → ⚠️, Error → ❌
/// </summary>
public class RiskToIconConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter,
        System.Globalization.CultureInfo culture)
    {
        if (value is RiskLevel risk)
        {
            return risk switch
            {
                RiskLevel.Pass => "✅",
                RiskLevel.Warning => "⚠️",
                RiskLevel.Error => "❌",
                _ => "❓"
            };
        }
        return "❓";
    }

    public object ConvertBack(object value, Type targetType, object parameter,
        System.Globalization.CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// 风险等级到前景色转换器
/// Pass → 绿色, Warning → 橙色, Error → 红色
/// </summary>
public class RiskToForegroundConverter : IValueConverter
{
    private static readonly SolidColorBrush PassBrush = new(Color.FromRgb(0x2E, 0x7D, 0x32));
    private static readonly SolidColorBrush WarningBrush = new(Color.FromRgb(0xE6, 0x51, 0x00));
    private static readonly SolidColorBrush ErrorBrush = new(Color.FromRgb(0xC6, 0x28, 0x28));
    private static readonly SolidColorBrush DefaultBrush = new(Color.FromRgb(0x21, 0x21, 0x21));

    public object Convert(object value, Type targetType, object parameter,
        System.Globalization.CultureInfo culture)
    {
        if (value is RiskLevel risk)
        {
            return risk switch
            {
                RiskLevel.Pass => PassBrush,
                RiskLevel.Warning => WarningBrush,
                RiskLevel.Error => ErrorBrush,
                _ => DefaultBrush
            };
        }
        return DefaultBrush;
    }

    public object ConvertBack(object value, Type targetType, object parameter,
        System.Globalization.CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// 风险等级到背景色转换器
/// Pass → 浅绿, Warning → 浅橙, Error → 浅红
/// </summary>
public class RiskToBackgroundConverter : IValueConverter
{
    private static readonly SolidColorBrush PassBgBrush = new(Color.FromRgb(0xE8, 0xF5, 0xE9));
    private static readonly SolidColorBrush WarningBgBrush = new(Color.FromRgb(0xFF, 0xF3, 0xE0));
    private static readonly SolidColorBrush ErrorBgBrush = new(Color.FromRgb(0xFF, 0xEB, 0xEE));
    private static readonly SolidColorBrush DefaultBgBrush = new(Color.FromRgb(0xF5, 0xF5, 0xF5));

    public object Convert(object value, Type targetType, object parameter,
        System.Globalization.CultureInfo culture)
    {
        if (value is RiskLevel risk)
        {
            return risk switch
            {
                RiskLevel.Pass => PassBgBrush,
                RiskLevel.Warning => WarningBgBrush,
                RiskLevel.Error => ErrorBgBrush,
                _ => DefaultBgBrush
            };
        }
        return DefaultBgBrush;
    }

    public object ConvertBack(object value, Type targetType, object parameter,
        System.Globalization.CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

#endregion
