using TTTools.FileWorkbench.Models;
using TTTools.FileWorkbench.ViewModels;

namespace TTTools.FileWorkbench.Tests.ViewModels;

/// <summary>
/// FileItemViewModel 单元测试
/// 测试单个文件项的 ViewModel 绑定属性和选中逻辑。
/// </summary>
public class FileItemViewModelTests
{
    /// <summary>
    /// 创建测试用临时图片文件
    /// </summary>
    private static string CreateTestImageFile()
    {
        var path = Path.Combine(Path.GetTempPath(), $"tt_test_{Guid.NewGuid():N}.jpg");
        File.WriteAllText(path, "test image content");
        return path;
    }

    [Fact]
    public void Constructor_ShouldPopulatePropertiesFromFileItem()
    {
        var filePath = CreateTestImageFile();
        try
        {
            var fileItem = FileItem.FromPath(filePath);
            var vm = new FileItemViewModel(fileItem);

            Assert.Equal(filePath, vm.FilePath);
            Assert.Equal(Path.GetFileName(filePath), vm.FileName);
            Assert.True(vm.IsSupported);
            Assert.True(vm.IsImage);
            Assert.False(vm.IsPdf);
            Assert.False(vm.IsSelected);
        }
        finally
        {
            File.Delete(filePath);
        }
    }

    [Fact]
    public void IsSelected_ShouldToggleAndNotify()
    {
        var filePath = CreateTestImageFile();
        try
        {
            var fileItem = FileItem.FromPath(filePath);
            var vm = new FileItemViewModel(fileItem);

            var propertyChanged = false;
            vm.PropertyChanged += (_, e) =>
            {
                if (e.PropertyName == nameof(FileItemViewModel.IsSelected))
                    propertyChanged = true;
            };

            vm.IsSelected = true;
            Assert.True(vm.IsSelected);
            Assert.True(propertyChanged);
            Assert.True(fileItem.IsSelected); // 同步到模型
        }
        finally
        {
            File.Delete(filePath);
        }
    }

    [Fact]
    public void ToggleSelectCommand_ShouldToggleSelection()
    {
        var filePath = CreateTestImageFile();
        try
        {
            var fileItem = FileItem.FromPath(filePath);
            var vm = new FileItemViewModel(fileItem);

            vm.ToggleSelectCommand.Execute(null);
            Assert.True(vm.IsSelected);

            vm.ToggleSelectCommand.Execute(null);
            Assert.False(vm.IsSelected);
        }
        finally
        {
            File.Delete(filePath);
        }
    }

    [Fact]
    public void ToggleSelect_ShouldTriggerSelectionChanged()
    {
        var filePath = CreateTestImageFile();
        try
        {
            var fileItem = FileItem.FromPath(filePath);
            var vm = new FileItemViewModel(fileItem);

            FileItemViewModel? received = null;
            vm.SelectionChanged += (_, e) => received = e;

            vm.ToggleSelectCommand.Execute(null);
            Assert.NotNull(received);
            Assert.Same(vm, received);
        }
        finally
        {
            File.Delete(filePath);
        }
    }

    [Fact]
    public void IsImage_ShouldReturnTrueForImageFiles()
    {
        var filePath = CreateTestImageFile();
        try
        {
            var fileItem = FileItem.FromPath(filePath);
            var vm = new FileItemViewModel(fileItem);
            Assert.True(vm.IsImage);
            Assert.Equal("🖼", vm.FileTypeIcon);
        }
        finally
        {
            File.Delete(filePath);
        }
    }

    [Fact]
    public void PdfFile_ShouldHaveCorrectProperties()
    {
        var filePath = Path.Combine(Path.GetTempPath(), $"tt_test_{Guid.NewGuid():N}.pdf");
        File.WriteAllText(filePath, "test pdf content");
        try
        {
            var fileItem = FileItem.FromPath(filePath);
            var vm = new FileItemViewModel(fileItem);
            Assert.False(vm.IsImage);
            Assert.True(vm.IsPdf);
            Assert.Equal("📄", vm.FileTypeIcon);
        }
        finally
        {
            File.Delete(filePath);
        }
    }

    [Fact]
    public void UnsupportedFile_ShouldHaveWarningStatus()
    {
        var filePath = Path.Combine(Path.GetTempPath(), $"tt_test_{Guid.NewGuid():N}.xyz");
        File.WriteAllText(filePath, "test unsupported content");
        try
        {
            var fileItem = FileItem.FromPath(filePath);
            var vm = new FileItemViewModel(fileItem);
            Assert.False(vm.IsSupported);
            Assert.Equal("格式不支持", vm.StatusText);
            Assert.Equal("📁", vm.FileTypeIcon);
        }
        finally
        {
            File.Delete(filePath);
        }
    }

    [Fact]
    public void Constructor_NullFileItem_ShouldThrow()
    {
        Assert.Throws<ArgumentNullException>(() => new FileItemViewModel(null!));
    }
}
