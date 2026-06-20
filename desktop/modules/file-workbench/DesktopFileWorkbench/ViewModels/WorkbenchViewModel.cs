using System.Collections.ObjectModel;
using System.Windows.Input;
using TTTools.FileWorkbench.Models;
using TTTools.FileWorkbench.Services;
using TTShared.FileSystem;
using TTShared.Logging;
using TTShared.UI;

namespace TTTools.FileWorkbench.ViewModels;

/// <summary>
/// 文件工作台主 ViewModel
/// 管理文件导入、文件列表、文件预览、最近文件的整体工作台流程。
/// 这是文件工作台的核心控制器，所有 UI 操作都通过此 VM 中转。
/// </summary>
public class WorkbenchViewModel : BaseViewModel
{
    private readonly RecentFilesService _recentFiles;
    private readonly FileSystemService _fileSystem;
    private readonly AppLogger? _logger;

    private string? _previewFilePath;
    private string _statusMessage = "拖拽文件到此处，或点击导入按钮开始";
    private bool _isLoading;
    private string? _filterText;

    /// <summary>工作台中的文件列表</summary>
    public ObservableCollection<FileItemViewModel> Files { get; } = new();

    /// <summary>最近文件列表</summary>
    public ObservableCollection<RecentFileEntry> RecentFiles { get; } = new();

    /// <summary>当前预览的文件路径（null 表示无预览）</summary>
    public string? PreviewFilePath
    {
        get => _previewFilePath;
        set
        {
            if (SetProperty(ref _previewFilePath, value))
            {
                OnPropertyChanged(nameof(HasPreview));
                OnPropertyChanged(nameof(PreviewFileName));
                OnPropertyChanged(nameof(IsPreviewImage));
            }
        }
    }

    /// <summary>是否有文件正在预览</summary>
    public bool HasPreview => !string.IsNullOrEmpty(PreviewFilePath) && File.Exists(PreviewFilePath);

    /// <summary>预览文件的名称</summary>
    public string PreviewFileName => HasPreview ? Path.GetFileName(PreviewFilePath!) : string.Empty;

    /// <summary>预览文件是否为图片（可在 WPF 中直接渲染）</summary>
    public bool IsPreviewImage => HasPreview && FileSystemService.IsImageFile(PreviewFilePath!);

    /// <summary>当前状态栏消息</summary>
    public string StatusMessage
    {
        get => _statusMessage;
        set => SetProperty(ref _statusMessage, value);
    }

    /// <summary>是否正在加载</summary>
    public bool IsLoading
    {
        get => _isLoading;
        set => SetProperty(ref _isLoading, value);
    }

    /// <summary>过滤文本（按文件名过滤）</summary>
    public string? FilterText
    {
        get => _filterText;
        set
        {
            if (SetProperty(ref _filterText, value))
                ApplyFilter();
        }
    }

    /// <summary>已导入文件数量（不含过滤）</summary>
    public int FileCount => Files.Count;

    /// <summary>选中文件数量</summary>
    public int SelectedCount => Files.Count(f => f.IsSelected);

    /// <summary>导入文件命令</summary>
    public ICommand ImportFilesCommand { get; }

    /// <summary>清空工作台命令</summary>
    public ICommand ClearAllCommand { get; }

    /// <summary>移除选中文件命令</summary>
    public ICommand RemoveSelectedCommand { get; }

    /// <summary>预览文件命令</summary>
    public ICommand PreviewFileCommand { get; }

    /// <summary>打开最近文件命令</summary>
    public ICommand OpenRecentFileCommand { get; }

    /// <summary>清除最近文件命令</summary>
    public ICommand ClearRecentCommand { get; }

    /// <summary>全选命令</summary>
    public ICommand SelectAllCommand { get; }

    /// <summary>反选命令</summary>
    public ICommand InvertSelectionCommand { get; }

    public WorkbenchViewModel(RecentFilesService recentFiles, FileSystemService fileSystem,
        AppLogger? logger = null)
    {
        _recentFiles = recentFiles ?? throw new ArgumentNullException(nameof(recentFiles));
        _fileSystem = fileSystem ?? throw new ArgumentNullException(nameof(fileSystem));
        _logger = logger;

        ImportFilesCommand = new RelayCommand<string?>(ImportFiles);
        ClearAllCommand = new RelayCommand(ClearAll, () => Files.Count > 0);
        RemoveSelectedCommand = new RelayCommand(RemoveSelected, () => SelectedCount > 0);
        PreviewFileCommand = new RelayCommand<FileItemViewModel?>(PreviewFile);
        OpenRecentFileCommand = new RelayCommand<RecentFileEntry?>(OpenRecentFile);
        ClearRecentCommand = new RelayCommand(ClearRecentFiles, () => RecentFiles.Count > 0);
        SelectAllCommand = new RelayCommand(SelectAll, () => Files.Count > 0);
        InvertSelectionCommand = new RelayCommand(InvertSelection, () => Files.Count > 0);

        // 订阅最近文件变更
        _recentFiles.RecentFilesChanged += (_, _) => RefreshRecentFiles();

        // 监听文件列表变更以更新命令状态
        Files.CollectionChanged += (_, _) => RefreshCommandStates();

        // 初始加载最近文件
        RefreshRecentFiles();
    }

    /// <summary>
    /// 默认构造函数（用于设计时）
    /// </summary>
    public WorkbenchViewModel() : this(new RecentFilesService(), new FileSystemService())
    { }

    /// <summary>
    /// 通过拖拽事件导入文件
    /// 由 View 层在拖拽完成时调用，传入拖入的文件路径列表。
    /// </summary>
    /// <param name="filePaths">拖入的文件路径列表</param>
    public void ImportDroppedFiles(IEnumerable<string> filePaths)
    {
        AddFilesCore(filePaths);
    }

    /// <summary>
    /// 导入文件（通过文件选择对话框或拖拽）
    /// </summary>
    /// <param name="paths">文件路径（未使用，这里作为 RelayCommand 占位）</param>
    private void ImportFiles(string? paths)
    {
        // 通过 OpenFileDialog 选择文件导入（由 View 层配合使用）
        // ViewModel 本身不依赖 WPF 对话框，由 View 调用 ImportDroppedFiles 完成
    }

    /// <summary>
    /// 添加文件到工作台的核心逻辑
    /// </summary>
    private void AddFilesCore(IEnumerable<string> filePaths)
    {
        if (filePaths == null) return;

        var addedCount = 0;
        var skippedCount = 0;

        foreach (var path in filePaths)
        {
            if (string.IsNullOrWhiteSpace(path)) continue;
            if (!File.Exists(path))
            {
                skippedCount++;
                continue;
            }

            // 去重：相同路径不重复添加
            var normalizedPath = Path.GetFullPath(path);
            if (Files.Any(f =>
                string.Equals(f.FilePath, normalizedPath, StringComparison.OrdinalIgnoreCase)))
            {
                skippedCount++;
                continue;
            }

            var fileItem = FileItem.FromPath(normalizedPath);
            var vm = new FileItemViewModel(fileItem);
            vm.SelectionChanged += OnFileSelectionChanged;
            Files.Add(vm);

            // 记录到最近文件
            _recentFiles.RecordFile(normalizedPath);
            addedCount++;
        }

        UpdateStatus(addedCount, skippedCount);

        _logger?.Info(
            $"文件导入完成：成功 {addedCount} 个，跳过 {skippedCount} 个",
            "file-workbench");
    }

    /// <summary>
    /// 清空工作台所有文件
    /// </summary>
    private void ClearAll()
    {
        foreach (var vm in Files)
            vm.SelectionChanged -= OnFileSelectionChanged;

        Files.Clear();
        PreviewFilePath = null;
        StatusMessage = "工作台已清空";
        _logger?.Info("工作台已清空", "file-workbench");
    }

    /// <summary>
    /// 移除选中的文件
    /// </summary>
    private void RemoveSelected()
    {
        var selectedItems = Files.Where(f => f.IsSelected).ToList();
        foreach (var vm in selectedItems)
        {
            vm.SelectionChanged -= OnFileSelectionChanged;
            Files.Remove(vm);
        }

        // 如果预览的文件被移除了，清除预览
        if (PreviewFilePath != null && !Files.Any(f =>
                string.Equals(f.FilePath, PreviewFilePath, StringComparison.OrdinalIgnoreCase)))
        {
            PreviewFilePath = null;
        }

        StatusMessage = $"已移除 {selectedItems.Count} 个文件";
        _logger?.Info($"移除选中文件：{selectedItems.Count} 个", "file-workbench");
    }

    /// <summary>
    /// 预览指定文件
    /// </summary>
    private void PreviewFile(FileItemViewModel? fileVm)
    {
        if (fileVm == null) return;

        var path = fileVm.FilePath;
        if (!File.Exists(path))
        {
            StatusMessage = $"文件不存在：{path}";
            PreviewFilePath = null;
            return;
        }

        PreviewFilePath = path;
        StatusMessage = $"正在预览：{fileVm.FileName}";
    }

    /// <summary>
    /// 从最近文件中打开一个文件
    /// </summary>
    private void OpenRecentFile(RecentFileEntry? entry)
    {
        if (entry == null) return;

        if (!File.Exists(entry.FilePath))
        {
            StatusMessage = $"文件不存在：{entry.FilePath}";
            _recentFiles.CleanInvalidEntries();
            return;
        }

        AddFilesCore(new[] { entry.FilePath });
    }

    /// <summary>
    /// 清除所有最近文件记录
    /// </summary>
    private void ClearRecentFiles()
    {
        _recentFiles.Clear();
        StatusMessage = "最近文件记录已清除";
    }

    /// <summary>
    /// 全选所有文件
    /// </summary>
    private void SelectAll()
    {
        foreach (var vm in Files)
            vm.IsSelected = true;
        RefreshCommandStates();
    }

    /// <summary>
    /// 反选文件
    /// </summary>
    private void InvertSelection()
    {
        foreach (var vm in Files)
            vm.IsSelected = !vm.IsSelected;
        RefreshCommandStates();
    }

    /// <summary>
    /// 文件选中状态变更时刷新命令和预览状态
    /// </summary>
    private void OnFileSelectionChanged(object? sender, FileItemViewModel e)
    {
        RefreshCommandStates();
    }

    /// <summary>
    /// 刷新最近文件列表到 ObservableCollection
    /// </summary>
    private void RefreshRecentFiles()
    {
        RecentFiles.Clear();
        var existingFiles = _recentFiles.GetExistingFiles();
        foreach (var entry in existingFiles)
            RecentFiles.Add(entry);
    }

    /// <summary>
    /// 更新命令的可执行状态
    /// </summary>
    private void RefreshCommandStates()
    {
        OnPropertyChanged(nameof(FileCount));
        OnPropertyChanged(nameof(SelectedCount));

        (ClearAllCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (RemoveSelectedCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (ClearRecentCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (SelectAllCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (InvertSelectionCommand as RelayCommand)?.RaiseCanExecuteChanged();
    }

    /// <summary>
    /// 按过滤文本过滤文件列表（预留，配合 CollectionViewSource 使用）
    /// </summary>
    private void ApplyFilter()
    {
        // 过滤逻辑由 View 层的 CollectionViewSource 处理
        // ViewModel 保留此入口用于日志和状态同步
        _logger?.Debug($"文件过滤：'{FilterText}'", "file-workbench");
    }

    /// <summary>
    /// 更新状态栏消息
    /// </summary>
    private void UpdateStatus(int addedCount, int skippedCount)
    {
        var parts = new List<string>();
        if (addedCount > 0) parts.Add($"已导入 {addedCount} 个文件");
        if (skippedCount > 0) parts.Add($"跳过 {skippedCount} 个（重复或不存在）");

        StatusMessage = parts.Count > 0
            ? string.Join("，", parts)
            : "未导入任何文件";

        OnPropertyChanged(nameof(FileCount));
    }
}
