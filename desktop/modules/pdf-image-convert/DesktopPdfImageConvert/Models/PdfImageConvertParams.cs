using System.Text.Json.Serialization;

namespace TTTools.PdfImageConvert.Models;

/// <summary>
/// PDF/图片互转参数（C# 侧，对应 Python ConvertParams dataclass）
/// 序列化时字段名保持 camelCase 以匹配 Python 侧 JSON 协议。
/// 桌面端不决定套装权限、额度扣费和模型选择。
/// </summary>
public class PdfImageConvertParams
{
    /// <summary>转换方向: pdf_to_images / images_to_pdf</summary>
    [JsonPropertyName("direction")]
    public string Direction { get; set; } = "pdf_to_images";

    /// <summary>输出格式: png / jpeg（仅 PDF→图片时生效）</summary>
    [JsonPropertyName("output_format")]
    public string OutputFormat { get; set; } = "png";

    /// <summary>PDF 渲染 DPI（72-600），默认 200</summary>
    [JsonPropertyName("dpi")]
    public int Dpi { get; set; } = 200;

    /// <summary>JPEG 输出质量（1-100），默认 92</summary>
    [JsonPropertyName("jpeg_quality")]
    public int JpegQuality { get; set; } = 92;

    /// <summary>PDF 转图片时的页码范围（1-based），[start, end] 包含两端。null 表示全部页面</summary>
    [JsonPropertyName("page_range")]
    public List<int>? PageRange { get; set; }

    /// <summary>最多转换页数，null 表示不限制</summary>
    [JsonPropertyName("page_limit")]
    public int? PageLimit { get; set; }

    /// <summary>输出文件路径（可选），PDF→图片时为输出目录，图片→PDF 时为输出 pdf 文件路径</summary>
    [JsonPropertyName("output_path")]
    public string? OutputPath { get; set; }
}
