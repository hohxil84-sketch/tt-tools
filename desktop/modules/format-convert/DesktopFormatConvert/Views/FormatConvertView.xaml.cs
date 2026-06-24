using System.Windows;
using System.Windows.Controls;
using TTTools.FormatConvert.ViewModels;

namespace TTTools.FormatConvert.Views;

/// <summary>
/// 格式转换/压缩/裁剪/旋转模块主视图
/// 支持拖拽文件到窗口进行处理。
/// </summary>
public partial class FormatConvertView : UserControl
{
    public FormatConvertView()
    {
        InitializeComponent();
    }

    /// <summary>
    /// 拖拽进入窗口时设置拖放效果。
    /// </summary>
    private void FormatConvertView_DragEnter(object sender, DragEventArgs e)
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
    /// 拖拽放下时获取文件路径并交给 ViewModel 处理。
    /// </summary>
    private void FormatConvertView_Drop(object sender, DragEventArgs e)
    {
        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            var files = (string[])e.Data.GetData(DataFormats.FileDrop);
            if (files != null && files.Length > 0)
            {
                if (DataContext is FormatConvertViewModel vm)
                {
                    vm.ProcessDroppedFiles(files);
                }
            }
        }
        e.Handled = true;
    }
}
