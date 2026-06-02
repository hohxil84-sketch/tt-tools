using System.Text.Json;
using TTShared.CloudApi.Dtos;

namespace TTShared.Tests.CloudApi;

public class DtoTests
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    [Fact]
    public void ApiResponse_ShouldDeserialize_LoginData()
    {
        var json = @"{
            ""success"": true,
            ""data"": {
                ""access_token"": ""at_123"",
                ""refresh_token"": ""rt_456"",
                ""token_type"": ""bearer"",
                ""expires_in"": 1800,
                ""user"": { ""id"": ""u1"", ""account"": ""test@test.com"", ""plan_code"": ""standard"" },
                ""device"": { ""id"": ""d1"", ""status"": ""active"", ""is_new"": true }
            },
            ""error"": null,
            ""request_id"": ""req_001""
        }";

        var response = JsonSerializer.Deserialize<ApiResponse<LoginData>>(json, JsonOptions);

        Assert.NotNull(response);
        Assert.True(response!.Success);
        Assert.Equal("req_001", response.RequestId);
        Assert.NotNull(response.Data);
        Assert.Equal("at_123", response.Data!.AccessToken);
        Assert.Equal("rt_456", response.Data.RefreshToken);
        Assert.Equal(1800, response.Data.ExpiresIn);
        Assert.Equal("u1", response.Data.User.Id);
        Assert.Equal("d1", response.Data.Device.Id);
    }

    [Fact]
    public void ApiResponse_ShouldDeserialize_Error()
    {
        var json = @"{
            ""success"": false,
            ""data"": null,
            ""error"": { ""code"": ""invalid_credentials"", ""message"": ""账号或密码错误"" },
            ""request_id"": ""req_002""
        }";

        var response = JsonSerializer.Deserialize<ApiResponse<LoginData>>(json, JsonOptions);

        Assert.NotNull(response);
        Assert.False(response!.Success);
        Assert.False(response.IsSuccess);
        Assert.NotNull(response.Error);
        Assert.Equal("invalid_credentials", response.Error!.Code);
        Assert.Equal("账号或密码错误", response.Error.Message);
    }

    [Fact]
    public void LoginRequest_ShouldSerializeCorrectly()
    {
        var request = new LoginRequest
        {
            Account = "test@example.com",
            Password = "secret",
            DeviceFingerprint = "fp_abc123",
            DeviceName = "DESKTOP-01",
            ClientVersion = "0.1.0"
        };

        var json = JsonSerializer.Serialize(request, JsonOptions);
        Assert.Contains("\"account\":\"test@example.com\"", json);
        Assert.Contains("\"device_fingerprint\":\"fp_abc123\"", json);
    }

    [Fact]
    public void EntitlementCheckRequest_ShouldSerializeCorrectly()
    {
        var request = new EntitlementCheckRequest
        {
            Feature = "resize_image_local_paid",
            Operation = "single",
            ClientRequestId = "req_xyz"
        };

        var json = JsonSerializer.Serialize(request, JsonOptions);
        Assert.Contains("\"feature\":\"resize_image_local_paid\"", json);
        Assert.Contains("\"client_request_id\":\"req_xyz\"", json);
    }

    [Fact]
    public void AiCopyGenerateRequest_ShouldSerializeCorrectly()
    {
        var request = new AiCopyGenerateRequest
        {
            Scene = "poster",
            ProductName = "测试产品",
            SellingPoints = new List<string> { "高速", "高清" },
            Tone = "direct",
            ClientRequestId = "copy_001"
        };

        var json = JsonSerializer.Serialize(request, JsonOptions);
        Assert.Contains("\"scene\":\"poster\"", json);
        // JSON 序列化器默认转义非 ASCII 字符（中文），此处检查 snake_case 字段名存在即可
        Assert.Contains("\"selling_points\":", json);
        Assert.Contains("\"client_request_id\":\"copy_001\"", json);
    }

    [Fact]
    public void PaginatedData_ShouldDeserializeCorrectly()
    {
        var json = @"{
            ""items"": [],
            ""total"": 0,
            ""limit"": 50,
            ""offset"": 0
        }";

        var data = JsonSerializer.Deserialize<PaginatedData<CreditLedgerItemDto>>(json, JsonOptions);
        Assert.NotNull(data);
        Assert.Equal(0, data!.Total);
        Assert.Equal(50, data.Limit);
    }
}
