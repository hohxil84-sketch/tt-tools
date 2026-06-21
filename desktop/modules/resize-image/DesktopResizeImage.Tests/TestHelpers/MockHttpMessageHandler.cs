using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.Json;

namespace TTTools.ResizeImage.Tests.TestHelpers;

/// <summary>
/// 用于单元测试的 HTTP 消息处理器
/// 允许预设响应，避免测试依赖真实网络。
/// 用于模拟 CloudApiClient 的 /api/v1/entitlements/check 返回。
/// CloudApiClient.CheckEntitlementAsync 不是 virtual 方法，通过注入 HttpClient 进行测试（C2）。
/// </summary>
public class MockHttpMessageHandler : HttpMessageHandler
{
    private readonly Func<HttpRequestMessage, HttpResponseMessage> _handler;

    public MockHttpMessageHandler(Func<HttpRequestMessage, HttpResponseMessage> handler)
    {
        _handler = handler;
    }

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request, CancellationToken cancellationToken)
    {
        return Task.FromResult(_handler(request));
    }

    /// <summary>
    /// 创建返回 200 和指定 JSON body 的处理器。
    /// </summary>
    public static MockHttpMessageHandler CreateJsonResponse(object body)
    {
        var json = JsonSerializer.Serialize(body, new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
        });
        return new MockHttpMessageHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        });
    }

    /// <summary>
    /// 创建返回指定状态码的处理器。
    /// </summary>
    public static MockHttpMessageHandler CreateErrorResponse(
        HttpStatusCode statusCode = HttpStatusCode.InternalServerError)
    {
        return new MockHttpMessageHandler(_ =>
            new HttpResponseMessage(statusCode));
    }
}
