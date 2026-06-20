using System.Windows.Input;
using TTTools.FileWorkbench.Models;
using TTShared.UI;

namespace TTTools.FileWorkbench.ViewModels;

/// <summary>
/// 单个文件项的 ViewModel
/// 包装 FileItem 模型，提供 UI 绑定的属性和选中操作。
/// </summary>
public class FileItemViewModel : BaseViewModel
{
    private readonly FileItem _fileItem;
    private bool _isSelected;

    /// <summary>文件完整路径</summary>
    public string FilePath => _fileItem.FilePath;

    /// <summary>文件名</summary>
    public string FileName => _fileItem.FileName;

    /// <summary>文件扩展名</summary>
    public string Extension => _fileItem.Extension;

    /// <summary>文件大小人类可读</summary>
    public string SizeDisplay => _fileItem.SizeDisplay;

    /// <summary>是否为支持的图片</summary>
    public bool IsImage => _fileItem.IsImage;

    /// <summary>是否为 PDF</summary>
    public bool IsPdf => _fileItem.IsPdf;

    /// <summary>是否为支持格式</summary>
    public bool IsSupported => _fileItem.IsSupported;

    /// <summary>是否被选中</summary>
    public bool IsSelected
    {
        get => _isSelected;
        set
        {
            if (SetProperty(ref _isSelected, value))
            {
                // 同步到底层模型
                _fileItem.IsSelected = value;
            }
        }
    }

    /// <summary>文件类型图标标识（用于 UI 展示不同类型图标）</summary>
    public string FileTypeIcon => _fileItem.IsImage ? "🖼" :
                                   _fileItem.IsPdf ? "📄" : "📁";

    /// <summary>文件状态文本</summary>
    public string StatusText => !_fileItem.IsSupported ? "格式不支持" : "就绪";

    /// <summary>选中/取消选中命令</summary>
    public ICommand ToggleSelectCommand { get; }

    /// <summary>选中状态变更事件</summary>
    public event EventHandler<FileItemViewModel>? SelectionChanged;

    public FileItemViewModel(FileItem fileItem)
    {
        _fileItem = fileItem ?? throw new ArgumentNullException(nameof(fileItem));
        _isSelected = fileItem.IsSelected;
        ToggleSelectCommand = new RelayCommand(ToggleSelect);
    }

    /// <summary>
    /// 获取底层 FileItem 模型
    /// </summary>
    public FileItem GetModel() => _fileItem;

    /// <summary>
    /// 切换选中状态
    /// </summary>
    private void ToggleSelect()
    {
        IsSelected = !IsSelected;
        SelectionChanged?.Invoke(this, this);
    }
}
