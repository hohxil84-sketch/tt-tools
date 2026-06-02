using TTShared.Auth;

namespace TTShared.Tests.Auth;

public class TokenStorageTests
{
    [Fact]
    public void SaveAndLoadTokens_ShouldRoundTrip()
    {
        var tempFile = Path.Combine(Path.GetTempPath(), $"tt_test_tokens_{Guid.NewGuid():N}.dat");
        var storage = new TokenStorage(tempFile);

        try
        {
            storage.SaveTokens("access_abc", "refresh_xyz");
            var (access, refresh) = storage.LoadTokens();

            Assert.Equal("access_abc", access);
            Assert.Equal("refresh_xyz", refresh);
        }
        finally
        {
            SafeDelete(tempFile);
        }
    }

    [Fact]
    public void LoadTokens_ShouldReturnEmpty_WhenFileNotExists()
    {
        var tempFile = Path.Combine(Path.GetTempPath(), $"tt_test_tokens_nonexist_{Guid.NewGuid():N}.dat");
        var storage = new TokenStorage(tempFile);

        var (access, refresh) = storage.LoadTokens();

        Assert.Equal(string.Empty, access);
        Assert.Equal(string.Empty, refresh);
    }

    [Fact]
    public void ClearTokens_ShouldRemoveFile()
    {
        var tempFile = Path.Combine(Path.GetTempPath(), $"tt_test_tokens_clear_{Guid.NewGuid():N}.dat");
        var storage = new TokenStorage(tempFile);

        try
        {
            storage.SaveTokens("access", "refresh");
            Assert.True(File.Exists(tempFile));

            storage.ClearTokens();
            Assert.False(File.Exists(tempFile));
        }
        finally
        {
            SafeDelete(tempFile);
        }
    }

    private static void SafeDelete(string path)
    {
        try { File.Delete(path); } catch { }
    }
}
