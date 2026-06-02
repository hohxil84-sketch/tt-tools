using System.Security.Cryptography;
using System.Text;

namespace TTShared.Auth;

/// <summary>
/// 设备指纹生成器
/// 基于机器特征生成唯一设备标识，用于云端设备绑定和鉴权。
/// 使用 MachineGuid + 机器名 + 用户名组合生成确定性指纹。
/// </summary>
public static class DeviceFingerprint
{
    /// <summary>
    /// 获取当前设备的指纹哈希
    /// </summary>
    /// <returns>设备指纹 SHA256 哈希字符串</returns>
    public static string GetFingerprint()
    {
        // 组合机器标识：Windows MachineGuid + 机器名 + 用户名
        var machineGuid = GetMachineGuid();
        var machineName = Environment.MachineName;
        var userName = Environment.UserName;

        var raw = $"{machineGuid}|{machineName}|{userName}";
        var hashBytes = SHA256.HashData(Encoding.UTF8.GetBytes(raw));
        return Convert.ToHexString(hashBytes).ToLowerInvariant();
    }

    /// <summary>
    /// 获取 Windows 注册表中的 MachineGuid
    /// </summary>
    private static string GetMachineGuid()
    {
        try
        {
            using var key = Microsoft.Win32.Registry.LocalMachine
                .OpenSubKey(@"SOFTWARE\Microsoft\Cryptography");
            return key?.GetValue("MachineGuid")?.ToString() ?? Environment.MachineName;
        }
        catch
        {
            return Environment.MachineName;
        }
    }
}
