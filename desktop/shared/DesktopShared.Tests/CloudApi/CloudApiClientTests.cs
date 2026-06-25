using System.Net;
using TTShared.Auth;
using TTShared.CloudApi;
using TTShared.CloudApi.Dtos;

namespace TTShared.Tests.CloudApi;

public class CloudApiClientTests
{
    [Fact]
    public async Task LoginAsync_ErrorStatusWithApiResponse_ShouldReturnBackendError()
    {
        var body = """
        {
          "success": false,
          "data": null,
          "error": {
            "code": "UNKNOWN_ERROR",
            "message": "服务内部异常"
          },
          "request_id": "req_backend"
        }
        """;
        var client = CreateClient(HttpStatusCode.InternalServerError, body);

        var result = await client.LoginAsync("admin@tttools.com", "admin123", "test-device");

        Assert.NotNull(result);
        Assert.False(result!.Success);
        Assert.Equal("UNKNOWN_ERROR", result.Error?.Code);
        Assert.Equal("服务内部异常", result.Error?.Message);
        Assert.Equal("req_backend", result.RequestId);
    }

    [Fact]
    public async Task LoginAsync_ErrorStatusWithoutBody_ShouldReturnHttpError()
    {
        var client = CreateClient(HttpStatusCode.BadGateway, "");

        var result = await client.LoginAsync("admin@tttools.com", "admin123", "test-device");

        Assert.NotNull(result);
        Assert.False(result!.Success);
        Assert.Equal("http_error", result.Error?.Code);
        Assert.Contains("502", result.Error?.Message);
    }

    [Fact]
    public async Task LoginAsync_ErrorStatusWithNonJsonBody_ShouldReturnHttpError()
    {
        var client = CreateClient(HttpStatusCode.InternalServerError, "<html>error</html>");

        var result = await client.LoginAsync("admin@tttools.com", "admin123", "test-device");

        Assert.NotNull(result);
        Assert.False(result!.Success);
        Assert.Equal("http_error", result.Error?.Code);
        Assert.Contains("500", result.Error?.Message);
    }

    private static CloudApiClient CreateClient(HttpStatusCode statusCode, string body)
    {
        var handler = new StaticResponseHandler(statusCode, body);
        var httpClient = new HttpClient(handler) { BaseAddress = new Uri("http://test.local") };
        return new CloudApiClient(httpClient, new AuthState());
    }

    private sealed class StaticResponseHandler : HttpMessageHandler
    {
        private readonly HttpStatusCode _statusCode;
        private readonly string _body;

        public StaticResponseHandler(HttpStatusCode statusCode, string body)
        {
            _statusCode = statusCode;
            _body = body;
        }

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            return Task.FromResult(new HttpResponseMessage(_statusCode)
            {
                Content = new StringContent(_body, Encoding.UTF8, "application/json")
            });
        }
    }
}
