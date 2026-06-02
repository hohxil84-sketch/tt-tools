using TTShared.Auth;

namespace TTShared.Tests.Auth;

public class DeviceFingerprintTests
{
    [Fact]
    public void GetFingerprint_ShouldReturnNonEmpty()
    {
        var fingerprint = DeviceFingerprint.GetFingerprint();
        Assert.False(string.IsNullOrEmpty(fingerprint));
    }

    [Fact]
    public void GetFingerprint_ShouldReturnConsistentValue()
    {
        var fp1 = DeviceFingerprint.GetFingerprint();
        var fp2 = DeviceFingerprint.GetFingerprint();
        Assert.Equal(fp1, fp2);
    }

    [Fact]
    public void GetFingerprint_ShouldBeHexString()
    {
        var fingerprint = DeviceFingerprint.GetFingerprint();
        // SHA256 哈希应为 64 位十六进制字符串
        Assert.Equal(64, fingerprint.Length);
        Assert.Matches("^[a-f0-9]+$", fingerprint);
    }
}
