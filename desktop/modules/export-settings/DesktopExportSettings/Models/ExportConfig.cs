namespace TTTools.ExportSettings.Models;

/// <summary>
/// 导出配置模型
/// 定义导出目标格式、输出目录、质量等参数。
/// </summary>
public class ExportConfig
{
    /// <summary>导出目标格式：original / pdf / png / jpeg</summary>
    public string Format { get; set; } = "original";

    /// <summary>输出目录路径</summary>
    public string OutputDirectory { get; set; } = string.Empty;

    /// <summary>JPEG 质量（1-100），默认 90</summary>
    public int JpegQuality { get; set; } = 90;

    /// <summary>导出 DPI，0 表示保持原始</summary>
    public int Dpi { get; set; }

    /// <summary>是否覆盖已存在的文件</summary>
    public bool OverwriteExisting { get; set; }

    /// <summary>是否保留原始目录结构</summary>
    public bool PreserveDirectoryStructure { get; set; } = true;

    /// <summary>文件名前缀（可选）</summary>
    public string? FileNamePrefix { get; set; }

    /// <summary>支持的导出格式列表</summary>
    public static readonly Dictionary<string, string> SupportedFormats = new()
    {
        { "original", "原始格式（复制）" },
        { "pdf", "PDF 文档" },
        { "png", "PNG 图片" },
        { "jpeg", "JPEG 图片" }
    };
}
