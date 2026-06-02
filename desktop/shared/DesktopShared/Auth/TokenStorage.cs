using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace TTShared.Auth;

/// <summary>
/// 令牌安全存储
/// 使用 Windows DPAPI (Data Protection API) 加密存储 access_token 和 refresh_token。
/// 令牌存储在用户本地应用数据目录，仅当前 Windows 用户可解密。
/// </summary>
public class TokenStorage
{
    private readonly string _tokenFilePath;
    private static readonly byte[] EntropyToken = Encoding.UTF8.GetBytes("TTTools.TokenStorage.v1");

    /// <summary>
    /// 令牌文件数据结构
    /// </summary>
    private class TokenFile
    {
        public string EncryptedAccessToken { get; set; } = string.Empty;
        public string EncryptedRefreshToken { get; set; } = string.Empty;
    }

    public TokenStorage() : this(
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "TTTools", "auth", "tokens.dat"))
    { }

    public TokenStorage(string tokenFilePath)
    {
        _tokenFilePath = tokenFilePath;
    }

    /// <summary>
    /// 加密并保存令牌到本地文件
    /// </summary>
    public void SaveTokens(string accessToken, string refreshToken)
    {
        try
        {
            var dir = Path.GetDirectoryName(_tokenFilePath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }

            var tokenFile = new TokenFile
            {
                EncryptedAccessToken = Encrypt(accessToken),
                EncryptedRefreshToken = Encrypt(refreshToken)
            };

            var json = JsonSerializer.Serialize(tokenFile);
            File.WriteAllText(_tokenFilePath, json);
        }
        catch (Exception)
        {
            // 静默失败：令牌保存失败不应阻止登录流程，仅影响持久化
        }
    }

    /// <summary>
    /// 从本地文件加载并解密令牌
    /// </summary>
    /// <returns>(accessToken, refreshToken) 元组，失败时返回空字符串</returns>
    public (string accessToken, string refreshToken) LoadTokens()
    {
        try
        {
            if (!File.Exists(_tokenFilePath))
            {
                return (string.Empty, string.Empty);
            }

            var json = File.ReadAllText(_tokenFilePath);
            var tokenFile = JsonSerializer.Deserialize<TokenFile>(json);

            if (tokenFile == null)
            {
                return (string.Empty, string.Empty);
            }

            return (
                Decrypt(tokenFile.EncryptedAccessToken),
                Decrypt(tokenFile.EncryptedRefreshToken)
            );
        }
        catch (Exception)
        {
            return (string.Empty, string.Empty);
        }
    }

    /// <summary>
    /// 清除已保存的令牌
    /// </summary>
    public void ClearTokens()
    {
        try
        {
            if (File.Exists(_tokenFilePath))
            {
                File.Delete(_tokenFilePath);
            }
        }
        catch (Exception)
        {
            // 静默失败
        }
    }

    /// <summary>
    /// 使用 Windows DPAPI 加密字符串
    /// </summary>
    private static string Encrypt(string plainText)
    {
        if (string.IsNullOrEmpty(plainText)) return string.Empty;

        var plainBytes = Encoding.UTF8.GetBytes(plainText);
        var encryptedBytes = ProtectedData.Protect(plainBytes, EntropyToken,
            DataProtectionScope.CurrentUser);
        return Convert.ToBase64String(encryptedBytes);
    }

    /// <summary>
    /// 使用 Windows DPAPI 解密字符串
    /// </summary>
    private static string Decrypt(string encryptedText)
    {
        if (string.IsNullOrEmpty(encryptedText)) return string.Empty;

        var encryptedBytes = Convert.FromBase64String(encryptedText);
        var plainBytes = ProtectedData.Unprotect(encryptedBytes, EntropyToken,
            DataProtectionScope.CurrentUser);
        return Encoding.UTF8.GetString(plainBytes);
    }
}
