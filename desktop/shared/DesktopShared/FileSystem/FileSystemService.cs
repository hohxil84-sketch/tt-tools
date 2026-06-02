namespace TTShared.FileSystem;

/// <summary>
/// 文件系统服务
/// 提供安全的文件操作、临时文件管理、文件类型检测等基础能力。
/// 本地免费任务默认不上传原文件到云端。
/// </summary>
public class FileSystemService
{
    private readonly string _baseTempDir;

    /// <summary>支持的图片文件扩展名</summary>
    public static readonly HashSet<string> ImageExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp", ".ico"
    };

    /// <summary>支持的 PDF 扩展名</summary>
    public static readonly HashSet<string> PdfExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".pdf"
    };

    /// <summary>支持的所有可处理文件扩展名</summary>
    public static readonly HashSet<string> AllSupportedExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp", ".ico",
        ".pdf",
        ".psd", ".ai", ".eps", ".svg",
        ".cdr"
    };

    public FileSystemService() : this(
        Path.Combine(Path.GetTempPath(), "TTTools"))
    { }

    public FileSystemService(string baseTempDir)
    {
        _baseTempDir = baseTempDir;
        EnsureDirectory(_baseTempDir);
    }

    /// <summary>
    /// 获取临时文件目录
    /// </summary>
    public string GetTempDirectory()
    {
        EnsureDirectory(_baseTempDir);
        return _baseTempDir;
    }

    /// <summary>
    /// 创建临时文件路径
    /// </summary>
    public string CreateTempFilePath(string extension)
    {
        EnsureDirectory(_baseTempDir);
        var fileName = $"tt_{Guid.NewGuid():N}{EnsureDotPrefix(extension)}";
        return Path.Combine(_baseTempDir, fileName);
    }

    /// <summary>
    /// 创建临时目录
    /// </summary>
    public string CreateTempDirectory()
    {
        var dir = Path.Combine(_baseTempDir, $"tt_{Guid.NewGuid():N}");
        Directory.CreateDirectory(dir);
        return dir;
    }

    /// <summary>
    /// 安全删除文件（不存在时不抛异常）
    /// </summary>
    public bool SafeDeleteFile(string path)
    {
        try
        {
            if (File.Exists(path))
            {
                File.Delete(path);
                return true;
            }
            return false;
        }
        catch
        {
            return false;
        }
    }

    /// <summary>
    /// 安全删除目录（递归，不存在时不抛异常）
    /// </summary>
    public bool SafeDeleteDirectory(string path)
    {
        try
        {
            if (Directory.Exists(path))
            {
                Directory.Delete(path, recursive: true);
                return true;
            }
            return false;
        }
        catch
        {
            return false;
        }
    }

    /// <summary>
    /// 获取文件扩展名（含点号，小写）
    /// </summary>
    public static string GetExtension(string filePath)
        => Path.GetExtension(filePath).ToLowerInvariant();

    /// <summary>
    /// 判断是否为支持的图片文件
    /// </summary>
    public static bool IsImageFile(string filePath)
        => ImageExtensions.Contains(GetExtension(filePath));

    /// <summary>
    /// 判断是否为 PDF 文件
    /// </summary>
    public static bool IsPdfFile(string filePath)
        => PdfExtensions.Contains(GetExtension(filePath));

    /// <summary>
    /// 判断文件是否为支持处理的类型
    /// </summary>
    public static bool IsSupportedFile(string filePath)
        => AllSupportedExtensions.Contains(GetExtension(filePath));

    /// <summary>
    /// 获取文件大小（字节），失败返回 -1
    /// </summary>
    public static long GetFileSize(string path)
    {
        try
        {
            return new FileInfo(path).Length;
        }
        catch
        {
            return -1;
        }
    }

    /// <summary>
    /// 清理临时目录中的所有文件
    /// </summary>
    public void CleanTempFiles()
    {
        try
        {
            if (Directory.Exists(_baseTempDir))
            {
                foreach (var file in Directory.GetFiles(_baseTempDir, "*.*",
                    SearchOption.AllDirectories))
                {
                    try { File.Delete(file); } catch { /* 跳过锁定文件 */ }
                }
            }
        }
        catch
        {
            // 静默失败：临时文件清理不应影响主流程
        }
    }

    /// <summary>
    /// 确保目录存在
    /// </summary>
    private static void EnsureDirectory(string path)
    {
        if (!Directory.Exists(path))
            Directory.CreateDirectory(path);
    }

    /// <summary>
    /// 确保扩展名以点号开头
    /// </summary>
    private static string EnsureDotPrefix(string extension)
        => extension.StartsWith('.') ? extension : $".{extension}";
}
