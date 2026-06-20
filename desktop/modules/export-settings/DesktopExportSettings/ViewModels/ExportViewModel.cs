using System.Collections.ObjectModel;
using System.Windows.Input;
using TTTools.ExportSettings.Models;
using TTTools.ExportSettings.Services;
using TTShared.FileSystem;
using TTShared.UI;

namespace TTTools.ExportSettings.ViewModels;

/// <summary>
/// 导出页面 ViewModel
/// 管理导出文件列表、配置选项、导出进度和导出命令。
/// </summary>
public class ExportViewModel : BaseViewModel
{
    private readonly ExportService _exportService;
    private readonly FileSystemService _fileSystem;

    /// <summary>待导出文件列表</summary>
    public ObservableCollection<string> SourceFiles { get; } = new();

    /// <summary>导出配置</summary>
    public ExportConfig Config { get; } = new();

    /// <summary>导出进度（百分比 0-100）</summary>
    private double _progress;
    public double Progress
    {
        get => _progress;
        set => SetProperty(ref _progress, value);
    }

    /// <summary>进度文本</summary>
    private string _progressText = "就绪";
    public string ProgressText
    {
        get => _progressText;
        set => SetProperty(ref _progressText, value);
    }

    /// <summary>是否正在导出</summary>
    private bool _isExporting;
    public bool IsExporting
    {
        get => _isExporting;
        set => SetProperty(ref _isExporting, value);
    }

    /// <summary>最后一次导出结果</summary>
    private ExportResult? _lastResult;
    public ExportResult? LastResult
    {
        get => _lastResult;
        set => SetProperty(ref _lastResult, value);
    }

    /// <summary>结果摘要文本</summary>
    private string _resultSummary = string.Empty;
    public string ResultSummary
    {
        get => _resultSummary;
        set => SetProperty(ref _resultSummary, value);
    }

    /// <summary>选中的导出格式索引</summary>
    private int _selectedFormatIndex;
    public int SelectedFormatIndex
    {
        get => _selectedFormatIndex;
        set
        {
            if (SetProperty(ref _selectedFormatIndex, value))
            {
                var keys = ExportConfig.SupportedFormats.Keys.ToList();
                if (value >= 0 && value < keys.Count)
                    Config.Format = keys[value];
            }
        }
    }

    /// <summary>导出格式列表（用于 UI 绑定）</summary>
    public List<string> FormatLabels { get; } = ExportConfig.SupportedFormats.Values.ToList();

    /// <summary>添加文件命令</summary>
    public ICommand AddFilesCommand { get; }

    /// <summary>移除选中文件命令</summary>
    public ICommand RemoveFileCommand { get; }

    /// <summary>清空文件列表命令</summary>
    public ICommand ClearFilesCommand { get; }

    /// <summary>选择输出目录命令</summary>
    public ICommand SelectOutputDirCommand { get; }

    /// <summary>开始导出命令</summary>
    public ICommand StartExportCommand { get; }

    /// <summary>取消导出命令</summary>
    public ICommand CancelExportCommand { get; }

    private CancellationTokenSource? _cts;

    public ExportViewModel(ExportService? exportService = null, FileSystemService? fileSystem = null)
    {
        _fileSystem = fileSystem ?? new FileSystemService();
        _exportService = exportService ?? new ExportService(_fileSystem);

        AddFilesCommand = new RelayCommand(AddFiles);
        RemoveFileCommand = new RelayCommand<string>(RemoveFile);
        ClearFilesCommand = new RelayCommand(ClearFiles);
        SelectOutputDirCommand = new RelayCommand(SelectOutputDir);
        StartExportCommand = new AsyncRelayCommand(StartExportAsync);
        CancelExportCommand = new RelayCommand(CancelExport);
    }

    /// <summary>
    /// 打开文件对话框添加文件
    /// 实际集成时需要 Microsoft.Win32.OpenFileDialog。
    /// 当前为可测试方法。
    /// </summary>
    public void AddFiles()
    {
        // 实际 WPF 中会使用 OpenFileDialog 选择文件
        // 此处提供方法供 View 层调用
    }

    /// <summary>
    /// 添加文件路径到列表（供 View 层调用）
    /// </summary>
    public void AddFilePaths(IEnumerable<string> filePaths)
    {
        foreach (var path in filePaths)
        {
            if (!SourceFiles.Contains(path) &&
                FileSystemService.IsSupportedFile(path))
            {
                SourceFiles.Add(path);
            }
        }

        UpdateProgressText();
    }

    /// <summary>
    /// 移除指定文件
    /// </summary>
    private void RemoveFile(string? filePath)
    {
        if (filePath != null && SourceFiles.Contains(filePath))
        {
            SourceFiles.Remove(filePath);
            UpdateProgressText();
        }
    }

    /// <summary>
    /// 清空文件列表
    /// </summary>
    private void ClearFiles()
    {
        SourceFiles.Clear();
        UpdateProgressText();
    }

    /// <summary>
    /// 选择输出目录
    /// 实际集成时需要 Microsoft.Win32.SaveFileDialog 或 FolderBrowserDialog。
    /// </summary>
    public void SelectOutputDir()
    {
        // 实际 WPF 中使用 FolderBrowserDialog 选择目录
        // 此处提供方法供 View 层调用
    }

    /// <summary>
    /// 设置输出目录路径（供 View 层调用）
    /// </summary>
    public void SetOutputDirectory(string directoryPath)
    {
        if (!string.IsNullOrWhiteSpace(directoryPath))
        {
            Config.OutputDirectory = directoryPath;
            OnPropertyChanged(nameof(Config));
        }
    }

    /// <summary>
    /// 异步执行导出
    /// </summary>
    private async Task StartExportAsync()
    {
        if (SourceFiles.Count == 0)
        {
            ResultSummary = "没有待导出的文件";
            return;
        }

        if (string.IsNullOrWhiteSpace(Config.OutputDirectory))
        {
            ResultSummary = "请先选择输出目录";
            return;
        }

        IsExporting = true;
        Progress = 0;
        ProgressText = "正在导出...";
        ResultSummary = string.Empty;
        LastResult = null;

        _cts = new CancellationTokenSource();

        try
        {
            var progress = new Progress<(int current, int total)>(p =>
            {
                Progress = p.total > 0 ? (double)p.current / p.total * 100 : 0;
                ProgressText = $"正在导出... {p.current}/{p.total}";
            });

            LastResult = await _exportService.ExportAsync(
                SourceFiles.ToList(),
                Config,
                progress,
                _cts.Token);

            if (LastResult.Success)
            {
                ResultSummary = $"导出完成！成功导出 {LastResult.SuccessCount} 个文件，耗时 {LastResult.ElapsedMs}ms";
            }
            else
            {
                ResultSummary = $"导出完成，成功 {LastResult.SuccessCount} 个，失败 {LastResult.FailureCount} 个";
            }
        }
        catch (OperationCanceledException)
        {
            ResultSummary = "导出已取消";
        }
        catch (Exception ex)
        {
            ResultSummary = $"导出失败：{ex.Message}";
        }
        finally
        {
            IsExporting = false;
            _cts?.Dispose();
            _cts = null;
        }
    }

    /// <summary>
    /// 取消当前导出
    /// </summary>
    private void CancelExport()
    {
        _cts?.Cancel();
        ProgressText = "正在取消...";
    }

    /// <summary>
    /// 更新进度文本显示
    /// </summary>
    private void UpdateProgressText()
    {
        ProgressText = SourceFiles.Count > 0
            ? $"已选择 {SourceFiles.Count} 个文件"
            : "就绪";
    }
}
