using System.Windows.Controls;
using Microsoft.Win32;
using TTTools.ExportSettings.ViewModels;

namespace TTTools.ExportSettings.Views;

/// <summary>
/// 导出页面视图
/// 处理文件选择对话框等 UI 交互。
/// </summary>
public partial class ExportView : UserControl
{
    public ExportView()
    {
        InitializeComponent();
    }

    /// <summary>
    /// 打开文件选择对话框添加文件
    /// </summary>
    private void OnAddFilesClick(object sender, System.Windows.RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Title = "选择要导出的文件",
            Multiselect = true,
            Filter = "支持的文件|*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.tiff;*.tif;*.webp;*.ico;*.pdf;*.psd;*.ai;*.eps;*.svg;*.cdr|所有文件|*.*"
        };

        if (dialog.ShowDialog() == true)
        {
            if (DataContext is ExportViewModel vm)
            {
                vm.AddFilePaths(dialog.FileNames);
            }
        }
    }

    /// <summary>
    /// 选择输出目录
    /// </summary>
    private void OnSelectOutputDirClick(object sender, System.Windows.RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Title = "选择导出目标目录",
            CheckFileExists = false,
            CheckPathExists = true,
            FileName = "选择文件夹",
            Filter = "文件夹|*."
        };

        if (dialog.ShowDialog() == true)
        {
            var dir = System.IO.Path.GetDirectoryName(dialog.FileName);
            if (!string.IsNullOrEmpty(dir) && DataContext is ExportViewModel vm)
            {
                vm.SetOutputDirectory(dir);
            }
        }
    }
}
