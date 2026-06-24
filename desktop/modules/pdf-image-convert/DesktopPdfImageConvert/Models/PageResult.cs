namespace TTTools.PdfImageConvert.Models;

/// <summary>
/// 单页/单图转换结果（对应 Python PageImageResult dataclass）
/// </summary>
public class PageResult
{
    /// <summary>页码（1-based），PDF→图片时表示原始页码，图片→PDF 时表示插入序号</summary>
    public int PageNumber { get; set; }

    /// <summary>图片宽度（像素）</summary>
    public int Width { get; set; }

    /// <summary>图片高度（像素）</summary>
    public int Height { get; set; }

    /// <summary>图片格式，如 "png"、"jpeg"、PDF 页面为 "pdf_page"</summary>
    public string Format { get; set; } = string.Empty;

    /// <summary>图片字节大小</summary>
    public int SizeBytes { get; set; }
}
