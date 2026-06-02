using TTShared.CloudApi;

namespace TTShared.Tests.CloudApi;

public class CloudApiExceptionTests
{
    [Fact]
    public void Constructor_ShouldSetProperties()
    {
        var ex = new CloudApiException("rate_limit", "请求频率过高", "req_001");

        Assert.Equal("rate_limit", ex.ErrorCode);
        Assert.Equal("请求频率过高", ex.Message);
        Assert.Equal("req_001", ex.RequestId);
    }

    [Fact]
    public void Constructor_WithInnerException_ShouldSetAllProperties()
    {
        var inner = new InvalidOperationException("网络超时");
        var ex = new CloudApiException("network_error", "网络请求失败", "req_002", inner);

        Assert.Equal("network_error", ex.ErrorCode);
        Assert.Same(inner, ex.InnerException);
    }
}
