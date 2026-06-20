namespace TTTools.FileWorkbench.Models;

/// <summary>
/// 文件工作台中的文件项数据模型
/// 记录文件的路径、名称、类型、大小等元信息。
/// </summary>
public class FileItem
{
    /// <summary>文件完整路径</summary>
    public string FilePath { get; set; } = string.Empty;

    /// <summary>文件名（含扩展名）</summary>
    public string FileName => Path.GetFileName(FilePath);

    /// <summary>文件扩展名（小写，含点号）</summary>
    public string Extension { get; set; } = string.Empty;

    /// <summary>文件大小（字节），-1 表示未知</summary>
    public long SizeBytes { get; set; }

    /// <summary>文件大小的人类可读格式</summary>
    public string SizeDisplay => FormatFileSize(SizeBytes);

    /// <summary>MIME 类型推断</summary>
    public string MimeType { get; set; } = string.Empty;

    /// <summary>文件导入时间</summary>
    public DateTime ImportedAt { get; set; } = DateTime.Now;

    /// <summary>是否为支持的图片文件</summary>
    public bool IsImage { get; set; }

    /// <summary>是否为 PDF 文件</summary>
    public bool IsPdf { get; set; }

    /// <summary>导入时是否通过了格式检查</summary>
    public bool IsSupported { get; set; }

    /// <summary>文件当前是否被选中</summary>
    public bool IsSelected { get; set; }

    /// <summary>
    /// 从文件路径创建 FileItem，自动填充元信息
    /// </summary>
    /// <param name="filePath">文件完整路径</param>
    /// <returns>填充好元信息的 FileItem</returns>
    public static FileItem FromPath(string filePath)
    {
        var ext = Path.GetExtension(filePath).ToLowerInvariant();
        var size = GetSafeFileSize(filePath);

        return new FileItem
        {
            FilePath = filePath,
            Extension = ext,
            SizeBytes = size,
            MimeType = GetMimeType(ext),
            ImportedAt = DateTime.Now,
            IsImage = TTShared.FileSystem.FileSystemService.IsImageFile(filePath),
            IsPdf = TTShared.FileSystem.FileSystemService.IsPdfFile(filePath),
            IsSupported = TTShared.FileSystem.FileSystemService.IsSupportedFile(filePath)
        };
    }

    /// <summary>
    /// 安全获取文件大小，失败返回 -1
    /// </summary>
    private static long GetSafeFileSize(string path)
    {
        try
        {
            var info = new FileInfo(path);
            return info.Exists ? info.Length : -1;
        }
        catch
        {
            return -1;
        }
    }

    /// <summary>
    /// 根据扩展名推断 MIME 类型
    /// </summary>
    private static string GetMimeType(string extension) => extension switch
    {
        ".jpg" or ".jpeg" => "image/jpeg",
        ".png" => "image/png",
        ".bmp" => "image/bmp",
        ".gif" => "image/gif",
        ".tiff" or ".tif" => "image/tiff",
        ".webp" => "image/webp",
        ".ico" => "image/x-icon",
        ".pdf" => "application/pdf",
        ".psd" => "image/vnd.adobe.photoshop",
        ".ai" => "application/postscript",
        ".eps" => "application/postscript",
        ".svg" => "image/svg+xml",
        ".cdr" => "application/x-cdr",
        _ => "application/octet-stream"
    };

    /// <summary>
    /// 格式化文件大小为人类可读字符串
    /// </summary>
    private static string FormatFileSize(long bytes)
    {
        if (bytes < 0) return "未知大小";
        if (bytes < 1024) return $"{bytes} B";
        if (bytes < 1024 * 1024) return $"{bytes / 1024.0:F1} KB";
        if (bytes < 1024 * 1024 * 1024) return $"{bytes / (1024.0 * 1024.0):F1} MB";
        return $"{bytes / (1024.0 * 1024.0 * 1024.0):F2} GB";
    }
}
