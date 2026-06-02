using TTShared.FileSystem;

namespace TTShared.Tests.FileSystem;

public class FileSystemServiceTests
{
    private readonly FileSystemService _fs = new();

    [Fact]
    public void GetTempDirectory_ShouldReturnValidPath()
    {
        var dir = _fs.GetTempDirectory();
        Assert.False(string.IsNullOrEmpty(dir));
        Assert.True(Directory.Exists(dir));
    }

    [Fact]
    public void CreateTempFilePath_ShouldReturnUniquePath()
    {
        var path1 = _fs.CreateTempFilePath(".png");
        var path2 = _fs.CreateTempFilePath(".png");

        Assert.NotEqual(path1, path2);
        Assert.EndsWith(".png", path1);
        Assert.EndsWith(".png", path2);
    }

    [Fact]
    public void CreateTempDirectory_ShouldCreateAndExist()
    {
        var dir = _fs.CreateTempDirectory();
        Assert.True(Directory.Exists(dir));

        // 清理
        _fs.SafeDeleteDirectory(dir);
    }

    [Fact]
    public void SafeDeleteFile_ShouldReturnFalse_WhenNotExists()
    {
        var result = _fs.SafeDeleteFile(@"C:\non_existent_file_12345.xyz");
        Assert.False(result);
    }

    [Fact]
    public void IsImageFile_ShouldRecognizeCommonFormats()
    {
        Assert.True(FileSystemService.IsImageFile("test.jpg"));
        Assert.True(FileSystemService.IsImageFile("test.PNG"));
        Assert.True(FileSystemService.IsImageFile("test.bmp"));
        Assert.False(FileSystemService.IsImageFile("test.pdf"));
        Assert.False(FileSystemService.IsImageFile("test.doc"));
    }

    [Fact]
    public void IsPdfFile_ShouldRecognizePdf()
    {
        Assert.True(FileSystemService.IsPdfFile("doc.pdf"));
        Assert.True(FileSystemService.IsPdfFile("doc.PDF"));
        Assert.False(FileSystemService.IsPdfFile("doc.jpg"));
    }

    [Fact]
    public void IsSupportedFile_ShouldRecognizeSupportedFormats()
    {
        Assert.True(FileSystemService.IsSupportedFile("test.jpg"));
        Assert.True(FileSystemService.IsSupportedFile("test.pdf"));
        Assert.True(FileSystemService.IsSupportedFile("test.psd"));
        Assert.True(FileSystemService.IsSupportedFile("test.svg"));
        Assert.False(FileSystemService.IsSupportedFile("test.exe"));
    }

    [Fact]
    public void GetExtension_ShouldReturnLowercase()
    {
        var ext = FileSystemService.GetExtension("TEST.PNG");
        Assert.Equal(".png", ext);
    }

    [Fact]
    public void GetFileSize_ShouldReturnSize_ForExistingFile()
    {
        var tempFile = _fs.CreateTempFilePath(".txt");
        File.WriteAllText(tempFile, "hello world");
        try
        {
            var size = FileSystemService.GetFileSize(tempFile);
            Assert.True(size > 0);
        }
        finally
        {
            _fs.SafeDeleteFile(tempFile);
        }
    }

    [Fact]
    public void GetFileSize_ShouldReturnNegative_ForNonExistentFile()
    {
        var size = FileSystemService.GetFileSize(@"C:\non_existent_file_12345.xyz");
        Assert.Equal(-1, size);
    }
}
