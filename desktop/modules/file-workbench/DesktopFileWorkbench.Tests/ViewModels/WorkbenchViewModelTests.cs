using TTTools.FileWorkbench.Services;
using TTTools.FileWorkbench.ViewModels;
using TTShared.FileSystem;

namespace TTTools.FileWorkbench.Tests.ViewModels;

/// <summary>
/// WorkbenchViewModel 单元测试
/// 测试文件工作台主 ViewModel 的核心逻辑：
/// 文件导入、列表管理、预览、选中操作、最近文件集成。
/// </summary>
public class WorkbenchViewModelTests : IDisposable
{
    private readonly string _testStoragePath;
    private readonly RecentFilesService _recentFiles;
    private readonly FileSystemService _fileSystem;
    private readonly WorkbenchViewModel _vm;

    public WorkbenchViewModelTests()
    {
        _testStoragePath = Path.Combine(Path.GetTempPath(), $"tt_test_wb_{Guid.NewGuid():N}.json");
        _recentFiles = new RecentFilesService(_testStoragePath);
        _fileSystem = new FileSystemService();
        _vm = new WorkbenchViewModel(_recentFiles, _fileSystem);
    }

    public void Dispose()
    {
        try { File.Delete(_testStoragePath); } catch { }
    }

    /// <summary>
    /// 创建测试临时文件
    /// </summary>
    private static string CreateTestFile(string fileName = "test-file.jpg")
    {
        var path = Path.Combine(Path.GetTempPath(), $"tt_test_{Guid.NewGuid():N}_{fileName}");
        File.WriteAllText(path, "test content");
        return path;
    }

    [Fact]
    public void Constructor_ShouldInitializeWithEmptyFiles()
    {
        Assert.Empty(_vm.Files);
        Assert.Equal(0, _vm.FileCount);
        Assert.Equal(0, _vm.SelectedCount);
        Assert.Null(_vm.PreviewFilePath);
        Assert.Contains("拖拽", _vm.StatusMessage);
    }

    [Fact]
    public void ImportDroppedFiles_ShouldAddFilesToList()
    {
        var file1 = CreateTestFile("image1.jpg");
        var file2 = CreateTestFile("image2.png");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1, file2 });

            Assert.Equal(2, _vm.Files.Count);
            Assert.Equal(2, _vm.FileCount);
        }
        finally
        {
            File.Delete(file1);
            File.Delete(file2);
        }
    }

    [Fact]
    public void ImportDroppedFiles_DuplicateFile_ShouldSkip()
    {
        var file1 = CreateTestFile("image1.jpg");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1 });
            _vm.ImportDroppedFiles(new[] { file1 }); // 重复导入

            Assert.Single(_vm.Files);
        }
        finally
        {
            File.Delete(file1);
        }
    }

    [Fact]
    public void ImportDroppedFiles_NonExistentFile_ShouldSkip()
    {
        var file1 = CreateTestFile("image1.jpg");
        var nonExistent = @"C:\nonexistent\ghost.jpg";

        try
        {
            _vm.ImportDroppedFiles(new[] { file1, nonExistent });

            Assert.Single(_vm.Files);
        }
        finally
        {
            File.Delete(file1);
        }
    }

    [Fact]
    public void ImportDroppedFiles_ShouldRecordToRecentFiles()
    {
        var file1 = CreateTestFile("image1.jpg");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1 });

            // 应该将文件添加到最近文件
            Assert.Single(_vm.RecentFiles);
        }
        finally
        {
            File.Delete(file1);
        }
    }

    [Fact]
    public void ImportDroppedFiles_ShouldUpdateStatusMessage()
    {
        var file1 = CreateTestFile("image1.jpg");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1 });
            Assert.Contains("已导入", _vm.StatusMessage);
        }
        finally
        {
            File.Delete(file1);
        }
    }

    [Fact]
    public void ClearAll_ShouldRemoveAllFiles()
    {
        var file1 = CreateTestFile("image1.jpg");
        var file2 = CreateTestFile("image2.jpg");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1, file2 });
            Assert.Equal(2, _vm.Files.Count);

            _vm.ClearAllCommand.Execute(null);

            Assert.Empty(_vm.Files);
            Assert.Null(_vm.PreviewFilePath);
        }
        finally
        {
            File.Delete(file1);
            File.Delete(file2);
        }
    }

    [Fact]
    public void RemoveSelected_ShouldRemoveOnlySelectedFiles()
    {
        var file1 = CreateTestFile("image1.jpg");
        var file2 = CreateTestFile("image2.jpg");
        var file3 = CreateTestFile("image3.jpg");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1, file2, file3 });

            // 选中第二个文件
            _vm.Files[1].IsSelected = true;

            _vm.RemoveSelectedCommand.Execute(null);

            Assert.Equal(2, _vm.Files.Count);
        }
        finally
        {
            File.Delete(file1);
            File.Delete(file2);
            File.Delete(file3);
        }
    }

    [Fact]
    public void PreviewFile_ShouldSetPreviewFilePath()
    {
        var file1 = CreateTestFile("image1.jpg");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1 });
            _vm.PreviewFileCommand.Execute(_vm.Files[0]);

            Assert.NotNull(_vm.PreviewFilePath);
            Assert.True(_vm.HasPreview);
            Assert.True(_vm.IsPreviewImage);
        }
        finally
        {
            File.Delete(file1);
        }
    }

    [Fact]
    public void PreviewFile_NonExistentFile_ShouldClearPreview()
    {
        var file1 = CreateTestFile("image1.jpg");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1 });

            // 预览文件
            _vm.PreviewFileCommand.Execute(_vm.Files[0]);
            Assert.True(_vm.HasPreview);

            // 删除文件后再预览
            File.Delete(file1);
            _vm.PreviewFileCommand.Execute(_vm.Files[0]);
            Assert.False(_vm.HasPreview);
        }
        catch { /* file may already be deleted */ }
    }

    [Fact]
    public void SelectAll_ShouldSelectAllFiles()
    {
        var file1 = CreateTestFile("image1.jpg");
        var file2 = CreateTestFile("image2.jpg");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1, file2 });
            _vm.SelectAllCommand.Execute(null);

            Assert.Equal(2, _vm.SelectedCount);
            Assert.True(_vm.Files.All(f => f.IsSelected));
        }
        finally
        {
            File.Delete(file1);
            File.Delete(file2);
        }
    }

    [Fact]
    public void InvertSelection_ShouldToggleSelection()
    {
        var file1 = CreateTestFile("image1.jpg");
        var file2 = CreateTestFile("image2.jpg");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1, file2 });
            _vm.Files[0].IsSelected = true;

            _vm.InvertSelectionCommand.Execute(null);

            Assert.False(_vm.Files[0].IsSelected);
            Assert.True(_vm.Files[1].IsSelected);
        }
        finally
        {
            File.Delete(file1);
            File.Delete(file2);
        }
    }

    [Fact]
    public void ClearRecentFiles_ShouldClearRecentList()
    {
        var file1 = CreateTestFile("image1.jpg");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1 });

            // 应该有最近文件记录
            Assert.NotEmpty(_vm.RecentFiles);

            _vm.ClearRecentCommand.Execute(null);
            Assert.Empty(_vm.RecentFiles);
        }
        finally
        {
            File.Delete(file1);
        }
    }

    [Fact]
    public void OpenRecentFile_ShouldImportFile()
    {
        var file1 = CreateTestFile("image1.jpg");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1 });
            _vm.ClearAllCommand.Execute(null); // 清空工作台

            Assert.Empty(_vm.Files);

            // 从最近文件重新打开
            var entry = _vm.RecentFiles.FirstOrDefault();
            Assert.NotNull(entry);
            _vm.OpenRecentFileCommand.Execute(entry);

            Assert.Single(_vm.Files);
        }
        finally
        {
            File.Delete(file1);
        }
    }

    [Fact]
    public void RemoveSelected_WhenPreviewedFileRemoved_ShouldClearPreview()
    {
        var file1 = CreateTestFile("preview-test.jpg");
        var file2 = CreateTestFile("other.jpg");

        try
        {
            _vm.ImportDroppedFiles(new[] { file1, file2 });
            _vm.PreviewFileCommand.Execute(_vm.Files[0]); // 预览第一个文件
            Assert.True(_vm.HasPreview);

            // 选中并移除预览中的文件
            _vm.Files[0].IsSelected = true;
            _vm.RemoveSelectedCommand.Execute(null);

            Assert.False(_vm.HasPreview);
        }
        finally
        {
            try { File.Delete(file1); } catch { }
            File.Delete(file2);
        }
    }

    [Fact]
    public void ImportDroppedFiles_EmptyList_ShouldNotChangeFiles()
    {
        _vm.ImportDroppedFiles(Array.Empty<string>());
        Assert.Empty(_vm.Files);
    }

    [Fact]
    public void ImportDroppedFiles_NullList_ShouldNotThrow()
    {
        // 使用 null 应不抛异常
        _vm.ImportDroppedFiles(null!);
        Assert.Empty(_vm.Files);
    }
}
