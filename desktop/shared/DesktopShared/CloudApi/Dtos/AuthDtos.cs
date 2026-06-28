using System.Text.Json.Serialization;

namespace TTShared.CloudApi.Dtos;

// ============ Auth / Device DTOs（对应 OpenAPI auth-device.yaml）============

/// <summary>登录请求</summary>
public class LoginRequest
{
    [JsonPropertyName("account")]
    public string Account { get; set; } = string.Empty;

    [JsonPropertyName("password")]
    public string Password { get; set; } = string.Empty;

    [JsonPropertyName("device_fingerprint")]
    public string DeviceFingerprint { get; set; } = string.Empty;

    [JsonPropertyName("device_name")]
    public string? DeviceName { get; set; }

    [JsonPropertyName("client_version")]
    public string? ClientVersion { get; set; }
}

/// <summary>登录响应数据</summary>
public class LoginData
{
    [JsonPropertyName("access_token")]
    public string AccessToken { get; set; } = string.Empty;

    [JsonPropertyName("refresh_token")]
    public string RefreshToken { get; set; } = string.Empty;

    [JsonPropertyName("token_type")]
    public string TokenType { get; set; } = "bearer";

    [JsonPropertyName("expires_in")]
    public int ExpiresIn { get; set; }

    [JsonPropertyName("user")]
    public UserDto User { get; set; } = new();

    [JsonPropertyName("device")]
    public DeviceDto Device { get; set; } = new();
}

/// <summary>用户信息 DTO</summary>
public class UserDto
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("account")]
    public string Account { get; set; } = string.Empty;

    [JsonPropertyName("display_name")]
    public string? DisplayName { get; set; }

    [JsonPropertyName("plan_id")]
    public string PlanId { get; set; } = string.Empty;
}

/// <summary>设备信息 DTO</summary>
public class DeviceDto
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; set; } = "active";

    [JsonPropertyName("is_new")]
    public bool IsNew { get; set; }
}

/// <summary>刷新令牌请求</summary>
public class RefreshRequest
{
    [JsonPropertyName("refresh_token")]
    public string RefreshToken { get; set; } = string.Empty;
}

/// <summary>刷新令牌响应数据</summary>
public class RefreshData
{
    [JsonPropertyName("access_token")]
    public string AccessToken { get; set; } = string.Empty;

    [JsonPropertyName("refresh_token")]
    public string RefreshToken { get; set; } = string.Empty;

    [JsonPropertyName("token_type")]
    public string TokenType { get; set; } = "bearer";

    [JsonPropertyName("expires_in")]
    public int ExpiresIn { get; set; }
}

/// <summary>退出登录请求</summary>
public class LogoutRequest
{
    [JsonPropertyName("refresh_token")]
    public string RefreshToken { get; set; } = string.Empty;
}

/// <summary>当前设备信息</summary>
public class CurrentDeviceDto
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("device_fingerprint")]
    public string DeviceFingerprint { get; set; } = string.Empty;

    [JsonPropertyName("device_name")]
    public string DeviceName { get; set; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("bound_at")]
    public string? BoundAt { get; set; }

    [JsonPropertyName("last_seen_at")]
    public string? LastSeenAt { get; set; }
}

/// <summary>绑定设备请求</summary>
public class BindDeviceRequest
{
    [JsonPropertyName("device_fingerprint")]
    public string DeviceFingerprint { get; set; } = string.Empty;

    [JsonPropertyName("device_name")]
    public string? DeviceName { get; set; }

    [JsonPropertyName("client_version")]
    public string? ClientVersion { get; set; }
}
