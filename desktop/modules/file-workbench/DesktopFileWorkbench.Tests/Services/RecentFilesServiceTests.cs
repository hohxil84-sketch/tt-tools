using TTTools.FileWorkbench.Services;

namespace TTTools.FileWorkbench.Tests.Services;

/// <summary>
/// RecentFilesService 单元测试
/// 测试最近文件记录的增删改查和持久化逻辑。
/// </summary>
public class RecentFilesServiceTests : IDisposable
{
    private readonly string _testStoragePath;

    public RecentFilesServiceTests()
    {
        _testStoragePath = Path.Combine(Path.GetTempPath(), $"tt_test_recent_{Guid.NewGuid():N}.json");
    }

    public void Dispose()
    {
        try { File.Delete(_testStoragePath); } catch { }
    }

    /// <summary>
    /// 创建测试用的临时文件并返回路径
    /// </summary>
    private static string CreateTestFile(string fileName = "test-file.jpg")
    {
        var path = Path.Combine(Path.GetTempPath(), $"tt_test_{Guid.NewGuid():N}_{fileName}");
        File.WriteAllText(path, "test content");
        return path;
    }

    [Fact]
    public void Constructor_ShouldCreateEmptyList()
    {
        var service = new RecentFilesService(_testStoragePath);
        Assert.Empty(service.Entries);
    }

    [Fact]
    public void RecordFile_ShouldAddToTopOfList()
    {
        var service = new RecentFilesService(_testStoragePath);
        var file1 = CreateTestFile("file1.jpg");
        var file2 = CreateTestFile("file2.png");

        try
        {
            service.RecordFile(file1);
            service.RecordFile(file2);

            Assert.Equal(2, service.Entries.Count);
            // file2 最后添加，应在列表顶部
            Assert.EndsWith("file2.png", service.Entries[0].FileName);
        }
        finally
        {
            File.Delete(file1);
            File.Delete(file2);
        }
    }

    [Fact]
    public void RecordFile_DuplicateFile_ShouldMoveToTop()
    {
        var service = new RecentFilesService(_testStoragePath);
        var file1 = CreateTestFile("file1.jpg");
        var file2 = CreateTestFile("file2.jpg");

        try
        {
            service.RecordFile(file1);
            service.RecordFile(file2);
            // 再次记录 file1，应移到顶部且不重复
            service.RecordFile(file1);

            Assert.Equal(2, service.Entries.Count);
            // file1 应在顶部
            Assert.EndsWith("file1.jpg", service.Entries[0].FileName);
            Assert.EndsWith("file2.jpg", service.Entries[1].FileName);
        }
        finally
        {
            File.Delete(file1);
            File.Delete(file2);
        }
    }

    [Fact]
    public void RecordFile_NonexistentFile_ShouldNotAdd()
    {
        var service = new RecentFilesService(_testStoragePath);
        var nonexistentPath = @"C:\nonexistent\test.jpg";

        service.RecordFile(nonexistentPath);

        Assert.Empty(service.Entries);
    }

    [Fact]
    public void RecordFile_ExceedsMaxCount_ShouldTrimOldest()
    {
        var service = new RecentFilesService(_testStoragePath, maxCount: 3);

        // 创建 5 个测试文件
        var files = new List<string>();
        try
        {
            for (var i = 0; i < 5; i++)
            {
                files.Add(CreateTestFile($"file{i}.jpg"));
            }

            foreach (var f in files)
                service.RecordFile(f);

            // 最多保留 3 条
            Assert.Equal(3, service.Entries.Count);
        }
        finally
        {
            foreach (var f in files) { try { File.Delete(f); } catch { } }
        }
    }

    [Fact]
    public void RemoveFile_ShouldRemoveSpecificEntry()
    {
        var service = new RecentFilesService(_testStoragePath);
        var file1 = CreateTestFile("file1.jpg");
        var file2 = CreateTestFile("file2.jpg");

        try
        {
            service.RecordFile(file1);
            service.RecordFile(file2);
            service.RemoveFile(file1);

            Assert.Single(service.Entries);
            Assert.EndsWith("file2.jpg", service.Entries[0].FileName);
        }
        finally
        {
            File.Delete(file1);
            File.Delete(file2);
        }
    }

    [Fact]
    public void Clear_ShouldRemoveAllEntries()
    {
        var service = new RecentFilesService(_testStoragePath);
        var file1 = CreateTestFile("file1.jpg");
        var file2 = CreateTestFile("file2.jpg");

        try
        {
            service.RecordFile(file1);
            service.RecordFile(file2);
            service.Clear();

            Assert.Empty(service.Entries);
        }
        finally
        {
            File.Delete(file1);
            File.Delete(file2);
        }
    }

    [Fact]
    public void GetExistingFiles_ShouldFilterDeletedFiles()
    {
        var service = new RecentFilesService(_testStoragePath);
        var file1 = CreateTestFile("file1.jpg");
        var file2 = CreateTestFile("file2.jpg");

        try
        {
            service.RecordFile(file1);
            service.RecordFile(file2);

            // 删除 file1
            File.Delete(file1);

            var existingFiles = service.GetExistingFiles();
            Assert.Single(existingFiles);
            Assert.EndsWith("file2.jpg", existingFiles[0].FileName);
        }
        finally
        {
            try { File.Delete(file1); } catch { }
            File.Delete(file2);
        }
    }

    [Fact]
    public void CleanInvalidEntries_ShouldRemoveDeletedFiles()
    {
        var service = new RecentFilesService(_testStoragePath);
        var file1 = CreateTestFile("file1.jpg");
        var file2 = CreateTestFile("file2.jpg");

        try
        {
            service.RecordFile(file1);
            service.RecordFile(file2);

            File.Delete(file1);
            service.CleanInvalidEntries();

            Assert.Single(service.Entries);
        }
        finally
        {
            try { File.Delete(file1); } catch { }
            File.Delete(file2);
        }
    }

    [Fact]
    public void RecordFile_ShouldTriggerRecentFilesChangedEvent()
    {
        var service = new RecentFilesService(_testStoragePath);
        var eventTriggered = false;
        service.RecentFilesChanged += (_, _) => eventTriggered = true;

        var file1 = CreateTestFile("file1.jpg");
        try
        {
            service.RecordFile(file1);
            Assert.True(eventTriggered);
        }
        finally
        {
            File.Delete(file1);
        }
    }

    [Fact]
    public void Persistence_ShouldSurviveNewInstance()
    {
        var file1 = CreateTestFile("file1.jpg");

        try
        {
            // 第一个实例保存数据
            var service1 = new RecentFilesService(_testStoragePath);
            service1.RecordFile(file1);

            // 第二个实例从文件加载数据
            var service2 = new RecentFilesService(_testStoragePath);
            Assert.Single(service2.Entries);
            Assert.EndsWith("file1.jpg", service2.Entries[0].FileName);
        }
        finally
        {
            File.Delete(file1);
        }
    }
}
